"""Mock of the cognitive service routes used by the citizen interface.

Serves the same paths as the real service (as observed in its templates) with fixture data, so the interface,
receipt and verification can be developed and demonstrated before the service is available.
Run from apps/llm-service:  uvicorn mock.app:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import pathlib
import secrets
import unicodedata
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from leia.registry import build_router, ots_stamp, payload_hash, build_payload, render

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURE = pathlib.Path(os.getenv("LEIA_FIXTURE", ROOT.parent.parent / "examples" / "fixture-honorarios.json"))

app = FastAPI(title="LeIA mock service")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")

STATE: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
ATTEMPTS: dict[str, dict[str, Any]] = {}


def _task(hash_: str) -> dict[str, Any]:
    if hash_ != STATE["tarefa"]["hash"]:
        raise HTTPException(status_code=404)
    return STATE


def _public_attempt(attempt: dict[str, Any] | None) -> dict[str, Any] | None:
    if not attempt:
        return None
    return {k: attempt[k] for k in ("aprovado", "hash_imutavel", "acertos", "total", "numero")}


def _public_questions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"id": q["id"], "enunciado": q["enunciado"], "alternativas": q["alternativas"], "area": q["area"]}
            for q in state["questoes"]["questoes"]]


@app.get("/")
def home():
    return RedirectResponse(f"/t/{STATE['tarefa']['hash']}")


@app.get("/t/{hash_}")
def citizen_page(request: Request, hash_: str):
    state = _task(hash_)
    last = STATE["tentativas"][-1] if STATE["tentativas"] else None
    return render(templates, request, "leia/cliente.html",
                  {"tarefa": state["tarefa"], "resumo_md": state["resumo_md"], "questoes": state["questoes"],
                   "topicos": state.get("topicos"), "ultima_tentativa": last})


@app.get("/api/t/{hash_}")
def task_json(hash_: str):
    """Proposed addition for the service: the citizen page data as JSON, without the answer key."""
    state = _task(hash_)
    last = STATE["tentativas"][-1] if STATE["tentativas"] else None
    return {"tarefa": state["tarefa"], "resumo_md": state["resumo_md"], "topicos": state.get("topicos"),
            "questoes": _public_questions(state), "ultima_tentativa": _public_attempt(last)}


@app.post("/api/t/{hash_}/quiz")
async def quiz(hash_: str, body: dict[str, Any]):
    state = _task(hash_)
    respostas = {str(k): v for k, v in (body.get("respostas") or {}).items()}
    erros, acertos = [], 0
    for q in state["questoes"]["questoes"]:
        chosen = respostas.get(str(q["id"]))
        if chosen == q["correta"]:
            acertos += 1
        else:
            erros.append({"id": q["id"], "area": q["area"], "enunciado": q["enunciado"], "escolhida": chosen})
    total = len(state["questoes"]["questoes"])
    numero = len(STATE["tentativas"]) + 1
    aprovado = acertos >= state.get("minimo_aprovacao", 10)
    created = datetime.now(timezone.utc)
    attempt = {"tarefa_hash": hash_, "numero": numero, "acertos": acertos, "total": total, "aprovado": aprovado,
               "criada_em": created, "salt": secrets.token_hex(20)}
    attempt["hash_imutavel"] = hashlib.sha256(
        json.dumps({"tarefa": hash_, "numero": numero, "respostas": respostas, "criada_em": created.isoformat()},
                   sort_keys=True).encode()).hexdigest()
    if aprovado:
        _, digest = payload_hash(build_payload(attempt))
        attempt["ots"] = await asyncio.to_thread(ots_stamp, digest)
    STATE["tentativas"].append(attempt)
    ATTEMPTS[attempt["hash_imutavel"]] = attempt
    return {"aprovado": aprovado, "acertos": acertos, "total": total, "numero": numero,
            "hash_imutavel": attempt["hash_imutavel"], "erros": erros}


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


@app.post("/api/t/{hash_}/chat")
async def chat(hash_: str, body: dict[str, Any]):
    """Grounded answer: finds the topic whose title or quote shares words with the question; otherwise refuses."""
    state = _task(hash_)
    msg = _norm(body.get("mensagem") or "")
    words = {w for w in msg.replace("?", " ").split() if len(w) > 3}
    best, score = None, 0
    for t in state.get("topicos", []):
        hay = _norm(t["titulo"] + " " + t["explicacao"] + " " + t["trecho"])
        s = sum(1 for w in words if w in hay)
        if s > score:
            best, score = t, s
    if best and score >= 2:
        answer = f"{best['explicacao']} O documento diz: \"{best['trecho']}\" (cláusula {best['clausula']})."
    else:
        answer = "Isso não está escrito neste documento. Posso explicar só o que está nele. Se for importante, anote para perguntar à sua advogada."

    async def stream():
        for i in range(0, len(answer), 12):
            yield f"data: {json.dumps({'t': answer[i:i+12]}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.02)
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/t/{hash_}/pdf-assinado")
def signed_pdf(hash_: str):
    last = next((t for t in reversed(STATE["tentativas"]) if t["aprovado"]), None)
    if not last:
        raise HTTPException(status_code=404, detail="nenhum registro aprovado")
    return RedirectResponse(f"/t/{last['hash_imutavel']}/comprovante")


app.include_router(build_router(ATTEMPTS.get, templates))
