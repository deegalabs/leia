# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   SESSÃO — memória persistente por sessão de login (session_token)       ║
# ║                                                                          ║
# ║   Cada usuário logado tem UM arquivo workspace/_sessoes/{token}.json     ║
# ║   com até 3 "abas" de destilação já processadas:                        ║
# ║     - jurisprudencia                                                     ║
# ║     - resumo_estruturado                                                 ║
# ║     - chat  (destilação de PDF feita direto no Chat Bot)                ║
# ║                                                                           ║
# ║   Só a parte "resumo estruturado" da destilação de cada aba entra no     ║
# ║   anexo compartilhado com o LLM — nunca o PDF, nunca o texto bruto.       ║
# ║                                                                           ║
# ║   A memória do fluxo de PDF ASSINADO (tarefas/cliente) é INTEIRAMENTE    ║
# ║   separada: vive em workspace/{hash}/ e nunca é lida por este módulo.    ║
# ║   Isso garante que ela nunca vaza para o anexo do chat.                  ║
# ║                                                                           ║
# ║   A sessão morre com o login: encerrar_sessao() (logout) já zera o       ║
# ║   session_token do usuário; aqui apagamos também o arquivo associado.    ║
# ╚══════════════════════════════════════════════════════════════════════════╝
from __future__ import annotations
import json, logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

log = logging.getLogger("sessao")

ABAS = ("jurisprudencia", "resumo_estruturado", "chat")
Aba = Literal["jurisprudencia", "resumo_estruturado", "chat"]

from .workspace import BASE as _WORKSPACE_BASE

BASE = _WORKSPACE_BASE / "_sessoes"
BASE.mkdir(parents=True, exist_ok=True)


def _arquivo(token: str) -> Path:
    # token já é um secrets.token_urlsafe(32) — seguro usar como nome de arquivo
    return BASE / f"{token}.json"


def _vazio() -> dict:
    return {aba: None for aba in ABAS}


def carregar(token: str) -> dict:
    """Carrega a memória de sessão (as 3 abas). Nunca inclui PDF assinado."""
    p = _arquivo(token)
    if not p.exists():
        return _vazio()
    try:
        dados = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _vazio()
    base = _vazio()
    base.update({k: v for k, v in dados.items() if k in ABAS})
    return base


def _salvar(token: str, dados: dict) -> None:
    _arquivo(token).write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def registrar_destilacao(
    token: str,
    aba: Aba,
    *,
    hash_: str,
    titulo: str,
    resumo_estruturado: Any,
) -> None:
    """
    Chamado quando uma destilação (jurisprudência / resumo estruturado / chat)
    termina com sucesso. Guarda SÓ a parte "resumo estruturado" — nunca o PDF
    nem o texto bruto — associada à sessão de login corrente.

    Sobrescreve o que já havia nessa aba (uma destilação por aba por vez,
    a mais recente é a que acompanha a conversa).
    """
    if aba not in ABAS:
        raise ValueError(f"aba inválida: {aba}")
    dados = carregar(token)
    dados[aba] = {
        "hash": hash_,
        "titulo": titulo,
        "processado_em": datetime.utcnow().isoformat(),
        "resumo_estruturado": resumo_estruturado,
    }
    _salvar(token, dados)
    log.info("💾 memória de sessão atualizada | token=%s… | aba=%s | hash=%s",
             (token or "")[:8], aba, hash_)


def limpar(token: str, aba: Optional[Aba] = None) -> None:
    """Limpa uma aba específica, ou a sessão inteira se aba=None."""
    if aba is None:
        p = _arquivo(token)
        if p.exists():
            p.unlink()
        return
    dados = carregar(token)
    dados[aba] = None
    _salvar(token, dados)


def encerrar(token: str) -> None:
    """Chamado no logout — a memória de sessão não sobrevive ao login."""
    limpar(token)


# ══════════════════════════════════════════════════════════════════════════
#  ANEXO COMPARTILHADO — o processo estruturado (T6_FUSAO_MEMORIA) da aba
#  que já tiver sido destilada, para acompanhar toda pergunta do usuário.
# ══════════════════════════════════════════════════════════════════════════
def anexo_compartilhado(token: str) -> Optional[dict]:
    """
    Retorna o "processo" (T6_FUSAO_MEMORIA) da destilação mais recente
    disponível nesta sessão — hoje, só a aba "chat" alimenta isso; as
    demais abas ficam prontas para o mesmo tratamento quando entrarem.
    Retorna None se nada foi destilado ainda nesta sessão.

    Formato do retorno: {"titulo": ..., "processo": <T6_FUSAO_MEMORIA>, "hash": ...}
    O "hash" é o hash do workspace/{hash}/ de onde veio a destilação — serve
    para o chat gravar o log de depuração (payload enviado/recebido do LLM)
    junto dos T*.json da mesma sessão de destilação.
    """
    dados = carregar(token)
    for aba in ABAS:
        d = dados.get(aba)
        if d and d.get("resumo_estruturado") is not None:
            return {
                "titulo": d.get("titulo"),
                "processo": d["resumo_estruturado"],
                "hash": d.get("hash"),
            }
    return None


def resumo_abas_processadas(token: str) -> list[dict]:
    """
    Lista curta (para o aviso "arquivo processado e compartilhado nesta
    sessão") com o essencial de cada aba já destilada.
    """
    dados = carregar(token)
    out = []
    for aba in ABAS:
        d = dados.get(aba)
        if d:
            out.append({
                "aba": aba,
                "hash": d.get("hash"),
                "titulo": d.get("titulo"),
                "processado_em": d.get("processado_em"),
            })
    return out
