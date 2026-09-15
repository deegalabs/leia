"""Public JSON for the citizen app and the registry adapter. Included from main.py.

GET /api/t/{hash}: the same data the service renders in /t/{hash}, as JSON and without the answer key, plus
``etapas`` (the 14 workflow steps with state and time) and up to 60 pipeline events. When the task came from
the external "Resumo estruturado" flow (only ``resumo_estruturado.json`` in the workspace), the summary and the
topics are built from it and the journey has no questions (``sem_perguntas``).
GET /api/t/{hash}/inferencias: what the workflow tagged over the original text; during ``criada``/``processando``
it answers with ``parcial: true`` and the classes produced so far (files T1..T5), so the waiting screen can show
the document being marked.
is_gated(): lawyer review gate; while a lawyer's task is ``pronta`` the public routes hide the explanation.
POST /api/t/{hash}/duvida: a doubt for the lawyer who sent the document (409 when nobody did).
POST /api/t/{hash}/vincular: links the signed-in citizen to the task (Bearer, papel cidadao).
stamp_attempt(): OpenTimestamps proof of an approved attempt, stored in the task workspace.
get_attempt(): adapter used by leia.registry (receipt and public verification).
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

import core.tentativas as tn
import core.workspace as ws
from app_gestao import _ler_artefato, _ler_json
from core.auth import usuario_api
from core.db import Duvida, Tarefa, Tentativa, Usuario, engine, get_session
from leia.ratelimit import rate_limit
from leia.registry import build_payload, ots_digest, ots_stamp, payload_hash

READY_STATUSES = ("pronta", "enviada", "assinada")
GATE_MESSAGE = "Em revisão pelo advogado"
PUBLIC_EVENT_TYPES = {"criada", "pdf_salvo", "pipeline_start", "texto_extraido", "task_start", "task_done", "task_error",
                      "erro_extracao", "pipeline_done", "tentativa", "carimbo_publico", "duvida_enviada", "reprocessar",
                      "aprovada",
                      # external "Resumo estruturado" flow (core/api.py): job progress, no personal data
                      "resumo_estruturado_start", "resumo_estruturado_job", "resumo_estruturado_status",
                      "resumo_estruturado_done", "resumo_estruturado_erro"}
PUBLIC_EVENT_LIMIT = 60

# The 14 workflow tasks of protocolo_pdf.json (ids as written there) with the pt-BR names of docs/API-V3-CONTRACT.md.
STEP_NAMES: dict[str, str] = {
    "T1_IDENTIFICADOR_PARTES": "Identificar as partes",
    "T2_IDENTIFICADOR_DATAS_VALORES": "Datas e valores",
    "T3_IDENTIFICADOR_FATOS": "Fatos",
    "T4_IDENTIFICADOR_FUNDAMENTOS": "Fundamentos, leis e decisões",
    "T5_IDENTIFICADOR_PEDIDOS": "Pedidos",
    "T6_FUSAO_MEMORIA": "Juntar a memória",
    "T7_SINTESE_FATOS": "Resumir os fatos",
    "T8_SINTESE_FUNDAMENTOS": "Resumir os fundamentos",
    "T9_SINTESE_PEDIDOS": "Resumir os pedidos",
    "T10_SINTESE_IDENTIFICACAO": "Quem é quem",
    "T11_SINTESE_CONTEXTO": "Contexto do processo",
    "T12_PROCESSAMENTO": "Marcar o texto",
    "T13_HUMANIZACAO": "Explicar em linguagem simples",
    "T14_QUESTOES": "Preparar as perguntas",
}
FRAGMENT_FILES = ["T1_IDENTIFICADOR_PARTES.json", "T2_IDENTIFICADOR_DATAS_VALORES.json", "T3_IDENTIFICADOR_FATOS.json",
                  "T4_IDENTIFICADOR_FUNDAMENTOS.json", "T5_IDENTIFICADOR_PEDIDOS.json"]
EXTERNAL_RESULT_FILE = "resumo_estruturado.json"
EXTERNAL_TEXT_FILE = "resumo_estruturado_texto.txt"


def public_events(events: list[dict[str, Any]], limit: int = PUBLIC_EVENT_LIMIT) -> list[dict[str, Any]]:
    """Pipeline events only, without the visitor's IP or user agent; the last ``limit`` ones."""
    out = [{k: v for k, v in e.items() if k not in ("ip", "ua", "user_agent", "advogado_id", "usuario_id")} for e in events if e.get("tipo") in PUBLIC_EVENT_TYPES]
    return out[-limit:]


def is_external_flow(events: list[dict[str, Any]], workspace_dir: Optional[Path]) -> bool:
    """True when the task went through the external "Resumo estruturado" API instead of the local workflow."""
    if any(str(e.get("tipo", "")).startswith("resumo_estruturado") for e in events):
        return True
    return bool(workspace_dir) and (Path(workspace_dir) / EXTERNAL_RESULT_FILE).exists()


def build_steps(events: list[dict[str, Any]], workspace_dir: Optional[Path] = None) -> list[dict[str, Any]]:
    """The 14 workflow steps with ``estado`` and ``tempo`` derived from log.jsonl (task_start / task_done /
    task_error, latest event wins) and, when the log says nothing about a step, from the presence of its
    ``T*.json`` file. Empty for tasks of the external flow that never ran the local workflow."""
    steps = {sid: {"id": sid, "nome": name, "estado": "pendente", "tempo": None} for sid, name in STEP_NAMES.items()}
    for e in events:
        step = steps.get(str(e.get("id") or ""))
        if not step:
            continue
        tipo = e.get("tipo")
        if tipo == "task_start":
            step["estado"], step["tempo"] = "em_andamento", None
        elif tipo == "task_done":
            step["estado"], step["tempo"] = "concluida", e.get("tempo")
        elif tipo == "task_error":
            step["estado"] = "erro"
    if workspace_dir:
        for sid, step in steps.items():
            if step["estado"] == "pendente" and (Path(workspace_dir) / f"{sid}.json").exists():
                step["estado"] = "concluida"
    out = list(steps.values())
    if all(s["estado"] == "pendente" for s in out) and is_external_flow(events, workspace_dir):
        return []
    return out


def is_gated(t: Tarefa) -> bool:
    """Lawyer review gate (docs/API-V3-CONTRACT.md): a task sent by a lawyer or admin stays hidden from the citizen
    while ``pronta`` (ready for review) until the lawyer approves it (``enviada``). Tasks sent by a citizen are
    never gated: ``pronta`` already releases them."""
    return t.status == "pronta" and (t.origem or "advogado") != "cidadao"
router = APIRouter()


def _public_questions(doc: Any) -> list[dict[str, Any]]:
    items = doc.get("questoes", []) if isinstance(doc, dict) else []
    return [{"id": q.get("id"), "enunciado": q.get("enunciado"), "alternativas": q.get("alternativas", []), "area": q.get("area")}
            for q in items if isinstance(q, dict)]


def _public_attempt(t: Optional[Tentativa]) -> Optional[dict[str, Any]]:
    if not t:
        return None
    return {"aprovado": t.aprovado, "hash_imutavel": t.hash_imutavel, "acertos": t.acertos, "total": t.total, "numero": t.numero}


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def _quotes(obj: Any, out: list[str]) -> list[str]:
    """Every literal quote (trecho_verbatim) found anywhere in the persistent memory."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "trecho_verbatim" and isinstance(v, str) and len(v) > 12:
                out.append(v)
            else:
                _quotes(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _quotes(v, out)
    return out


def topics_from_summary(resumo_md: str, memoria: Any) -> Optional[list[dict[str, Any]]]:
    """Sections of the plain-language summary, each with the literal quote from the memory that best matches it."""
    parts = [p.strip() for p in re.split(r"\n(?=##? )", resumo_md or "") if p.strip()]
    if not parts:
        return None
    quotes = _quotes(memoria, [])
    topics = []
    for i, part in enumerate(parts, 1):
        m = re.match(r"^##? (.+)\n?([\s\S]*)$", part)
        titulo, texto = (m.group(1).strip(), m.group(2).strip()) if m else (f"Ponto {i}", part)
        words = {w for w in _norm(texto).split() if len(w) > 4}
        best, score = None, 0
        for q in quotes:
            s = len(words & {w for w in _norm(q).split() if len(w) > 4})
            if s > score:
                best, score = q, s
        topic = {"id": i, "titulo": titulo, "explicacao_md": texto}
        if best and score >= 3:
            topic["trecho"] = best
        topics.append(topic)
    return topics


EXTERNAL_CLASS_LABELS = {
    "fatos": ("Fatos", "#F9DEDC"),
    "decisao": ("Decisão", "#D2E3FC"),
    "base_legal": ("Base legal", "#EADDFF"),
    "dispositivos": ("Dispositivos", "#EADDFF"),
    "pedidos": ("Pedidos", "#FFDDBE"),
    "precedentes": ("Precedentes", "#E3F1F1"),
    "relevancia": ("Relevância", "#C8E6C9"),
}
_ROMAN = re.compile(r"^(?:[ivx]+)_")


def humanize(key: Any, fallback: str = "") -> str:
    """``especie_recurso`` -> ``Especie recurso``; the fallback when the key is empty."""
    s = str(key or "").replace("_", " ").strip()
    return (s[:1].upper() + s[1:]) if s else fallback


def external_class_label(key: str) -> tuple[str, str]:
    """``classe_ii_base_legal`` -> ("Base legal", color). Unknown classes get the humanized key and a neutral color."""
    base = _ROMAN.sub("", key[len("classe_"):] if key.startswith("classe_") else key)
    return EXTERNAL_CLASS_LABELS.get(base, (humanize(base, key), "#ECEFF1"))


def _strings_of(obj: Any, out: list[str], limit: int = 4) -> list[str]:
    """First meaningful string values of a parsed ``valor`` (dict or list), in document order."""
    if len(out) >= limit:
        return out
    if isinstance(obj, dict):
        for v in obj.values():
            _strings_of(v, out, limit)
    elif isinstance(obj, list):
        for v in obj:
            _strings_of(v, out, limit)
    elif isinstance(obj, (str, int, float)) and not isinstance(obj, bool):
        s = str(obj).strip()
        if s and s.lower() not in ("null", "none") and s not in out:
            out.append(s)
    return out


def value_text(valor: Any) -> str:
    """``valor`` as one line: strings as they are (a JSON string is parsed), dicts and lists reduced to their
    first meaningful values joined by ", "."""
    if isinstance(valor, str):
        s = valor.strip()
        if s[:1] in ("{", "[") and s[-1:] in ("}", "]"):
            try:
                return ", ".join(_strings_of(json.loads(s), []))
            except ValueError:
                return s
        return s
    if isinstance(valor, (dict, list)):
        return ", ".join(_strings_of(valor, []))
    return "" if valor is None else str(valor)


def external_parts(doc: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """(processo, _ui) of a resumo_estruturado.json; ``_ui`` may sit at the root or inside ``processo``."""
    if not isinstance(doc, dict):
        return {}, {}
    processo = doc.get("processo") if isinstance(doc.get("processo"), dict) else doc
    ui = doc.get("_ui") if isinstance(doc.get("_ui"), dict) else processo.get("_ui")
    return processo, ui if isinstance(ui, dict) else {}


def external_classes(processo: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    """The ``classe_*`` lists of the external result, in document order (conferencia, resumo_* and resposta_final skipped)."""
    return [(k, v) for k, v in processo.items() if k.startswith("classe_") and isinstance(v, list)]


def _ui_entry(ui: dict[str, Any], cls: str, n: int) -> dict[str, Any]:
    items = ui.get(cls)
    if isinstance(items, list) and n < len(items) and isinstance(items[n], dict):
        return items[n]
    return {}


def _score(entry: dict[str, Any]) -> Optional[float]:
    s = entry.get("score_trecho_verbatim")
    try:
        return float(s) if s is not None and not isinstance(s, bool) else None
    except (TypeError, ValueError):
        return None


def external_summary(doc: Any) -> tuple[str, list[dict[str, Any]]]:
    """Fallback for tasks of the external flow: (resumo_md from resposta_final, topics from the classe_* items).
    Each topic: titulo = humanized ``campo``, explicacao = ``valor`` (or ``sintese_relacao``), trecho = ``trecho_verbatim``,
    score from ``_ui`` when present."""
    processo, ui = external_parts(doc)
    final = processo.get("resposta_final") if processo.get("resposta_final") is not None else (doc.get("resposta_final") if isinstance(doc, dict) else None)
    resumo_md = (final.get("texto") if isinstance(final, dict) else final) or ""
    topics: list[dict[str, Any]] = []
    for cls, items in external_classes(processo):
        label, _ = external_class_label(cls)
        for n, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            explicacao = value_text(it.get("valor")) or value_text(it.get("sintese_relacao"))
            topic: dict[str, Any] = {"id": len(topics) + 1, "titulo": humanize(it.get("campo"), label), "explicacao": explicacao,
                                     "classe": cls}
            if it.get("trecho_verbatim"):
                topic["trecho"] = str(it["trecho_verbatim"])
            score = _score(_ui_entry(ui, cls, n))
            if score is not None:
                topic["score"] = score
            topics.append(topic)
    return str(resumo_md), topics


def _task_or_404(session: Session, hash_: str) -> Tarefa:
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t:
        raise HTTPException(404, "Link inválido ou expirado")
    return t


def lawyer_of(session: Session, t: Tarefa) -> Optional[Usuario]:
    """The owner, unless the owner is a citizen who sent the document alone."""
    owner = session.get(Usuario, t.advogado_id)
    return owner if owner and owner.papel != "cidadao" else None


class DuvidaIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    contexto: Optional[list[dict[str, Any]]] = None


@router.get("/api/t/{hash_}")
async def api_cliente_json(hash_: str, session: Session = Depends(get_session)):
    t = _task_or_404(session, hash_)
    lawyer = lawyer_of(session, t)
    doubts = session.exec(select(func.count(Duvida.id)).where(Duvida.tarefa_id == t.id)).one()
    events = ws.ler_eventos(t.hash)
    base = {"tarefa": {"hash": t.hash, "titulo": t.titulo, "status": t.status}, "eventos": public_events(events, PUBLIC_EVENT_LIMIT),
            "etapas": build_steps(events, ws.pasta(t.hash)),
            "advogado": {"nome": lawyer.nome} if lawyer else None, "tem_advogado": lawyer is not None,
            "cidadao_vinculado": t.cidadao_id is not None, "duvidas_enviadas": int(doubts or 0)}
    if is_gated(t):
        base["tarefa"]["status"] = "revisao"
        return {**base, "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    if t.status not in READY_STATUSES:
        return {**base, "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    lista = tn.listar(t.id)
    ultima = _public_attempt(lista[-1] if lista else None)
    resumo_md = _ler_artefato(t.hash, "resumo_humanizado.md")
    if resumo_md is None:
        externo = _ler_json(t.hash, EXTERNAL_RESULT_FILE)
        if externo is not None:
            # external flow: no local explanation nor questions; the journey ends without the check
            resumo_md, topicos = external_summary(externo)
            return {**base, "resumo_md": resumo_md, "topicos": topicos, "questoes": [], "sem_perguntas": True, "ultima_tentativa": ultima}
        resumo_md = ""
    questoes = _public_questions(_ler_json(t.hash, "questoes.json") or {})
    memoria = _ler_json(t.hash, "memoria_persistente.json")
    return {**base, "resumo_md": resumo_md, "topicos": topics_from_summary(resumo_md, memoria),
            "questoes": questoes, "sem_perguntas": not questoes, "ultima_tentativa": ultima}


@router.post("/api/t/{hash_}/duvida", dependencies=[Depends(rate_limit)])
async def api_cliente_duvida(hash_: str, body: DuvidaIn, session: Session = Depends(get_session)):
    t = _task_or_404(session, hash_)
    if lawyer_of(session, t) is None:
        raise HTTPException(409, "Este documento não tem um advogado para receber a dúvida.")
    texto = body.texto.strip()
    if not texto:
        raise HTTPException(400, "Escreva a sua dúvida.")
    contexto = None
    if body.contexto:
        keep = [{"role": "bot" if str(m.get("role")) == "bot" else "user", "text": str(m.get("text", ""))[:4000]}
                for m in body.contexto[-20:] if isinstance(m, dict)]
        contexto = json.dumps(keep, ensure_ascii=False)
    d = Duvida(tarefa_id=t.id, texto=texto, contexto=contexto)
    session.add(d); session.commit(); session.refresh(d)
    ws.registrar_evento(t.hash, "duvida_enviada", duvida_id=d.id, chars=len(texto))
    return {"id": d.id, "criada_em": d.criada_em.isoformat()}


@router.post("/api/t/{hash_}/vincular")
async def api_cliente_vincular(hash_: str, u: Usuario = Depends(usuario_api), session: Session = Depends(get_session)):
    if u.papel != "cidadao":
        raise HTTPException(403, "Só uma conta de cidadã pode se vincular a um documento.")
    t = _task_or_404(session, hash_)
    if t.cidadao_id is None:
        t.cidadao_id = u.id
        session.add(t); session.commit()
        ws.registrar_evento(t.hash, "cidadao_vinculado", cidadao_id=u.id)
    elif t.cidadao_id != u.id:
        raise HTTPException(409, "Este documento já está vinculado a outra conta.")
    return {"ok": True}


def _ots_path(tarefa_hash: str, numero: int):
    return ws.pasta(tarefa_hash) / f"tentativa_{numero}.ots"


def get_attempt(hash_imutavel: str) -> Optional[dict[str, Any]]:
    """Adapter for leia.registry.build_router. Nothing personal reaches the published payload."""
    with Session(engine) as s:
        tent = s.exec(select(Tentativa).where(Tentativa.hash_imutavel == hash_imutavel)).first()
        if not tent:
            return None
        t = s.get(Tarefa, tent.tarefa_id)
    created = tent.criada_em.replace(tzinfo=timezone.utc) if tent.criada_em.tzinfo is None else tent.criada_em
    p = _ots_path(t.hash, tent.numero)
    return {"hash_imutavel": tent.hash_imutavel, "tarefa_hash": t.hash, "numero": tent.numero, "acertos": tent.acertos,
            "total": tent.total, "aprovado": tent.aprovado, "criada_em": created,
            "ots": p.read_bytes() if p.exists() else None}


def stamp_attempt(tarefa_hash: str, numero: int, hash_imutavel: str) -> None:
    """Background task after an approved attempt: public timestamp of the payload hash."""
    attempt = get_attempt(hash_imutavel)
    if not attempt:
        return
    _, digest = payload_hash(build_payload(attempt))
    # Uma prova só vale para o registro sobre o qual foi feita. Se o payload mudou depois do carimbo,
    # o arquivo em disco é de um registro que não existe mais e precisa ser refeito, não preservado.
    existente = attempt.get("ots")
    if existente and ots_digest(existente) == digest:
        return
    proof = ots_stamp(digest)
    if proof:
        _ots_path(tarefa_hash, numero).write_bytes(proof)
        ws.registrar_evento(tarefa_hash, "carimbo_publico", numero=numero, payload_hash=digest)


# ══════════════════════════════════════════════════════════════════════════
#  LeIA: inferences over the original text (what the workflow tagged and concluded), verified by substring
# ══════════════════════════════════════════════════════════════════════════
CLASS_LABELS = {
    "identificacao": ("Quem é quem", "#D2E3FC"),
    "datas_valores": ("Datas e valores", "#C8E6C9"),
    "fatos": ("Fatos", "#F9DEDC"),
    "fundamentos": ("Fundamentos: leis e decisões citadas", "#EADDFF"),
    "pedidos": ("Pedidos", "#FFDDBE"),
}
SYNTHESIS_FILES = [("T10_SINTESE_IDENTIFICACAO.json", "identificacao"), ("T7_SINTESE_FATOS.json", "fatos"),
                   ("T8_SINTESE_FUNDAMENTOS.json", "fundamentos"), ("T9_SINTESE_PEDIDOS.json", "pedidos"),
                   ("T11_SINTESE_CONTEXTO.json", "contexto")]


def _norm_map(text: str) -> tuple[str, list[int]]:
    """Whitespace-collapsed copy of the text plus a map from each collapsed char to its original offset."""
    out: list[str] = []
    idx: list[int] = []
    prev_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                out.append(" ")
                idx.append(i)
            prev_space = True
        else:
            out.append(ch)
            idx.append(i)
            prev_space = False
    return "".join(out), idx


def find_span(text_norm: str, idx: list[int], quote: str) -> Optional[list[int]]:
    q = " ".join((quote or "").split())
    if len(q) < 3:
        return None
    pos = text_norm.find(q)
    if pos < 0:
        pos = text_norm.lower().find(q.lower())
        if pos < 0:
            return None
    return [idx[pos], idx[pos + len(q) - 1] + 1]


def parse_pos(pos: Any, text_len: int) -> Optional[list[int]]:
    """First valid ``inicio:fim`` of a ``_ui`` position (one range, or several separated by comma or semicolon,
    with or without brackets). ``0:0`` and ranges outside the text are not valid."""
    if not isinstance(pos, str):
        return None
    for part in re.split(r"[,;]", pos.strip().strip("[]")):
        m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", part)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if 0 <= a < b <= text_len:
            return [a, b]
    return None


def _item(cls: str, n: int, it: dict[str, Any], texto: str, text_norm: str, idx: list[int], cor: str,
          ui_entry: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """One tagged item verified over the text: the ``_ui`` position when valid, else the substring search."""
    quote = it.get("trecho_verbatim") or ""
    span = parse_pos((ui_entry or {}).get("pos_trecho_verbatim"), len(texto)) if ui_entry else None
    if span is None:
        span = find_span(text_norm, idx, quote)
    out = {"ref": f"{cls}[{n}]", "campo": it.get("campo"), "valor": it.get("valor"), "trecho": quote,
           "pos": span, "conferido": bool(span), "cor": cor}
    score = _score(ui_entry) if ui_entry else None
    if score is not None:
        out["score"] = score
    return out


def _syntheses(sinteses_raw: list[tuple[str, Any]], labels: dict[str, tuple[str, str]]) -> list[dict[str, Any]]:
    sinteses = []
    for cls, raw in sinteses_raw:
        if not isinstance(raw, dict) or not raw:
            continue
        body = next(iter(raw.values())) if len(raw) == 1 and isinstance(next(iter(raw.values())), dict) else raw
        if not isinstance(body, dict):
            continue
        sinteses.append({"classe": cls, "rotulo": labels.get(cls, ("Contexto do processo", "#E3F1F1"))[0],
                         "texto": body.get("valor") or "", "lastro": [str(x) for x in (body.get("lastro") or [])]})
    return sinteses


def build_inferences(texto: str, memoria: Any, tagueado: Any, sinteses_raw: list[tuple[str, Any]]) -> dict[str, Any]:
    text_norm, idx = _norm_map(texto or "")
    colors: dict[str, str] = {}
    for cls, items in ((tagueado or {}).get("_ui") or {}).items() if isinstance(tagueado, dict) else []:
        for it in items or []:
            if isinstance(it, dict) and it.get("categoria") and it.get("cor"):
                colors[f"{cls}:{it['categoria']}"] = it["cor"]
    mem = (memoria or {}).get("memoria_persistente", memoria) if isinstance(memoria, dict) else {}
    classes, total, conferidos = [], 0, 0
    for cls, (label, default_color) in CLASS_LABELS.items():
        items = mem.get(cls) if isinstance(mem, dict) else None
        if not isinstance(items, list):
            continue
        out = []
        for n, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            item = _item(cls, n, it, texto or "", text_norm, idx, colors.get(f"{cls}:{it.get('campo')}", default_color))
            total += 1
            conferidos += 1 if item["conferido"] else 0
            out.append(item)
        classes.append({"classe": cls, "rotulo": label, "cor": default_color, "itens": out})
    return {"texto": texto or "", "classes": classes, "sinteses": _syntheses(sinteses_raw, CLASS_LABELS), "total": total, "conferidos": conferidos}


def build_external_inferences(texto: str, doc: Any) -> dict[str, Any]:
    """Inferences of a resumo_estruturado.json (external flow): classes from ``processo.classe_*`` with labels from
    the key, positions from ``_ui`` when valid (else substring), ``score`` from ``_ui``; syntheses from ``resumo_classe_*``."""
    processo, ui = external_parts(doc)
    text_norm, idx = _norm_map(texto or "")
    classes, total, conferidos = [], 0, 0
    groups: dict[str, list[str]] = {}
    for cls, items in external_classes(processo):
        label, color = external_class_label(cls)
        m = re.match(r"^classe_([ivx]+)_", cls)
        if m:
            groups.setdefault(m.group(1), []).append(label)
        out = []
        for n, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            item = _item(cls, n, it, texto or "", text_norm, idx, color, _ui_entry(ui, cls, n))
            item["valor"] = value_text(it.get("valor"))
            total += 1
            conferidos += 1 if item["conferido"] else 0
            out.append(item)
        classes.append({"classe": cls, "rotulo": label, "cor": color, "itens": out})
    sinteses = []
    for key, body in processo.items():
        if not key.startswith("resumo_classe_") or not isinstance(body, dict):
            continue
        roman = key[len("resumo_classe_"):]
        names = groups.get(roman) or []
        rotulo = " e ".join([names[0]] + [n[:1].lower() + n[1:] for n in names[1:]]) if names else humanize(body.get("campo"), key)
        sinteses.append({"classe": key, "rotulo": rotulo, "texto": value_text(body.get("valor")) or value_text(body.get("sintese_relacao")),
                         "lastro": [str(x) for x in (body.get("lastro") or [])]})
    return {"texto": texto or "", "classes": classes, "sinteses": sinteses, "total": total, "conferidos": conferidos}


@router.get("/api/t/{hash_}/inferencias")
async def api_cliente_inferencias(hash_: str, session: Session = Depends(get_session)):
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t:
        raise HTTPException(404, "Link inválido ou expirado")
    if is_gated(t):
        raise HTTPException(409, GATE_MESSAGE)
    if t.status in READY_STATUSES:
        return {"tarefa": {"hash": t.hash, "titulo": t.titulo}, **inferences_of(t)}
    if t.status in ("criada", "processando"):
        return {"tarefa": {"hash": t.hash, "titulo": t.titulo}, **partial_inferences_of(t)}
    raise HTTPException(409, "A explicação ainda está sendo preparada")


def inferences_of(t: Tarefa) -> dict[str, Any]:
    """Inference body of a finished task from its workspace artifacts (shared with the lawyer review route).
    Without ``memoria_persistente.json`` but with ``resumo_estruturado.json`` (external flow) the body comes from the latter."""
    memoria = _ler_json(t.hash, "memoria_persistente.json")
    texto = _ler_artefato(t.hash, "texto_extraido.txt")
    if memoria is None:
        externo = _ler_json(t.hash, EXTERNAL_RESULT_FILE)
        if externo is not None:
            texto = texto if texto is not None else (_ler_artefato(t.hash, EXTERNAL_TEXT_FILE) or "")
            return {**build_external_inferences(texto, externo), "parcial": False}
    sinteses_raw = [(cls, _ler_json(t.hash, name)) for name, cls in SYNTHESIS_FILES]
    return {**build_inferences(texto or "", memoria, _ler_json(t.hash, "texto_tagueado.json"), sinteses_raw), "parcial": False}


def partial_inferences_of(t: Tarefa) -> dict[str, Any]:
    """Inference body while the workflow runs: the text once extracted and the classes of the T1..T5 files that
    already exist (each one ``{"<classe>": [itens]}``), plus the syntheses of T7..T11 when present."""
    mem: dict[str, list[Any]] = {}
    for name in FRAGMENT_FILES:
        doc = _ler_json(t.hash, name)
        if isinstance(doc, dict):
            for cls, items in doc.items():
                if cls in CLASS_LABELS and isinstance(items, list):
                    mem.setdefault(cls, []).extend(items)
    sinteses_raw = [(cls, _ler_json(t.hash, name)) for name, cls in SYNTHESIS_FILES]
    return {**build_inferences(_ler_artefato(t.hash, "texto_extraido.txt") or "", {"memoria_persistente": mem}, None, sinteses_raw),
            "parcial": True}
