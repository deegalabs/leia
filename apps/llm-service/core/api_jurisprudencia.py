# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   API — cliente da API pública externa de PESQUISA DE JURISPRUDÊNCIA      ║
# ║   Espelha core/api.py (Resumo Estruturado): mesmo contrato submit/status/  ║
# ║   result, mesmo padrão de persistência em workspace/{hash}/.              ║
# ╚══════════════════════════════════════════════════════════════════════════╝
from __future__ import annotations
import os, json, time, asyncio, logging
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlmodel import Session

from core.db import engine, Tarefa, LogEvento
from core.workspace import pasta, registrar_evento

log = logging.getLogger("jurisprudencia")

JURISPRUDENCIA_API_BASE = os.getenv(
    "JURISPRUDENCIA_API_BASE",
    "https://api.jurisprudencia.com.br",
)

POLL_INTERVAL = 1.5
POLL_TIMEOUT  = 600.0


class JurisprudenciaError(Exception):
    """Erro de comunicação com a API pública externa de jurisprudência."""


# ══════════════════════════════════════════════════════════════════════════
#  CHAMADAS CRUAS
# ══════════════════════════════════════════════════════════════════════════
async def submeter(
    pdf_bytes: Optional[bytes] = None,
    texto: Optional[str] = None,
    filename: str = "documento.pdf",
    consulta: Optional[str] = None,
) -> dict:
    """POST /submit — envia PDF, texto ou apenas uma consulta textual de pesquisa."""
    if not pdf_bytes and not (texto and texto.strip()) and not (consulta and consulta.strip()):
        raise JurisprudenciaError("Envie um PDF, um texto ou uma consulta de pesquisa.")

    data: dict[str, Any] = {}
    if consulta:
        data["consulta"] = consulta
    files = None
    if pdf_bytes:
        files = {"file": (filename, pdf_bytes, "application/pdf")}
    elif texto:
        data["text"] = texto

    async with httpx.AsyncClient(base_url=JURISPRUDENCIA_API_BASE, timeout=60.0) as cli:
        r = await cli.post("/submit", data=data, files=files)
        if r.status_code >= 400:
            raise JurisprudenciaError(f"submit falhou ({r.status_code}): {r.text[:300]}")
        return r.json()


async def consultar_status(job_id: str) -> dict:
    async with httpx.AsyncClient(base_url=JURISPRUDENCIA_API_BASE, timeout=30.0) as cli:
        r = await cli.get(f"/status/{job_id}")
        if r.status_code >= 400:
            raise JurisprudenciaError(f"status falhou ({r.status_code}): {r.text[:300]}")
        return r.json()


async def obter_resultado(job_id: str) -> dict:
    async with httpx.AsyncClient(base_url=JURISPRUDENCIA_API_BASE, timeout=60.0) as cli:
        r = await cli.get(f"/result/{job_id}")
        if r.status_code >= 400:
            raise JurisprudenciaError(f"result falhou ({r.status_code}): {r.text[:300]}")
        return r.json()


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS DE PERSISTÊNCIA (mesmo padrão de core/api.py)
# ══════════════════════════════════════════════════════════════════════════
def _atualizar_status(tarefa_id: int, status_: str) -> None:
    with Session(engine) as s:
        t = s.get(Tarefa, tarefa_id)
        if not t:
            return
        t.status = status_
        t.atualizada_em = datetime.utcnow()
        s.add(t)
        s.add(LogEvento(tarefa_id=tarefa_id, tipo=f"status:{status_}", payload=None))
        s.commit()


def _salvar_json(hash_: str, nome: str, conteudo: Any) -> None:
    (pasta(hash_) / nome).write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ══════════════════════════════════════════════════════════════════════════
#  ORQUESTRAÇÃO
# ══════════════════════════════════════════════════════════════════════════
async def executar_jurisprudencia(
    tarefa_id: int,
    pdf_bytes: Optional[bytes] = None,
    texto: Optional[str] = None,
    consulta: Optional[str] = None,
    filename: str = "documento.pdf",
    session_token: Optional[str] = None,
) -> None:
    """
    Entry-point chamado por BackgroundTasks a partir de
    POST /api/jurisprudencia/submit.

    Envia para a API externa de jurisprudência, aguarda concluir e salva
    o resultado (dados_llm / doc_text) no workspace da tarefa. Ao concluir
    com sucesso, registra a parte "resumo estruturado" na memória de sessão
    do usuário (aba "jurisprudencia"), se um session_token foi informado.
    """
    with Session(engine) as s:
        t = s.get(Tarefa, tarefa_id)
        if not t:
            log.error("Tarefa %s não encontrada", tarefa_id)
            return
        hash_ = t.hash
        titulo = t.titulo

    log.info("═" * 70)
    log.info("🎬 JURISPRUDÊNCIA (API externa) | tarefa_id=%s", tarefa_id)

    _atualizar_status(tarefa_id, "processando")
    registrar_evento(hash_, "jurisprudencia_start", tarefa_id=tarefa_id)

    # ── 1. Envia para a API externa
    try:
        envio = await submeter(pdf_bytes=pdf_bytes, texto=texto, filename=filename, consulta=consulta)
    except Exception as e:
        log.error("💥 submit falhou | %s", e)
        _atualizar_status(tarefa_id, "falhou")
        registrar_evento(hash_, "jurisprudencia_erro", etapa="submit", erro=str(e))
        return

    job_id = envio.get("job_id")
    total_steps = envio.get("total_steps")
    if not job_id:
        log.error("💥 API externa não retornou job_id | %s", envio)
        _atualizar_status(tarefa_id, "falhou")
        registrar_evento(hash_, "jurisprudencia_erro", etapa="submit",
                         erro="resposta sem job_id")
        return

    registrar_evento(hash_, "jurisprudencia_job", job_id=job_id, total_steps=total_steps)
    _salvar_json(hash_, "jurisprudencia_job.json", envio)

    # ── 2. Poll até status == done | error | timeout
    t0 = time.time()
    while True:
        if time.time() - t0 > POLL_TIMEOUT:
            log.error("💥 timeout aguardando job %s", job_id)
            _atualizar_status(tarefa_id, "falhou")
            registrar_evento(hash_, "jurisprudencia_erro", etapa="timeout", job_id=job_id)
            return

        await asyncio.sleep(POLL_INTERVAL)
        try:
            st = await consultar_status(job_id)
        except Exception as e:
            log.warning("⚠️  status falhou, tentando de novo | %s", e)
            continue

        registrar_evento(
            hash_, "jurisprudencia_status",
            step=st.get("current_step"), idx=st.get("step_index"),
            total=st.get("total_steps"), status=st.get("status"),
            tokens=st.get("tokens_total"), elapsed=st.get("elapsed"),
        )

        if st.get("status") == "error":
            log.error("💥 job %s falhou | %s", job_id, st.get("error"))
            _atualizar_status(tarefa_id, "falhou")
            registrar_evento(hash_, "jurisprudencia_erro", etapa="job",
                             erro=st.get("error"))
            return

        if st.get("status") == "done":
            break

    # ── 3. Resultado final
    try:
        res = await obter_resultado(job_id)
    except Exception as e:
        log.error("💥 result falhou | %s", e)
        _atualizar_status(tarefa_id, "falhou")
        registrar_evento(hash_, "jurisprudencia_erro", etapa="result", erro=str(e))
        return

    dados_llm = res.get("dados_llm")
    _salvar_json(hash_, "jurisprudencia_resultado.json", dados_llm)
    if res.get("doc_text"):
        (pasta(hash_) / "jurisprudencia_texto.txt").write_text(
            str(res["doc_text"]), encoding="utf-8"
        )

    _atualizar_status(tarefa_id, "pronta")
    registrar_evento(
        hash_, "jurisprudencia_done",
        tokens=res.get("tokens_total"), elapsed=res.get("elapsed"),
    )

    # ── 4. Memória de sessão — só a parte "resumo estruturado", nunca o PDF
    if session_token:
        from core import sessao as sess
        sess.registrar_destilacao(
            session_token, "jurisprudencia",
            hash_=hash_, titulo=titulo, resumo_estruturado=dados_llm,
        )

    log.info("🏁 JURISPRUDÊNCIA concluída | tarefa=%s job=%s", tarefa_id, job_id)
