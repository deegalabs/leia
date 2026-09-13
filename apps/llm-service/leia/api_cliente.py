"""Public JSON for the citizen app and the registry adapter. Included from main.py.

GET /api/t/{hash}: the same data the service renders in /t/{hash}, as JSON and without the answer key.
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
from leia.registry import build_payload, ots_stamp, payload_hash

READY_STATUSES = ("pronta", "enviada", "assinada")
GATE_MESSAGE = "Em revisão pelo advogado"
PUBLIC_EVENT_TYPES = {"criada", "pdf_salvo", "pipeline_start", "texto_extraido", "task_start", "task_done", "task_error",
                      "erro_extracao", "pipeline_done", "tentativa", "carimbo_publico", "duvida_enviada", "reprocessar",
                      "aprovada"}


def public_events(events: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    """Pipeline events only, without the visitor's IP or user agent."""
    out = [{k: v for k, v in e.items() if k not in ("ip", "ua", "user_agent", "advogado_id", "usuario_id")} for e in events if e.get("tipo") in PUBLIC_EVENT_TYPES]
    return out[-limit:]


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
    base = {"tarefa": {"hash": t.hash, "titulo": t.titulo, "status": t.status}, "eventos": public_events(ws.ler_eventos(t.hash), 8),
            "advogado": {"nome": lawyer.nome} if lawyer else None, "tem_advogado": lawyer is not None,
            "cidadao_vinculado": t.cidadao_id is not None, "duvidas_enviadas": int(doubts or 0)}
    if is_gated(t):
        base["tarefa"]["status"] = "revisao"
        return {**base, "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    if t.status not in READY_STATUSES:
        return {**base, "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    resumo_md = _ler_artefato(t.hash, "resumo_humanizado.md") or ""
    questoes = _ler_json(t.hash, "questoes.json") or {}
    memoria = _ler_json(t.hash, "memoria_persistente.json")
    lista = tn.listar(t.id)
    return {**base, "resumo_md": resumo_md, "topicos": topics_from_summary(resumo_md, memoria),
            "questoes": _public_questions(questoes), "ultima_tentativa": _public_attempt(lista[-1] if lista else None)}


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
    """Adapter for leia.registry.build_router. Nothing personal: the salt is derived from the attempt hash."""
    with Session(engine) as s:
        tent = s.exec(select(Tentativa).where(Tentativa.hash_imutavel == hash_imutavel)).first()
        if not tent:
            return None
        t = s.get(Tarefa, tent.tarefa_id)
    created = tent.criada_em.replace(tzinfo=timezone.utc) if tent.criada_em.tzinfo is None else tent.criada_em
    p = _ots_path(t.hash, tent.numero)
    return {"hash_imutavel": tent.hash_imutavel, "tarefa_hash": t.hash, "numero": tent.numero, "acertos": tent.acertos,
            "total": tent.total, "aprovado": tent.aprovado, "criada_em": created, "salt": tent.hash_imutavel[:40],
            "ots": p.read_bytes() if p.exists() else None}


def stamp_attempt(tarefa_hash: str, numero: int, hash_imutavel: str) -> None:
    """Background task after an approved attempt: public timestamp of the payload hash."""
    attempt = get_attempt(hash_imutavel)
    if not attempt or attempt.get("ots"):
        return
    _, digest = payload_hash(build_payload(attempt))
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
            quote = it.get("trecho_verbatim") or ""
            span = find_span(text_norm, idx, quote)
            total += 1
            conferidos += 1 if span else 0
            out.append({"ref": f"{cls}[{n}]", "campo": it.get("campo"), "valor": it.get("valor"), "trecho": quote,
                        "pos": span, "conferido": bool(span),
                        "cor": colors.get(f"{cls}:{it.get('campo')}", default_color)})
        classes.append({"classe": cls, "rotulo": label, "cor": default_color, "itens": out})
    sinteses = []
    for cls, raw in sinteses_raw:
        if not isinstance(raw, dict) or not raw:
            continue
        body = next(iter(raw.values())) if len(raw) == 1 and isinstance(next(iter(raw.values())), dict) else raw
        if not isinstance(body, dict):
            continue
        sinteses.append({"classe": cls, "rotulo": CLASS_LABELS.get(cls, ("Contexto do processo", "#E3F1F1"))[0],
                         "texto": body.get("valor") or "", "lastro": [str(x) for x in (body.get("lastro") or [])]})
    return {"texto": texto or "", "classes": classes, "sinteses": sinteses, "total": total, "conferidos": conferidos}


@router.get("/api/t/{hash_}/inferencias")
async def api_cliente_inferencias(hash_: str, session: Session = Depends(get_session)):
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t:
        raise HTTPException(404, "Link inválido ou expirado")
    if is_gated(t):
        raise HTTPException(409, GATE_MESSAGE)
    if t.status not in READY_STATUSES:
        raise HTTPException(409, "A explicação ainda está sendo preparada")
    return {"tarefa": {"hash": t.hash, "titulo": t.titulo}, **inferences_of(t)}


def inferences_of(t: Tarefa) -> dict[str, Any]:
    """Inference body of a task from its workspace artifacts (shared with the lawyer review route)."""
    texto = _ler_artefato(t.hash, "texto_extraido.txt") or ""
    sinteses_raw = [(cls, _ler_json(t.hash, name)) for name, cls in SYNTHESIS_FILES]
    return build_inferences(texto, _ler_json(t.hash, "memoria_persistente.json"), _ler_json(t.hash, "texto_tagueado.json"), sinteses_raw)
