from __future__ import annotations
import hashlib, hmac, secrets
from typing import Optional

from fastapi import HTTPException, Cookie, Depends, Header, HTTPException, status
from sqlmodel import Session, select

from .db import Usuario, get_session

_ITERS = 200_000


def hash_password(senha: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, _ITERS)
    return f"pbkdf2_sha256${_ITERS}${salt.hex()}${dk.hex()}"


def verify_password(senha: str, hash_: str) -> bool:
    try:
        alg, iters, salt_hex, dk_hex = hash_.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", senha.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def authenticate(session: Session, email: str, senha: str) -> Optional[Usuario]:
    u = session.exec(select(Usuario).where(Usuario.email == email.strip().lower())).first()
    if not u or not verify_password(senha, u.senha_hash):
        return None
    u.session_token = secrets.token_urlsafe(32)
    session.add(u); session.commit(); session.refresh(u)
    return u


def end_session(session: Session, u: Usuario) -> None:
    u.session_token = None
    session.add(u); session.commit()


# LeIA: "Authorization: Bearer <token>" is accepted next to the cookie (the app runs on another origin).
def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token.strip() or ""


def _resolve_user(session: Session, sessao: Optional[str], authorization: Optional[str],
                      sem_credencial_redireciona: bool) -> Usuario:
    bearer = _bearer_token(authorization)
    if bearer is not None:
        u = session.exec(select(Usuario).where(Usuario.session_token == bearer)).first() if bearer else None
        if not u:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada. Entre de novo.")
        return u
    if not sessao:
        if sem_credencial_redireciona:
            raise HTTPException(status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Entre na sua conta para continuar.")
    u = session.exec(select(Usuario).where(Usuario.session_token == sessao)).first()
    if not u:
        if sem_credencial_redireciona:
            raise HTTPException(status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada. Entre de novo.")
    return u


def current_user(
    sessao: Optional[str] = Cookie(default=None, alias="sessao"),
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> Usuario:
    """Cookie or Bearer. Without any credential: 303 to /login (templates). Invalid Bearer: 401 JSON."""
    return _resolve_user(session, sessao, authorization, sem_credencial_redireciona=True)


# LeIA: same resolution for the JSON API, but 401 instead of a redirect when nothing is sent
def api_user(
    sessao: Optional[str] = Cookie(default=None, alias="sessao"),
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> Usuario:
    return _resolve_user(session, sessao, authorization, sem_credencial_redireciona=False)


# LeIA: o cadastro de cidadã é aberto por desenho, então estar logado não é barreira nenhuma.
# As rotas de bastidor (protocolo, contexto, chat interno) exigem o papel de fornecedor.
def admin_user(u: Usuario = Depends(api_user)) -> Usuario:
    if u.papel != "fornecedor":
        raise HTTPException(status_code=403, detail="Rota restrita ao fornecedor.")
    return u


def create_initial_user(session: Session, email: str, senha: str, nome: str, papel: str):
    """Usado no primeiro boot para criar o dono do sistema."""
    if session.exec(select(Usuario).where(Usuario.email == email.lower())).first():
        return None
    u = Usuario(email=email.lower(), senha_hash=hash_password(senha), nome=nome, papel=papel)
    session.add(u); session.commit(); session.refresh(u)
    return u