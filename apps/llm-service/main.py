# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   PIPELINE v45 — FastAPI + Streaming + Gestão + Compat Starlette 0.36+   ║
# ╚══════════════════════════════════════════════════════════════════════════╝
from __future__ import annotations
import os, json, re, time, asyncio, logging
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import AsyncGroq
from sqlmodel import Session

from core.workspace import folder as _workspace_folder

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

ARQUIVO_CONFIG   = "protocolo.json"
ARQUIVO_HELP     = "help.md"
ARQUIVO_CONTEXTO = "contexto_persistente.json"
CONTEXTO_PATH = Path(os.getenv("PERSISTENT_CONTEXT_FILE", str(Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parent))) / ARQUIVO_CONTEXTO)))
CONTEXTO_PATH.parent.mkdir(parents=True, exist_ok=True)
DELAY_ENTRE_AGENTES = 0.2
STOP_KEYWORD     = "STOP_PIPELINE:"
MODELO_PADRAO    = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

BASE_DIR = Path(__file__).resolve().parent
log.info("LeIA · serviço cognitivo | Groq: %s",
         "OK" if "gsk_" in groq_key else "⚠️ placeholder")

# ─── APP ─────────────────────────────────────────────────────────────────
_docs_on = os.getenv("DOCS_ENABLED", "false").lower() in ("1", "true", "yes")
app = FastAPI(title="LeIA · serviço cognitivo", docs_url="/docs" if _docs_on else None,
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
#  JSON → TEXTO HUMANO
# ══════════════════════════════════════════════════════════════════════════
def _label(k: str) -> str:
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
            rot = _label(k)
            txt = _fmt_valor(val, indent + 1)
            linhas.append(f"{pad}{rot}:{txt}" if txt.startswith("\n")
                          else f"{pad}{rot}: {txt}")
        return "\n" + "\n".join(linhas)
    return str(v)


def format_text_content(content) -> str:
    if isinstance(content, str):
        s = content.strip()
        if s.startswith(("{", "[")) and s.endswith(("}", "]")):
            try:
                return format_text_content(json.loads(s))
            except Exception:
                pass
        return content
    if isinstance(content, dict):
        partes = []
        for k, v in content.items():
            rot = _label(k)
            txt = _fmt_valor(v, 0)
            partes.append(f"▸ {rot}:{txt}" if txt.startswith("\n")
                          else f"▸ {rot}: {txt}")
        return "\n".join(partes)
    if isinstance(content, list):
        blocos = []
        for i, item in enumerate(content, 1):
            blocos.append(f"── Item {i} ──")
            blocos.append(format_text_content(item))
            blocos.append("")
        return "\n".join(blocos).rstrip()
    return str(content)


# ══════════════════════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════════════
def estimar_tokens(t) -> int:
    return len(str(t)) // 4


def _read_file(nome: str, default: str = "") -> str:
    try:
        return (BASE_DIR / nome).read_text(encoding="utf-8")
    except Exception as e:
        log.warning("⚠️  Falha lendo %s: %s", nome, e)
        return default


def load_protocol() -> str:
    return _read_file(ARQUIVO_CONFIG, "[]")


def load_help() -> str:
    return _read_file(ARQUIVO_HELP, "# Help\n\nCrie `help.md` na raiz.")


def save_protocol(conteudo: str) -> str:
    try:
        agentes = json.loads(conteudo)
        (BASE_DIR / ARQUIVO_CONFIG).write_text(conteudo, encoding="utf-8")
        log.info("💾 protocolo salvo | %d agentes", len(agentes))
        return f"✅ Protocolo salvo ({len(agentes)} agentes)"
    except Exception as e:
        log.error("❌ protocolo inválido | %s", e)
        return f"❌ Erro JSON: {e}"


def load_persistent_context() -> list:
    try:
        return json.loads(CONTEXTO_PATH.read_text(encoding="utf-8"))
    except Exception:
        log.info("📝 contexto persistente vazio")
        return []


def save_persistent_context(ctx: list) -> None:
    try:
        CONTEXTO_PATH.write_text(
            json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.error("❌ contexto save | %s", e)


def clear_persistent_context() -> str:
    try:
        CONTEXTO_PATH.write_text("[]", encoding="utf-8")
        log.info("🗑️  contexto limpo")
        return "✅ Contexto limpo"
    except Exception as e:
        return f"❌ Erro: {e}"


def limitar_timeline(timeline, max_chars: int = 12000, max_msgs: int = 12):
    """
    Seleciona as mensagens mais recentes até o orçamento de chars/msgs.

    Bug corrigido: a versão anterior fazia `acum += len(t)` e só DEPOIS
    verificava o limite — então quando a ÚLTIMA mensagem (a pergunta atual,
    já com o objetivo/T6_FUSAO_MEMORIA embutido) sozinha já passava de
    max_chars, ela era descartada inteira e o modelo recebia só o system
    prompt + a instrução final, sem pergunta nem contexto nenhum (é
    exatamente o que aconteceu: "0 msgs · 23121 chars" no log — a mensagem
    de 23k chars foi contada e depois jogada fora).

    Agora a última mensagem da timeline (o input atual do usuário) NUNCA é
    descartada por estourar o orçamento — só o histórico anterior a ela é
    cortado para caber no que sobrar do orçamento.
    """
    if not timeline:
        return [], 0, 0

    *historico, atual = timeline
    atual_content = str(atual.get("content", ""))
    acum = len(atual_content)
    if acum > max_chars:
        log.warning("⚠️  mensagem atual (%d chars) já excede max_chars (%d) "
                    "sozinha — mantida integralmente mesmo assim", acum, max_chars)
    sel = [atual]

    for msg in reversed(historico):
        t = str(msg.get("content", ""))
        acum += len(t)
        if acum > max_chars or len(sel) >= max_msgs:
            break
        sel.append(msg)

    sel.reverse()
    return sel, acum, estimar_tokens(acum)


def read_attachment_bytes(nome: str, conteudo: bytes) -> str:
    try:
        texto = conteudo.decode("utf-8", errors="replace")
        log.info("📎 anexo | %s | %d chars", nome, len(texto))
        return f"\n\n[ANEXO: {nome}]\n{texto}\n[FIM ANEXO]\n"
    except Exception as e:
        log.error("❌ anexo %s | %s", nome, e)
        return ""


# ══════════════════════════════════════════════════════════════════════════
#  DEBUG — payload real enviado/recebido do LLM no Chat Bot, gravado em
#  workspace/{hash}/chat_llm_debug.jsonl (mesma folder do T6_FUSAO_MEMORIA.json
#  daquela sessão de destilação). Existe para depurar por que o chat às vezes
#  não usa o processo destilado para responder: com isso dá pra conferir,
#  linha a linha, exatamente o que foi montado e mandado pro modelo (incluindo
#  se o T6 realmente foi injetado no prompt) e o que ele devolveu.
# ══════════════════════════════════════════════════════════════════════════
def _debug_log_llm(hash_sessao: str | None, tipo: str, **dados) -> None:
    if not hash_sessao:
        log.info("🐞 debug LLM | sem hash de sessão (nenhum T6 destilado ainda) | tipo=%s", tipo)
        return
    try:
        linha = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipo": tipo,
            **dados,
        }
        p = _workspace_folder(hash_sessao) / "chat_llm_debug.jsonl"
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False, default=str) + "\n")
        log.info("🐞 debug LLM salvo | hash=%s… | tipo=%s | %s",
                  hash_sessao[:8], tipo, p)
    except Exception as e:
        log.error("❌ debug LLM falhou | hash=%s | %s", hash_sessao, e)


def has_stop_keyword(texto) -> bool:
    return bool(texto and re.search(r"\b" + re.escape(STOP_KEYWORD) + r"\b",
                                    str(texto), re.I))


def _extract_json(texto: str) -> str:
    t = (texto or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json|jshon|javascript)?\s*", "", t, flags=re.I)
        t = re.sub(r"\s*```\s*$", "", t).strip()
    for abre, fecha in (("{", "}"), ("[", "]")):
        i, j = t.find(abre), t.rfind(fecha)
        if i >= 0 and j > i:
            return t[i:j + 1]
    return t


def _build_messages(timeline, config) -> list:
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
async def _run_agent(timeline, config, emitir_stream: bool = False,
                            debug_hash: str | None = None):
    nome   = config.get("nome", "?")
    modelo = config.get("modelo") or MODELO_PADRAO
    tipo   = config.get("tipo_saida", "texto").lower()

    log.info("━" * 62)
    log.info("🔥 AGENTE | %s | stream=%s", nome, emitir_stream)
    log.info("   modelo=%s · tipo_saida=%s", modelo, tipo)

    messages = _build_messages(timeline, config)
    total_chars = sum(len(m.get("content", "")) for m in messages)
    log.info("   → payload | %d msgs · ~%d chars", len(messages), total_chars)
    _debug_log_llm(debug_hash, "chat_llm_payload_enviado",
                    agente=nome, modelo=modelo, total_chars=total_chars,
                    messages=messages)
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
                content = json.loads(_extract_json(out_raw))
                log.info("   ✅ JSON | %d chaves", len(content))
            except Exception:
                log.info("   ℹ️  fallback: texto")

        _debug_log_llm(debug_hash, "chat_llm_payload_recebido",
                        agente=nome, tempo=round(tempo, 3),
                        think_chars=len(think_raw), resposta_bruta=out_raw,
                        resposta=content)

        yield ("done", {
            "role": "assistant",
            "agent": nome,
            "content": content,
            "text": format_text_content(content),
            "is_json": isinstance(content, (dict, list)),
            "groq_payload_real": messages,
            "tempo": tempo,
            "think_chars": len(think_raw),
        })
    except Exception as e:
        log.error("   💥 ERRO | %s", e)
        _debug_log_llm(debug_hash, "chat_llm_erro", agente=nome, erro=str(e))
        yield ("error", str(e))


# ══════════════════════════════════════════════════════════════════════════
#  SSE
# ══════════════════════════════════════════════════════════════════════════
def _sse(evt: dict) -> str:
    return f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"


async def _stream_orchestrator(texto, anexos, protocolo_json, objetivo, isolar_pergunta=True,
                                debug_hash: str | None = None):
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

    ctx = load_persistent_context()
    ctx.append({
        "role": "user",
        "content": f"[USUARIO] {texto}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    ctx_sessao = ""
    if objetivo and objetivo.strip():
        ctx_sessao += f"[OBJETIVO DO MODELO]\n{objetivo.strip()}\n[FIM OBJETIVO]\n\n"
    for nome, blob in anexos:
        ctx_sessao += read_attachment_bytes(nome, blob)

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

        async for kind, payload in _run_agent(
            timeline, cfg, emitir_stream=eh_ultimo, debug_hash=debug_hash
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

                if has_stop_keyword(resp):
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
                save_persistent_context(ctx)
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
#  ROTAS — API
# ══════════════════════════════════════════════════════════════════════════
@app.get("/api/protocolo")
async def api_get_protocolo(u: Usuario = Depends(admin_user)):
    return {"conteudo": load_protocol()}


@app.post("/api/protocolo")
async def api_post_protocolo(payload: dict, u: Usuario = Depends(admin_user)):
    return {"message": save_protocol(payload.get("conteudo", "[]"))}


@app.get("/api/help")
async def api_get_help(u: Usuario = Depends(admin_user)):
    return {"conteudo": load_help()}


@app.get("/api/contexto")
async def api_get_contexto(u: Usuario = Depends(admin_user)):
    return {"contexto": load_persistent_context()}


@app.post("/api/contexto/limpar")
async def api_post_limpar_contexto(u: Usuario = Depends(admin_user)):
    return {"message": clear_persistent_context()}


@app.post("/api/chat")
async def api_chat(
    request: Request,
    texto: str = Form(...),
    objetivo: str = Form(""),
    protocolo_json: str = Form(""),
    anexos: List[UploadFile] = File(default=[]),
    u: Usuario = Depends(admin_user),
):
    # O front-end não edita mais o protocolo por requisição (o antigo painel
    # de edição foi removido do template). Se não vier nada usável aqui,
    # cai pro protocolo.json canônico do servidor — sem isso o chat ficava
    # respondendo vazio (protocolo="{}" => 0 agentes executados).
    protocolo_efetivo = protocolo_json
    try:
        _p = json.loads(protocolo_json or "null")
        if not isinstance(_p, list) or not _p:
            protocolo_efetivo = load_protocol()
    except Exception:
        protocolo_efetivo = load_protocol()

    # Anexo compartilhado (server-side, autoritativo): o processo
    # estruturado (T6_FUSAO_MEMORIA) já destilado nesta sessão de login.
    # Acompanha TODA pergunta do usuário. Nunca inclui PDF, texto bruto,
    # nem nada do fluxo de PDF assinado (memória inteiramente separada).
    from core import session as sess
    token = u.session_token
    anexo = sess.shared_attachment(token) if token else None
    hash_sessao = anexo.get("hash") if anexo else None
    objetivo_efetivo = objetivo
    if anexo:
        objetivo_efetivo += (
            "\n\nO processo abaixo (\"" + str(anexo.get("titulo") or "documento") + "\") "
            "já foi destilado nesta sessão e está disponível para responder à "
            "pergunta do usuário. Use SOMENTE estes dados — responda em "
            "português do Brasil, direto, à pergunta específica feita.\n\n"
            "PROCESSO:\n"
            + json.dumps(anexo["processo"], ensure_ascii=False)
        )
        # Grava o T6 exatamente como foi injetado no prompt — permite conferir
        # se o conteúdo de T6_FUSAO_MEMORIA.json realmente chegou ao modelo
        # (e em que formato), sem precisar reconstruir isso a partir do log
        # geral de payload de cada agente.
        _debug_log_llm(hash_sessao, "chat_contexto_t6_injetado",
                        titulo=anexo.get("titulo"),
                        pergunta_usuario=texto,
                        t6_processo=anexo["processo"])
    else:
        log.warning("⚠️  chat sem T6 destilado nesta sessão — "
                    "respondendo sem processo anexado | user=%s", u.email)

    anexos_bytes = []
    for up in anexos:
        if up and up.filename:
            anexos_bytes.append((up.filename, await up.read()))
    gen = _stream_orchestrator(texto, anexos_bytes, protocolo_efetivo, objetivo_efetivo,
                                isolar_pergunta=True, debug_hash=hash_sessao)
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