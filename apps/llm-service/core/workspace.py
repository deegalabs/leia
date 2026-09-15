from __future__ import annotations
import json, os, secrets
from datetime import datetime
from pathlib import Path

BASE = Path(os.getenv("WORKSPACE_DIR", str(Path(os.getenv("DATA_DIR", ".")) / "workspace")))
BASE.mkdir(parents=True, exist_ok=True)


def new_hash() -> str:
    """URL-safe, ~22 chars, não sequencial, difícil de adivinhar."""
    return secrets.token_urlsafe(16)


def folder(h: str) -> Path:
    p = BASE / h
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_meta(h: str, meta: dict) -> None:
    (folder(h) / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def record_event(h: str, tipo: str, **dados) -> None:
    linha = {"ts": datetime.utcnow().isoformat(), "tipo": tipo, **dados}
    with (folder(h) / "log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def read_events(h: str) -> list[dict]:
    p = folder(h) / "log.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]