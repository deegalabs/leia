# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   GESTÃO v3.1 — Login · Dashboard · Tarefas · Quiz · Chat · PDF assinado ║
# ║   Compat Starlette ≥ 0.36 (TemplateResponse(request, name, context))     ║
# ╚══════════════════════════════════════════════════════════════════════════╝
from __future__ import annotations
import os
import json, logging, shutil, secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import (APIRouter, BackgroundTasks, Depends, Form, HTTPException,
                     Request, UploadFile, File, status)
from fastapi.responses import (RedirectResponse, FileResponse,
                               StreamingResponse)
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from core.db import (Usuario, Tarefa, LogEvento, Tentativa,
                     get_session, init_db, engine)
from core.db import Duvida                       # LeIA: doubts sent by the citizen
from leia.pipeline import run_pipeline           # LeIA: semaphore around the workflow
from leia.ratelimit import rate_limit            # LeIA: per-IP limit on public write routes
from core.auth import (authenticate, end_session, current_user,
                       create_initial_user, hash_password)
from core import workspace as ws
from core import session as sess
from core import attempts as tn
from core.pdf_sign import build_signed_pdf

log = logging.getLogger("gestao")

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════
def _ok_pdf(up: UploadFile) -> bool:
    return (up.filename or "").lower().endswith(".pdf")


def _read_artifact(hash_: str, nome: str) -> Optional[str]:
    p = ws.folder(hash_) / nome
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


def _read_json(hash_: str, nome: str):
    txt = _read_artifact(hash_, nome)
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except Exception:
        return None


def _permite_ver(u: Usuario, t: Tarefa) -> bool:
    # LeIA: fornecedor sees everything; anyone else sees what they sent or, as a citizen, what is linked to them
    if u.papel == "fornecedor":
        return True
    return t.advogado_id == u.id or (t.cidadao_id is not None and t.cidadao_id == u.id)


# LeIA: shared by POST /tarefas/nova (panel) and POST /api/tarefas (app): workspace, original.pdf, meta.json,
# events, LogEvento and the background workflow. ``origem`` and ``cidadao_id`` are the v3 columns.
async def create_pdf_task(
    session: Session,
    u: Usuario,
    titulo: str,
    pdf: UploadFile,
    bg: BackgroundTasks,
    *,
    origem: str = "advogado",
    cidadao_id: Optional[int] = None,
    session_token: Optional[str] = None,
) -> Tarefa:
    if not _ok_pdf(pdf):
        raise HTTPException(400, "Envie um PDF.")

    h = ws.new_hash()
    folder = ws.folder(h)

    conteudo = await pdf.read()
    # LeIA: size cap and real PDF check (the extension alone is not enough)
    if len(conteudo) > int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024:
        raise HTTPException(413, "Arquivo grande demais. Envie um PDF de até %s MB." % os.getenv("MAX_UPLOAD_MB", "15"))
    if not conteudo.startswith(b"%PDF"):
        raise HTTPException(400, "Este arquivo não é um PDF.")
    if not conteudo:
        raise HTTPException(400, "O arquivo está vazio.")
    (folder / "original.pdf").write_bytes(conteudo)

    titulo_final = (titulo or "").strip()[:200] or (pdf.filename or "documento")[:200]
    t = Tarefa(
        hash=h,
        titulo=titulo_final,
        advogado_id=u.id,
        status="criada",
        pdf_nome=pdf.filename,
        workspace_path=str(folder),
        rodada=1,
        origem=origem,
        cidadao_id=cidadao_id,
    )
    session.add(t); session.commit(); session.refresh(t)

    ws.save_meta(h, {
        "hash": h,
        "titulo": t.titulo,
        "advogado": {"id": u.id, "email": u.email, "nome": u.nome},
        "pdf_nome": pdf.filename,
        "pdf_bytes": len(conteudo),
        "criada_em": t.criada_em.isoformat(),
        "origem": origem,
    })
    ws.record_event(h, "criada", tarefa_id=t.id, advogado_id=u.id)
    ws.record_event(h, "pdf_salvo", nome=pdf.filename, bytes=len(conteudo))

    session.add(LogEvento(tarefa_id=t.id, tipo="criada",
                          payload=f'{{"hash":"{h}"}}'))
    session.commit()

    from main import groq_client
    bg.add_task(run_pipeline, t.id, groq_client, "", session_token)

    log.info("📁 Tarefa criada + pipeline agendada | id=%s hash=%s origem=%s", t.id, h, origem)
    return t


# ══════════════════════════════════════════════════════════════════════════
#  NOVA TAREFA
# ══════════════════════════════════════════════════════════════════════════
@router.post("/api/pdf/destilar")
async def api_pdf_destilar(
    request: Request,
    bg: BackgroundTasks,
    pdf: UploadFile = File(...),
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """
    Versão JSON (para o chat/LeIA) do fluxo de `nova_post`: recebe um PDF,
    cria a Tarefa e dispara o protocolo de destilação (protocolo_pdf.json)
    em background. O front-end acompanha o progresso via
    GET /api/tarefas/{id}/status (eventos task_start/task_done/task_error).
    Não devolvemos HTML — devolvemos {tarefa_id, hash} para o chat renderizar
    os blocos de inferência.
    """
    if not _ok_pdf(pdf):
        raise HTTPException(400, "Envie um PDF.")

    h = ws.new_hash()
    folder = ws.folder(h)

    conteudo = await pdf.read()
    # LeIA: size cap and real PDF check (the extension alone is not enough)
    if len(conteudo) > int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024:
        raise HTTPException(413, "Arquivo grande demais. Envie um PDF de até %s MB." % os.getenv("MAX_UPLOAD_MB", "15"))
    if not conteudo.startswith(b"%PDF"):
        raise HTTPException(400, "Este arquivo não é um PDF.")
    (folder / "original.pdf").write_bytes(conteudo)

    t = Tarefa(
        hash=h,
        titulo=(pdf.filename or "documento")[:200],
        advogado_id=u.id,
        status="criada",
        pdf_nome=pdf.filename,
        workspace_path=str(folder),
        rodada=1,
    )
    session.add(t); session.commit(); session.refresh(t)

    ws.save_meta(h, {
        "hash": h,
        "titulo": t.titulo,
        "advogado": {"id": u.id, "email": u.email, "nome": u.nome},
        "pdf_nome": pdf.filename,
        "pdf_bytes": len(conteudo),
        "criada_em": t.criada_em.isoformat(),
        "origem": "chat_destilacao",
    })
    ws.record_event(h, "criada", tarefa_id=t.id, advogado_id=u.id)
    ws.record_event(h, "pdf_salvo", nome=pdf.filename, bytes=len(conteudo))

    session.add(LogEvento(tarefa_id=t.id, tipo="criada",
                          payload=f'{{"hash":"{h}"}}'))
    session.commit()

    token = u.session_token  # LeIA: v5 (Carlos) reads the token from the user
    from main import groq_client
    bg.add_task(run_pipeline, t.id, groq_client, "", token)   # LeIA: bounded by PIPELINE_CONCURRENCY

    if not token:
        log.warning("⚠️  [chat] session_token ausente para usuário %s — "
                   "destilação NÃO será registrada na memória de sessão", u.id)

    log.info("📁 [chat] Tarefa criada + destilação agendada | id=%s hash=%s", t.id, h)
    return {"tarefa_id": t.id, "hash": h}


@router.get("/api/pdf/{hash_}/destilado")
async def api_pdf_destilado(
    hash_: str,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """
    Devolve o material DESTILADO da tarefa (nunca o PDF/texto bruto):
    memoria_persistente.json (fusão T1-T5), resumo_humanizado.md e
    questoes.json, quando já existirem. É isso — e só isso — que o chat
    deve guardar/reusar como contexto do documento.
    """
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t or not _permite_ver(u, t):
        raise HTTPException(404)

    return {
        "status": t.status,
        "titulo": t.titulo,
        "memoria": _read_json(hash_, "memoria_persistente.json"),
        "resumo": _read_artifact(hash_, "resumo_humanizado.md"),
    }


@router.get("/api/pdf/{hash_}/log")
async def api_pdf_log(
    hash_: str,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """
    Eventos do protocolo de destilação (log.jsonl) para alimentar os
    blocos de inferência no chat (task_start/task_done/pipeline_done/erro).
    Nunca expõe o PDF ou o texto bruto — só marcos do processo.
    """
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t or not _permite_ver(u, t):
        raise HTTPException(404)

    eventos = [
        e for e in ws.read_events(hash_)
        if e.get("tipo") in (
            "pipeline_start", "texto_extraido", "task_start",
            "task_done", "task_error", "erro_extracao",
            "erro_protocolo", "pipeline_done",
        )
    ]
    return {"status": t.status, "eventos": eventos}


# ══════════════════════════════════════════════════════════════════════════
#  RESUMO ESTRUTURADO (novo) — via API pública externa
#  api.resumoestruturado.com.br. NÃO usa Groq/protocolo_pdf.json local:
#  quem decompõe o documento é o backend externo (core/pesquisa.py).
#  O resultado é salvo no workspace no mesmo padrão da destilação local.
# ══════════════════════════════════════════════════════════════════════════
@router.post("/api/resumo-estruturado/submit")
async def api_resumo_estruturado_submit(
    request: Request,
    bg: BackgroundTasks,
    pdf: Optional[UploadFile] = File(default=None),
    texto: Optional[str] = Form(default=None),
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """
    Recebe um PDF OU um texto colado e dispara o envio para a API pública
    externa (api.resumoestruturado.com.br) em background. Cria uma Tarefa
    e um workspace/{hash}/ do mesmo jeito que o fluxo local — só que quem
    decompõe é o serviço externo, não o Groq.
    """
    if not pdf and not (texto and texto.strip()):
        raise HTTPException(400, "Envie um PDF ou um texto.")
    if pdf and pdf.filename and not _ok_pdf(pdf):
        raise HTTPException(400, "Envie um PDF.")

    h = ws.new_hash()
    folder = ws.folder(h)

    pdf_bytes: Optional[bytes] = None
    nome_pdf: Optional[str] = None
    if pdf and pdf.filename:
        pdf_bytes = await pdf.read()
        nome_pdf = pdf.filename
        (folder / "original.pdf").write_bytes(pdf_bytes)

    t = Tarefa(
        hash=h,
        titulo=(nome_pdf or (texto or "").strip()[:60] or "resumo estruturado")[:200],
        advogado_id=u.id,
        status="criada",
        pdf_nome=nome_pdf,
        workspace_path=str(folder),
        rodada=1,
    )
    session.add(t); session.commit(); session.refresh(t)

    ws.save_meta(h, {
        "hash": h,
        "titulo": t.titulo,
        "advogado": {"id": u.id, "email": u.email, "nome": u.nome},
        "pdf_nome": nome_pdf,
        "criada_em": t.criada_em.isoformat(),
        "origem": "resumo_estruturado_api_externa",
    })
    ws.record_event(h, "criada", tarefa_id=t.id, advogado_id=u.id)
    session.add(LogEvento(tarefa_id=t.id, tipo="criada", payload=f'{{"hash":"{h}"}}'))
    session.commit()

    token = u.session_token
    from core.api import run_structured_summary
    bg.add_task(run_structured_summary, t.id, pdf_bytes, texto,
                nome_pdf or "documento.pdf", token)

    log.info("📁 [resumo estruturado · API externa] Tarefa criada | id=%s hash=%s", t.id, h)
    return {"tarefa_id": t.id, "hash": h}


@router.get("/api/resumo-estruturado/{hash_}/status")
async def api_resumo_estruturado_status(
    hash_: str,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Eventos do acompanhamento do job na API externa (resumo_estruturado_*)."""
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t or not _permite_ver(u, t):
        raise HTTPException(404)

    eventos = [
        e for e in ws.read_events(hash_)
        if str(e.get("tipo", "")).startswith("resumo_estruturado")
    ]
    return {"status": t.status, "eventos": eventos}


@router.get("/api/resumo-estruturado/{hash_}/resultado")
async def api_resumo_estruturado_resultado(
    hash_: str,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Devolve o resultado já salvo no workspace (dados_llm + doc_text)."""
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t or not _permite_ver(u, t):
        raise HTTPException(404)

    return {
        "status": t.status,
        "titulo": t.titulo,
        "dados_llm": _read_json(hash_, "resumo_estruturado.json"),
        "doc_text": _read_artifact(hash_, "resumo_estruturado_texto.txt"),
    }


@router.post("/api/resumo-estruturado/{hash_}/rerun/{step_id}")
async def api_resumo_estruturado_rerun(
    hash_: str,
    step_id: str,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Proxy para /jobs/{job_id}/rerun/{step_id} na API externa."""
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t or not _permite_ver(u, t):
        raise HTTPException(404)

    job = _read_json(hash_, "resumo_estruturado_job.json") or {}
    job_id = job.get("job_id")
    if not job_id:
        raise HTTPException(409, "Nenhum job da API externa associado a esta tarefa.")

    from core.api import rerun_step, ResumoEstruturadoError
    try:
        return await rerun_step(job_id, step_id)
    except ResumoEstruturadoError as e:
        raise HTTPException(502, str(e))


# ══════════════════════════════════════════════════════════════════════════
#  JURISPRUDÊNCIA — via API pública externa (mesmo padrão do Resumo
#  Estruturado acima). Aceita PDF, texto colado ou uma consulta de pesquisa.
# ══════════════════════════════════════════════════════════════════════════
@router.post("/api/jurisprudencia/submit")
async def api_jurisprudencia_submit(
    request: Request,
    bg: BackgroundTasks,
    pdf: Optional[UploadFile] = File(default=None),
    texto: Optional[str] = Form(default=None),
    consulta: Optional[str] = Form(default=None),
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """
    Recebe um PDF, um texto colado, e/ou uma consulta de pesquisa, e
    dispara o envio para a API pública externa de jurisprudência em
    background. Cria uma Tarefa e workspace/{hash}/ no mesmo padrão dos
    outros dois fluxos.
    """
    if not pdf and not (texto and texto.strip()) and not (consulta and consulta.strip()):
        raise HTTPException(400, "Envie um PDF, um texto ou uma consulta de pesquisa.")
    if pdf and pdf.filename and not _ok_pdf(pdf):
        raise HTTPException(400, "Envie um PDF.")

    h = ws.new_hash()
    folder = ws.folder(h)

    pdf_bytes: Optional[bytes] = None
    nome_pdf: Optional[str] = None
    if pdf and pdf.filename:
        pdf_bytes = await pdf.read()
        nome_pdf = pdf.filename
        (folder / "original.pdf").write_bytes(pdf_bytes)

    titulo = (nome_pdf or (consulta or "").strip()[:60]
              or (texto or "").strip()[:60] or "pesquisa de jurisprudência")[:200]

    t = Tarefa(
        hash=h,
        titulo=titulo,
        advogado_id=u.id,
        status="criada",
        pdf_nome=nome_pdf,
        workspace_path=str(folder),
        rodada=1,
    )
    session.add(t); session.commit(); session.refresh(t)

    ws.save_meta(h, {
        "hash": h,
        "titulo": t.titulo,
        "advogado": {"id": u.id, "email": u.email, "nome": u.nome},
        "pdf_nome": nome_pdf,
        "consulta": consulta,
        "criada_em": t.criada_em.isoformat(),
        "origem": "jurisprudencia_api_externa",
    })
    ws.record_event(h, "criada", tarefa_id=t.id, advogado_id=u.id)
    session.add(LogEvento(tarefa_id=t.id, tipo="criada", payload=f'{{"hash":"{h}"}}'))
    session.commit()

    token = u.session_token
    from core.api_caselaw import run_caselaw
    bg.add_task(run_caselaw, t.id, pdf_bytes, texto, consulta,
                nome_pdf or "documento.pdf", token)

    log.info("📁 [jurisprudência · API externa] Tarefa criada | id=%s hash=%s", t.id, h)
    return {"tarefa_id": t.id, "hash": h}


@router.get("/api/jurisprudencia/{hash_}/status")
async def api_jurisprudencia_status(
    hash_: str,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Eventos do acompanhamento do job na API externa (jurisprudencia_*)."""
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t or not _permite_ver(u, t):
        raise HTTPException(404)

    eventos = [
        e for e in ws.read_events(hash_)
        if str(e.get("tipo", "")).startswith("jurisprudencia")
    ]
    return {"status": t.status, "eventos": eventos}


@router.get("/api/jurisprudencia/{hash_}/resultado")
async def api_jurisprudencia_resultado(
    hash_: str,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Devolve o resultado já salvo no workspace (dados_llm + doc_text)."""
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t or not _permite_ver(u, t):
        raise HTTPException(404)

    return {
        "status": t.status,
        "titulo": t.titulo,
        "dados_llm": _read_json(hash_, "jurisprudencia_resultado.json"),
        "doc_text": _read_artifact(hash_, "jurisprudencia_texto.txt"),
    }


# ══════════════════════════════════════════════════════════════════════════
#  MEMÓRIA DE SESSÃO — anexo compartilhado (jurisprudência + resumo
#  estruturado + chat) que acompanha toda pergunta do usuário. Persiste
#  enquanto a sessão de login estiver aberta; some no logout. NUNCA inclui
#  nada do fluxo de PDF assinado (esse é isolado por completo).
# ══════════════════════════════════════════════════════════════════════════
@router.get("/api/sessao/memoria")
async def api_sessao_memoria(
    u: Usuario = Depends(current_user),
):
    """
    Devolve o estado atual da memória de sessão: quais abas já têm uma
    destilação processada (para o aviso no topo do chat) + o JSON completo
    das 3 partes (para inspeção/depuração no painel de Contexto).
    """
    token = u.session_token
    return {
        "processadas": sess.processed_tabs_summary(token),
        "anexo": sess.shared_attachment(token),
    }


@router.post("/api/sessao/memoria/limpar")
async def api_sessao_memoria_limpar(
    aba: Optional[str] = Form(default=None),
    u: Usuario = Depends(current_user),
):
    """
    Limpa a memória de sessão. Se `aba` vier informado
    (jurisprudencia|resumo_estruturado|chat), limpa só aquela aba;
    senão, limpa a sessão inteira (as 3 abas).
    """
    if aba is not None and aba not in sess.ABAS:
        raise HTTPException(400, f"aba inválida: {aba}")
    token = u.session_token
    sess.clear(token, aba)  # type: ignore[arg-type]
    return {"message": "✅ Memória de sessão limpa" + (f" (aba: {aba})" if aba else "")}


# ══════════════════════════════════════════════════════════════════════════
#  REPROCESSAR (reroda pipeline do zero, mesma rodada)
# ══════════════════════════════════════════════════════════════════════════
@router.post("/tarefas/{tarefa_id}/reprocess")
async def reprocess(
    tarefa_id: int,
    bg: BackgroundTasks,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    t = session.get(Tarefa, tarefa_id)
    if not t:
        raise HTTPException(404, "Tarefa não encontrada")
    if not _permite_ver(u, t):
        raise HTTPException(403, "Sem acesso")
    if t.status == "processando":
        raise HTTPException(409, "Já está processando")

    for nome in (
        "texto_extraido.txt", "memoria_persistente.json", "texto_tagueado.json",
        "resumo_humanizado.md", "questoes.json", "pdf_assinado.pdf",
    ):
        p = ws.folder(t.hash) / nome
        if p.exists():
            p.unlink()

    for p in ws.folder(t.hash).glob("T*.json"):
        p.unlink()

    t.status = "criada"
    t.atualizada_em = datetime.utcnow()
    session.add(t)
    session.add(LogEvento(tarefa_id=t.id, tipo="reprocess", payload=None))
    session.commit()

    ws.record_event(t.hash, "reprocess")

    from main import groq_client
    bg.add_task(run_pipeline, t.id, groq_client, "")   # LeIA: bounded by PIPELINE_CONCURRENCY

    log.info("🔄 Reprocessando tarefa %s (hash=%s)", t.id, t.hash)
    return RedirectResponse(f"/tarefas/{t.id}", status_code=303)


# ══════════════════════════════════════════════════════════════════════════
#  NOVA RODADA (clona a tarefa e gera novas questões)
# ══════════════════════════════════════════════════════════════════════════
@router.post("/tarefas/{tarefa_id}/nova-rodada")
async def nova_rodada(
    tarefa_id: int,
    bg: BackgroundTasks,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    t = session.get(Tarefa, tarefa_id)
    if not t:
        raise HTTPException(404)
    if not _permite_ver(u, t):
        raise HTTPException(403)

    rodada_anterior = t.rodada or 1
    nova_rodada_n = rodada_anterior + 1

    h = ws.new_hash()
    new_folder = ws.folder(h)
    pdf_orig = Path(t.workspace_path) / "original.pdf"
    if not pdf_orig.exists():
        raise HTTPException(500, "PDF original não encontrado")
    shutil.copy(pdf_orig, new_folder / "original.pdf")

    novo = Tarefa(
        hash=h,
        titulo=f"{t.titulo} · rodada {nova_rodada_n}",
        advogado_id=t.advogado_id,
        status="criada",
        pdf_nome=t.pdf_nome,
        workspace_path=str(new_folder),
        clone_de=t.id,
        rodada=nova_rodada_n,
    )
    session.add(novo); session.commit(); session.refresh(novo)

    ws.save_meta(h, {
        "hash": h,
        "titulo": novo.titulo,
        "clone_de": t.id,
        "clone_hash": t.hash,
        "rodada": nova_rodada_n,
        "criada_em": novo.criada_em.isoformat(),
    })
    ws.record_event(h, "clonada", origem=t.hash, rodada=nova_rodada_n)

    from main import groq_client
    variacao = (
        f"RODADA_{nova_rodada_n}_HASH_{h[:8]}_NONCE_{secrets.token_hex(4)} — "
        f"Gere 12 questões COMPLETAMENTE DIFERENTES das geradas na rodada anterior "
        f"(novos enunciados, novas alternativas, novas áreas priorizadas)."
    )
    bg.add_task(run_pipeline, novo.id, groq_client, variacao)   # LeIA: bounded by PIPELINE_CONCURRENCY

    log.info("🔁 Nova rodada | origem=%s novo=%s hash=%s", t.id, novo.id, h)
    return RedirectResponse(f"/tarefas/{novo.id}", status_code=303)


# ══════════════════════════════════════════════════════════════════════════
#  DOWNLOAD DE ARTEFATO (advogado/gerente)
# ══════════════════════════════════════════════════════════════════════════
@router.get("/tarefas/{tarefa_id}/artefato/{nome}")
async def baixar_artefato(
    tarefa_id: int,
    nome: str,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    t = session.get(Tarefa, tarefa_id)
    if not t:
        raise HTTPException(404)
    if not _permite_ver(u, t):
        raise HTTPException(403)

    permitidos = {
        "texto_extraido.txt", "memoria_persistente.json", "texto_tagueado.json",
        "resumo_humanizado.md", "questoes.json", "log.jsonl", "meta.json",
    }
    if nome not in permitidos and not nome.startswith("T"):
        raise HTTPException(400, "Nome não permitido")

    p = ws.folder(t.hash) / nome
    if not p.exists():
        raise HTTPException(404, "Artefato não existe")

    return FileResponse(p, filename=f"{t.hash}_{nome}")


# ══════════════════════════════════════════════════════════════════════════
#  API AUXILIAR: status da tarefa (auto-refresh seletivo)
# ══════════════════════════════════════════════════════════════════════════
@router.get("/api/tarefas/{tarefa_id}/status")
async def api_status(
    tarefa_id: int,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    t = session.get(Tarefa, tarefa_id)
    if not t or not _permite_ver(u, t):
        raise HTTPException(404)

    eventos = ws.read_events(t.hash)
    return {
        "status": t.status,
        "atualizada_em": t.atualizada_em.isoformat(),
        "eventos_recentes": eventos[-8:],
    }


# ══════════════════════════════════════════════════════════════════════════
#  API PÚBLICA DO CLIENTE — quiz
# ══════════════════════════════════════════════════════════════════════════
@router.post("/api/t/{hash_}/quiz", dependencies=[Depends(rate_limit)])   # LeIA: per-IP limit
async def api_quiz(
    hash_: str,
    payload: dict,
    request: Request,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
):
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t:
        raise HTTPException(404, "Link inválido")

    from leia.api_citizen import GATE_MESSAGE, is_gated   # LeIA: local import (leia.api_citizen imports this module)
    if is_gated(t):   # LeIA: lawyer review gate, the citizen only answers after the lawyer approves
        raise HTTPException(409, GATE_MESSAGE)

    questoes_doc = _read_json(t.hash, "questoes.json") or {}
    questoes = questoes_doc.get("questoes", [])
    if not questoes:
        raise HTTPException(409, "Questões não disponíveis")

    respostas = payload.get("respostas") or {}
    try:
        tent = tn.record(t, respostas, questoes)
    except tn.AttemptsExhausted:
        # Não é reprovação: a explicação continua aberta. O que não acontece mais é gerar
        # registro de compreensão por tentativa e erro.
        raise HTTPException(429, "Você já conferiu algumas vezes. Para não registrar algo que talvez "
                                 "ainda não esteja claro, fale com quem enviou o documento.")
    erros = tn.review_points(tent, questoes)
    erros = [{"id": e.get("id"), "area": e.get("area"), "enunciado": e.get("enunciado"), "escolhida": e.get("escolhida")} for e in erros]  # LeIA: no answer key to the browser

    if tent.aprovado:  # LeIA: public timestamp (OpenTimestamps) of the approved attempt, in background
        from leia.api_citizen import stamp_attempt
        background.add_task(stamp_attempt, t.hash, tent.numero, tent.hash_imutavel)

    ws.record_event(t.hash, "tentativa",
                        numero=tent.numero, acertos=tent.acertos,
                        total=tent.total, aprovado=tent.aprovado,
                        hash=tent.hash_imutavel)

    if tent.aprovado and t.status != "assinada":
        t.status = "assinada"
        t.atualizada_em = datetime.utcnow()
        session.add(t)
        session.add(LogEvento(tarefa_id=t.id, tipo="assinada",
                              payload=f'{{"tentativa":{tent.numero}}}'))
        session.commit()

    return {
        "numero": tent.numero,
        "acertos": tent.acertos,
        "total": tent.total,
        "aprovado": tent.aprovado,
        "hash_imutavel": tent.hash_imutavel,
        "ts": tent.criada_em.isoformat(),
        "erros": erros,
        "pode_baixar_pdf": tent.aprovado,
    }


# ══════════════════════════════════════════════════════════════════════════
#  API PÚBLICA DO CLIENTE — chat (streaming)
# ══════════════════════════════════════════════════════════════════════════
@router.post("/api/t/{hash_}/chat", dependencies=[Depends(rate_limit)])   # LeIA: per-IP limit
async def api_cliente_chat(
    hash_: str,
    payload: dict,
    session: Session = Depends(get_session),
):
    t = session.exec(select(Tarefa).where(Tarefa.hash == hash_)).first()
    if not t:
        raise HTTPException(404, "Link inválido")

    from leia.api_citizen import GATE_MESSAGE, is_gated   # LeIA: local import (leia.api_citizen imports this module)
    if is_gated(t):   # LeIA: lawyer review gate, no chat before the lawyer approves
        raise HTTPException(409, GATE_MESSAGE)

    pergunta = (payload.get("mensagem") or "").strip()
    if not pergunta:
        raise HTTPException(400, "Mensagem vazia")

    resumo = _read_artifact(t.hash, "resumo_humanizado.md") or ""
    memoria = _read_json(t.hash, "memoria_persistente.json") or {}
    memoria_str = json.dumps(memoria, ensure_ascii=False, indent=2)[:int(os.getenv("CITIZEN_CHAT_MEMORY_CHARS", "12000"))]

    system_prompt = (
        "Você é um ASSISTENTE JURÍDICO que ajuda um CLIENTE LEIGO a entender "
        "o processo dele. Use APENAS as informações do contexto abaixo. "
        "NUNCA invente fato, número, data ou dispositivo legal. "
        "Se a resposta não estiver no contexto, diga que não foi informado. "
        "Linguagem simples, direta, sem latim, sem juridiquês. "
        "Se o cliente pedir conselho jurídico (o que fazer), oriente-o a "
        "conversar com o advogado responsável.\n\n"
        f"=== RESUMO DO PROCESSO ===\n{resumo}\n\n"
        f"=== MEMÓRIA ESTRUTURADA ===\n{memoria_str}"
    )

    from main import groq_client as gc

    async def gerar():
        try:
            stream = await gc.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": pergunta},
                ],
                temperature=float(os.getenv("CITIZEN_CHAT_TEMPERATURE", "0.3")),
                max_completion_tokens=int(os.getenv("CITIZEN_CHAT_MAX_TOKENS", "1500")),
                stream=True,
            )
            async for ch in stream:
                delta = ch.choices[0].delta
                txt = getattr(delta, "content", None) or ""
                if txt:
                    payload_json = json.dumps({"t": txt}, ensure_ascii=False)
                    yield f"data: {payload_json}\n\n"
            yield "data: {\"done\": true}\n\n"
        except Exception as e:
            payload_json = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {payload_json}\n\n"

    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ══════════════════════════════════════════════════════════════════════════
#  PDF ASSINADO
# ══════════════════════════════════════════════════════════════════════════
def _dados_assinatura(t: Tarefa, melhor: Tentativa) -> dict:
    return {
        "titulo": t.titulo,
        "tarefa_hash": t.hash,
        "numero": melhor.numero,
        "acertos": melhor.acertos,
        "total": melhor.total,
        "ts": melhor.criada_em.isoformat(),
        "ip": melhor.ip,
        "user_agent": melhor.user_agent,
        "hash_imutavel": melhor.hash_imutavel,
    }


@router.get("/tarefas/{tarefa_id}/pdf-assinado")
async def admin_baixar_pdf_assinado(
    tarefa_id: int,
    u: Usuario = Depends(current_user),
    session: Session = Depends(get_session),
):
    t = session.get(Tarefa, tarefa_id)
    if not t:
        raise HTTPException(404)
    if not _permite_ver(u, t):
        raise HTTPException(403)

    melhor = tn.best(t.id)
    if not melhor or not melhor.aprovado:
        raise HTTPException(403, "Sem tentativa aprovada")

    pdf_orig = Path(t.workspace_path) / "original.pdf"
    if not pdf_orig.exists():
        raise HTTPException(404, "PDF original não encontrado")

    dados = _dados_assinatura(t, melhor)
    saida = Path(t.workspace_path) / "pdf_assinado.pdf"
    build_signed_pdf(pdf_orig, saida, dados)
    ws.record_event(t.hash, "pdf_assinado_admin",
                        tentativa=melhor.numero)
    return FileResponse(
        saida,
        filename=f"{t.hash}_assinado.pdf",
        media_type="application/pdf",
    )