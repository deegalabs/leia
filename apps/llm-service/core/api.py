# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   API — cliente da API pública externa api.resumoestruturado.com.br              ║
# ║   Usado SOMENTE pelo endpoint inferencia dados em  "Resumo Estruturado"    ║
# ║   nº 42/2026). Não passa pelo Groq/protocolo_pdf.json local — quem            ║
# ║   decompõe o documento é o backend externo. Aqui só orquestramos o         ║
# ║   envio/acompanhamento e salvamos o resultado no workspace/{hash}/,          ║
# ║   no mesmo padrão usado pelo pipeline_pdf.py.                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝
from __future__ import annotations
import os, json, time, asyncio, logging
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlmodel import Session

from core.db import engine, Tarefa, LogEvento
from core.workspace import pasta, registrar_evento

log = logging.getLogger("pesquisa")

# API pública, sem chave. O front-end original (BeeROOT) usa caminho relativo
# "/api", servido pelo próprio domínio do produto
#   RESUMO_ESTRUTURADO_API_BASE=https://api.resumoestruturado.com.br
RESUMO_API_BASE = os.getenv(
    "RESUMO_ESTRUTURADO_API_BASE",
    "https://api.resumoestruturado.com.br",
)

POLL_INTERVAL = float(os.getenv("EXTERNAL_POLL_INTERVAL", "1.5"))
POLL_TIMEOUT = float(os.getenv("EXTERNAL_POLL_TIMEOUT", "600"))
HTTP_TIMEOUT = float(os.getenv("EXTERNAL_HTTP_TIMEOUT", "60"))


class ResumoEstruturadoError(Exception):
    """Erro de comunicação com a API pública externa."""


# ══════════════════════════════════════════════════════════════════════════
#  CHAMADAS CRUAS — espelham exatamente o contrato usado pelo front BeeROOT
# ══════════════════════════════════════════════════════════════════════════
async def submeter(
    pdf_bytes: Optional[bytes] = None,
    texto: Optional[str] = None,
    filename: str = "documento.pdf",
    enable_synthesis: bool = True,
    reasoning_effort: str = "medium",
    modo_disparo: str = "paralelo",
) -> dict:
    """POST /submit — envia PDF (arquivo) ou texto bruto. Retorna {job_id, total_steps}."""
    if not pdf_bytes and not (texto and texto.strip()):
        raise ResumoEstruturadoError("Envie um PDF ou um texto.")

    data = {
        "enable_synthesis": "true" if enable_synthesis else "false",
        "reasoning_effort": reasoning_effort,
        "modo_disparo": modo_disparo,
    }
    files = None
    if pdf_bytes:
        files = {"file": (filename, pdf_bytes, "application/pdf")}
    else:
        data["text"] = texto

    async with httpx.AsyncClient(base_url=RESUMO_API_BASE, timeout=HTTP_TIMEOUT) as cli:
        r = await cli.post("/submit", data=data, files=files)
        if r.status_code >= 400:
            raise ResumoEstruturadoError(f"submit falhou ({r.status_code}): {r.text[:300]}")
        return r.json()


async def consultar_status(job_id: str) -> dict:
    """GET /status/{job_id}"""
    async with httpx.AsyncClient(base_url=RESUMO_API_BASE, timeout=HTTP_TIMEOUT / 2) as cli:
        r = await cli.get(f"/status/{job_id}")
        if r.status_code >= 400:
            raise ResumoEstruturadoError(f"status falhou ({r.status_code}): {r.text[:300]}")
        return r.json()


async def obter_resultado(job_id: str) -> dict:
    """GET /result/{job_id}"""
    async with httpx.AsyncClient(base_url=RESUMO_API_BASE, timeout=HTTP_TIMEOUT) as cli:
        r = await cli.get(f"/result/{job_id}")
        if r.status_code >= 400:
            raise ResumoEstruturadoError(f"result falhou ({r.status_code}): {r.text[:300]}")
        return r.json()


async def rerun_step(job_id: str, step_id: str) -> dict:
    """POST /jobs/{job_id}/rerun/{step_id}"""
    async with httpx.AsyncClient(base_url=RESUMO_API_BASE, timeout=HTTP_TIMEOUT / 2) as cli:
        r = await cli.post(f"/jobs/{job_id}/rerun/{step_id}")
        if r.status_code >= 400:
            raise ResumoEstruturadoError(f"rerun falhou ({r.status_code}): {r.text[:300]}")
        return r.json()


async def exportar_pdf(dados_llm: Any, doc_text: str, subtitulo: Optional[str] = None) -> bytes:
    """POST /export-pdf — devolve os bytes do PDF gerado pela API externa."""
    payload: dict[str, Any] = {"dados_llm": dados_llm, "doc_text": doc_text}
    if subtitulo:
        payload["subtitulo"] = subtitulo
    async with httpx.AsyncClient(base_url=RESUMO_API_BASE, timeout=HTTP_TIMEOUT) as cli:
        r = await cli.post("/export-pdf", json=payload)
        if r.status_code >= 400:
            raise ResumoEstruturadoError(f"export-pdf falhou ({r.status_code}): {r.text[:300]}")
        return r.content


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS DE PERSISTÊNCIA (mesmo padrão do pipeline_pdf.py)
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
#  ORQUESTRAÇÃO — envia à API externa, acompanha por polling e salva no
#  workspace/{hash}/ (resumo_estruturado.json + resumo_estruturado_texto.txt)
# ══════════════════════════════════════════════════════════════════════════
async def executar_resumo_estruturado(
    tarefa_id: int,
    pdf_bytes: Optional[bytes] = None,
    texto: Optional[str] = None,
    filename: str = "documento.pdf",
    session_token: Optional[str] = None,
) -> None:
    """
    Entry-point chamado por BackgroundTasks a partir de
    POST /api/resumo-estruturado/submit.

    Não decompõe nada localmente: envia o documento para
    api.resumoestruturado.com.br, aguarda o job concluir e salva o
    resultado (dados_llm / doc_text) no workspace da tarefa — no mesmo
    padrão de arquivos usado pelo pipeline_pdf.py local.
    """
    with Session(engine) as s:
        t = s.get(Tarefa, tarefa_id)
        if not t:
            log.error("Tarefa %s não encontrada", tarefa_id)
            return
        hash_ = t.hash
        titulo = t.titulo

    log.info("═" * 70)
    log.info("🎬 RESUMO ESTRUTURADO (API externa) | tarefa_id=%s", tarefa_id)

    _atualizar_status(tarefa_id, "processando")
    registrar_evento(hash_, "resumo_estruturado_start", tarefa_id=tarefa_id)

    # ── 1. Envia para a API externa
    try:
        envio = await submeter(pdf_bytes=pdf_bytes, texto=texto, filename=filename)
    except Exception as e:
        log.error("💥 submit falhou | %s", e)
        _atualizar_status(tarefa_id, "falhou")
        registrar_evento(hash_, "resumo_estruturado_erro", etapa="submit", erro=str(e))
        return

    job_id = envio.get("job_id")
    total_steps = envio.get("total_steps")
    if not job_id:
        log.error("💥 API externa não retornou job_id | %s", envio)
        _atualizar_status(tarefa_id, "falhou")
        registrar_evento(hash_, "resumo_estruturado_erro", etapa="submit",
                         erro="resposta sem job_id")
        return

    registrar_evento(hash_, "resumo_estruturado_job", job_id=job_id, total_steps=total_steps)
    _salvar_json(hash_, "resumo_estruturado_job.json", envio)

    # ── 2. Poll até status == done | error | timeout
    t0 = time.time()
    while True:
        if time.time() - t0 > POLL_TIMEOUT:
            log.error("💥 timeout aguardando job %s", job_id)
            _atualizar_status(tarefa_id, "falhou")
            registrar_evento(hash_, "resumo_estruturado_erro", etapa="timeout", job_id=job_id)
            return

        await asyncio.sleep(POLL_INTERVAL)
        try:
            st = await consultar_status(job_id)
        except Exception as e:
            log.warning("⚠️  status falhou, tentando de novo | %s", e)
            continue

        registrar_evento(
            hash_, "resumo_estruturado_status",
            step=st.get("current_step"), idx=st.get("step_index"),
            total=st.get("total_steps"), status=st.get("status"),
            tokens=st.get("tokens_total"), elapsed=st.get("elapsed"),
        )

        if st.get("status") == "error":
            log.error("💥 job %s falhou | %s", job_id, st.get("error"))
            _atualizar_status(tarefa_id, "falhou")
            registrar_evento(hash_, "resumo_estruturado_erro", etapa="job",
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
        registrar_evento(hash_, "resumo_estruturado_erro", etapa="result", erro=str(e))
        return

    dados_llm = res.get("dados_llm")
    _salvar_json(hash_, "resumo_estruturado.json", dados_llm)
    if res.get("doc_text"):
        (pasta(hash_) / "resumo_estruturado_texto.txt").write_text(
            str(res["doc_text"]), encoding="utf-8"
        )

    _atualizar_status(tarefa_id, "pronta")
    registrar_evento(
        hash_, "resumo_estruturado_done",
        tokens=res.get("tokens_total"), elapsed=res.get("elapsed"),
    )

    # Memória de sessão — só a parte "resumo estruturado", nunca o PDF/texto
    if session_token:
        from core import sessao as sess
        sess.registrar_destilacao(
            session_token, "resumo_estruturado",
            hash_=hash_, titulo=titulo, resumo_estruturado=dados_llm,
        )

    log.info("🏁 RESUMO ESTRUTURADO concluído | tarefa=%s job=%s", tarefa_id, job_id)
