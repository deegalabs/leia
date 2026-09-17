"""Re-stamping sweep: whoever was left without a public proof gets one, and promises are completed.

The stamp is attempted once, in the background, right after an attempt is approved. When the calendars were
down in that minute the receipt stayed without a proof forever, because nothing ever came back for it. This
module is what comes back. It walks the frozen consent records, stamps again the ones whose ``.ots`` file is
missing or was made over another payload, and asks the calendars for the Bitcoin attestation the pending
proofs are still waiting for.

By hand, from apps/llm-service:  python -m leia.stamping
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterable, Optional

from leia.registry import ots_digest, ots_stamp, upgrade_proof

log = logging.getLogger("aduc")

# One sweep at a time: the ticker and an operator asking for a sweep would otherwise stamp the same record
# twice and each write a different proof over the other's file.
_sweep_lock = threading.Lock()


@dataclass(frozen=True)
class StampTarget:
    """One frozen consent record and the file where its proof belongs."""

    attempt_hash: str
    payload_sha256: str
    proof_path: Path


def needs_stamp(target: StampTarget) -> bool:
    """A proof that is missing, unreadable, or made over another payload is not a proof of this record."""
    try:
        if not target.proof_path.exists():
            return True
        return ots_digest(target.proof_path.read_bytes()) != target.payload_sha256
    except OSError:
        return True


def stamp_targets() -> list[StampTarget]:
    """Every frozen consent record, paired with the path where its proof is kept."""
    from sqlmodel import Session, select

    from core.db import ConsentRecord, Tarefa, Tentativa, engine
    from leia.api_citizen import _ots_path

    targets: list[StampTarget] = []
    with Session(engine) as s:
        for record in s.exec(select(ConsentRecord)).all():
            attempt = s.exec(select(Tentativa).where(Tentativa.hash_imutavel == record.attempt_hash)).first()
            task = s.get(Tarefa, attempt.tarefa_id) if attempt else None
            if attempt is None or task is None:
                continue  # the record outlived the attempt it describes: there is no workspace to write into
            targets.append(StampTarget(record.attempt_hash, record.payload_sha256,
                                       _ots_path(task.hash, attempt.numero)))
    return targets


def sweep(targets: Optional[Iterable[StampTarget]] = None) -> dict[str, Any]:
    """Stamp what is missing and complete what is still a promise. Returns the report."""
    items = list(stamp_targets() if targets is None else targets)
    records: list[dict[str, Any]] = []
    report: dict[str, Any] = {"checked": len(items), "stamped": 0, "upgraded": 0, "failed": 0, "records": records}
    for item in items:
        entry: dict[str, Any] = {"attempt_hash": item.attempt_hash, "stamped": False, "upgraded": False,
                                 "reason": ""}
        records.append(entry)
        try:
            if needs_stamp(item):
                outcome = ots_stamp(item.payload_sha256)
                if outcome.proof is None:
                    entry["reason"] = outcome.reason
                    report["failed"] += 1
                    continue
                item.proof_path.parent.mkdir(parents=True, exist_ok=True)
                item.proof_path.write_bytes(outcome.proof)
                entry["stamped"] = True
                report["stamped"] += 1
            bigger = upgrade_proof(item.proof_path.read_bytes())
            if bigger:
                item.proof_path.write_bytes(bigger)
                entry["upgraded"] = True
                report["upgraded"] += 1
        except OSError as erro:
            # The sweep runs unattended: one record whose file cannot be read or written must not take the
            # rest of the queue down with it, which is the failure this whole module exists to undo.
            entry["reason"] = f"a prova não pôde ser gravada: {erro}"
            report["failed"] += 1
    return report


def sweep_once(run: Optional[Callable[[], dict[str, Any]]] = None) -> dict[str, Any]:
    """Run a sweep unless one is already in flight, in which case the report says it was skipped."""
    if not _sweep_lock.acquire(blocking=False):
        return {"skipped": True, "checked": 0, "stamped": 0, "upgraded": 0, "failed": 0, "records": []}
    try:
        report = (run or sweep)()
    finally:
        _sweep_lock.release()
    return {"skipped": False, **report}


def sweep_interval_seconds() -> float:
    """How often the service sweeps, from OTS_SWEEP_MINUTES. Zero turns the sweep off."""
    try:
        return max(0.0, float(os.getenv("OTS_SWEEP_MINUTES", "30") or 0)) * 60
    except ValueError:
        return 30 * 60


async def sweep_ticker(interval: float) -> None:
    """Sweep forever, off the event loop. The first sweep waits one interval, so a restart loop cannot
    turn into a burst of calendar submissions."""
    while True:
        await asyncio.sleep(interval)
        try:
            report = await asyncio.to_thread(sweep_once)
        except Exception:
            log.exception("varredura de carimbos falhou")
            continue
        if report["stamped"] or report["upgraded"] or report["failed"]:
            log.info("varredura de carimbos: %s", json.dumps(report, ensure_ascii=False))


@contextlib.asynccontextmanager
async def sweep_lifespan(app: Any) -> AsyncIterator[None]:
    """FastAPI lifespan: keeps the sweep running while the service is up, and stops it with the service."""
    interval = sweep_interval_seconds()
    task = asyncio.create_task(sweep_ticker(interval)) if interval else None
    app.state.ots_sweep = task
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


if __name__ == "__main__":
    from core.db import init_db

    init_db()  # the service does this when it boots; run by hand there is nobody to have done it
    print(json.dumps(sweep_once(), ensure_ascii=False, indent=2))
