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
from datetime import datetime, timezone
from typing import Any, Callable, Optional

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


def ots_stamp(hash_hex: str) -> Optional[bytes]:
    """Timestamp a sha256 digest with public OpenTimestamps calendars. Returns the .ots proof or None."""
    if os.getenv("OTS_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return None
    try:
        from opentimestamps.calendar import RemoteCalendar  # type: ignore
        from opentimestamps.core.op import OpSHA256  # type: ignore
        from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp  # type: ignore
        from opentimestamps.core.serialize import BytesSerializationContext  # type: ignore

        digest = bytes.fromhex(hash_hex)
        timestamp = Timestamp(digest)
        detached = DetachedTimestampFile(OpSHA256(), timestamp)
        calendars = [
            "https://a.pool.opentimestamps.org",
            "https://b.pool.opentimestamps.org",
            "https://alice.btc.calendar.opentimestamps.org",
            "https://bob.btc.calendar.opentimestamps.org",
        ]
        stamped = False
        for url in calendars:
            try:
                calendar_ts = RemoteCalendar(url).submit(digest, timeout=8)
                timestamp.merge(calendar_ts)
                stamped = True
                break
            except Exception:
                continue
        if not stamped:
            return None
        ctx = BytesSerializationContext()
        detached.serialize(ctx)
        return ctx.getbytes()
    except Exception:
        return None


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
            return JSONResponse({"payload": data["payload"], "canonical": data["canonical"],
                                 "payloadHash": data["payload_hash"], "otsPresent": data["ots_present"]})
        return render(templates, request, "leia/verify.html", data)

    @router.get("/verify/{attempt_hash}/proof.ots")
    def proof(attempt_hash: str):
        data = _load(attempt_hash)
        if not data["ots_present"]:
            raise HTTPException(status_code=404, detail="carimbo ainda pendente")
        return Response(content=base64.b64decode(data["ots_base64"]), media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{attempt_hash[:12]}.ots"'})

    return router
