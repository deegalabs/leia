"""Public JSON for the citizen app and the registry adapter. Included from main.py.

GET /api/t/{hash}: the same data the service renders in /t/{hash}, as JSON and without the answer key, plus
``etapas`` (the 15 workflow steps with state and time), ``tipo_documento`` (the species the engine read the
document as, which is what chose the vocabulary of every step below it) and up to 60 pipeline events.
GET /api/t/{hash}/inferencias: what the workflow tagged over the original text; during ``criada``/``processando``
it answers with ``parcial: true`` and the classes produced so far (files T1..T5), so the waiting screen can show
the document being marked.
is_gated(): lawyer review gate; while a lawyer's task is ``pronta`` the public routes hide the explanation.
Fidelity gate (E11): a section of the summary and a synthesis only reach the screen when what they declare as
source is a quote ``locate`` finds in the document; ``sections_without_anchor()`` and ``sinteses_sem_lastro``
name what was held back, and an explanation with nothing left answers ``falhou`` instead of a blank page.
POST /api/t/{hash}/duvida: a doubt for the lawyer who sent the document (409 when nobody did).
POST /api/t/{hash}/vincular: links the signed-in citizen to the task (Bearer, papel cidadao).
stamp_attempt(): OpenTimestamps proof of an approved attempt, stored in the task workspace; it writes down
both outcomes, ``carimbo_publico`` and ``carimbo_falhou`` with the reason the calendars gave.
ots_status(): the three states the receipt may claim (``ausente``, ``pendente``, ``confirmado``), per ADR-0010.
get_attempt(): adapter used by leia.registry (receipt and public verification).
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

import core.attempts as tn
import core.document_type as dt
import core.workspace as ws
from app_gestao import _read_artifact, _read_json
from core.anchors import locate, norm_map
from core.auth import api_user, optional_api_user
from leia import invites  # LeIA: the invite that governs the document link
from leia.registry import sha256_hex
from core.db import ConsentRecord, Duvida, Tarefa, Tentativa, Usuario, engine, get_session
from leia.ratelimit import rate_limit
from leia.registry import build_payload, ots_bitcoin_height, ots_digest, ots_stamp, payload_hash

READY_STATUSES = ("pronta", "enviada", "assinada")
GATE_MESSAGE = "Em revisão pelo advogado"
PUBLIC_EVENT_TYPES = {"criada", "pdf_salvo", "pipeline_start", "texto_extraido", "task_start", "task_done", "task_error",
                      "erro_extracao", "pipeline_done", "tentativa", "carimbo_publico", "carimbo_falhou",
                      "duvida_enviada", "reprocess", "aprovada", "tipo_documento",
}
# ``tipo_documento_corrigido`` fica fora desta lista de propósito: ele carrega o id de quem corrigiu, e quem
# revisou o documento de alguém não é assunto de rota pública.
PUBLIC_EVENT_LIMIT = 60

# The 15 workflow tasks of protocolo_pdf.json (ids as written there) with the pt-BR names of docs/API-V3-CONTRACT.md.
STEP_NAMES: dict[str, str] = {
    "T0_TIPO_DOCUMENTO": "Reconhecer o tipo do documento",
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
# Os dois fluxos que mandavam o documento para fora foram removidos. O arquivo continua nomeado aqui só para
# reconhecer documento antigo que veio por aquele caminho e falhar dizendo o motivo, em vez de mostrar uma tela
# de explicação vazia com ar de normalidade.
LEGACY_EXTERNAL_FILE = "resumo_estruturado.json"


def public_events(events: list[dict[str, Any]], limit: int = PUBLIC_EVENT_LIMIT) -> list[dict[str, Any]]:
    """Pipeline events only, without the visitor's IP or user agent; the last ``limit`` ones."""
    out = [{k: v for k, v in e.items() if k not in ("ip", "ua", "user_agent", "advogado_id", "cidadao_id", "usuario_id")} for e in events if e.get("tipo") in PUBLIC_EVENT_TYPES]
    return out[-limit:]


def build_steps(events: list[dict[str, Any]], workspace_dir: Optional[Path] = None) -> list[dict[str, Any]]:
    """The 15 workflow steps with ``estado`` and ``tempo`` derived from log.jsonl (task_start / task_done /
    task_error, latest event wins) and, when the log says nothing about a step, from the presence of its
    ``T*.json`` file."""
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
    return out


def is_gated(t: Tarefa) -> bool:
    """Lawyer review gate (docs/API-V3-CONTRACT.md): a task sent by a lawyer or admin stays hidden from the citizen
    while ``pronta`` (ready for review) until the lawyer approves it (``enviada``). Tasks sent by a citizen are
    never gated: ``pronta`` already releases them."""
    return t.status == "pronta" and (t.origem or "advogado") != "cidadao"
router = APIRouter()


def _public_questions(doc: Any) -> list[dict[str, Any]]:
    """A pergunta como a pessoa a recebe: com o ponto do documento de onde ela nasceu, sem o gabarito.

    ``secao`` e ``trecho`` são o que permitem voltar ao ponto no papel dela em vez de tentar lembrar, e são o
    que o "não lembro, mostra de novo" abre. ``correta`` e ``justificativa`` continuam do lado de cá: quem
    responde não pode receber a resposta junto com a pergunta."""
    items = doc.get("questoes", []) if isinstance(doc, dict) else []
    return [{"id": q.get("id"), "enunciado": q.get("enunciado"), "alternativas": q.get("alternativas", []),
             "area": q.get("area"), "secao": q.get("secao"), "trecho": q.get("trecho"),
             "conferencia": q.get("conferencia")}
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


def _section_key(titulo: str) -> str:
    """The heading as a comparable key: no accents, no emoji, no punctuation, one space between words.
    The model writes the heading with an emoji in front, and that emoji is decoration, not identity."""
    base = _norm(titulo or "")
    return " ".join("".join(c if c.isalnum() or c.isspace() else " " for c in base).split())


_SECTION_SOURCES: Optional[dict[str, list[str]]] = None


def section_sources() -> dict[str, list[str]]:
    """Which memory classes each summary section is explaining, as declared in the protocol.

    The section headings are fixed by the task that writes the summary, so this link is knowable, not
    guessable. It lives next to that task in ``protocolo_pdf.json`` because the day the headings change the
    link has to change with them."""
    global _SECTION_SOURCES
    if _SECTION_SOURCES is None:
        _SECTION_SOURCES = {}
        try:
            from core.pipeline_pdf import PROTOCOLO_PDF

            doc = json.loads(Path(PROTOCOLO_PDF).read_text(encoding="utf-8"))
            for task in doc.get("tasks") or []:
                mapa = task.get("ancoras_por_secao")
                if isinstance(mapa, dict):
                    _SECTION_SOURCES.update({_section_key(k): [str(v) for v in (vals or [])] for k, vals in mapa.items()})
        except Exception:
            pass
    return _SECTION_SOURCES


def _refs_of(sinteses_raw: list[tuple[str, Any]], classes: list[str]) -> list[str]:
    """The memory items a synthesis says it used (``lastro``), for the classes this section explains."""
    refs: list[str] = []
    for cls, body in sinteses_raw or []:
        if cls not in classes or not isinstance(body, dict):
            continue
        for value in body.values():
            if isinstance(value, dict):
                refs.extend(str(x) for x in (value.get("lastro") or []))
    return refs


def _quote_of(memoria: Any, ref: str) -> Optional[str]:
    m = re.fullmatch(r"([a-z_]+)\[(\d+)\]", ref.strip())
    if not m:
        return None
    mem = (memoria or {}).get("memoria_persistente", memoria) if isinstance(memoria, dict) else {}
    items = mem.get(m.group(1)) if isinstance(mem, dict) else None
    n = int(m.group(2))
    if isinstance(items, list) and n < len(items) and isinstance(items[n], dict):
        q = items[n].get("trecho_verbatim")
        return q if isinstance(q, str) and q.strip() else None
    return None


def _sections(resumo_md: str, memoria: Any, documento: str = "",
              sinteses_raw: Optional[list[tuple[str, Any]]] = None) -> tuple[Optional[list[dict[str, Any]]], list[str]]:
    """Sections that may be published, each with the literal quote of what it explains, and the titles of the
    ones held back.

    The quote is what the citizen reads beside the explanation, presented as copied from the document, so two
    different things have to be true and both used to be guessed. Which quote belongs to this section comes
    from the protocol, which fixes the headings, plus the ``lastro`` the synthesis itself declares. Whether the
    quote exists in the document is decided by ``locate``: word overlap once put a quote about the facts under
    "who is in this story", and a checked excerpt about the wrong subject is its own kind of lie.

    A section that declares a source and reaches no checked item is held back instead of published without a
    quote. The landing page promises a literal excerpt beside every explanation, and a section that arrives
    bare looks exactly like the ones that were checked, so the citizen has no way of telling which is which.
    The section the protocol maps to no class at all, the one-line summary, is about the whole case and never
    promised a quote, so it stays."""
    parts = [p.strip() for p in re.split(r"\n(?=##? )", resumo_md or "") if p.strip()]
    if not parts:
        return None, []
    sources = section_sources()
    text_norm, idx = norm_map(documento or "")
    topics, sem_lastro = [], []
    for i, part in enumerate(parts, 1):
        m = re.match(r"^##? (.+)\n?([\s\S]*)$", part)
        titulo, texto = (m.group(1).strip(), m.group(2).strip()) if m else (f"Ponto {i}", part)
        topic = {"id": i, "titulo": titulo, "explicacao_md": texto}
        classes = sources.get(_section_key(titulo)) or []
        if classes:
            for ref in _refs_of(sinteses_raw or [], classes):
                q = _quote_of(memoria, ref)
                found = locate(documento, text_norm, idx, q) if q else None
                if found:
                    topic["trecho"] = q
                    topic["conferencia"] = {"metodo": found["metodo"], "score": found["score"]}
                    break
            if "trecho" not in topic:
                sem_lastro.append(titulo)
                continue
        topics.append(topic)
    return topics, sem_lastro


def topics_from_summary(resumo_md: str, memoria: Any, documento: str = "",
                        sinteses_raw: Optional[list[tuple[str, Any]]] = None) -> Optional[list[dict[str, Any]]]:
    """The sections of the plain-language summary that the document sustains (see ``_sections``)."""
    return _sections(resumo_md, memoria, documento, sinteses_raw)[0]


def sections_without_anchor(resumo_md: str, memoria: Any, documento: str = "",
                            sinteses_raw: Optional[list[tuple[str, Any]]] = None) -> list[str]:
    """Titles of the sections held back for having no checked item, for the lawyer review screen and the
    quality gate: a discard nobody can see is a discard nobody can fix."""
    return _sections(resumo_md, memoria, documento, sinteses_raw)[1]
_ROMAN = re.compile(r"^(?:[ivx]+)_")


def humanize(key: Any, fallback: str = "") -> str:
    """``especie_recurso`` -> ``Especie recurso``; the fallback when the key is empty."""
    s = str(key or "").replace("_", " ").strip()
    return (s[:1].upper() + s[1:]) if s else fallback


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
async def api_cliente_json(hash_: str, visitante: Optional[Usuario] = Depends(optional_api_user),
                           session: Session = Depends(get_session)):
    t = _task_or_404(session, hash_)
    invites.ensure_valid(session, t, visitante)
    lawyer = lawyer_of(session, t)
    doubts = session.exec(select(func.count(Duvida.id)).where(Duvida.tarefa_id == t.id)).one()
    events = ws.read_events(t.hash)
    base = {"tarefa": {"hash": t.hash, "titulo": t.titulo, "status": t.status}, "eventos": public_events(events, PUBLIC_EVENT_LIMIT),
            "etapas": build_steps(events, ws.folder(t.hash)),
            # Sai em ``base``, e não junto da explicação, porque vale também enquanto a tarefa é preparada e
            # quando ela falha: é a primeira coisa que o motor descobre sobre o documento, e saber que ele
            # foi lido como contrato ou como decisão é o que torna conferível tudo o que vem depois.
            "tipo_documento": dt.public(t.hash),
            "advogado": {"nome": lawyer.nome} if lawyer else None, "tem_advogado": lawyer is not None,
            "cidadao_vinculado": t.cidadao_id is not None, "duvidas_enviadas": int(doubts or 0),
            "convite": invites.public_json(session, t)}
    if _read_artifact(t.hash, "resumo_humanizado.md") is None and _read_json(t.hash, LEGACY_EXTERNAL_FILE) is not None:
        # Documento preparado pelo fluxo externo, que não existe mais. Vem antes do portão de revisão porque
        # o portão pressupõe que existe uma explicação para o advogado conferir, e aqui não existe.
        return {**base, "tarefa": {**base["tarefa"], "status": "falhou"},
                "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    if is_gated(t):
        base["tarefa"]["status"] = "revisao"
        return {**base, "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    if t.status not in READY_STATUSES:
        return {**base, "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    lista = tn.list_all(t.id)
    ultima = _public_attempt(lista[-1] if lista else None)
    resumo_md = _read_artifact(t.hash, "resumo_humanizado.md")
    if resumo_md is None:
        resumo_md = ""
    questoes = _public_questions(_read_json(t.hash, "questoes.json") or {})
    memoria = _read_json(t.hash, "memoria_persistente.json")
    documento = _read_artifact(t.hash, "texto_extraido.txt") or ""
    sinteses_raw = [(cls, _read_json(t.hash, name)) for name, cls in SYNTHESIS_FILES]
    topicos = topics_from_summary(resumo_md, memoria, documento, sinteses_raw)
    if topicos is not None and not topicos:
        # Every section was held back for having no checked quote, so the markdown summary stops going out
        # too: the app rebuilds the topics from it whenever the list arrives empty, and the person would read
        # back, with no quote at all, exactly what the gate just stopped. An explicit state, not a blank page.
        return {**base, "tarefa": {**base["tarefa"], "status": "falhou"}, "motivo": "explicacao_sem_lastro",
                "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    return {**base, "resumo_md": resumo_md, "topicos": topicos,
            "questoes": questoes, "sem_perguntas": not questoes, "ultima_tentativa": ultima}


@router.post("/api/t/{hash_}/duvida", dependencies=[Depends(rate_limit)])
async def api_cliente_duvida(hash_: str, body: DuvidaIn, visitante: Optional[Usuario] = Depends(optional_api_user),
                             session: Session = Depends(get_session)):
    t = _task_or_404(session, hash_)
    invites.ensure_valid(session, t, visitante)
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
    ws.record_event(t.hash, "duvida_enviada", duvida_id=d.id, chars=len(texto))
    return {"id": d.id, "criada_em": d.criada_em.isoformat()}


@router.post("/api/t/{hash_}/vincular")
async def api_cliente_vincular(hash_: str, u: Usuario = Depends(api_user), session: Session = Depends(get_session)):
    if u.papel != "cidadao":
        raise HTTPException(403, "Só uma conta de cidadã pode se vincular a um documento.")
    t = _task_or_404(session, hash_)
    invites.ensure_linkable(session, t, u)
    if t.cidadao_id is None:
        t.cidadao_id = u.id
        session.add(t); session.commit()
        ws.record_event(t.hash, "cidadao_vinculado", cidadao_id=u.id)
    elif t.cidadao_id != u.id:
        raise HTTPException(409, "Este documento já está vinculado a outra conta.")
    return {"ok": True}


def _ots_path(tarefa_hash: str, numero: int):
    return ws.folder(tarefa_hash) / f"tentativa_{numero}.ots"


# Os três estados que o carimbo pode ter (ADR-0010). São valores de contrato do JSON público, não texto
# de tela: quem lê é o lib/stamp.ts, que escolhe a frase em pt-BR a partir deles.
OTS_ABSENT, OTS_PENDING, OTS_CONFIRMED = "ausente", "pendente", "confirmado"


def _iso_utc(ts: Any) -> Optional[str]:
    """Event timestamps are written naive, in UTC; what leaves the service says which zone that is."""
    try:
        moment = datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _last_stamp_attempt(tarefa_hash: str, numero: int) -> Optional[str]:
    """When the service last tried to stamp this attempt, whatever came of the try."""
    for event in reversed(ws.read_events(tarefa_hash)):
        if event.get("tipo") in ("carimbo_publico", "carimbo_falhou") and event.get("numero") == numero:
            return _iso_utc(event.get("ts"))
    return None


def ots_status(proof: Optional[bytes], payload_sha256: str, last_attempt: Optional[str]) -> dict[str, Any]:
    """The public stamp in the only three states it can honestly be in (ADR-0010).

    A proof made over another payload counts as ``ausente``: it belongs to a record that no longer exists.
    ``pendente`` is the calendar's promise and ``confirmado`` is the Bitcoin block that closes it, which is the
    difference the screen could not tell and so promised every receipt that the stamp was on its way.
    """
    if not proof or not payload_sha256 or ots_digest(proof) != payload_sha256:
        return {"otsState": OTS_ABSENT, "otsBlockHeight": None, "otsLastAttempt": last_attempt}
    height = ots_bitcoin_height(proof)
    return {"otsState": OTS_CONFIRMED if height is not None else OTS_PENDING,
            "otsBlockHeight": height, "otsLastAttempt": last_attempt}


def _document_sha(tarefa_hash: str) -> str:
    """The PDF the person actually received, as it was stored."""
    caminho = ws.folder(tarefa_hash) / "original.pdf"
    return sha256_hex(caminho.read_bytes()) if caminho.exists() else ""


def _summary_sha(tarefa_hash: str) -> str:
    """The explanation the person actually read, in the form the screen rendered it."""
    resumo = _read_artifact(tarefa_hash, "resumo_humanizado.md")
    return sha256_hex(resumo) if resumo else ""


def freeze_record(tarefa_hash: str, numero: int, hash_imutavel: str) -> None:
    """Writes down the consent record at the moment it was earned, and never touches it again.

    Until now the record was rebuilt from the database on every visit, so changing a row changed the published
    proof, and the public timestamp then vouched for a record that no longer existed. Freezing it here is also
    what lets the payload say **which** document and **which** explanation were understood: those hashes exist
    now, while the artifacts are on disk, and asking for them later would be asking after the fact."""
    from leia.registry import build_payload, payload_hash

    base = get_attempt(hash_imutavel)
    if base is None:
        return
    base = {**base, "pdf_sha256": _document_sha(tarefa_hash), "resumo_sha256": _summary_sha(tarefa_hash)}
    canonical, digest = payload_hash(build_payload(base))
    with Session(engine) as s:
        if s.exec(select(ConsentRecord).where(ConsentRecord.attempt_hash == hash_imutavel)).first():
            return  # já gravado: registro não se reescreve
        s.add(ConsentRecord(attempt_hash=hash_imutavel, document_sha256=base["pdf_sha256"],
                            summary_sha256=base["resumo_sha256"], canonical=canonical, payload_sha256=digest))
        s.commit()


def stored_record(hash_imutavel: str) -> Optional[dict[str, str]]:
    with Session(engine) as s:
        rec = s.exec(select(ConsentRecord).where(ConsentRecord.attempt_hash == hash_imutavel)).first()
    if not rec:
        return None
    return {"canonical": rec.canonical, "payload_sha256": rec.payload_sha256,
            "pdf_sha256": rec.document_sha256, "resumo_sha256": rec.summary_sha256}


def get_attempt(hash_imutavel: str) -> Optional[dict[str, Any]]:
    """Adapter for leia.registry.build_router. Nothing personal reaches the published payload."""
    with Session(engine) as s:
        tent = s.exec(select(Tentativa).where(Tentativa.hash_imutavel == hash_imutavel)).first()
        if not tent:
            return None
        t = s.get(Tarefa, tent.tarefa_id)
    created = tent.criada_em.replace(tzinfo=timezone.utc) if tent.criada_em.tzinfo is None else tent.criada_em
    p = _ots_path(t.hash, tent.numero)
    proof = p.read_bytes() if p.exists() else None
    gravado = stored_record(hash_imutavel) or {}
    import core.attempts as _tn
    # Tarefa de origem "cidadao" não passa por revisão (ver is_gated); tarefa de advogado só chega a ser
    # respondida depois que ele aprova, porque o portão barra antes. Então a origem responde a pergunta.
    revisada = (t.origem or "advogado") != "cidadao"
    dados = {"hash_imutavel": tent.hash_imutavel, "tarefa_hash": t.hash, "numero": tent.numero, "acertos": tent.acertos,
             "total": tent.total, "aprovado": tent.aprovado, "criada_em": created,
             "revisado_por_advogado": revisada, "instrumento": "multiple-choice",
             "piso": _tn.pass_mark(tent.total),
             "pdf_sha256": gravado.get("pdf_sha256", ""), "resumo_sha256": gravado.get("resumo_sha256", ""),
             "registro": gravado or None,
             "ots": proof}
    # O carimbo é sobre o registro publicado: congelado, é o hash gravado; antes de existir registro congelado,
    # é o que o comprovante remonta agora, o mesmo que leia.registry publica. Só é preciso saber o hash quando
    # existe prova para comparar, e remontá-lo custa mais do que abrir a página.
    published = gravado.get("payload_sha256") or (payload_hash(build_payload(dados))[1] if proof else "")
    dados["ots_status"] = ots_status(proof, published, _last_stamp_attempt(t.hash, tent.numero))
    return dados


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
    outcome = ots_stamp(digest)
    if outcome.proof:
        _ots_path(tarefa_hash, numero).write_bytes(outcome.proof)
        ws.record_event(tarefa_hash, "carimbo_publico", numero=numero, payload_hash=digest)
    else:
        # Sem isto o comprovante ficava sem prova e sem explicação: ninguém sabia se os calendários caíram, se
        # o carimbo está desligado ou se nunca foi tentado, e a varredura não tinha o que reler.
        ws.record_event(tarefa_hash, "carimbo_falhou", numero=numero, payload_hash=digest,
                        motivo=outcome.reason, tentativas=outcome.attempts)


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
# A ``lastro`` ref may name another synthesis instead of a memory item, and it names it by task id.
SYNTHESIS_ID_BY_CLASS = {cls: name[: -len(".json")] for name, cls in SYNTHESIS_FILES}


def _item(cls: str, n: int, it: dict[str, Any], texto: str, text_norm: str, idx: list[int], cor: str,
          ui_entry: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """One tagged item, with its position found here over the text. The ``_ui`` position the model writes is
    ignored on purpose (see ``locate``); what still comes from ``_ui`` is the relevance score, which is the
    model's opinion about the item and is labelled as such."""
    quote = it.get("trecho_verbatim") or ""
    found = locate(texto, text_norm, idx, quote)
    # O trecho publicado é a fatia do documento naquela posição, nunca a transcrição do modelo. Medido num
    # agravo real de 14 páginas: a extração do PDF quebra palavra ("compa nhia", "fls.\n52/68"), o modelo
    # normaliza ao transcrever, o locate acha assim mesmo pelo estágio normalizado ou aproximado, e o item
    # saía com a posição do documento e o texto do modelo. Num caso ele trocou 52/68 por 52/66: a pessoa
    # procura no papel um trecho que não está lá, com o selo de conferido ao lado. Publicar a fatia torna
    # ``documento[pos] == trecho`` verdade por construção, que é a promessa do produto escrita em código.
    trecho = texto[found["pos"][0]:found["pos"][1]] if found else quote
    out = {"ref": f"{cls}[{n}]", "campo": it.get("campo"), "valor": it.get("valor"), "trecho": trecho,
           "pos": found["pos"] if found else None, "conferido": bool(found), "cor": cor}
    if found:
        out["conferencia"] = {"metodo": found["metodo"], "score": found["score"]}
    score = _score(ui_entry) if ui_entry else None
    if score is not None:
        out["score"] = score
    return out


def _synthesis_body(raw: Any) -> Optional[dict[str, Any]]:
    """The body of a synthesis file, which wraps its single field under a name the model chose."""
    if not isinstance(raw, dict) or not raw:
        return None
    body = next(iter(raw.values())) if len(raw) == 1 and isinstance(next(iter(raw.values())), dict) else raw
    return body if isinstance(body, dict) else None


def _reaches_document(ref: str, bodies: dict[str, dict[str, Any]], memoria: Any, texto: str, text_norm: str,
                      idx: list[int], seen: set[str]) -> bool:
    """Whether this ``lastro`` ref ends in a quote that exists in the document.

    A ref is either a memory item (``pedidos[0]``) or another synthesis (``T7_SINTESE_FATOS``), and a synthesis
    is worth exactly what the items under it are worth, so the chain is followed to the end. ``seen`` stops the
    day a model writes a synthesis that grounds itself."""
    ref = (ref or "").strip()
    if not ref or ref in seen:
        return False
    seen.add(ref)
    quote = _quote_of(memoria, ref)
    if quote:
        return locate(texto, text_norm, idx, quote) is not None
    body = bodies.get(ref)
    if body is None:
        return False
    return any(_reaches_document(str(r), bodies, memoria, texto, text_norm, idx, seen) for r in (body.get("lastro") or []))


def _syntheses(sinteses_raw: list[tuple[str, Any]], labels: dict[str, tuple[str, str]], memoria: Any, texto: str,
               text_norm: str, idx: list[int]) -> tuple[list[dict[str, Any]], list[str]]:
    """The syntheses that the document sustains, and the classes of the ones dropped on the way.

    A synthesis is a paragraph the model wrote about the case, and the only thing tying it to the document is
    the ``lastro`` it declares. Measured on 17/09/2026, the synthesis of fundamentos of the one public case had
    1293 characters, named six legal provisions and declared ``lastro: []``: it read exactly like the ones that
    are backed, and both the citizen and the lawyer got it. So a declared ref that reaches nothing in the
    document is the same as no ref at all, and neither is published."""
    bodies: dict[str, dict[str, Any]] = {}
    for cls, raw in sinteses_raw or []:
        body = _synthesis_body(raw)
        if body is not None and cls in SYNTHESIS_ID_BY_CLASS:
            bodies[SYNTHESIS_ID_BY_CLASS[cls]] = body
    sinteses, sem_lastro = [], []
    for cls, raw in sinteses_raw or []:
        body = _synthesis_body(raw)
        if body is None:
            continue
        lastro = [str(x) for x in (body.get("lastro") or [])]
        if not any(_reaches_document(ref, bodies, memoria, texto, text_norm, idx, set()) for ref in lastro):
            sem_lastro.append(cls)
            continue
        sinteses.append({"classe": cls, "rotulo": labels.get(cls, ("Contexto do processo", "#E3F1F1"))[0],
                         "texto": body.get("valor") or "", "lastro": lastro})
    return sinteses, sem_lastro


def build_inferences(texto: str, memoria: Any, tagueado: Any, sinteses_raw: list[tuple[str, Any]]) -> dict[str, Any]:
    text_norm, idx = norm_map(texto or "")
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
    sinteses, sem_lastro = _syntheses(sinteses_raw, CLASS_LABELS, memoria, texto or "", text_norm, idx)
    # The discard is declared, not silent: whoever reviews has to see that a synthesis existed and did not
    # make it through, instead of finding an empty space where a paragraph used to be.
    return {"texto": texto or "", "classes": classes, "sinteses": sinteses, "sinteses_sem_lastro": sem_lastro,
            "total": total, "conferidos": conferidos}


@router.get("/api/t/{hash_}/inferencias")
async def api_cliente_inferencias(hash_: str, visitante: Optional[Usuario] = Depends(optional_api_user),
                                  session: Session = Depends(get_session)):
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t:
        raise HTTPException(404, "Link inválido ou expirado")
    invites.ensure_valid(session, t, visitante)
    if is_gated(t):
        raise HTTPException(409, GATE_MESSAGE)
    if t.status in READY_STATUSES:
        return {"tarefa": {"hash": t.hash, "titulo": t.titulo}, **inferences_of(t)}
    if t.status in ("criada", "processando"):
        return {"tarefa": {"hash": t.hash, "titulo": t.titulo}, **partial_inferences_of(t)}
    raise HTTPException(409, "A explicação ainda está sendo preparada")


def inferences_of(t: Tarefa) -> dict[str, Any]:
    """Inference body of a finished task from its workspace artifacts (shared with the lawyer review route).
    """
    memoria = _read_json(t.hash, "memoria_persistente.json")
    texto = _read_artifact(t.hash, "texto_extraido.txt")
    sinteses_raw = [(cls, _read_json(t.hash, name)) for name, cls in SYNTHESIS_FILES]
    return {**build_inferences(texto or "", memoria, _read_json(t.hash, "texto_tagueado.json"), sinteses_raw), "parcial": False}


def partial_inferences_of(t: Tarefa) -> dict[str, Any]:
    """Inference body while the workflow runs: the text once extracted and the classes of the T1..T5 files that
    already exist (each one ``{"<classe>": [itens]}``), plus the syntheses of T7..T11 when present."""
    mem: dict[str, list[Any]] = {}
    for name in FRAGMENT_FILES:
        doc = _read_json(t.hash, name)
        if isinstance(doc, dict):
            for cls, items in doc.items():
                if cls in CLASS_LABELS and isinstance(items, list):
                    mem.setdefault(cls, []).extend(items)
    sinteses_raw = [(cls, _read_json(t.hash, name)) for name, cls in SYNTHESIS_FILES]
    return {**build_inferences(_read_artifact(t.hash, "texto_extraido.txt") or "", {"memoria_persistente": mem}, None, sinteses_raw),
            "parcial": True}
