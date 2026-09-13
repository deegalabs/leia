"""Public JSON for the citizen app and the registry adapter. Included from main.py.

GET /api/t/{hash}: the same data the service renders in /t/{hash}, as JSON and without the answer key.
stamp_attempt(): OpenTimestamps proof of an approved attempt, stored in the task workspace.
get_attempt(): adapter used by leia.registry (receipt and public verification).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

import core.tentativas as tn
import core.workspace as ws
from app_gestao import _ler_artefato, _ler_json
from core.db import Tarefa, Tentativa, engine, get_session
from leia.registry import build_payload, ots_stamp, payload_hash

READY_STATUSES = ("pronta", "enviada", "assinada")
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


@router.get("/api/t/{hash_}")
async def api_cliente_json(hash_: str, session: Session = Depends(get_session)):
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t:
        raise HTTPException(404, "Link inválido ou expirado")
    base = {"tarefa": {"hash": t.hash, "titulo": t.titulo, "status": t.status}, "eventos": ws.ler_eventos(t.hash)[-8:]}
    if t.status not in READY_STATUSES:
        return {**base, "resumo_md": None, "topicos": None, "questoes": [], "ultima_tentativa": None}
    resumo_md = _ler_artefato(t.hash, "resumo_humanizado.md") or ""
    questoes = _ler_json(t.hash, "questoes.json") or {}
    memoria = _ler_json(t.hash, "memoria_persistente.json")
    lista = tn.listar(t.id)
    return {**base, "resumo_md": resumo_md, "topicos": topics_from_summary(resumo_md, memoria),
            "questoes": _public_questions(questoes), "ultima_tentativa": _public_attempt(lista[-1] if lista else None)}


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
