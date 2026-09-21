"""Accounts for the app (Bearer token): signup, login, me, logout. Included from main.py.

The token is ``Usuario.session_token`` (one per user; a new login rotates it). ``papel`` is ``cidadao``,
``advogado`` (only while ADVOGADO_SIGNUP is true) or ``fornecedor`` (admin, created from ADMIN_EMAIL only).
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from core.auth import authenticate, end_session, hash_password, api_user
from core.db import Usuario, get_session
from leia.ratelimit import rate_limit

router = APIRouter()

PAPEIS_CADASTRO = ("cidadao", "advogado")


class CadastroIn(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    senha: str = Field(min_length=6, max_length=200)
    papel: str = "cidadao"
    oab: Optional[str] = Field(default=None, max_length=40)


class LoginIn(BaseModel):
    email: str
    senha: str


def public_user(u: Usuario) -> dict:
    """The key is always there, and it is null for whoever has no number.

    A citizen account carries no OAB, so the screen that reads this never has to ask whose account it is
    before deciding what to show: no number, no claim."""
    return {"id": u.id, "nome": u.nome, "email": u.email, "papel": u.papel, "oab": u.oab}


def advogado_signup_enabled() -> bool:
    return os.getenv("ADVOGADO_SIGNUP", "true").lower() in ("1", "true", "yes")


@router.post("/api/auth/cadastro", dependencies=[Depends(rate_limit)])
def cadastro(body: CadastroIn, session: Session = Depends(get_session)):
    papel = body.papel.strip().lower()
    if papel not in PAPEIS_CADASTRO:
        raise HTTPException(403, "Este tipo de conta não pode ser criado por aqui.")
    if papel == "advogado" and not advogado_signup_enabled():
        raise HTTPException(403, "O cadastro de advogados está fechado no momento.")
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(422, "Informe um e-mail válido.")
    if session.exec(select(Usuario).where(Usuario.email == email)).first():
        raise HTTPException(409, "Já existe uma conta com este e-mail.")
    # O número só é guardado em conta de advogado. Numa conta de cidadã ele não afirma nada e seria mais um
    # dado pessoal parado no banco, então é descartado aqui, onde se sabe o papel.
    oab = (body.oab or "").strip() if papel == "advogado" else ""
    u = Usuario(email=email, senha_hash=hash_password(body.senha), nome=body.nome.strip(), papel=papel,
                oab=oab or None)
    session.add(u); session.commit(); session.refresh(u)
    u = authenticate(session, email, body.senha)  # issues the first token
    return {"token": u.session_token, "usuario": public_user(u)}


@router.post("/api/auth/login", dependencies=[Depends(rate_limit)])
def login(body: LoginIn, session: Session = Depends(get_session)):
    email = body.email.strip().lower()
    u = authenticate(session, email, body.senha)
    if not u:
        raise HTTPException(401, "E-mail ou senha não conferem.")
    return {"token": u.session_token, "usuario": public_user(u)}


@router.get("/api/auth/me")
def me(u: Usuario = Depends(api_user)):
    return {"usuario": public_user(u)}


@router.post("/api/auth/logout")
def logout(u: Usuario = Depends(api_user), session: Session = Depends(get_session)):
    end_session(session, u)
    return {"ok": True}
