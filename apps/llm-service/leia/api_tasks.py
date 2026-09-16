"""Tasks (documents) of the signed-in user, for the app panel (Bearer). Included from main.py.

Visibility (docs/API-V3-CONTRACT.md): ``fornecedor`` sees every task, ``advogado`` the ones they sent,
``cidadao`` the ones they sent plus the ones linked to them (``tarefa.cidadao_id``).

Lawyer review (contract section "Revisão do advogado antes de liberar"): GET /api/tarefas/{id}/revisao returns what
the workflow extracted and concluded, including the answer key; POST /api/tarefas/{id}/aprovar moves the task from
``pronta`` to ``enviada`` and releases the public link to the citizen.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional

from leia.ratelimit import rate_limit  # LeIA: per-IP limit on uploads
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

import core.attempts as tn
import core.workspace as ws
from app_gestao import _read_artifact, _read_json, _permite_ver, create_pdf_task
from core.auth import api_user
from leia.api_citizen import inferences_of, public_events  # LeIA: no ip/ua in the JSON
from leia import invites  # LeIA: the invite that governs the document link
from core.db import Duvida, LogEvento, Tarefa, Tentativa, Usuario, get_session

READY_STATUSES = ("pronta", "enviada", "assinada")
router = APIRouter()


class RespostaIn(BaseModel):
    resposta: str = Field(min_length=1, max_length=8000)


def client_link(request: Request, t: Tarefa) -> str:
    return (os.getenv("CLIENT_APP_URL") or str(request.base_url)).rstrip("/") + f"/t/{t.hash}"


def can_manage(u: Usuario, t: Tarefa) -> bool:
    """Owner or admin: answers doubts."""
    return u.papel == "fornecedor" or t.advogado_id == u.id


def _name(u: Optional[Usuario]) -> Optional[dict[str, Any]]:
    return {"nome": u.nome} if u else None


def people(session: Session, t: Tarefa, users: Optional[dict[int, Usuario]] = None) -> tuple[Optional[dict], Optional[dict]]:
    """(cidadao, advogado) as ``{nome}`` or null. The owner counts as lawyer unless their papel is cidadao."""
    users = users if users is not None else {}
    owner = users.get(t.advogado_id) or session.get(Usuario, t.advogado_id)
    citizen = (users.get(t.cidadao_id) or session.get(Usuario, t.cidadao_id)) if t.cidadao_id else None
    advogado = _name(owner) if owner and owner.papel != "cidadao" else None
    return _name(citizen), advogado


def attempt_json(t: Optional[Tentativa]) -> Optional[dict[str, Any]]:
    if not t:
        return None
    return {"aprovado": t.aprovado, "acertos": t.acertos, "total": t.total, "numero": t.numero}


def doubt_json(d: Duvida) -> dict[str, Any]:
    try:
        contexto = json.loads(d.contexto) if d.contexto else None
    except Exception:
        contexto = None
    return {"id": d.id, "texto": d.texto, "contexto": contexto, "criada_em": d.criada_em.isoformat(),
            "respondida": d.respondida, "resposta": d.resposta,
            "respondida_em": d.respondida_em.isoformat() if d.respondida_em else None}


def task_json(t: Tarefa) -> dict[str, Any]:
    return {"id": t.id, "hash": t.hash, "titulo": t.titulo, "status": t.status,
            "criada_em": t.criada_em.isoformat(), "atualizada_em": t.atualizada_em.isoformat(),
            "origem": t.origem or "advogado"}


@router.get("/api/tarefas")
def list_tasks(request: Request, u: Usuario = Depends(api_user), session: Session = Depends(get_session)):
    q = select(Tarefa).order_by(Tarefa.criada_em.desc())   # type: ignore
    if u.papel == "advogado":
        q = q.where(Tarefa.advogado_id == u.id)
    elif u.papel != "fornecedor":
        q = q.where((Tarefa.advogado_id == u.id) | (Tarefa.cidadao_id == u.id))
    tasks = list(session.exec(q).all())
    if not tasks:
        return {"tarefas": []}

    ids = [t.id for t in tasks]
    user_ids = {t.advogado_id for t in tasks} | {t.cidadao_id for t in tasks if t.cidadao_id}
    users = {x.id: x for x in session.exec(select(Usuario).where(Usuario.id.in_(user_ids))).all()}   # type: ignore
    last_attempt: dict[int, Tentativa] = {}
    for a in session.exec(select(Tentativa).where(Tentativa.tarefa_id.in_(ids)).order_by(Tentativa.numero)).all():   # type: ignore
        last_attempt[a.tarefa_id] = a
    open_doubts = dict(session.exec(
        select(Duvida.tarefa_id, func.count(Duvida.id)).where(Duvida.tarefa_id.in_(ids), Duvida.respondida == False)   # type: ignore  # noqa: E712
        .group_by(Duvida.tarefa_id)).all())

    out = []
    for t in tasks:
        cidadao, advogado = people(session, t, users)
        out.append({**task_json(t), "link_cliente": client_link(request, t),
                    "ultima_tentativa": attempt_json(last_attempt.get(t.id)),
                    "duvidas_abertas": int(open_doubts.get(t.id, 0)), "cidadao": cidadao, "advogado": advogado})
    return {"tarefas": out}


@router.post("/api/tarefas", status_code=201, dependencies=[Depends(rate_limit)])
async def create_task(bg: BackgroundTasks, titulo: str = Form(""), pdf: UploadFile = File(...),
                      u: Usuario = Depends(api_user), session: Session = Depends(get_session)):
    is_citizen = u.papel == "cidadao"
    t = await create_pdf_task(session, u, titulo, pdf, bg,
                              origem="cidadao" if is_citizen else "advogado",
                              cidadao_id=u.id if is_citizen else None)
    return {"id": t.id, "hash": t.hash, "status": t.status}


def _load_visible(session: Session, u: Usuario, tarefa_id: int) -> Tarefa:
    t = session.get(Tarefa, tarefa_id)
    if not t:
        raise HTTPException(404, "Documento não encontrado")
    if not _permite_ver(u, t):
        raise HTTPException(403, "Você não tem acesso a este documento")
    return t


@router.get("/api/tarefas/{tarefa_id}")
def get_task(tarefa_id: int, request: Request, u: Usuario = Depends(api_user),
             session: Session = Depends(get_session)):
    t = _load_visible(session, u, tarefa_id)
    cidadao, advogado = people(session, t)
    attempts = [{"numero": a.numero, "acertos": a.acertos, "total": a.total, "aprovado": a.aprovado,
                 "criada_em": a.criada_em.isoformat(), "hash_imutavel": a.hash_imutavel} for a in tn.list_all(t.id)]
    doubts = session.exec(select(Duvida).where(Duvida.tarefa_id == t.id).order_by(Duvida.criada_em)).all()   # type: ignore
    return {"tarefa": task_json(t), "link_cliente": client_link(request, t),
            "convite": invites.to_json(invites.active_invite(session, t.id)),
            "resumo_md": (_read_artifact(t.hash, "resumo_humanizado.md") or "") if t.status in READY_STATUSES else None,
            "eventos": public_events(ws.read_events(t.hash), 20), "tentativas": attempts,
            "duvidas": [doubt_json(d) for d in doubts], "cidadao": cidadao, "advogado": advogado}


class ConviteIn(BaseModel):
    email: Optional[str] = None
    validade_horas: Optional[int] = None


def _owned(session: Session, u: Usuario, tarefa_id: int) -> Tarefa:
    """Only whoever sent the document decides who may open it."""
    t = session.get(Tarefa, tarefa_id)
    if not t or t.advogado_id != u.id:
        raise HTTPException(404, "Documento não encontrado")
    return t


@router.post("/api/tarefas/{tarefa_id}/convite")
def issue_invite(tarefa_id: int, body: ConviteIn, u: Usuario = Depends(api_user),
                 session: Session = Depends(get_session)):
    t = _owned(session, u, tarefa_id)
    inv = invites.issue(session, t, u, email=body.email, hours=body.validade_horas)
    ws.record_event(t.hash, "convite_emitido", convite_id=inv.id, com_destinataria=bool(inv.email))
    return invites.to_json(inv)


@router.delete("/api/tarefas/{tarefa_id}/cidadao")
def unlink_citizen(tarefa_id: int, u: Usuario = Depends(api_user), session: Session = Depends(get_session)):
    """Desfaz o vínculo. Sem isto, uma conta errada ficava com o documento para sempre e a destinatária
    legítima recebia 409 no próprio documento dela."""
    t = _owned(session, u, tarefa_id)
    if t.cidadao_id is None:
        raise HTTPException(404, "Este documento não está vinculado a ninguém.")
    # A tentativa pertence à tarefa, não à pessoa: trocar a conta vinculada por cima de uma tentativa faria
    # a próxima cidadã herdar o comprovante da anterior, que afirma que **outra** pessoa entendeu o documento.
    # Desvincular serve para consertar vínculo errado, e vínculo errado se descobre antes de alguém responder.
    from core.db import Tentativa
    if session.exec(select(Tentativa).where(Tentativa.tarefa_id == t.id)).first() is not None:
        raise HTTPException(409, "Este documento já tem conferência registrada nesta conta. Envie o documento "
                                 "de novo para a outra pessoa, em vez de trocar quem está vinculado aqui.")
    t.cidadao_id = None
    session.add(t); session.commit()
    ws.record_event(t.hash, "cidadao_desvinculado")
    return {"ok": True}


@router.delete("/api/tarefas/{tarefa_id}/convite")
def revoke_invite(tarefa_id: int, u: Usuario = Depends(api_user), session: Session = Depends(get_session)):
    t = _owned(session, u, tarefa_id)
    inv = invites.active_invite(session, t.id)
    if inv is None:
        raise HTTPException(404, "Este documento não tem convite para cancelar.")
    invites.revoke(session, inv)
    ws.record_event(t.hash, "convite_revogado", convite_id=inv.id)
    return invites.to_json(inv)


@router.post("/api/tarefas/{tarefa_id}/duvidas/{duvida_id}/responder")
def answer_doubt(tarefa_id: int, duvida_id: int, body: RespostaIn, u: Usuario = Depends(api_user),
                 session: Session = Depends(get_session)):
    t = _load_visible(session, u, tarefa_id)
    if not can_manage(u, t):
        raise HTTPException(403, "Só quem enviou o documento pode responder")
    d = session.get(Duvida, duvida_id)
    if not d or d.tarefa_id != t.id:
        raise HTTPException(404, "Dúvida não encontrada")
    d.resposta = body.resposta.strip()
    d.respondida = True
    d.respondida_em = datetime.utcnow()
    session.add(d); session.commit()
    ws.record_event(t.hash, "duvida_respondida", duvida_id=d.id, por=u.id)
    return {"ok": True}


# ── lawyer review before releasing the link to the citizen ────────────────

def review_questions(doc: Any) -> list[dict[str, Any]]:
    """Every question with its answer key. Lawyer-only: never reuse this in a public route."""
    items = doc.get("questoes", []) if isinstance(doc, dict) else []
    return [{"id": q.get("id"), "area": q.get("area"), "dificuldade": q.get("dificuldade"), "enunciado": q.get("enunciado"),
             "alternativas": q.get("alternativas", []), "correta": q.get("correta"), "justificativa": q.get("justificativa")}
            for q in items if isinstance(q, dict)]


@router.get("/api/tarefas/{tarefa_id}/revisao")
def review_task(tarefa_id: int, request: Request, u: Usuario = Depends(api_user),
                session: Session = Depends(get_session)):
    t = _load_visible(session, u, tarefa_id)
    if not can_manage(u, t):
        raise HTTPException(403, "Só quem enviou o documento pode revisar")
    if t.status in ("criada", "processando"):
        raise HTTPException(409, "A explicação ainda está sendo preparada")
    return {"tarefa": {"id": t.id, "hash": t.hash, "titulo": t.titulo, "status": t.status, "origem": t.origem or "advogado"},
            "inferencias": {"tarefa": {"hash": t.hash, "titulo": t.titulo}, **inferences_of(t)},
            "resumo_md": _read_artifact(t.hash, "resumo_humanizado.md") or "",
            "questoes": review_questions(_read_json(t.hash, "questoes.json") or {}),
            "link_cliente": client_link(request, t)}


@router.post("/api/tarefas/{tarefa_id}/aprovar")
def approve_task(tarefa_id: int, u: Usuario = Depends(api_user), session: Session = Depends(get_session)):
    t = _load_visible(session, u, tarefa_id)
    if not can_manage(u, t):
        raise HTTPException(403, "Só quem enviou o documento pode aprovar")
    if t.status != "pronta":
        raise HTTPException(409, "O documento não está pronto para aprovação")
    t.status = "enviada"
    t.atualizada_em = datetime.utcnow()
    session.add(t)
    session.add(LogEvento(tarefa_id=t.id, tipo="aprovada", payload=json.dumps({"usuario_id": u.id})))
    session.commit()
    ws.record_event(t.hash, "aprovada", usuario_id=u.id)
    return {"ok": True, "status": "enviada"}
