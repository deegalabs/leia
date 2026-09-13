"""Bounded runner for the PDF workflow (core.pipeline_pdf.executar_pipeline_pdf).

Every background run goes through one asyncio.Semaphore sized by PIPELINE_CONCURRENCY (default 3), so a
burst of uploads does not open more Groq streams than the account can take. Nothing else is shared: each
task has its own workspace folder and its own row, and an unexpected exception in one run is recorded on
that task only (status "falhou") and never reaches the others.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

from sqlmodel import Session

from core import workspace as ws
from core.db import LogEvento, Tarefa, engine

log = logging.getLogger("leia.pipeline")

_semaphore: asyncio.Semaphore | None = None
_semaphore_size = 0


def concurrency() -> int:
    try:
        return max(1, int(os.getenv("PIPELINE_CONCURRENCY", "3")))
    except ValueError:
        return 3


def semaphore() -> asyncio.Semaphore:
    global _semaphore, _semaphore_size
    size = concurrency()
    if _semaphore is None or _semaphore_size != size:
        _semaphore = asyncio.Semaphore(size)
        _semaphore_size = size
    return _semaphore


def _mark_failed(tarefa_id: int, erro: str) -> None:
    with Session(engine) as s:
        t = s.get(Tarefa, tarefa_id)
        if not t:
            return
        t.status = "falhou"
        t.atualizada_em = datetime.utcnow()
        s.add(t)
        s.add(LogEvento(tarefa_id=tarefa_id, tipo="erro_pipeline", payload=erro[:2000]))
        s.commit()
        ws.registrar_evento(t.hash, "erro_pipeline", erro=erro[:500])


async def run_pipeline(tarefa_id: int, groq_client, variacao: str = "", session_token: str | None = None) -> None:
    """Drop-in for ``executar_pipeline_pdf`` in ``BackgroundTasks.add_task``."""
    from core.pipeline_pdf import executar_pipeline_pdf

    sem = semaphore()
    if sem.locked():
        log.info("pipeline queued | tarefa=%s | limit=%s", tarefa_id, concurrency())
    async with sem:
        try:
            await executar_pipeline_pdf(tarefa_id, groq_client, variacao, session_token)
        except Exception as e:  # noqa: BLE001 (the failure belongs to this task only)
            log.exception("pipeline crashed | tarefa=%s", tarefa_id)
            try:
                _mark_failed(tarefa_id, f"{type(e).__name__}: {e}")
            except Exception:  # noqa: BLE001
                log.exception("could not record the failure | tarefa=%s", tarefa_id)
