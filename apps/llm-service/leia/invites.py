"""The invite that governs a document link.

Until now the link was a bearer credential: whoever had the address opened the document, forever, and
nobody could take that back. An invite adds the three things that were missing: an end date, a way to
cancel, and, when whoever sent it knows the address, a single person it is addressed to.

A document with no invite behaves exactly as before, so links that already circulated keep working.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from core.db import Invite, Tarefa, Usuario

DEFAULT_HOURS = 30 * 24


def normalize_email(email: Optional[str]) -> Optional[str]:
    e = (email or "").strip().lower()
    return e or None


def active_invite(session: Session, task_id: int) -> Optional[Invite]:
    """The last invite issued for the document. Issuing a new one supersedes the previous."""
    return session.exec(
        select(Invite).where(Invite.task_id == task_id).order_by(Invite.id.desc())  # type: ignore[arg-type]
    ).first()


def issue(session: Session, t: Tarefa, by: Usuario, email: Optional[str] = None,
          hours: Optional[int] = None) -> Invite:
    horas = DEFAULT_HOURS if hours is None else max(1, int(hours))
    inv = Invite(task_id=t.id, email=normalize_email(email), created_by=by.id,
                 expires_at=datetime.utcnow() + timedelta(hours=horas))
    session.add(inv)
    session.commit()
    session.refresh(inv)
    return inv


def revoke(session: Session, inv: Invite) -> Invite:
    if inv.revoked_at is None:
        inv.revoked_at = datetime.utcnow()
        session.add(inv)
        session.commit()
        session.refresh(inv)
    return inv


def to_json(inv: Optional[Invite]) -> Optional[dict]:
    if inv is None:
        return None
    return {"id": inv.id, "email": inv.email,
            "expira_em": inv.expires_at.isoformat() if inv.expires_at else None,
            "revogado_em": inv.revoked_at.isoformat() if inv.revoked_at else None,
            "criado_em": inv.created_at.isoformat()}


def masked(email: Optional[str]) -> Optional[str]:
    """A hint, not the address: enough for the person to recognise their own e-mail, not enough to collect it."""
    if not email or "@" not in email:
        return None
    user, _, domain = email.partition("@")
    return f"{user[:2]}***@{domain}"


def public_json(session: Session, t: Tarefa) -> Optional[dict]:
    """What the citizen's screen needs to know about the invite, and nothing more."""
    inv = active_invite(session, t.id)
    if inv is None or inv.revoked_at is not None:
        return None
    return {"enderecado": bool(inv.email), "para": masked(inv.email),
            "expira_em": inv.expires_at.isoformat() if inv.expires_at else None}


def _mine(t: Tarefa, visitor: Optional[Usuario]) -> bool:
    return visitor is not None and visitor.id in (t.advogado_id, t.cidadao_id)


def ensure_valid(session: Session, t: Tarefa, visitor: Optional[Usuario] = None) -> None:
    """Whether the link still works at all. This is about the link, not about who is holding it,
    so it applies to reading, asking and everything else, with or without an account."""
    if _mine(t, visitor):
        return
    inv = active_invite(session, t.id)
    if inv is None:
        return
    if inv.revoked_at is not None:
        raise HTTPException(403, "Este link foi cancelado por quem enviou o documento.")
    if inv.expires_at is not None and inv.expires_at <= datetime.utcnow():
        raise HTTPException(403, "Este link venceu. Peça um novo a quem enviou o documento.")


def ensure_recipient(session: Session, t: Tarefa, visitor: Optional[Usuario]) -> None:
    """Only for what produces the record or ties the document to an account.

    Reading and asking stay open to whoever holds a valid link, on purpose: requiring an account to read is a
    barrier for exactly the person this is for, who may be on a borrowed phone. What the addressee protects is
    the receipt, which claims that one named person understood the document."""
    ensure_valid(session, t, visitor)
    if _mine(t, visitor):
        return
    inv = active_invite(session, t.id)
    if inv is None or not inv.email:
        return
    if visitor is None:
        raise HTTPException(403, "Para guardar o comprovante, entre com o e-mail que recebeu este documento.")
    if normalize_email(visitor.email) != inv.email:
        raise HTTPException(403, "Este documento foi enviado para outra pessoa, então o comprovante não pode sair nesta conta.")
