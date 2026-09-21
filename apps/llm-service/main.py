# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   PIPELINE v45 — FastAPI + Streaming + Gestão + Compat Starlette 0.36+   ║
# ╚══════════════════════════════════════════════════════════════════════════╝
from __future__ import annotations
import asyncio, os, logging
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import AsyncGroq
from sqlmodel import Session

# ─── LOGGING ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("aduc")

# ─── CONFIG ──────────────────────────────────────────────────────────────
groq_key = os.getenv("GROQ_API_KEY") or os.getenv("API_KEY", "")
groq_client = AsyncGroq(api_key=groq_key)


BASE_DIR = Path(__file__).resolve().parent
log.info("LeIA · serviço cognitivo | Groq: %s",
         "OK" if "gsk_" in groq_key else "⚠️ placeholder")

# ─── APP ─────────────────────────────────────────────────────────────────
# LeIA: the re-stamping sweep is tied to the service lifetime, so a receipt the calendars failed to stamp
# stops being a receipt without a proof forever. OTS_SWEEP_MINUTES=0 turns it off.
from leia.stamping import sweep_lifespan                       # noqa: E402

_docs_on = os.getenv("DOCS_ENABLED", "false").lower() in ("1", "true", "yes")
app = FastAPI(title="LeIA · serviço cognitivo", lifespan=sweep_lifespan,
              docs_url="/docs" if _docs_on else None,
              redoc_url="/redoc" if _docs_on else None, openapi_url="/openapi.json" if _docs_on else None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# ══════════════════════════════════════════════════════════════════════════
#  BOOTSTRAP: banco + usuário admin inicial + rotas de gestão
# ══════════════════════════════════════════════════════════════════════════
from core.db import init_db, engine, Usuario                  # noqa: E402
from core.auth import create_initial_user, admin_user    # noqa: E402
from app_gestao import router as gestao_router                # noqa: E402

init_db()

with Session(engine) as _s:
    # LeIA: the first admin only exists when ADMIN_PASSWORD is set explicitly (no default password)
    if not os.getenv("ADMIN_PASSWORD"):
        log.error("ADMIN_PASSWORD não definida: nenhum usuário inicial foi criado")
    elif create_initial_user(
        _s,
        email=os.getenv("ADMIN_EMAIL", "admin@local"),
        senha=os.getenv("ADMIN_PASSWORD"),
        nome=os.getenv("ADMIN_NAME", "Administrador"),
        papel="fornecedor",
    ):
        log.warning("🔐 Usuário inicial criado: %s", os.getenv("ADMIN_EMAIL", "admin@local"))

app.include_router(gestao_router)

# LeIA: JSON for the citizen app, receipt, public verification and timestamp (apps/web consumes these)
from leia.api_citizen import router as cliente_router, get_attempt   # noqa: E402
from leia.registry import build_router as build_registry_router       # noqa: E402
from leia.api_auth import router as auth_router                       # noqa: E402  accounts (Bearer)
from leia.api_tasks import router as tarefas_router                 # noqa: E402  documents of the signed-in user

app.include_router(cliente_router)
app.include_router(build_registry_router(get_attempt, templates))
app.include_router(auth_router)
app.include_router(tarefas_router)


# LeIA: liveness signal for the host. The new version only takes over when this answers,
# so it must not depend on the model, on the database or on any credential.
@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════════
#  ROTAS — API
# ══════════════════════════════════════════════════════════════════════════
@app.post("/api/admin/stamps/reprocess")
async def api_reprocess_stamps(u: Usuario = Depends(admin_user)):
    """Sweep the consent records now instead of waiting for the ticker. Restricted to the service owner."""
    from leia.stamping import sweep_once

    return await asyncio.to_thread(sweep_once)
