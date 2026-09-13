from __future__ import annotations
import hashlib, hmac, secrets
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from sqlmodel import Session, select

from .db import Usuario, get_session

_ITERS = 200_000


def hash_senha(senha: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, _ITERS)
    return f"pbkdf2_sha256${_ITERS}${salt.hex()}${dk.hex()}"


def verificar_senha(senha: str, hash_: str) -> bool:
    try:
        alg, iters, salt_hex, dk_hex = hash_.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", senha.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def autenticar(session: Session, email: str, senha: str) -> Optional[Usuario]:
    u = session.exec(select(Usuario).where(Usuario.email == email.strip().lower())).first()
    if not u or not verificar_senha(senha, u.senha_hash):
        return None
    u.session_token = secrets.token_urlsafe(32)
    session.add(u); session.commit(); session.refresh(u)
    return u


def encerrar_sessao(session: Session, u: Usuario) -> None:
    u.session_token = None
    session.add(u); session.commit()


def usuario_atual(
    sessao: Optional[str] = Cookie(default=None, alias="sessao"),
    session: Session = Depends(get_session),
) -> Usuario:
    if not sessao:
        raise HTTPException(status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    u = session.exec(select(Usuario).where(Usuario.session_token == sessao)).first()
    if not u:
        raise HTTPException(status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return u


def criar_usuario_inicial(session: Session, email: str, senha: str, nome: str, papel: str):
    """Usado no primeiro boot para criar o dono do sistema."""
    if session.exec(select(Usuario).where(Usuario.email == email.lower())).first():
        return None
    u = Usuario(email=email.lower(), senha_hash=hash_senha(senha), nome=nome, papel=papel)
    session.add(u); session.commit(); session.refresh(u)
    return u