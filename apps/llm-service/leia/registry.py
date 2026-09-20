"""Receipt and public verification for a comprehension attempt.

Integration (one line in the service): ``app.include_router(build_router(get_attempt, templates))``
where ``get_attempt(hash) -> dict | None`` returns the attempt as stored by the service.

Expected attempt fields (names follow the service): ``hash_imutavel`` (sha256 hex of the attempt),
``tarefa_hash`` (document/task token), ``numero`` (round), ``acertos``, ``total``, ``aprovado`` (bool),
``criada_em`` (datetime, UTC), optional ``pdf_sha256`` and ``resumo_sha256``.
Nothing personal is included in the canonical payload.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response


def render(templates: Any, request: Request, name: str, context: dict[str, Any]):
    """Works with both TemplateResponse signatures (Starlette < 0.29 and >= 0.29)."""
    try:
        return templates.TemplateResponse(request, name, context)
    except TypeError:
        context["request"] = request
        return templates.TemplateResponse(name, context)

# v3 acrescenta três campos e não tira nenhum: quem revisou, por qual instrumento mediu e qual era o piso.
# Comprovante gravado antes disto continua abrindo, porque o registro congelado guarda o próprio canônico.
PAYLOAD_SCHEMA = "leia.payload.v3"


def canonical_json(obj: dict[str, Any]) -> str:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8 kept. Equivalent to RFC 8785 for strings, ints and bools."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def build_payload(attempt: dict[str, Any]) -> dict[str, Any]:
    """Consent payload, published in full so a third party can recompute the hash.

    It carries no personal data and, since v2, no document token either: the receipt is meant to be shown
    to third parties, and publishing the task hash handed them the citizen's private link. ``documentRef``
    identifies the document without revealing it, and whoever already holds the link can confirm the match.
    """
    created = attempt.get("criada_em")
    if isinstance(created, datetime):
        created_iso = created.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    else:
        created_iso = str(created)
    return {
        "schema": PAYLOAD_SCHEMA,
        "documentRef": sha256_hex(attempt.get("tarefa_hash", "")),
        "attemptRound": int(attempt.get("numero") or 1),
        "attemptSha256": attempt.get("hash_imutavel", ""),
        "documentSha256": attempt.get("pdf_sha256") or "",
        "summarySha256": attempt.get("resumo_sha256") or "",
        "understood": bool(attempt.get("aprovado")),
        # "understood" sozinho é afirmação forte e o terceiro não sabe por qual régua. Estes dois dizem a
        # régua, para ele julgar o peso em vez de aceitar ou recusar no escuro.
        "instrument": str(attempt.get("instrumento") or "multiple-choice"),
        "passMark": int(attempt.get("piso") or 0),
        "answered": int(attempt.get("total") or 0),
        # Metade da tese do produto é a supervisão humana, e o artefato que circula não dizia se ela existiu.
        "reviewedByLawyer": bool(attempt.get("revisado_por_advogado")),
        "createdAt": created_iso,
    }


def ots_digest(proof: bytes) -> Optional[str]:
    """Hex digest a detached OpenTimestamps proof was made over, or None when it cannot be read."""
    try:
        from opentimestamps.core.serialize import BytesDeserializationContext  # type: ignore
        from opentimestamps.core.timestamp import DetachedTimestampFile  # type: ignore
        ctx = BytesDeserializationContext(proof)
        return DetachedTimestampFile.deserialize(ctx).file_digest.hex()
    except Exception:
        return None


def payload_hash(payload: dict[str, Any]) -> tuple[str, str]:
    canonical = canonical_json(payload)
    return canonical, sha256_hex(canonical)


OTS_CALENDARS = (
    "https://a.pool.opentimestamps.org",
    "https://b.pool.opentimestamps.org",
    "https://alice.btc.calendar.opentimestamps.org",
    "https://bob.btc.calendar.opentimestamps.org",
)
# The stamp is the only public proof of the consent, and the network fails. A single pass lost that proof
# for good; these waits give the calendar time to come back before the case is left to the sweep.
OTS_RETRY_WAITS = (2, 8, 30)
_sleep = time.sleep  # single waiting point, so a test can watch the backoff grow without living through it


@dataclass(frozen=True)
class StampOutcome:
    """What one stamping run produced.

    ``proof`` is the detached .ots file, or None when the run failed. Failure used to be a mute None, so the
    caller could not tell a disabled stamp from four calendars down, and nobody could say what to retry:
    ``reason`` is that sentence, and ``attempts`` counts the calendar submissions it took to get there.
    """

    proof: Optional[bytes]
    reason: str = ""
    attempts: int = 0
    rounds: int = 0

    def __bool__(self) -> bool:
        """True only when a proof came back, so ``if outcome:`` asks what the caller means to ask."""
        return self.proof is not None


def ots_timeout() -> float:
    """Seconds a calendar has to answer. Eight was not enough for the pool under load."""
    try:
        return float(os.getenv("OTS_TIMEOUT", "15"))
    except ValueError:
        return 15.0


def _submit_round(digest: bytes, timeout: float) -> tuple[list[Any], list[str]]:
    """One round: submit to every calendar at the same time and keep every answer that arrives.

    The old code stopped at the first calendar that answered, so the proof hung on that one calendar being
    up. Submitting to all of them costs nothing extra in wall clock and the attestations merge.
    """
    from opentimestamps.calendar import RemoteCalendar  # type: ignore

    answers: list[Any] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=len(OTS_CALENDARS)) as pool:
        running = {pool.submit(RemoteCalendar(url).submit, digest, timeout): url for url in OTS_CALENDARS}
        for future, url in running.items():
            try:
                answers.append(future.result())
            except Exception as erro:
                # An exception object is always truthy, so the fallback has to test the message itself:
                # socket timeouts arrive with an empty one and would report the calendar and nothing else.
                failures.append(f"{url}: {str(erro) or type(erro).__name__}")
    return answers, failures


def ots_stamp(hash_hex: str) -> StampOutcome:
    """Timestamp a sha256 digest with the public OpenTimestamps calendars, insisting when they do not answer."""
    if os.getenv("OTS_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return StampOutcome(None, "carimbo desligado por OTS_ENABLED")
    try:
        from opentimestamps.core.op import OpSHA256  # type: ignore
        from opentimestamps.core.serialize import BytesSerializationContext  # type: ignore
        from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp  # type: ignore
    except Exception as erro:
        return StampOutcome(None, f"biblioteca de carimbo indisponível: {erro}")
    try:
        digest = bytes.fromhex(hash_hex)
    except ValueError as erro:
        return StampOutcome(None, f"hash fora de formato para carimbo: {erro}")

    timestamp = Timestamp(digest)
    detached = DetachedTimestampFile(OpSHA256(), timestamp)
    timeout = ots_timeout()
    attempts = 0
    failures: list[str] = []
    for round_number, wait in enumerate((0, *OTS_RETRY_WAITS), start=1):
        if wait:
            _sleep(wait)
        answers, failures = _submit_round(digest, timeout)
        attempts += len(answers) + len(failures)
        if not answers:
            continue
        for calendar_ts in answers:
            timestamp.merge(calendar_ts)
        ctx = BytesSerializationContext()
        detached.serialize(ctx)
        return StampOutcome(ctx.getbytes(), "", attempts, round_number)
    return StampOutcome(None, "; ".join(failures) or "nenhum calendário respondeu",
                        attempts, len(OTS_RETRY_WAITS) + 1)


def _attested(stamp: Any) -> Iterator[Any]:
    """The sub-timestamps that carry attestations, which are the ones a calendar can still complete."""
    if stamp.attestations:
        yield stamp
        return
    for sub in stamp.ops.values():
        yield from _attested(sub)


def ots_bitcoin_height(proof: bytes) -> Optional[int]:
    """Block that anchors the proof, or None while it is still a calendar promise."""
    from opentimestamps.core.notary import BitcoinBlockHeaderAttestation  # type: ignore
    from opentimestamps.core.serialize import BytesDeserializationContext  # type: ignore
    from opentimestamps.core.timestamp import DetachedTimestampFile  # type: ignore

    try:
        detached = DetachedTimestampFile.deserialize(BytesDeserializationContext(proof))
        for _, attestation in detached.timestamp.all_attestations():
            if isinstance(attestation, BitcoinBlockHeaderAttestation):
                return attestation.height
    except Exception:
        return None
    return None


def upgrade_proof(proof: bytes, timeout: Optional[float] = None) -> Optional[bytes]:
    """Fetch the attestations a pending proof is still missing. Returns the bigger proof, or None if unchanged.

    What the calendar hands back at stamping time is a promise: it commits to publish the digest in a Bitcoin
    block. Only after that block exists does the promise become something a third party can check without
    trusting the calendar, and nothing in the service ever came back to collect it.
    """
    try:
        from opentimestamps.calendar import DEFAULT_CALENDAR_WHITELIST, RemoteCalendar  # type: ignore
        from opentimestamps.core.notary import PendingAttestation  # type: ignore
        from opentimestamps.core.serialize import (BytesDeserializationContext,  # type: ignore
                                                   BytesSerializationContext)
        from opentimestamps.core.timestamp import DetachedTimestampFile  # type: ignore

        detached = DetachedTimestampFile.deserialize(BytesDeserializationContext(proof))
    except Exception:
        return None
    if ots_bitcoin_height(proof) is not None:
        return None  # already anchored: there is no attestation left to fetch

    timeout = ots_timeout() if timeout is None else timeout
    known = {attestation for _, attestation in detached.timestamp.all_attestations()}
    changed = False
    for stamp in _attested(detached.timestamp):
        for attestation in list(stamp.attestations):
            # Only the calendar that made the promise can complete it, and only if the official client
            # trusts it: a URI read from the file would let the file choose who we talk to.
            if not isinstance(attestation, PendingAttestation) or attestation.uri not in DEFAULT_CALENDAR_WHITELIST:
                continue
            try:
                upgraded = RemoteCalendar(attestation.uri).get_timestamp(stamp.msg, timeout=timeout)
            except Exception:
                continue
            fresh = {att for _, att in upgraded.all_attestations()} - known
            if fresh:
                known |= fresh
                stamp.merge(upgraded)
                changed = True
    if not changed:
        return None
    ctx = BytesSerializationContext()
    detached.serialize(ctx)
    return ctx.getbytes()


def qr_png_base64(text: str) -> str:
    import qrcode  # type: ignore

    img = qrcode.make(text, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def strip_pdf_metadata(pdf_bytes: bytes) -> bytes:
    """Remove document info and XMP metadata from a PDF (global rule: no tool metadata)."""
    from pypdf import PdfReader, PdfWriter  # type: ignore

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.metadata = None
    root = writer._root_object  # noqa: SLF001 (pypdf has no public API for this yet)
    if "/Metadata" in root:
        del root["/Metadata"]
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def build_router(get_attempt: Callable[[str], Optional[dict[str, Any]]], templates: Any,
                 base_url_env: str = "BASE_URL") -> APIRouter:
    """``templates`` is the service's Jinja2Templates instance; templates live in ``templates/leia/``."""
    router = APIRouter()

    def _load(attempt_hash: str) -> dict[str, Any]:
        attempt = get_attempt(attempt_hash)
        if not attempt:
            raise HTTPException(status_code=404, detail="comprovante não encontrado")
        # The record written down when the consent was earned wins over anything rebuilt now: a proof that
        # changes when a database row changes is not a proof. Attempts from before this existed still rebuild.
        gravado = attempt.get("registro") or {}
        if gravado.get("canonical") and gravado.get("payload_sha256"):
            canonical, digest = gravado["canonical"], gravado["payload_sha256"]
            payload = json.loads(canonical)
        else:
            payload = build_payload(attempt)
            canonical, digest = payload_hash(payload)
        ots = attempt.get("ots")  # bytes or None, stored by the service after stamping
        # A stamp only counts when it was made over this very record. A file on disk proves nothing:
        # if the payload changed after stamping, the proof belongs to a record that no longer exists.
        matches = bool(ots) and ots_digest(ots) == digest
        return {"attempt": attempt, "payload": payload, "canonical": canonical, "payload_hash": digest,
                "ots_present": matches, "ots_base64": base64.b64encode(ots).decode() if matches else None}

    @router.get("/t/{attempt_hash}/comprovante", response_class=HTMLResponse)
    def receipt(request: Request, attempt_hash: str):
        data = _load(attempt_hash)
        base = os.getenv(base_url_env, str(request.base_url).rstrip("/"))
        verify_url = f"{base}/verify/{attempt_hash}"
        data.update({"verify_url": verify_url, "qr_base64": qr_png_base64(verify_url)})
        return render(templates, request, "leia/comprovante.html", data)

    @router.get("/verify/{attempt_hash}")
    def verify(request: Request, attempt_hash: str, format: str = "html"):
        data = _load(attempt_hash)
        if format == "json":
            # otsState, otsBlockHeight e otsLastAttempt vêm de quem guarda a prova (ots_status do serviço):
            # "tem carimbo" sozinho não distingue a promessa do calendário do bloco que a fecha.
            return JSONResponse({"payload": data["payload"], "canonical": data["canonical"],
                                 "payloadHash": data["payload_hash"], "otsPresent": data["ots_present"],
                                 **(data["attempt"].get("ots_status") or {})})
        return render(templates, request, "leia/verify.html", data)

    @router.get("/verify/{attempt_hash}/proof.ots")
    def proof(attempt_hash: str):
        data = _load(attempt_hash)
        if not data["ots_present"]:
            raise HTTPException(status_code=404, detail="carimbo ainda pendente")
        return Response(content=base64.b64decode(data["ots_base64"]), media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{attempt_hash[:12]}.ots"'})

    return router
