# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   PIPELINE PDF v2 — Sequencial · ADUC-SDR · com variação p/ novas rodadas ║
# ╚══════════════════════════════════════════════════════════════════════════╝
"""
Orquestrador da pipeline PDF → resumo humanizado + questões.

Fluxo sequencial:
  PDF → texto_extraido.txt
       ↓
  T1..T5  (fragmentação por classe — 5 chamadas)
       ↓
  T6      (fusão em memoria_persistente.json)
       ↓
  T7..T11 (5 sínteses parciais)
       ↓
  T12     (_ui com posições para highlight)
       ↓
  T13     (resumo_humanizado.md)
       ↓
  T14     (12 questões → questoes.json)

Cada passo grava um arquivo no workspace/{hash}/ e um evento no log.jsonl.
"""
from __future__ import annotations
import json, logging, time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session

from core.db import engine, Tarefa, LogEvento
from core.pdf_extract import extrair_texto
from core.workspace import pasta, registrar_evento

log = logging.getLogger("pipeline_pdf")

PROTOCOLO_PDF = Path("protocolo_pdf.json")
MODELO_PADRAO = "openai/gpt-oss-120b"


# ══════════════════════════════════════════════════════════════════════════
#  EXECUÇÃO DE UMA TASK VIA GROQ
# ══════════════════════════════════════════════════════════════════════════
def _montar_prompt(task: dict, contexto_extra: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                f"AGENTE: {task.get('nome', task['id'])}\n"
                f"MISSÃO:\n{task['missao']}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"<contexto>\n{contexto_extra.strip()}\n</contexto>\n\n"
                "Execute a missão agora e produza APENAS a saída esperada. "
                "NÃO adicione comentários, preâmbulos ou epílogos."
            ),
        },
    ]


def _extrair_json_robusto(texto: str) -> str:
    """Recorta {...} ou [...] mesmo com prosa em volta e cercas ```json."""
    import re
    t = (texto or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json|jshon|javascript)?\s*", "", t, flags=re.I)
        t = re.sub(r"\s*```\s*$", "", t).strip()
    for abre, fecha in (("{", "}"), ("[", "]")):
        i, j = t.find(abre), t.rfind(fecha)
        if i >= 0 and j > i:
            return t[i:j + 1]
    return t


async def _executar_task_groq(
    task: dict,
    contexto_extra: str,
    groq_client,
) -> dict:
    """Executa uma task e retorna dict com raw, parsed, ok, tempo, erro."""
    messages = _montar_prompt(task, contexto_extra)
    modelo = task.get("modelo") or MODELO_PADRAO
    tipo   = (task.get("tipo_saida") or "json").lower()

    log.info("🔹 [%s] modelo=%s · tipo=%s", task["id"], modelo, tipo)
    t0 = time.time()
    out_raw = ""

    try:
        kwargs = dict(
            model=modelo,
            messages=messages,
            temperature=task.get("temperature", 0.0),
            max_completion_tokens=task.get("max_completion_tokens", 8000),
            top_p=1,
            stream=True,
        )
        # reasoning_format só existe em SDKs novos
        try:
            kwargs["reasoning_format"] = "parsed"
            stream = await groq_client.chat.completions.create(**kwargs)
        except TypeError:
            kwargs.pop("reasoning_format", None)
            stream = await groq_client.chat.completions.create(**kwargs)

        async for chunk in stream:
            delta = chunk.choices[0].delta
            c = getattr(delta, "content", None) or ""
            if c:
                out_raw += c

        tempo = time.time() - t0
        parsed = out_raw
        if tipo in ("json", "jshon"):
            try:
                parsed = json.loads(_extrair_json_robusto(out_raw))
            except Exception as e:
                log.warning("⚠️  [%s] JSON inválido | %s", task["id"], e)

        log.info("✅ [%s] %.2fs · %d chars", task["id"], tempo, len(out_raw))
        return {"raw": out_raw, "parsed": parsed, "ok": True, "tempo": tempo}

    except Exception as e:
        tempo = time.time() - t0
        log.error("💥 [%s] ERRO | %s", task["id"], e)
        return {"raw": out_raw, "parsed": None, "ok": False,
                "erro": str(e), "tempo": tempo}


# ══════════════════════════════════════════════════════════════════════════
#  CONTEXTO CUMULATIVO
# ══════════════════════════════════════════════════════════════════════════
def _contexto_para_task(
    modo: str,
    texto_pdf: str,
    outputs_anteriores: dict[str, Any],
) -> str:
    """
    modo ∈ {"texto_bruto", "outputs_anteriores"}
    """
    if modo == "texto_bruto":
        return f"<data_user>\n{texto_pdf}\n</data_user>"

    partes = ["<outputs_anteriores>"]
    for k, v in outputs_anteriores.items():
        if isinstance(v, (dict, list)):
            partes.append(f"<{k}>\n{json.dumps(v, ensure_ascii=False, indent=2)}\n</{k}>")
        else:
            partes.append(f"<{k}>\n{v}\n</{k}>")
    partes.append("</outputs_anteriores>")
    return "\n\n".join(partes)


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS DE PERSISTÊNCIA
# ══════════════════════════════════════════════════════════════════════════
def _atualizar_status(tarefa_id: int, status: str) -> None:
    with Session(engine) as s:
        t = s.get(Tarefa, tarefa_id)
        if not t:
            return
        t.status = status
        t.atualizada_em = datetime.utcnow()
        s.add(t)
        s.add(LogEvento(tarefa_id=tarefa_id, tipo=f"status:{status}",
                        payload=None))
        s.commit()


def _evento(tarefa_id: int, tipo: str, payload: dict | None = None) -> None:
    with Session(engine) as s:
        s.add(LogEvento(
            tarefa_id=tarefa_id,
            tipo=tipo,
            payload=json.dumps(payload or {}, ensure_ascii=False)[:2000],
        ))
        s.commit()


def _salvar(hash_: str, nome: str, conteudo: Any) -> Path:
    p = pasta(hash_) / nome
    if isinstance(conteudo, (dict, list)):
        p.write_text(
            json.dumps(conteudo, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        p.write_text(str(conteudo), encoding="utf-8")
    return p


# ══════════════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════
async def executar_pipeline_pdf(
    tarefa_id: int,
    groq_client,
    variacao: str = "",
    session_token: str | None = None,
) -> None:
    """
    Entry-point chamado por BackgroundTasks.

    Args:
        tarefa_id:     id da Tarefa no banco
        groq_client:   AsyncGroq já instanciado
        variacao:      (opcional) string para forçar questões diferentes na clonagem
        session_token: (opcional) sessão de login para registrar a destilação
                       (aba "chat") na memória de sessão ao concluir
    """
    log.info("═" * 70)
    log.info("🎬 PIPELINE PDF | tarefa_id=%s | variacao=%s",
             tarefa_id, "sim" if variacao else "não")

    # ── 1. Carrega tarefa
    with Session(engine) as s:
        t = s.get(Tarefa, tarefa_id)
        if not t:
            log.error("Tarefa %s não encontrada", tarefa_id)
            return
        hash_ = t.hash
        pdf_path = Path(t.workspace_path) / "original.pdf"

    _atualizar_status(tarefa_id, "processando")
    registrar_evento(hash_, "pipeline_start", tarefa_id=tarefa_id)

    # ── 2. Extrai texto do PDF
    try:
        texto_pdf = extrair_texto(pdf_path)
    except Exception as e:
        log.error("💥 Extração falhou | %s", e)
        _atualizar_status(tarefa_id, "falhou")
        _evento(tarefa_id, "erro_extracao", {"erro": str(e)})
        registrar_evento(hash_, "erro_extracao", erro=str(e))
        return

    _salvar(hash_, "texto_extraido.txt", texto_pdf)
    _evento(tarefa_id, "texto_extraido", {"chars": len(texto_pdf)})
    registrar_evento(hash_, "texto_extraido", chars=len(texto_pdf))
    log.info("📄 texto extraído | %d chars", len(texto_pdf))

    # ── 3. Carrega protocolo
    try:
        protocolo = json.loads(PROTOCOLO_PDF.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("💥 protocolo_pdf.json | %s", e)
        _atualizar_status(tarefa_id, "falhou")
        _evento(tarefa_id, "erro_protocolo", {"erro": str(e)})
        return

    tasks = protocolo["tasks"]
    total = len(tasks)
    tarefa_por_id = {tk["id"]: tk for tk in tasks}

    # ── 4. Loop sequencial
    outputs_anteriores: dict[str, Any] = {}
    cur_id = protocolo["workflow"]["start"]
    t_pipe = time.time()

    while cur_id and cur_id not in ("END_SUCCESS", "END_FAILURE"):
        task = tarefa_por_id.get(cur_id)
        if not task:
            log.error("Task %s não existe", cur_id)
            break

        try:
            idx = tasks.index(task) + 1
        except ValueError:
            idx = 0

        _evento(tarefa_id, "task_start", {
            "id": task["id"], "nome": task.get("nome"),
            "idx": idx, "total": total,
        })
        registrar_evento(hash_, "task_start",
                         id=task["id"], idx=idx, total=total)

        # Contexto
        modo = task.get("contexto_adicional", "texto_bruto")
        ctx = _contexto_para_task(modo, texto_pdf, outputs_anteriores)
        if variacao:
            ctx = f"<variacao>{variacao}</variacao>\n\n{ctx}"

        # Executa
        res = await _executar_task_groq(task, ctx, groq_client)

        if not res["ok"]:
            _evento(tarefa_id, "task_error", {
                "id": task["id"], "erro": res.get("erro"),
            })
            registrar_evento(hash_, "task_error",
                             id=task["id"], erro=res.get("erro"))
            _atualizar_status(tarefa_id, "falhou")
            return

        # Guarda output
        outputs_anteriores[task["id"]] = res["parsed"]

        # Salva arquivo da task
        _salvar(hash_, f"{task['id']}.json", res["parsed"])

        _evento(tarefa_id, "task_done", {
            "id": task["id"], "tempo": round(res["tempo"], 2),
        })
        registrar_evento(hash_, "task_done",
                         id=task["id"], tempo=round(res["tempo"], 2))

        # Próximo
        nxt = (task.get("transitions") or [{}])[0].get("target")
        cur_id = nxt

    # ── 5. Consolida artefatos finais
    if "T6_FUSAO_MEMORIA" in outputs_anteriores:
        _salvar(hash_, "memoria_persistente.json",
                outputs_anteriores["T6_FUSAO_MEMORIA"])

    if "T12_PROCESSAMENTO" in outputs_anteriores:
        _salvar(hash_, "texto_tagueado.json",
                outputs_anteriores["T12_PROCESSAMENTO"])

    if "T13_HUMANIZACAO" in outputs_anteriores:
        val = outputs_anteriores["T13_HUMANIZACAO"]
        if isinstance(val, dict):
            val = (val.get("resumo_humanizado")
                   or val.get("texto")
                   or json.dumps(val, ensure_ascii=False))
        _salvar(hash_, "resumo_humanizado.md", val)

    if "T14_QUESTOES" in outputs_anteriores:
        _salvar(hash_, "questoes.json", outputs_anteriores["T14_QUESTOES"])

    # ── 6. Finaliza
    tempo_total = round(time.time() - t_pipe, 2)
    _atualizar_status(tarefa_id, "pronta")
    _evento(tarefa_id, "pipeline_done", {"elapsed": tempo_total})
    registrar_evento(hash_, "pipeline_done", elapsed=tempo_total)

    # Memória de sessão — só a parte "resumo estruturado" (memoria_persistente
    # + resumo_humanizado), nunca o PDF nem o texto extraído.
    if session_token:
        with Session(engine) as s:
            t = s.get(Tarefa, tarefa_id)
            titulo = t.titulo if t else hash_
        from core import sessao as sess
        sess.registrar_destilacao(
            session_token, "chat",
            hash_=hash_, titulo=titulo,
            resumo_estruturado={
                "memoria_persistente": outputs_anteriores.get("T6_FUSAO_MEMORIA"),
                "resumo_humanizado": outputs_anteriores.get("T13_HUMANIZACAO"),
            },
        )

    log.info("🏁 PIPELINE | %.2fs | tarefa=%s", tempo_total, tarefa_id)