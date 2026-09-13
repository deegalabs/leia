# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   PIPELINE v45 — FastAPI + Streaming + Gestão + Compat Starlette 0.36+   ║
# ╚══════════════════════════════════════════════════════════════════════════╝
from __future__ import annotations
import os, json, re, time, asyncio, logging
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import AsyncGroq
from sqlmodel import Session

# ─── LOGGING ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("aduc")

# ─── CONFIG ──────────────────────────────────────────────────────────────
groq_key = os.getenv("GROQ_API_KEY") or os.getenv("API_KEY", "")
groq_client = AsyncGroq(api_key=groq_key)

ARQUIVO_CONFIG   = "protocolo.json"
ARQUIVO_HELP     = "help.md"
ARQUIVO_CONTEXTO = "contexto_persistente.json"
DELAY_ENTRE_AGENTES = 0.2
STOP_KEYWORD     = "STOP_PIPELINE:"
MODELO_PADRAO    = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

BASE_DIR = Path(__file__).resolve().parent
log.info("🚀 ADUC-SDR v45 | Groq: %s",
         "OK" if "gsk_" in groq_key else "⚠️ placeholder")

# ─── APP ─────────────────────────────────────────────────────────────────
app = FastAPI(title="LeIA · serviço cognitivo")
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
from core.auth import criar_usuario_inicial, usuario_atual    # noqa: E402
from app_gestao import router as gestao_router                # noqa: E402

init_db()

with Session(engine) as _s:
    if criar_usuario_inicial(
        _s,
        email=os.getenv("ADMIN_EMAIL", "admin@local"),
        senha=os.getenv("ADMIN_PASSWORD", "trocar123"),
        nome=os.getenv("ADMIN_NAME", "Administrador"),
        papel="fornecedor",
    ):
        log.warning("🔐 Usuário inicial criado: %s (senha definida por ADMIN_PASSWORD; troque em produção)", os.getenv("ADMIN_EMAIL", "admin@local"))

app.include_router(gestao_router)

# LeIA: JSON for the citizen app, receipt, public verification and timestamp (apps/web consumes these)
from leia.api_cliente import router as cliente_router, get_attempt   # noqa: E402
from leia.registry import build_router as build_registry_router       # noqa: E402

app.include_router(cliente_router)
app.include_router(build_registry_router(get_attempt, templates))


# ══════════════════════════════════════════════════════════════════════════
#  JSON → TEXTO HUMANO
# ══════════════════════════════════════════════════════════════════════════
def _rotulo(k: str) -> str:
    s = str(k).replace("_", " ").strip().lower()
    return s[:1].upper() + s[1:] if s else s


def _fmt_scalar(v) -> str:
    if v is None or v == "" or v == "null":
        return "—"
    if isinstance(v, bool):
        return "sim" if v else "não"
    return str(v).strip()


def _fmt_valor(v, indent: int = 0) -> str:
    pad = "  " * indent
    if v is None or v == "" or v == "null":
        return "—"
    if isinstance(v, (bool, int, float, str)):
        return _fmt_scalar(v)
    if isinstance(v, list):
        if not v:
            return "(vazio)"
        linhas = []
        for i, item in enumerate(v, 1):
            if isinstance(item, (dict, list)):
                sub = _fmt_valor(item, indent + 1).lstrip("\n")
                linhas.append(f"{pad}  {i}. {sub}")
            else:
                linhas.append(f"{pad}  • {_fmt_scalar(item)}")
        return "\n" + "\n".join(linhas)
    if isinstance(v, dict):
        if not v:
            return "(vazio)"
        linhas = []
        for k, val in v.items():
            rot = _rotulo(k)
            txt = _fmt_valor(val, indent + 1)
            linhas.append(f"{pad}{rot}:{txt}" if txt.startswith("\n")
                          else f"{pad}{rot}: {txt}")
        return "\n" + "\n".join(linhas)
    return str(v)


def formatar_conteudo_texto(content) -> str:
    if isinstance(content, str):
        s = content.strip()
        if s.startswith(("{", "[")) and s.endswith(("}", "]")):
            try:
                return formatar_conteudo_texto(json.loads(s))
            except Exception:
                pass
        return content
    if isinstance(content, dict):
        partes = []
        for k, v in content.items():
            rot = _rotulo(k)
            txt = _fmt_valor(v, 0)
            partes.append(f"▸ {rot}:{txt}" if txt.startswith("\n")
                          else f"▸ {rot}: {txt}")
        return "\n".join(partes)
    if isinstance(content, list):
        blocos = []
        for i, item in enumerate(content, 1):
            blocos.append(f"── Item {i} ──")
            blocos.append(formatar_conteudo_texto(item))
            blocos.append("")
        return "\n".join(blocos).rstrip()
    return str(content)


# ══════════════════════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════════════
def estimar_tokens(t) -> int:
    return len(str(t)) // 4


def _ler(nome: str, default: str = "") -> str:
    try:
        return (BASE_DIR / nome).read_text(encoding="utf-8")
    except Exception as e:
        log.warning("⚠️  Falha lendo %s: %s", nome, e)
        return default


def carregar_protocolo() -> str:
    return _ler(ARQUIVO_CONFIG, "[]")


def carregar_help() -> str:
    return _ler(ARQUIVO_HELP, "# Help\n\nCrie `help.md` na raiz.")


def salvar_protocolo(conteudo: str) -> str:
    try:
        agentes = json.loads(conteudo)
        (BASE_DIR / ARQUIVO_CONFIG).write_text(conteudo, encoding="utf-8")
        log.info("💾 protocolo salvo | %d agentes", len(agentes))
        return f"✅ Protocolo salvo ({len(agentes)} agentes)"
    except Exception as e:
        log.error("❌ protocolo inválido | %s", e)
        return f"❌ Erro JSON: {e}"


def carregar_contexto_persistente() -> list:
    try:
        return json.loads((BASE_DIR / ARQUIVO_CONTEXTO).read_text(encoding="utf-8"))
    except Exception:
        log.info("📝 contexto persistente vazio")
        return []


def salvar_contexto_persistente(ctx: list) -> None:
    try:
        (BASE_DIR / ARQUIVO_CONTEXTO).write_text(
            json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.error("❌ contexto save | %s", e)


def limpar_contexto_persistente() -> str:
    try:
        (BASE_DIR / ARQUIVO_CONTEXTO).write_text("[]", encoding="utf-8")
        log.info("🗑️  contexto limpo")
        return "✅ Contexto limpo"
    except Exception as e:
        return f"❌ Erro: {e}"


def limitar_timeline(timeline, max_chars: int = 12000, max_msgs: int = 12):
    acum, sel = 0, []
    for msg in reversed(timeline):
        t = str(msg.get("content", ""))
        acum += len(t)
        if acum > max_chars or len(sel) >= max_msgs:
            break
        sel.append(msg)
    sel.reverse()
    return sel, acum, estimar_tokens(acum)


def ler_anexo_bytes(nome: str, conteudo: bytes) -> str:
    try:
        texto = conteudo.decode("utf-8", errors="replace")
        log.info("📎 anexo | %s | %d chars", nome, len(texto))
        return f"\n\n[ANEXO: {nome}]\n{texto}\n[FIM ANEXO]\n"
    except Exception as e:
        log.error("❌ anexo %s | %s", nome, e)
        return ""


def verificar_stop(texto) -> bool:
    return bool(texto and re.search(r"\b" + re.escape(STOP_KEYWORD) + r"\b",
                                    str(texto), re.I))


def _extrair_json(texto: str) -> str:
    t = (texto or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json|jshon|javascript)?\s*", "", t, flags=re.I)
        t = re.sub(r"\s*```\s*$", "", t).strip()
    for abre, fecha in (("{", "}"), ("[", "]")):
        i, j = t.find(abre), t.rfind(fecha)
        if i >= 0 and j > i:
            return t[i:j + 1]
    return t


def _montar_messages(timeline, config) -> list:
    msgs = [{
        "role": "system",
        "content": f"AGENTE: {config['nome']}\nMISSÃO: {config['missao']}",
    }]
    limited, chars, toks = limitar_timeline(timeline, max_chars=15000, max_msgs=20)
    log.info("   ✂️  timeline | %d msgs · %d chars · ~%d tok", len(limited), chars, toks)
    for m in limited:
        if m.get("role") in ("user", "assistant"):
            c = m.get("content", "")
            if isinstance(c, (dict, list)):
                c = json.dumps(c, ensure_ascii=False)
            msgs.append({"role": m["role"], "content": str(c)})
    msgs.append({
        "role": "user",
        "content": (
            f"Com base em TODO o contexto acima e na missão do agente "
            f"'{config['nome']}', execute a missão agora e produza APENAS "
            f"a saída esperada para este agente."
        ),
    })
    return msgs


# ══════════════════════════════════════════════════════════════════════════
#  ENGINE — `emitir_stream=False` para intermediários
# ══════════════════════════════════════════════════════════════════════════
async def _executar_agente(timeline, config, emitir_stream: bool = False):
    nome   = config.get("nome", "?")
    modelo = config.get("modelo") or MODELO_PADRAO
    tipo   = config.get("tipo_saida", "texto").lower()

    log.info("━" * 62)
    log.info("🔥 AGENTE | %s | stream=%s", nome, emitir_stream)
    log.info("   modelo=%s · tipo_saida=%s", modelo, tipo)

    messages = _montar_messages(timeline, config)
    total_chars = sum(len(m.get("content", "")) for m in messages)
    log.info("   → payload | %d msgs · ~%d chars", len(messages), total_chars)
    yield ("meta", {"messages": messages, "modelo": modelo})

    inicio = time.time()
    out_raw, think_raw, chunk_n = "", "", 0

    try:
        kwargs = dict(
            model=modelo, messages=messages,
            temperature=1, max_completion_tokens=6048, top_p=1, stream=True,
        )
        try:
            kwargs["reasoning_format"] = "parsed"
            stream = await groq_client.chat.completions.create(**kwargs)
        except TypeError:
            kwargs.pop("reasoning_format", None)
            stream = await groq_client.chat.completions.create(**kwargs)

        async for chunk in stream:
            delta = chunk.choices[0].delta
            r = getattr(delta, "reasoning", None)
            if r:
                think_raw += r
                if emitir_stream:
                    yield ("think", r)
            c = delta.content or ""
            if c:
                out_raw += c
                chunk_n += 1
                if emitir_stream:
                    yield ("token", c)

        tempo = time.time() - inicio
        log.info("   ✅ | %d chunks · %d chars · %.2fs", chunk_n, len(out_raw), tempo)

        content = out_raw
        if tipo in ("json", "jshon"):
            try:
                content = json.loads(_extrair_json(out_raw))
                log.info("   ✅ JSON | %d chaves", len(content))
            except Exception:
                log.info("   ℹ️  fallback: texto")

        yield ("done", {
            "role": "assistant",
            "agent": nome,
            "content": content,
            "text": formatar_conteudo_texto(content),
            "is_json": isinstance(content, (dict, list)),
            "groq_payload_real": messages,
            "tempo": tempo,
            "think_chars": len(think_raw),
        })
    except Exception as e:
        log.error("   💥 ERRO | %s", e)
        yield ("error", str(e))


# ══════════════════════════════════════════════════════════════════════════
#  SSE
# ══════════════════════════════════════════════════════════════════════════
def _sse(evt: dict) -> str:
    return f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"


async def _stream_orquestrador(texto, anexos, protocolo_json, objetivo, isolar_pergunta=True):
    log.info("═" * 62)
    log.info("🎬 PIPELINE | %d chars · %d anexos", len(texto), len(anexos))

    if not texto.strip():
        yield _sse({"type": "error", "text": "Texto vazio"})
        return

    try:
        protocolo = json.loads(protocolo_json)
    except Exception as e:
        yield _sse({"type": "error", "text": f"JSON inválido: {e}"})
        return

    total = len(protocolo)
    log.info("   protocolo | %d agentes", total)
    yield _sse({"type": "user", "content": texto})

    ctx = carregar_contexto_persistente()
    ctx.append({
        "role": "user",
        "content": f"[USUARIO] {texto}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    ctx_sessao = ""
    if objetivo and objetivo.strip():
        ctx_sessao += f"[OBJETIVO DO MODELO]\n{objetivo.strip()}\n[FIM OBJETIVO]\n\n"
    for nome, blob in anexos:
        ctx_sessao += ler_anexo_bytes(nome, blob)

    # Cada pergunta é respondida de forma isolada: só a pergunta atual + o
    # anexo (resumo_estruturado da sessão), sem o histórico de turnos
    # anteriores (contexto_persistente.json) entrando no prompt do modelo.
    # O histórico continua sendo GRAVADO (para o painel de Memória), só não
    # é reenviado como contexto de conversa.
    if isolar_pergunta:
        timeline = [{"role": "user", "content": f"{ctx_sessao}{texto}".strip()}]
    else:
        timeline = [{"role": m["role"], "content": m["content"]} for m in ctx[:-1]]
        timeline.append({"role": "user", "content": f"{ctx_sessao}{texto}".strip()})

    t_pipe = time.time()

    for idx, cfg in enumerate(protocolo):
        nome = cfg.get("nome", f"agente_{idx}")
        eh_ultimo = (idx == total - 1)

        yield _sse({
            "type": "agent_start",
            "index": idx, "total": total,
            "name": nome,
            "model": cfg.get("modelo") or MODELO_PADRAO,
            "stream": eh_ultimo,
        })

        await asyncio.sleep(DELAY_ENTRE_AGENTES)

        async for kind, payload in _executar_agente(
            timeline, cfg, emitir_stream=eh_ultimo
        ):
            if kind == "meta":
                yield _sse({"type": "agent_payload",
                            "index": idx, "payload": payload["messages"]})

            elif kind == "token":
                yield _sse({"type": "agent_token", "index": idx, "text": payload})

            elif kind == "think":
                yield _sse({"type": "agent_think", "index": idx, "text": payload})

            elif kind == "done":
                res = payload
                yield _sse({
                    "type": "agent_done",
                    "index": idx, "name": nome,
                    "tempo": round(res["tempo"], 2),
                    "text": res["text"],
                    "is_json": res["is_json"],
                    "raw": (res["content"] if isinstance(res["content"], (str, dict, list))
                            else str(res["content"])),
                    "payload": res["groq_payload_real"],
                    "think_chars": res.get("think_chars", 0),
                    "final": eh_ultimo,
                })
                resp = res["content"]

                if verificar_stop(resp):
                    log.warning("🛑 STOP em %s", nome)
                    final = resp
                    if isinstance(resp, dict) and "proximo_passo" in resp:
                        final = str(resp["proximo_passo"]).replace(
                            STOP_KEYWORD, "").strip()
                    elif isinstance(resp, str):
                        final = resp.replace(STOP_KEYWORD, "").strip()
                    yield _sse({"type": "stop", "text": final})
                    yield _sse({"type": "final", "status": "stopped",
                                "elapsed": round(time.time() - t_pipe, 2)})
                    return

                persist = (f"[{nome}] " +
                           (resp if isinstance(resp, str)
                            else json.dumps(resp, ensure_ascii=False)))
                ctx.append({
                    "role": "assistant", "agent": nome, "content": persist,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                salvar_contexto_persistente(ctx)
                timeline.append({"role": "assistant", "content": resp})

            elif kind == "error":
                yield _sse({"type": "agent_error",
                            "index": idx, "name": nome, "error": payload})
                yield _sse({"type": "final", "status": "error"})
                return

    log.info("🏁 PIPELINE | %.2fs", time.time() - t_pipe)
    yield _sse({"type": "final", "status": "done",
                "elapsed": round(time.time() - t_pipe, 2)})


# ══════════════════════════════════════════════════════════════════════════
#  ROTAS — CHAT (protegido por login)
# ══════════════════════════════════════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, u: Usuario = Depends(usuario_atual)):
    """Chat do investigador AI. Exige login."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "protocolo_init": carregar_protocolo(),
            "help_init": carregar_help(),
            "usuario": u,
        },
    )


# ══════════════════════════════════════════════════════════════════════════
#  ROTAS — API
# ══════════════════════════════════════════════════════════════════════════
@app.get("/api/protocolo")
async def api_get_protocolo(u: Usuario = Depends(usuario_atual)):
    return {"conteudo": carregar_protocolo()}


@app.post("/api/protocolo")
async def api_post_protocolo(payload: dict, u: Usuario = Depends(usuario_atual)):
    return {"message": salvar_protocolo(payload.get("conteudo", "[]"))}


@app.get("/api/help")
async def api_get_help(u: Usuario = Depends(usuario_atual)):
    return {"conteudo": carregar_help()}


@app.get("/api/contexto")
async def api_get_contexto(u: Usuario = Depends(usuario_atual)):
    return {"contexto": carregar_contexto_persistente()}


@app.post("/api/contexto/limpar")
async def api_post_limpar_contexto(u: Usuario = Depends(usuario_atual)):
    return {"message": limpar_contexto_persistente()}


@app.post("/api/chat")
async def api_chat(
    request: Request,
    texto: str = Form(...),
    objetivo: str = Form(""),
    protocolo_json: str = Form(""),
    anexos: List[UploadFile] = File(default=[]),
    u: Usuario = Depends(usuario_atual),
):
    # O front-end não edita mais o protocolo por requisição (o antigo painel
    # de edição foi removido do template). Se não vier nada usável aqui,
    # cai pro protocolo.json canônico do servidor — sem isso o chat ficava
    # respondendo vazio (protocolo="{}" => 0 agentes executados).
    protocolo_efetivo = protocolo_json
    try:
        _p = json.loads(protocolo_json or "null")
        if not isinstance(_p, list) or not _p:
            protocolo_efetivo = carregar_protocolo()
    except Exception:
        protocolo_efetivo = carregar_protocolo()

    # Anexo compartilhado (server-side, autoritativo): JSON com as 3 partes
    # já destiladas nesta sessão de login — jurisprudência, resumo
    # estruturado e chat. Acompanha TODA pergunta do usuário. Nunca inclui
    # nada do fluxo de PDF assinado (memória inteiramente separada).
    from core import sessao as sess
    token = request.cookies.get("sessao")
    anexo = sess.anexo_compartilhado(token) if token else None
    objetivo_efetivo = objetivo
    if anexo:
        objetivo_efetivo += (
            "\n\nResponda em português do Brasil, de forma direta, à pergunta "
            "específica do usuário abaixo, usando como única fonte de contexto "
            "o documento/processo no anexo a seguir (campo \"resumo_estruturado\" "
            "de cada parte). Não use nenhuma outra memória ou conversa anterior."
            "\n\n<anexo_sessao_destilado>\n"
            + json.dumps(anexo, ensure_ascii=False)
            + "\n</anexo_sessao_destilado>"
        )

    anexos_bytes = []
    for up in anexos:
        if up and up.filename:
            anexos_bytes.append((up.filename, await up.read()))
    gen = _stream_orquestrador(texto, anexos_bytes, protocolo_efetivo, objetivo_efetivo,
                                isolar_pergunta=True)
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ══════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)