"""Tests for the v3 API (accounts, documents of the signed-in user, doubts, linking, rate limit, lawyer review gate).

Run from apps/llm-service: python -m pytest -q tests_leia.py tests_v3.py
SQLite in a temporary DATA_DIR, no OpenTimestamps, no Groq key: the workflow fails fast and the task ends
in "falhou", which is enough to check creation, visibility and the public JSON.
"""
from __future__ import annotations

import os

import io
import json
import os
import tempfile
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="leia-v3-")
os.environ.update({
    "DATA_DIR": TMP,
    "OTS_ENABLED": "false",
    "GROQ_API_KEY": "",
    "API_KEY": "",
    "ADMIN_EMAIL": "admin@test.local",
    "ADMIN_PASSWORD": "admin-secret-1",
    "CLIENT_APP_URL": "http://app.test",
    "RATE_LIMIT_PER_MINUTE": "200",
    "PIPELINE_CONCURRENCY": "2",
    # A bateria não fala com terceiro: o padrão aponta para api.resumoestruturado.com.br e
    # api.jurisprudencia.com.br, então rodar os testes mandava um PDF para fora, inclusive na integração contínua.
    "RESUMO_ESTRUTURADO_API_BASE": "http://127.0.0.1:9",
    "JURISPRUDENCIA_API_BASE": "http://127.0.0.1:9",
})
os.environ.pop("DATABASE_URL", None)
os.environ.pop("DB_PATH", None)
os.environ.pop("WORKSPACE_DIR", None)
os.environ.pop("ADVOGADO_SIGNUP", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

import main  # noqa: E402
from core import workspace as ws  # noqa: E402
from core.db import LogEvento, Tarefa, engine  # noqa: E402
from leia.ratelimit import limiter  # noqa: E402


class _FailingCompletions:
    async def create(self, **kwargs):
        raise RuntimeError("sem chave da Groq neste teste")


class _FailingGroq:
    class chat:  # noqa: N801 (mirrors the SDK shape)
        completions = _FailingCompletions()


main.groq_client = _FailingGroq()  # the workflow must fail fast and offline

client = TestClient(main.app)


def small_pdf(text: str = "Contrato de honorarios. O cliente paga vinte por cento ao final.") -> bytes:
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buf.getvalue()


def signup(email: str, papel: str, nome: str = "Pessoa", oab: str | None = None) -> dict:
    r = client.post("/api/auth/cadastro", json={"nome": nome, "email": email, "senha": "senha-123",
                                                "papel": papel, "oab": oab})
    assert r.status_code == 200, r.text
    return r.json()


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create_task(token: str, titulo: str = "Contrato") -> dict:
    r = client.post("/api/tarefas", data={"titulo": titulo},
                    files={"pdf": ("contrato.pdf", small_pdf(), "application/pdf")}, headers=bearer(token))
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def lawyer() -> dict:
    return signup("Advogada@Teste.local", "advogado", "Dra. Ana", oab="PR 12.345")


@pytest.fixture(scope="module")
def citizen() -> dict:
    return signup("cidada@teste.local", "cidadao", "Maria")


@pytest.fixture(scope="module")
def admin() -> dict:
    r = client.post("/api/auth/login", json={"email": "admin@test.local", "senha": "admin-secret-1"})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def lawyer_task(lawyer) -> dict:
    return create_task(lawyer["token"])


# ── accounts ──────────────────────────────────────────────────────────────

def test_signup_login_me_logout(lawyer):
    assert lawyer["usuario"]["email"] == "advogada@teste.local" and lawyer["usuario"]["papel"] == "advogado"
    assert lawyer["token"]

    dup = client.post("/api/auth/cadastro", json={"nome": "X", "email": "ADVOGADA@teste.local", "senha": "senha-123", "papel": "advogado"})
    assert dup.status_code == 409
    admin = client.post("/api/auth/cadastro", json={"nome": "X", "email": "x@teste.local", "senha": "senha-123", "papel": "fornecedor"})
    assert admin.status_code == 403

    bad = client.post("/api/auth/login", json={"email": "advogada@teste.local", "senha": "errada-123"})
    assert bad.status_code == 401

    first_token = lawyer["token"]
    ok = client.post("/api/auth/login", json={"email": "Advogada@teste.local", "senha": "senha-123"})
    assert ok.status_code == 200
    new_token = ok.json()["token"]
    assert new_token != first_token
    assert client.get("/api/auth/me", headers=bearer(first_token)).status_code == 401  # rotated
    me = client.get("/api/auth/me", headers=bearer(new_token))
    assert me.status_code == 200 and me.json()["usuario"]["nome"] == "Dra. Ana"

    assert client.post("/api/auth/logout", headers=bearer(new_token)).json() == {"ok": True}
    assert client.get("/api/auth/me", headers=bearer(new_token)).status_code == 401

    again = client.post("/api/auth/login", json={"email": "advogada@teste.local", "senha": "senha-123"})
    lawyer["token"] = again.json()["token"]  # keep the module fixture usable


def test_oab_survives_the_signup():
    """The number typed at signup is what the citizen sees to check who sent her the document.

    Until now the field existed on the form, travelled in the request and was dropped on arrival, which is
    worse than not asking: it promises a check that nothing can perform."""
    r = client.post("/api/auth/cadastro", json={"nome": "Dr. Ruy", "email": "ruy@teste.local",
                                                "senha": "senha-123", "papel": "advogado", "oab": " PR 12.345 "})
    assert r.status_code == 200, r.text
    assert r.json()["usuario"]["oab"] == "PR 12.345"
    token = r.json()["token"]
    assert client.get("/api/auth/me", headers=bearer(token)).json()["usuario"]["oab"] == "PR 12.345"

    # A citizen has no OAB, and the key must still be there: the screen reads it without asking whose it is.
    c = client.post("/api/auth/cadastro", json={"nome": "Joana", "email": "joana-oab@teste.local",
                                                "senha": "senha-123", "papel": "cidadao", "oab": "PR 999"})
    assert c.json()["usuario"]["oab"] is None


def test_lawyer_signup_can_be_closed():
    os.environ["ADVOGADO_SIGNUP"] = "false"
    try:
        r = client.post("/api/auth/cadastro", json={"nome": "X", "email": "fechado@teste.local", "senha": "senha-123", "papel": "advogado"})
        assert r.status_code == 403
        r = client.post("/api/auth/cadastro", json={"nome": "X", "email": "aberto@teste.local", "senha": "senha-123", "papel": "cidadao"})
        assert r.status_code == 200
    finally:
        os.environ.pop("ADVOGADO_SIGNUP", None)


def test_bearer_and_cookie_rules(lawyer):
    fresh = TestClient(main.app)  # no cookies from other tests
    assert fresh.get("/api/tarefas").status_code == 401
    assert fresh.get("/api/tarefas", headers=bearer("nao-existe")).status_code == 401
    r = fresh.get("/api/tarefas", headers=bearer("nao-existe"))
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/json")
    assert fresh.get("/api/tarefas", headers=bearer(lawyer["token"])).status_code == 200
    fresh.close()


# ── documents ─────────────────────────────────────────────────────────────

def test_create_task_and_read_it(lawyer, lawyer_task):
    assert lawyer_task["status"] == "criada" and len(lawyer_task["hash"]) >= 20
    r = client.get(f"/api/tarefas/{lawyer_task['id']}", headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tarefa"]["status"] in ("criada", "processando", "falhou")
    assert data["tarefa"]["origem"] == "advogado"
    assert data["link_cliente"] == f"http://app.test/t/{lawyer_task['hash']}"
    assert data["resumo_md"] is None and data["tentativas"] == [] and data["duvidas"] == []
    assert data["advogado"] == {"nome": "Dra. Ana"} and data["cidadao"] is None
    assert any(e["tipo"] == "pdf_salvo" for e in data["eventos"])
    # O `original.pdf` existe entre o envio e a extração, e some ali (E17-T06). Esta tarefa é criada sem
    # chave da Groq, então a rodada falha logo depois de extrair, e o arquivo já saiu.
    assert not (ws.folder(lawyer_task["hash"]) / "original.pdf").exists(), "o PDF continua guardado"
    assert (ws.folder(lawyer_task["hash"]) / "texto_extraido.txt").exists(), "o texto do documento sumiu junto"

    lst = client.get("/api/tarefas", headers=bearer(lawyer["token"])).json()["tarefas"]
    mine = [t for t in lst if t["id"] == lawyer_task["id"]]
    assert mine and mine[0]["duvidas_abertas"] == 0 and mine[0]["ultima_tentativa"] is None
    assert mine[0]["link_cliente"].startswith("http://app.test/t/")


def test_rejects_non_pdf(lawyer):
    r = client.post("/api/tarefas", data={"titulo": "x"}, files={"pdf": ("nota.txt", b"ola", "text/plain")},
                    headers=bearer(lawyer["token"]))
    assert r.status_code == 400


def test_visibility(lawyer, lawyer_task, citizen):
    other = signup("outro@teste.local", "advogado", "Dr. Outro")
    r = client.get(f"/api/tarefas/{lawyer_task['id']}", headers=bearer(other["token"]))
    assert r.status_code == 403
    assert client.get("/api/tarefas/999999", headers=bearer(other["token"])).status_code == 404
    assert client.get(f"/api/tarefas/{lawyer_task['id']}", headers=bearer(citizen["token"])).status_code == 403
    assert all(t["id"] != lawyer_task["id"] for t in client.get("/api/tarefas", headers=bearer(other["token"])).json()["tarefas"])

    admin = client.post("/api/auth/login", json={"email": "admin@test.local", "senha": "admin-secret-1"}).json()
    assert admin["usuario"]["papel"] == "fornecedor"
    assert client.get(f"/api/tarefas/{lawyer_task['id']}", headers=bearer(admin["token"])).status_code == 200
    ids = {t["id"] for t in client.get("/api/tarefas", headers=bearer(admin["token"])).json()["tarefas"]}
    assert lawyer_task["id"] in ids


# ── citizen routes ────────────────────────────────────────────────────────

def test_public_json_and_doubt_flow(lawyer, lawyer_task, citizen):
    # document sent by a citizen alone: no lawyer to receive doubts
    own = create_task(citizen["token"], "Meu contrato")
    pub = client.get(f"/api/t/{own['hash']}").json()
    assert pub["tem_advogado"] is False and pub["advogado"] is None and pub["cidadao_vinculado"] is True
    assert client.post(f"/api/t/{own['hash']}/duvida", json={"texto": "E agora?"}).status_code == 409
    detail = client.get(f"/api/tarefas/{own['id']}", headers=bearer(citizen["token"])).json()
    assert detail["tarefa"]["origem"] == "cidadao" and detail["cidadao"] == {"nome": "Maria"} and detail["advogado"] is None

    # document sent by a lawyer: doubt lands on the lawyer's task
    h = lawyer_task["hash"]
    pub = client.get(f"/api/t/{h}").json()
    assert pub["tem_advogado"] is True and pub["advogado"] == {"nome": "Dra. Ana", "oab": "PR 12.345"} and pub["duvidas_enviadas"] == 0
    assert client.post(f"/api/t/{h}/duvida", json={"texto": "   "}).status_code == 400
    r = client.post(f"/api/t/{h}/duvida", json={"texto": "Quanto pago se perder?",
                                                 "contexto": [{"role": "user", "text": "oi"}, {"role": "bot", "text": "ola"}]})
    assert r.status_code == 200, r.text
    doubt = r.json()
    assert doubt["id"] and doubt["criada_em"]
    assert client.get(f"/api/t/{h}").json()["duvidas_enviadas"] == 1
    assert any(e["tipo"] == "duvida_enviada" for e in ws.read_events(h))
    assert client.get("/api/t/nao-existe").status_code == 404

    detail = client.get(f"/api/tarefas/{lawyer_task['id']}", headers=bearer(lawyer["token"])).json()
    assert len(detail["duvidas"]) == 1 and detail["duvidas"][0]["respondida"] is False
    assert detail["duvidas"][0]["contexto"] == [{"role": "user", "text": "oi"}, {"role": "bot", "text": "ola"}]
    lst = client.get("/api/tarefas", headers=bearer(lawyer["token"])).json()["tarefas"]
    assert [t for t in lst if t["id"] == lawyer_task["id"]][0]["duvidas_abertas"] == 1

    # o texto da dúvida chega ao advogado pela API de detalhe, que é o que o app consome
    assert detail["duvidas"][0]["texto"] == "Quanto pago se perder?"

    # only the owner or the admin answers
    url = f"/api/tarefas/{lawyer_task['id']}/duvidas/{doubt['id']}/responder"
    assert client.post(url, json={"resposta": "x"}, headers=bearer(citizen["token"])).status_code == 403
    assert client.post(url, json={"resposta": "Nada: o contrato só cobra se ganhar."}, headers=bearer(lawyer["token"])).json() == {"ok": True}
    detail = client.get(f"/api/tarefas/{lawyer_task['id']}", headers=bearer(lawyer["token"])).json()
    d = detail["duvidas"][0]
    assert d["respondida"] is True and d["resposta"].startswith("Nada") and d["respondida_em"]
    assert client.post(f"/api/tarefas/{lawyer_task['id']}/duvidas/999999/responder", json={"resposta": "x"},
                       headers=bearer(lawyer["token"])).status_code == 404


def test_link_citizen(lawyer, lawyer_task, citizen):
    h = lawyer_task["hash"]
    assert client.post(f"/api/t/{h}/vincular").status_code == 401
    assert client.post(f"/api/t/{h}/vincular", headers=bearer(lawyer["token"])).status_code == 403
    # vincular é virar dona do documento, então exige convite vivo; ler segue aberto sem ele
    assert client.post(f"/api/t/{h}/vincular", headers=bearer(citizen["token"])).status_code == 403
    client.post(f"/api/tarefas/{lawyer_task['id']}/convite", json={"nome": "Destinatária", "email": None}, headers=bearer(lawyer["token"]))
    assert client.post(f"/api/t/{h}/vincular", headers=bearer(citizen["token"])).json() == {"ok": True}
    assert client.post(f"/api/t/{h}/vincular", headers=bearer(citizen["token"])).json() == {"ok": True}  # idempotent
    assert client.get(f"/api/t/{h}").json()["cidadao_vinculado"] is True

    detail = client.get(f"/api/tarefas/{lawyer_task['id']}", headers=bearer(citizen["token"]))
    assert detail.status_code == 200 and detail.json()["cidadao"] == {"nome": "Maria"}
    ids = {t["id"] for t in client.get("/api/tarefas", headers=bearer(citizen["token"])).json()["tarefas"]}
    assert lawyer_task["id"] in ids
    lst = client.get("/api/tarefas", headers=bearer(lawyer["token"])).json()["tarefas"]
    assert [t for t in lst if t["id"] == lawyer_task["id"]][0]["cidadao"] == {"nome": "Maria"}

    other = signup("outra@teste.local", "cidadao", "Joana")
    assert client.post(f"/api/t/{h}/vincular", headers=bearer(other["token"])).status_code == 409
    assert client.post(f"/api/t/{h}/vincular", headers=bearer(citizen["token"])).status_code == 200


FAKE_TEXT = "CLÁUSULA 2. O CONTRATANTE pagará honorários de vinte por cento ao final, só se ganhar a ação."


def fake_artifacts(h: str) -> None:
    """Workspace artifacts of a finished workflow, without the model."""
    folder = ws.folder(h)
    (folder / "resumo_humanizado.md").write_text("# Resumo em uma linha\nVocê paga só se ganhar.\n\n## O que aconteceu\nUm contrato.", encoding="utf-8")
    (folder / "questoes.json").write_text(json.dumps({"questoes": [
        {"id": 1, "area": "pedidos", "enunciado": "Quando você paga?", "alternativas": ["Sempre", "Só se ganhar", "Nunca", "Antes"],
         "correta": 1, "justificativa": "Está na cláusula 2.", "dificuldade": "facil"}]}), encoding="utf-8")
    (folder / "texto_extraido.txt").write_text(FAKE_TEXT, encoding="utf-8")
    (folder / "memoria_persistente.json").write_text(json.dumps({"memoria_persistente": {"datas_valores": [
        {"campo": "honorarios", "valor": "20%", "trecho_verbatim": "honorários de vinte por cento ao final"}]}}), encoding="utf-8")
    (folder / "T9_SINTESE_PEDIDOS.json").write_text(json.dumps({"sintese_pedidos": {"valor": "Paga 20% se ganhar.", "lastro": ["datas_valores[0]"]}}), encoding="utf-8")


def set_status(h: str, status: str) -> None:
    with Session(engine) as s:
        t = s.exec(select(Tarefa).where(Tarefa.hash == h)).one()
        t.status = status
        s.add(t); s.commit()


def test_public_json_never_leaks_the_answer_key(lawyer, lawyer_task):
    h = lawyer_task["hash"]
    fake_artifacts(h)
    set_status(h, "pronta")
    # a lawyer's task in "pronta" is still under review: nothing of the explanation leaves the service
    r = client.get(f"/api/t/{h}")
    assert r.status_code == 200 and r.json()["tarefa"]["status"] == "revisao"
    assert r.json()["questoes"] == [] and r.json()["resumo_md"] is None and r.json()["topicos"] is None
    assert client.post(f"/api/tarefas/{lawyer_task['id']}/aprovar", headers=bearer(lawyer["token"])).json() == {"ok": True, "status": "enviada"}
    r = client.get(f"/api/t/{h}")
    assert r.status_code == 200
    assert "correta" not in r.text and "justificativa" not in r.text
    data = r.json()
    assert data["tarefa"]["status"] == "enviada"
    assert data["questoes"][0]["enunciado"] == "Quando você paga?" and data["resumo_md"].startswith("# Resumo")
    assert data["tem_advogado"] is True


# ── lawyer review before releasing the link ───────────────────────────────

def test_review_requires_owner_and_finished_workflow(lawyer, citizen):
    task = create_task(lawyer["token"], "Para revisar")
    h, tid = task["hash"], task["id"]
    fake_artifacts(h)
    set_status(h, "processando")
    assert client.get(f"/api/tarefas/{tid}/revisao", headers=bearer(lawyer["token"])).status_code == 409
    assert client.post(f"/api/tarefas/{tid}/aprovar", headers=bearer(lawyer["token"])).status_code == 409

    set_status(h, "pronta")
    other = signup("revisor@teste.local", "advogado", "Dr. Revisor")
    assert client.get(f"/api/tarefas/{tid}/revisao", headers=bearer(other["token"])).status_code == 403
    assert client.post(f"/api/tarefas/{tid}/aprovar", headers=bearer(other["token"])).status_code == 403
    assert client.get(f"/api/tarefas/{tid}/revisao", headers=bearer(citizen["token"])).status_code == 403
    assert client.get("/api/tarefas/999999/revisao", headers=bearer(lawyer["token"])).status_code == 404
    assert client.get(f"/api/tarefas/{tid}/revisao").status_code == 401

    r = client.get(f"/api/tarefas/{tid}/revisao", headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tarefa"] == {"id": tid, "hash": h, "titulo": "Para revisar", "status": "pronta", "origem": "advogado"}
    assert data["link_cliente"] == f"http://app.test/t/{h}"
    assert data["resumo_md"].startswith("# Resumo")
    q = data["questoes"][0]
    assert q["correta"] == 1 and q["justificativa"] == "Está na cláusula 2." and q["dificuldade"] == "facil"
    inf = data["inferencias"]
    assert inf["tarefa"]["hash"] == h and inf["texto"] == FAKE_TEXT and inf["total"] == 1 and inf["conferidos"] == 1
    assert inf["classes"][0]["itens"][0]["pos"] and inf["sinteses"][0]["lastro"] == ["datas_valores[0]"]
    # the same body the public route returns once released
    set_status(h, "enviada")
    assert client.get(f"/api/t/{h}/inferencias").json() == inf
    set_status(h, "pronta")

    # the admin reviews and approves too; review keeps working after approval (status enviada)
    admin = client.post("/api/auth/login", json={"email": "admin@test.local", "senha": "admin-secret-1"}).json()
    assert client.get(f"/api/tarefas/{tid}/revisao", headers=bearer(admin["token"])).status_code == 200
    assert client.post(f"/api/tarefas/{tid}/aprovar", headers=bearer(admin["token"])).json() == {"ok": True, "status": "enviada"}
    assert client.post(f"/api/tarefas/{tid}/aprovar", headers=bearer(admin["token"])).status_code == 409
    assert client.get(f"/api/tarefas/{tid}/revisao", headers=bearer(lawyer["token"])).json()["tarefa"]["status"] == "enviada"


def test_gate_holds_lawyer_task_until_approval(lawyer):
    task = create_task(lawyer["token"], "Com gate")
    h, tid = task["hash"], task["id"]
    fake_artifacts(h)
    set_status(h, "pronta")

    pub = client.get(f"/api/t/{h}").json()
    assert pub["tarefa"]["status"] == "revisao" and pub["tem_advogado"] is True and pub["advogado"] == {"nome": "Dra. Ana", "oab": "PR 12.345"}
    assert pub["resumo_md"] is None and pub["topicos"] is None and pub["questoes"] == [] and pub["ultima_tentativa"] is None
    for r in (client.get(f"/api/t/{h}/inferencias"),
              client.post(f"/api/t/{h}/quiz", json={"respostas": {"1": 1}}),
              client.post(f"/api/t/{h}/chat", json={"mensagem": "Quanto pago?"})):
        assert r.status_code == 409 and r.json()["detail"] == "Em revisão pelo advogado"
    # the panel still sees the summary while the citizen waits
    detail = client.get(f"/api/tarefas/{tid}", headers=bearer(lawyer["token"])).json()
    assert detail["tarefa"]["status"] == "pronta" and detail["resumo_md"].startswith("# Resumo")

    r = client.post(f"/api/tarefas/{tid}/aprovar", headers=bearer(lawyer["token"]))
    assert r.status_code == 200 and r.json() == {"ok": True, "status": "enviada"}
    assert client.post(f"/api/tarefas/{tid}/aprovar", headers=bearer(lawyer["token"])).status_code == 409
    assert any(e["tipo"] == "aprovada" and e.get("usuario_id") == lawyer["usuario"]["id"] for e in ws.read_events(h))
    with Session(engine) as s:
        assert s.get(Tarefa, tid).status == "enviada"
        assert s.exec(select(LogEvento).where(LogEvento.tarefa_id == tid, LogEvento.tipo == "aprovada")).first()

    pub = client.get(f"/api/t/{h}").json()
    assert pub["tarefa"]["status"] == "enviada" and pub["resumo_md"].startswith("# Resumo") and pub["questoes"][0]["id"] == 1
    assert "correta" not in json.dumps(pub)
    assert any(e["tipo"] == "aprovada" and "usuario_id" not in e for e in pub["eventos"])
    assert client.get(f"/api/t/{h}/inferencias").status_code == 200
    quiz = client.post(f"/api/t/{h}/quiz", json={"respostas": {"1": 1}})
    assert quiz.status_code == 200 and quiz.json()["aprovado"] is True
    assert client.get(f"/api/t/{h}").json()["tarefa"]["status"] == "assinada"  # signed tasks stay released


def test_citizen_task_is_released_without_approval(citizen):
    task = create_task(citizen["token"], "Sozinha")
    h = task["hash"]
    fake_artifacts(h)
    set_status(h, "pronta")
    pub = client.get(f"/api/t/{h}").json()
    assert pub["tarefa"]["status"] == "pronta" and pub["tem_advogado"] is False
    assert pub["resumo_md"].startswith("# Resumo") and pub["questoes"][0]["enunciado"] == "Quando você paga?"
    assert client.get(f"/api/t/{h}/inferencias").status_code == 200
    quiz = client.post(f"/api/t/{h}/quiz", json={"respostas": {"1": 0}})
    assert quiz.status_code == 200 and quiz.json()["aprovado"] is False
    r = client.get(f"/api/tarefas/{task['id']}/revisao", headers=bearer(citizen["token"]))
    assert r.status_code == 200 and r.json()["tarefa"]["origem"] == "cidadao"


# ── scale and isolation ───────────────────────────────────────────────────

def test_rate_limit_per_ip():
    os.environ["RATE_LIMIT_PER_MINUTE"] = "3"
    limiter.reset()
    try:
        ip = {"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
        codes = [client.post("/api/auth/login", json={"email": "ninguem@teste.local", "senha": "x"}, headers=ip).status_code
                 for _ in range(4)]
        assert codes == [401, 401, 401, 429]
        blocked = client.post("/api/auth/login", json={"email": "ninguem@teste.local", "senha": "x"}, headers=ip)
        assert "Aguarde" in blocked.json()["detail"] and blocked.headers.get("retry-after")
        # another address is not affected
        r = client.post("/api/auth/login", json={"email": "ninguem@teste.local", "senha": "x"}, headers={"X-Forwarded-For": "198.51.100.7"})
        assert r.status_code == 401
    finally:
        os.environ["RATE_LIMIT_PER_MINUTE"] = "200"
        limiter.reset()


def test_failed_workflow_only_touches_its_own_task(lawyer):
    a = create_task(lawyer["token"], "A")
    b = create_task(lawyer["token"], "B")
    with Session(engine) as s:
        ta, tb = s.get(Tarefa, a["id"]), s.get(Tarefa, b["id"])
        assert ta.status == "falhou" and tb.status == "falhou"  # no key: each one fails on its own
        assert ta.workspace_path != tb.workspace_path
    assert any(e["tipo"] in ("task_error", "erro_pipeline") for e in ws.read_events(a["hash"]))


def test_inferences_are_verified_by_substring(tmp_path=None):
    """LeIA: inferences endpoint finds quotes with whitespace differences and reports unverified ones."""
    from leia.api_citizen import build_inferences
    texto = "CLÁUSULA 2. O CONTRATANTE pagará honorários iniciais de\nR$ 1.500,00 em três parcelas."
    memoria = {"memoria_persistente": {"datas_valores": [
        {"campo": "valor_contrato", "valor": "R$ 1.500,00", "trecho_verbatim": "honorários iniciais de R$ 1.500,00"},
        {"campo": "prazo", "valor": "x", "trecho_verbatim": "texto que não existe no documento"}]}}
    r = build_inferences(texto, memoria, None, [("fatos", {"sintese_fatos": {"valor": "Paga em três parcelas.", "lastro": ["datas_valores[0]"]}})])
    itens = r["classes"][0]["itens"]
    assert itens[0]["conferido"] and texto[itens[0]["pos"][0]:itens[0]["pos"][1]].startswith("honorários iniciais de")
    assert not itens[1]["conferido"] and itens[1]["pos"] is None
    assert r["total"] == 2 and r["conferidos"] == 1 and r["sinteses"][0]["lastro"] == ["datas_valores[0]"]


def test_shuffle_keeps_answer_and_public_events_have_no_ip():
    """LeIA: alternatives shuffled per task with the right index remapped; public events carry no ip/ua."""
    from core.pipeline_pdf import _embaralhar_alternativas
    from leia.api_citizen import public_events
    doc = {"questoes": [{"id": i, "alternativas": ["certa", "b", "c", "d"], "correta": 0} for i in range(1, 7)]}
    out = _embaralhar_alternativas(doc, "abc")
    assert all(q["alternativas"][q["correta"]] == "certa" for q in out["questoes"])
    assert any(q["correta"] != 0 for q in out["questoes"])
    same = _embaralhar_alternativas({"questoes": [{"id": i, "alternativas": ["certa", "b", "c", "d"], "correta": 0} for i in range(1, 7)]}, "abc")
    assert [q["correta"] for q in same["questoes"]] == [q["correta"] for q in out["questoes"]]
    ev = public_events([{"tipo": "cliente_abriu", "ip": "1.2.3.4", "ua": "x"}, {"tipo": "task_done", "id": "T1", "ip": "9.9.9.9"}])
    assert ev == [{"tipo": "task_done", "id": "T1"}]


# ── visible preparation and tasks of the external flow ────────────────────

def staged_log(h: str, events: list[dict]) -> None:
    """Replace the workspace log with the given events (ip/ua included on purpose)."""
    (ws.folder(h) / "log.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")


def test_steps_from_log_and_files(lawyer):
    """LeIA: etapas come from log.jsonl (T1 done, T2 running, others pending) and from the T*.json files."""
    from leia.api_citizen import STEP_NAMES, build_steps

    # Contra o protocolo, não contra um número: a tela de espera existe para mostrar as etapas que rodam, e
    # um número cravado aqui deixa etapa nova invisível para quem espera em vez de acusar a diferença.
    do_protocolo = [t["id"] for t in running_protocol()["tasks"] if t.get("missao")]
    assert list(STEP_NAMES) == do_protocolo, "a lista de etapas da tela não é a do protocolo que roda"
    task = create_task(lawyer["token"], "Em preparo")
    h = task["hash"]
    staged_log(h, [{"ts": "t", "tipo": "pipeline_start", "tarefa_id": task["id"], "ip": "1.2.3.4"},
                   {"ts": "t", "tipo": "task_start", "id": "T1_IDENTIFICADOR_PARTES", "idx": 1, "total": 16},
                   {"ts": "t", "tipo": "task_done", "id": "T1_IDENTIFICADOR_PARTES", "tempo": 4.2},
                   {"ts": "t", "tipo": "task_start", "id": "T2_IDENTIFICADOR_DATAS_VALORES", "idx": 2, "total": 16}])
    set_status(h, "processando")
    data = client.get(f"/api/t/{h}").json()
    assert data["tarefa"]["status"] == "processando" and data["resumo_md"] is None
    etapas = data["etapas"]
    assert [e["id"] for e in etapas] == list(STEP_NAMES) and etapas[1]["nome"] == "Identificar as partes"
    assert etapas[1] == {"id": "T1_IDENTIFICADOR_PARTES", "nome": "Identificar as partes", "estado": "concluida", "tempo": 4.2}
    assert etapas[2]["estado"] == "em_andamento" and etapas[2]["tempo"] is None
    assert all(e["estado"] == "pendente" for e in etapas[3:]) and etapas[-1]["nome"] == "Preparar as perguntas"
    assert all("ip" not in e and "ua" not in e for e in data["eventos"]) and data["eventos"][0]["tipo"] == "pipeline_start"

    # a file the log knows nothing about counts as done; an error in the log wins over a stale file
    (ws.folder(h) / "T3_IDENTIFICADOR_FATOS.json").write_text(json.dumps({"fatos": []}), encoding="utf-8")
    (ws.folder(h) / "T4_IDENTIFICADOR_FUNDAMENTOS.json").write_text(json.dumps({"fundamentos": []}), encoding="utf-8")
    ws.record_event(h, "task_start", id="T4_IDENTIFICADOR_FUNDAMENTOS", idx=4, total=16)
    ws.record_event(h, "task_error", id="T4_IDENTIFICADOR_FUNDAMENTOS", erro="x")
    states = {e["id"]: e["estado"] for e in build_steps(ws.read_events(h), ws.folder(h))}
    assert states["T3_IDENTIFICADOR_FATOS"] == "concluida" and states["T4_IDENTIFICADOR_FUNDAMENTOS"] == "erro"
    assert states["T5_IDENTIFICADOR_PEDIDOS"] == "pendente"
    # every status carries etapas (a fresh task: 14 pending steps; nothing from an external flow: none)
    assert build_steps([], None) and all(s["estado"] == "pendente" for s in build_steps([], None))


def test_public_events_drop_ip_and_keep_the_last_60(lawyer):
    task = create_task(lawyer["token"], "Muitos eventos")
    h = task["hash"]
    staged_log(h, [{"ts": "t", "tipo": "criada", "advogado_id": 1, "ip": "9.9.9.9", "ua": "x"}]
               + [{"ts": "t", "tipo": "task_done", "id": "T1_IDENTIFICADOR_PARTES", "tempo": n, "ip": "9.9.9.9", "ua": "x"} for n in range(70)]
               + [{"ts": "t", "tipo": "cliente_abriu", "ip": "9.9.9.9"}])
    ev = client.get(f"/api/t/{h}").json()["eventos"]
    assert len(ev) == 60 and ev[-1]["tempo"] == 69 and ev[0]["tempo"] == 10
    assert all(set(e) == {"ts", "tipo", "id", "tempo"} for e in ev)
    assert "9.9.9.9" not in json.dumps(ev)


def test_partial_inferences_while_processing(lawyer):
    """LeIA: during processando the inferences answer 200 with parcial true and the classes produced so far."""
    task = create_task(lawyer["token"], "Parcial")
    h = task["hash"]
    folder = ws.folder(h)
    folder.joinpath("texto_extraido.txt").unlink(missing_ok=True)  # the offline workflow already extracted it
    set_status(h, "criada")
    r = client.get(f"/api/t/{h}/inferencias")
    assert r.status_code == 200 and r.json()["parcial"] is True and r.json()["texto"] == "" and r.json()["classes"] == []
    folder.joinpath("texto_extraido.txt").write_text(FAKE_TEXT, encoding="utf-8")
    folder.joinpath("T1_IDENTIFICADOR_PARTES.json").write_text(json.dumps({"identificacao": [
        {"campo": "contratante", "valor": "O CONTRATANTE", "trecho_verbatim": "O CONTRATANTE pagará", "pos_trecho_verbatim": "0:0"}]}), encoding="utf-8")
    folder.joinpath("T3_IDENTIFICADOR_FATOS.json").write_text(json.dumps({"fatos": [
        {"campo": "condicao", "valor": "só se ganhar", "trecho_verbatim": "só se ganhar a ação", "pos_trecho_verbatim": "0:0"},
        {"campo": "outro", "valor": "x", "trecho_verbatim": "frase que não está no documento", "pos_trecho_verbatim": "0:0"}]}), encoding="utf-8")
    set_status(h, "processando")
    r = client.get(f"/api/t/{h}/inferencias")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["parcial"] is True and data["texto"] == FAKE_TEXT and data["sinteses"] == []
    assert [c["classe"] for c in data["classes"]] == ["identificacao", "fatos"]
    assert data["total"] == 3 and data["conferidos"] == 2
    item = data["classes"][0]["itens"][0]
    assert item["conferido"] and FAKE_TEXT[item["pos"][0]:item["pos"][1]] == "O CONTRATANTE pagará" and "score" not in item
    assert data["classes"][1]["itens"][1]["pos"] is None
    # finished tasks keep the full body and say so
    fake_artifacts(h)
    set_status(h, "enviada")
    full = client.get(f"/api/t/{h}/inferencias").json()
    assert full["parcial"] is False and full["classes"][0]["classe"] == "datas_valores" and full["sinteses"]
    set_status(h, "falhou")
    assert client.get(f"/api/t/{h}/inferencias").status_code == 409


def test_the_model_position_is_not_read_at_all():
    """Não basta preferir a busca do servidor: enquanto existir código que lê a posição escrita pelo modelo,
    alguém vai religá-lo achando que é um atalho inofensivo."""
    import leia.api_citizen as ac

    assert not hasattr(ac, "parse_pos"), "ainda existe leitor da posição escrita pelo modelo"
    assert "pos_trecho_verbatim" not in Path(ac.__file__).read_text(encoding="utf-8"), \
        "o campo de posição do modelo ainda é lido em algum lugar"


def test_value_text():
    from leia.api_citizen import value_text
    assert value_text('{"tipo": "lei", "norma": "CPC", "artigo": null}') == "lei, CPC"
    assert value_text({"a": {"b": "X"}, "c": ["Y", "X"]}) == "X, Y" and value_text("plain") == "plain" and value_text(None) == ""
    assert value_text("{não é json}") == "{não é json}"


# ── Remoção da casca legada do serviço ────────────────────────────────────────
# A jornada da cidadã vive no app Next e o painel interno herdado não faz parte do
# produto público. Estes testes falham enquanto as rotas HTML legadas existirem.

LEGACY_HTML_ROUTES = ["/", "/login", "/dashboard", "/tarefas/nova"]


def test_legacy_panel_routes_are_gone(lawyer):
    fresh = TestClient(main.app)
    for path in LEGACY_HTML_ROUTES:
        anon = fresh.get(path, follow_redirects=False)
        assert anon.status_code == 404, f"{path} anônimo devolveu {anon.status_code}"
        auth = fresh.get(path, headers=bearer(lawyer["token"]), follow_redirects=False)
        assert auth.status_code == 404, f"{path} autenticado devolveu {auth.status_code}"
    fresh.close()


def test_legacy_citizen_html_page_is_gone(lawyer_task):
    fresh = TestClient(main.app)
    r = fresh.get(f"/t/{lawyer_task['hash']}", follow_redirects=False)
    assert r.status_code == 404, f"a página HTML da cidadã ainda responde: {r.status_code}"
    assert "data-correta" not in r.text
    fresh.close()


def test_legacy_unauthenticated_pdf_route_is_gone(lawyer_task):
    fresh = TestClient(main.app)
    r = fresh.get(f"/t/{lawyer_task['hash']}/pdf-assinado", follow_redirects=False)
    assert r.status_code == 404, f"o PDF sem credencial ainda responde: {r.status_code}"
    fresh.close()


def test_no_legacy_template_survives_in_the_repo():
    import pathlib
    legados = ["index.html", "dashboard.html", "login.html", "cliente_view.html",
               "cliente_aguarde.html", "tarefa_detalhe.html", "tarefa_nova.html"]
    base = pathlib.Path(__file__).parent / "templates"
    presentes = [n for n in legados if (base / n).exists()]
    assert not presentes, f"templates legados ainda no repositório: {presentes}"
    dourado = [p.name for p in base.rglob("*.html") if "c9a84c" in p.read_text(encoding="utf-8", errors="ignore")]
    assert not dourado, f"paleta do produto de origem ainda presente em: {dourado}"


# ── Rotas de bastidor: exigem papel, não apenas estar logado ──────────────────
# O cadastro de cidadã é aberto por desenho, então "estar logado" não é barreira.

BACKSTAGE = [("post", "/api/admin/stamps/reprocess")]

# O produto anterior vivia aqui dentro: um chat sobre documentos, com protocolo editável por HTTP, anexo de
# arquivo arbitrário e memória por sessão de login. Ele perdeu a tela em setembro e continuou registrado,
# sem chamador nenhum. Saiu inteiro (#102). Esta lista existe para ele não voltar por descuido: cada uma
# destas rotas foi, um dia, superfície de exfiltração ou de injeção que ninguém estava olhando.
REMOVIDAS = [
    ("post", "/api/chat"), ("post", "/api/pdf/destilar"),
    ("get", "/api/protocolo"), ("post", "/api/protocolo"),
    ("get", "/api/help"), ("get", "/api/contexto"), ("post", "/api/contexto/limpar"),
    ("get", "/api/sessao/memoria"), ("post", "/api/sessao/memoria/limpar"),
]


def test_backstage_routes_require_the_supplier_role(citizen, lawyer):
    for method, path in BACKSTAGE:
        call = getattr(client, method)
        assert call(path).status_code == 401, f"{path} sem credencial"
        for quem, tok in (("cidadã", citizen["token"]), ("advogado", lawyer["token"])):
            r = call(path, headers=bearer(tok))
            assert r.status_code == 403, f"{path} aberta para {quem}: {r.status_code}"


def test_backstage_routes_stay_open_to_the_supplier():
    admin = client.post("/api/auth/login", json={"email": "admin@test.local", "senha": "admin-secret-1"}).json()
    for method, path in BACKSTAGE:
        r = getattr(client, method)(path, headers=bearer(admin["token"]))
        assert r.status_code == 200, f"{path} fechada para o fornecedor: {r.status_code}"


def test_the_previous_product_does_not_come_back(citizen):
    """Rota removida que volta é pior que rota que nunca saiu: ninguém procura por ela de novo.

    O 404 é conferido com credencial de cidadã, e não sem credencial nenhuma, porque uma rota que voltasse
    protegida por papel responderia 403 e passaria por 'ausente' num teste feito sem token."""
    for method, path in REMOVIDAS:
        r = getattr(client, method)(path, headers=bearer(citizen["token"]))
        assert r.status_code == 404, f"{path} voltou a existir e respondeu {r.status_code}"


# ── Hash da tentativa: reproduzível por terceiro e sem dado pessoal ───────────

def _tarefa_de_teste(hash_: str):
    from core.db import Session as _S, Tarefa as _T, engine as _e
    with _S(_e) as s:
        t = _T(hash=hash_, titulo="Contrato", advogado_id=1, status="enviada")
        s.add(t); s.commit(); s.refresh(t)
        return t


QUESTOES = [{"id": 1, "correta": 0}, {"id": 2, "correta": 1}, {"id": 3, "correta": 2}]


def test_attempt_hash_carries_no_personal_data(lawyer):
    """As colunas deixaram de existir em 20/09 (E17-T07). `record` continua aceitando os dois argumentos e
    continua os descartando, porque quem chama ainda os tem na mão e não pode passar a gravá-los por
    engano."""
    import core.attempts as tn
    from core.db import Tentativa

    t = _tarefa_de_teste("hash-tentativa-1")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES, "203.0.113.7", "Mozilla/5.0 (Android)")
    assert tent.hash_imutavel
    for morto in ("ip", "user_agent"):
        assert morto not in Tentativa.model_fields, f"a coluna {morto} continua no modelo"
        assert not hasattr(tent, morto), f"a linha gravada ainda carrega {morto}"


def test_attempt_hash_is_reproducible_from_what_is_stored(lawyer):
    """Tudo que entra no hash está na linha gravada, e nada além dela. A consulta entrou no preimage em
    20/09 e por isso entrou também na coluna: número que circula ao lado da prova sem estar dentro dela é
    número que qualquer um troca depois."""
    import core.attempts as tn
    t = _tarefa_de_teste("hash-tentativa-2")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES, "203.0.113.7", "Mozilla/5.0", consultas={"2": 1})
    gravadas = json.loads(tent.consultas)
    assert gravadas == {"2": 1}, "a consulta não ficou gravada, então ninguém tem como recalcular"
    recalculado = tn.attempt_hash(t.hash, tent.numero, tent.respostas, tent.criada_em, consultas=gravadas)
    assert recalculado == tent.hash_imutavel, "ninguém consegue recalcular o hash a partir do que está gravado"


def test_attempt_hash_does_not_depend_on_the_client(lawyer):
    import core.attempts as tn
    t = _tarefa_de_teste("hash-tentativa-3")
    a = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES, "203.0.113.7", "Chrome")
    b = tn.attempt_hash(t.hash, a.numero, a.respostas, a.criada_em, consultas=json.loads(a.consultas))
    assert a.hash_imutavel == b
    assert "PARA.AI" not in tn.PREIMAGE_SCHEMA, "a marca do produto de origem ainda está no hash"


# ── Teto de tentativas: o registro não pode ser obtido por tentativa e erro ───

def test_attempts_are_capped_so_the_record_cannot_be_brute_forced(lawyer, monkeypatch):
    import core.attempts as tn
    monkeypatch.setenv("QUIZ_MAX_ATTEMPTS", "3")
    t = _tarefa_de_teste("hash-teto")
    erradas = {"1": 9, "2": 9, "3": 9}
    for n in range(3):
        tent = tn.record(t, erradas, QUESTOES)
        assert tent.numero == n + 1 and not tent.aprovado
    assert tn.attempts_exhausted(t.id) is True
    with pytest.raises(tn.AttemptsExhausted):
        tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)


def test_the_cap_does_not_exist_before_it_is_reached(lawyer, monkeypatch):
    import core.attempts as tn
    monkeypatch.setenv("QUIZ_MAX_ATTEMPTS", "3")
    t = _tarefa_de_teste("hash-teto-2")
    tn.record(t, {"1": 9, "2": 9, "3": 9}, QUESTOES)
    assert tn.attempts_exhausted(t.id) is False
    ok = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)
    assert ok.aprovado is True


# ── Recarimbo: prova que não corresponde ao registro precisa ser refeita ──────

def test_a_stale_proof_does_not_block_a_new_stamp(tmp_path, monkeypatch):
    from leia import api_citizen as ac
    from leia.registry import StampOutcome, ots_digest

    chamadas = {"n": 0}
    monkeypatch.setattr(ac, "ots_stamp",
                        lambda digest: chamadas.__setitem__("n", chamadas["n"] + 1) or StampOutcome(b"prova-falsa"))
    assert ots_digest(b"prova-falsa") is None, "uma prova ilegível não pode contar como carimbo válido"

    t = _tarefa_de_teste("hash-recarimbo")
    import core.attempts as tn
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)
    caminho = ac._ots_path(t.hash, tent.numero)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"prova-de-um-registro-que-nao-existe-mais")

    ac.stamp_attempt(t.hash, tent.numero, tent.hash_imutavel)
    assert chamadas["n"] == 1, "a prova velha impediu o recarimbo"


# ── Sinal de vida: sem ele o deploy automático não sabe se a versão nova subiu ─

def test_health_answers_without_credentials_and_says_nothing_else():
    fresh = TestClient(main.app)
    r = fresh.get("/health")
    assert r.status_code == 200, "sem sinal de vida o deploy automático derruba a versão nova"
    assert r.json().get("status") == "ok"
    texto = r.text.lower()
    for vazamento in ("groq", "gsk_", "database_url", "admin", "senha", "password", "token"):
        assert vazamento not in texto, f"o sinal de vida é público e está mostrando {vazamento}"


def test_the_healthcheck_path_declared_to_the_host_is_really_served():
    """O caminho que o host consulta vive em .railway/railway.ts, fora desta folder.
    Se alguém remover a rota e esquecer a configuração, o deploy novo nunca assume e ninguém percebe."""
    import pathlib
    import re

    cfg = pathlib.Path(__file__).resolve().parents[2] / ".railway" / "railway.ts"
    assert cfg.exists(), "a configuração de deploy sumiu do repositório"
    achado = re.search(r"healthcheckPath:\s*\"([^\"]+)\"", cfg.read_text(encoding="utf-8"))
    assert achado, "nenhum healthcheckPath declarado: o host não tem como saber se a versão nova subiu"
    caminho = achado.group(1)
    r = TestClient(main.app).get(caminho)
    assert r.status_code == 200, f"o deploy espera 200 em {caminho} e a aplicação responde {r.status_code}"


# ── Convite: o link deixa de ser credencial de quem o tiver ───────────────────

def _nova_tarefa(lawyer) -> dict:
    return create_task(lawyer["token"], "Contrato com convite")


def _convidar(lawyer, tarefa_id: int, **corpo) -> dict:
    # O nome virou obrigatório no convite (E15-T02): é ele que a tela mostra para a pessoa confirmar que é
    # ela. Quem chama pode sobrescrever, e quem não se importa não precisa repetir a cada teste.
    corpo.setdefault("nome", "Destinatária")
    r = client.post(f"/api/tarefas/{tarefa_id}/convite", json=corpo, headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text
    return r.json()


def test_a_link_without_an_invite_keeps_working(lawyer_task):
    """Compatibilidade: link que já circulou não pode parar de abrir por causa desta mudança."""
    assert client.get(f"/api/t/{lawyer_task['hash']}").status_code == 200


def test_only_whoever_sent_the_document_can_invite_or_revoke(lawyer, citizen):
    t = _nova_tarefa(lawyer)
    r = client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Destinatária"}, headers=bearer(citizen["token"]))
    assert r.status_code in (403, 404), "uma conta qualquer conseguiu emitir convite para documento de outra pessoa"
    _convidar(lawyer, t["id"])
    r = client.delete(f"/api/tarefas/{t['id']}/convite", headers=bearer(citizen["token"]))
    assert r.status_code in (403, 404), "uma conta qualquer conseguiu revogar o convite de outra pessoa"


def test_a_revoked_invite_closes_the_link(lawyer):
    t = _nova_tarefa(lawyer)
    _convidar(lawyer, t["id"])
    assert client.get(f"/api/t/{t['hash']}").status_code == 200
    assert client.delete(f"/api/tarefas/{t['id']}/convite", headers=bearer(lawyer["token"])).status_code == 200
    r = client.get(f"/api/t/{t['hash']}")
    assert r.status_code == 403, "o link continuou abrindo depois de cancelado"
    assert "cancel" in r.json()["detail"].lower()


def test_an_expired_invite_closes_the_link(lawyer):
    from datetime import datetime, timedelta

    from core.db import Invite

    t = _nova_tarefa(lawyer)
    convite = _convidar(lawyer, t["id"], validade_horas=24)
    with Session(engine) as s:
        c = s.get(Invite, convite["id"])
        c.expires_at = datetime.utcnow() - timedelta(minutes=1)
        s.add(c); s.commit()
    r = client.get(f"/api/t/{t['hash']}")
    assert r.status_code == 403, "o link continuou abrindo depois de vencido"
    assert "venc" in r.json()["detail"].lower() or "expir" in r.json()["detail"].lower()


def test_an_addressed_invite_still_lets_anyone_read_and_ask(lawyer, citizen):
    """Ler e perguntar não exige identidade. Exigir conta para ler é barreira para quem mais precisa,
    e a pessoa pode estar num celular emprestado. O que a destinatária protege é o registro, não a leitura."""
    t = _nova_tarefa(lawyer)
    _convidar(lawyer, t["id"], email="outra.pessoa@teste.local")
    assert client.get(f"/api/t/{t['hash']}").status_code == 200, "leitura bloqueada por causa da destinatária"
    assert client.get(f"/api/t/{t['hash']}", headers=bearer(citizen["token"])).status_code == 200
    assert client.get(f"/api/t/{t['hash']}/inferencias").status_code in (200, 409)


def test_the_public_json_says_it_is_addressed_without_revealing_the_address(lawyer):
    t = _nova_tarefa(lawyer)
    _convidar(lawyer, t["id"], email="maria.silva@exemplo.local")
    convite = client.get(f"/api/t/{t['hash']}").json().get("convite")
    assert convite and convite["enderecado"] is True
    assert "maria.silva" not in json.dumps(convite), "o endereço inteiro da destinatária vazou no JSON público"
    assert convite["para"] and "***" in convite["para"]


def test_only_the_addressed_person_produces_the_record(lawyer, citizen):
    """O comprovante diz que uma pessoa entendeu. Quem não é ela não pode gerá-lo."""
    t = _nova_tarefa(lawyer)
    _convidar(lawyer, t["id"], email="outra.pessoa@teste.local")
    assert client.post(f"/api/t/{t['hash']}/quiz", json={"respostas": {}}).status_code == 403
    assert client.post(f"/api/t/{t['hash']}/quiz", json={"respostas": {}},
                       headers=bearer(citizen["token"])).status_code == 403
    assert client.post(f"/api/t/{t['hash']}/vincular", headers=bearer(citizen["token"])).status_code == 403


def test_the_person_it_was_addressed_to_can_do_everything(lawyer, citizen):
    t = _nova_tarefa(lawyer)
    _convidar(lawyer, t["id"], email=citizen["usuario"]["email"])
    assert client.get(f"/api/t/{t['hash']}", headers=bearer(citizen["token"])).status_code == 200
    assert client.post(f"/api/t/{t['hash']}/vincular", headers=bearer(citizen["token"])).status_code == 200


def test_a_cancelled_link_closes_reading_for_everyone(lawyer, citizen):
    """Validade do link não é sobre identidade: cancelado ou vencido, não abre nem para quem tem conta."""
    t = _nova_tarefa(lawyer)
    _convidar(lawyer, t["id"], email=citizen["usuario"]["email"])
    client.delete(f"/api/tarefas/{t['id']}/convite", headers=bearer(lawyer["token"]))
    assert client.get(f"/api/t/{t['hash']}").status_code == 403
    assert client.get(f"/api/t/{t['hash']}", headers=bearer(citizen["token"])).status_code == 403


def test_the_invite_also_closes_the_answers_route(lawyer):
    """De nada adianta fechar a leitura e deixar a gravação do registro aberta."""
    t = _nova_tarefa(lawyer)
    _convidar(lawyer, t["id"])
    client.delete(f"/api/tarefas/{t['id']}/convite", headers=bearer(lawyer["token"]))
    r = client.post(f"/api/t/{t['hash']}/quiz", json={"respostas": {}})
    assert r.status_code == 403, "o registro pôde ser gravado por um link cancelado"


def test_a_forged_forwarded_header_does_not_buy_a_new_identity():
    """Quem chama escolhe o que escrever no começo de X-Forwarded-For. Se a chave do limite sair dali,
    cada requisição vira um cliente novo, o balde nunca enche e o limite não limita nada.
    O que o proxy confiável acrescenta fica no fim, e é isso que vale."""
    os.environ["RATE_LIMIT_PER_MINUTE"] = "3"
    limiter.reset()
    try:
        codes = []
        for i in range(5):
            forjado = {"X-Forwarded-For": f"203.0.113.{i}, 198.51.100.77"}
            codes.append(client.post("/api/auth/login", json={"email": "ninguem@teste.local", "senha": "x"},
                                     headers=forjado).status_code)
        assert 429 in codes, "trocar o começo do cabeçalho contornou o limite por requisição"
        assert codes[:3] == [401, 401, 401] and codes[3] == 429
    finally:
        os.environ["RATE_LIMIT_PER_MINUTE"] = "200"
        limiter.reset()


# ── Âncora literal: quem confere é o servidor, nunca o modelo ─────────────────

DOC_TEXT = ("CLÁUSULA 3. O CONTRATANTE pagará honorários de vinte por cento sobre o proveito econômico,\n"
            "somente em caso de êxito. CLÁUSULA 4. As custas processuais correm por conta do CONTRATANTE.")


def test_a_quote_that_is_not_in_the_document_is_never_sealed():
    """O selo de conferido é a promessa central do produto. Trecho que não está no documento não recebe selo,
    e o item sai sem posição, em vez de apontar para qualquer lugar plausível."""
    from leia.api_citizen import build_inferences

    memoria = {"memoria_persistente": {"datas_valores": [
        {"campo": "multa", "valor": "R$ 5.000", "trecho_verbatim": "multa de cinco mil reais por descumprimento"}]}}
    item = build_inferences(DOC_TEXT, memoria, None, [])["classes"][0]["itens"][0]
    assert not item["conferido"] and item["pos"] is None, "trecho inventado recebeu selo de conferido"


def test_a_quote_with_small_differences_is_found_and_says_how():
    """O modelo devolve o trecho com pequenas diferenças de digitação. Achar é bom; dizer como achou é o que
    permite alguém decidir se confia."""
    from leia.api_citizen import build_inferences

    memoria = {"memoria_persistente": {"datas_valores": [
        {"campo": "honorarios", "valor": "20%", "trecho_verbatim": "honorarios de vinte por cento sobre o proveito economico"}]}}
    item = build_inferences(DOC_TEXT, memoria, None, [])["classes"][0]["itens"][0]
    assert item["conferido"], "não achou um trecho que está lá com diferenças pequenas"
    assert item["conferencia"]["metodo"] == "aproximado"
    assert 0.8 <= item["conferencia"]["score"] <= 1.0


def test_an_exact_quote_says_it_was_exact():
    from leia.api_citizen import build_inferences

    memoria = {"memoria_persistente": {"datas_valores": [
        {"campo": "custas", "valor": "x", "trecho_verbatim": "As custas processuais correm por conta do CONTRATANTE"}]}}
    item = build_inferences(DOC_TEXT, memoria, None, [])["classes"][0]["itens"][0]
    assert item["conferencia"]["metodo"] in ("exato", "normalizado") and item["conferencia"]["score"] == 1.0


def test_the_citizen_never_reads_a_quote_that_is_not_in_the_document():
    """Na jornada o trecho aparece ao lado da explicação como se fosse copiado do documento.
    Se ele foi inventado, ou se pertence a outro ponto, a pessoa está lendo uma citação falsa."""
    from leia.api_citizen import topics_from_summary

    resumo = "## Quanto você paga\n\nVocê paga vinte por cento do que ganhar, e só se ganhar."
    memoria = {"memoria_persistente": {"datas_valores": [
        {"campo": "x", "valor": "y", "trecho_verbatim": "o CONTRATANTE pagará multa de vinte por cento ao mês por atraso"}]}}
    topico = topics_from_summary(resumo, memoria, DOC_TEXT)[0]
    assert "trecho" not in topico, f"mostrou à cidadã um trecho que não está no documento: {topico.get('trecho')!r}"


# ── De onde vem o trecho de cada tópico: declarado, não adivinhado ────────────

RESUMO_ESTRUTURADO = """# Resumo em uma linha

Uma pessoa contratou uma advogada e combinou pagar só se ganhar.

## 👥 Quem está nesta história

Duas pessoas: quem contratou e quem foi contratada.

## 📖 O que aconteceu

Elas assinaram um combinado sobre o pagamento.

## 🤝 O que está sendo pedido

Ela pede que o combinado seja respeitado.
"""

MEMORIA_ESTRUTURADA = {"memoria_persistente": {
    "identificacao": [{"campo": "partes", "valor": "duas", "trecho_verbatim": "O CONTRATANTE pagará honorários de vinte por cento"}],
    "pedidos": [{"campo": "pedido", "valor": "x", "trecho_verbatim": "As custas processuais correm por conta do CONTRATANTE"}],
    "fatos": [{"campo": "inventado", "valor": "y", "trecho_verbatim": "cláusula de multa que não existe neste contrato"}],
}}
SINTESES_ESTRUTURADAS = [
    ("identificacao", {"sintese": {"valor": "Quem é quem", "lastro": ["identificacao[0]"]}}),
    ("fatos", {"sintese": {"valor": "O que aconteceu", "lastro": ["fatos[0]"]}}),
    ("pedidos", {"sintese": {"valor": "O que se pede", "lastro": ["pedidos[0]"]}}),
]


def test_each_topic_takes_its_quote_from_the_section_it_belongs_to():
    """A seção do resumo tem título fixo, definido no protocolo. Então de onde vem o trecho de cada uma é
    coisa declarada, não adivinhada por palavras em comum, que já colocou o trecho dos fatos embaixo de
    'quem está nesta história'."""
    from leia.api_citizen import topics_from_summary

    topicos = topics_from_summary(RESUMO_ESTRUTURADO, MEMORIA_ESTRUTURADA, DOC_TEXT, SINTESES_ESTRUTURADAS)
    por_titulo = {t["titulo"]: t for t in topicos}

    quem = por_titulo["👥 Quem está nesta história"]
    assert quem.get("trecho") == "O CONTRATANTE pagará honorários de vinte por cento", \
        f"pegou o trecho de outra seção: {quem.get('trecho')!r}"

    pedido = por_titulo["🤝 O que está sendo pedido"]
    assert pedido.get("trecho") == "As custas processuais correm por conta do CONTRATANTE"


def test_a_section_with_no_declared_source_shows_no_quote():
    """Resumo em uma linha fala do caso inteiro, não de uma cláusula. Sem fonte declarada, nada é mostrado,
    em vez de pendurar ali o trecho que por acaso tiver mais palavras em comum."""
    from leia.api_citizen import topics_from_summary

    topicos = topics_from_summary(RESUMO_ESTRUTURADO, MEMORIA_ESTRUTURADA, DOC_TEXT, SINTESES_ESTRUTURADAS)
    assert "trecho" not in topicos[0] and topicos[0]["titulo"] == "Resumo em uma linha"


# ── Porta de fidelidade: só é publicado o que o documento sustenta ────────────

SINTESE_SEM_LASTRO = ("O caso se apoia no artigo 22 da Lei 8.906/94, no artigo 389 do Código Civil e na Súmula 201 "
                      "do Superior Tribunal de Justiça, além da jurisprudência sobre honorários contratuais. ") * 6


def test_publish_drops_a_synthesis_with_empty_lastro():
    """Medida em evals/casos/contrato-honorarios.json: a síntese de fundamentos tem 1293 caracteres, cita seis
    dispositivos legais e chega com "lastro": []. Nada ali pode ser apontado dentro do documento da pessoa, e
    quem lê não tem como saber disso, porque a síntese aparece com a mesma cara das que têm lastro."""
    from leia.api_citizen import build_inferences

    memoria = {"memoria_persistente": {"pedidos": [
        {"campo": "custas", "valor": "contratante", "trecho_verbatim": "As custas processuais correm por conta do CONTRATANTE"}]}}
    sinteses = [("pedidos", {"sintese_pedidos": {"valor": "As custas ficam com quem contratou.", "lastro": ["pedidos[0]"]}}),
                ("fundamentos", {"sintese_fundamentos": {"valor": SINTESE_SEM_LASTRO, "lastro": []}})]
    r = build_inferences(DOC_TEXT, memoria, None, sinteses)
    assert [s["classe"] for s in r["sinteses"]] == ["pedidos"], "síntese sem lastro nenhum chegou à tela"
    assert r["sinteses_sem_lastro"] == ["fundamentos"], "o descarte precisa ficar visível para quem revisa"


def test_publish_drops_a_synthesis_whose_lastro_is_not_in_the_document():
    """Lastro preenchido não é lastro conferido: o item apontado precisa existir dentro do documento."""
    from leia.api_citizen import build_inferences

    memoria = {"memoria_persistente": {"fatos": [
        {"campo": "multa", "valor": "x", "trecho_verbatim": "cláusula de multa que não existe neste contrato"}]}}
    sinteses = [("fatos", {"sintese_fatos": {"valor": "O contrato prevê multa por atraso.", "lastro": ["fatos[0]"]}})]
    assert build_inferences(DOC_TEXT, memoria, None, sinteses)["sinteses"] == []


def test_publish_follows_a_lastro_that_points_at_another_synthesis():
    """T11_SINTESE_CONTEXTO declara lastro nas outras sínteses, não em item de memória. Seguir a corrente até o
    item é o que separa descartar uma síntese sustentada de publicar uma que não se sustenta."""
    from leia.api_citizen import build_inferences

    memoria = {"memoria_persistente": {"fatos": [
        {"campo": "pagamento", "valor": "20%",
         "trecho_verbatim": "O CONTRATANTE pagará honorários de vinte por cento sobre o proveito econômico"}]}}
    apoiada = [("fatos", {"s": {"valor": "Combinaram vinte por cento.", "lastro": ["fatos[0]"]}}),
               ("contexto", {"s": {"valor": "O combinado vale desde a assinatura.", "lastro": ["T7_SINTESE_FATOS"]}})]
    assert [s["classe"] for s in build_inferences(DOC_TEXT, memoria, None, apoiada)["sinteses"]] == ["fatos", "contexto"]

    solta = [("fundamentos", {"s": {"valor": SINTESE_SEM_LASTRO, "lastro": []}}),
             ("contexto", {"s": {"valor": "O combinado vale desde a assinatura.", "lastro": ["T8_SINTESE_FUNDAMENTOS"]}})]
    assert build_inferences(DOC_TEXT, memoria, None, solta)["sinteses"] == [], \
        "a corrente terminou em lastro vazio e a síntese foi publicada assim mesmo"


def test_publish_drops_a_section_with_nothing_checked_in_the_document():
    """A seção "O que aconteceu" explica a classe fatos, e o único fato tem trecho que não está no documento.
    Publicá-la é afirmar à cidadã, com a mesma cara das seções conferidas, algo que ninguém consegue apontar
    dentro do documento dela. A seção sem fonte declarada no protocolo continua, porque ela fala do caso
    inteiro e nunca prometeu trecho."""
    from leia.api_citizen import topics_from_summary

    titulos = [t["titulo"] for t in topics_from_summary(RESUMO_ESTRUTURADO, MEMORIA_ESTRUTURADA, DOC_TEXT, SINTESES_ESTRUTURADAS)]
    assert "📖 O que aconteceu" not in titulos, "seção sem nada conferido chegou à cidadã"
    assert titulos == ["Resumo em uma linha", "👥 Quem está nesta história", "🤝 O que está sendo pedido"]


def test_publish_names_the_sections_it_dropped():
    """O descarte não pode ser silencioso: é ele que o advogado revisa e a porta de qualidade mede."""
    from leia.api_citizen import sections_without_anchor

    assert sections_without_anchor(RESUMO_ESTRUTURADO, MEMORIA_ESTRUTURADA, DOC_TEXT, SINTESES_ESTRUTURADAS) == ["📖 O que aconteceu"]


def test_publish_an_explanation_with_nothing_left_says_so_instead_of_showing_a_blank_page(lawyer):
    """Descartar seção não pode virar tela em branco. Quando nada sobra, o serviço para de mandar a explicação
    inteira: sem isso o aplicativo remonta os tópicos a partir do resumo em markdown e a cidadã lê de volta,
    sem trecho nenhum, exatamente as seções que a porta tinha descartado."""
    t = create_task(lawyer["token"], "Nada conferido")
    h = t["hash"]
    pasta = ws.folder(h)
    (pasta / "resumo_humanizado.md").write_text("## 👥 Quem está nesta história\n\nDuas pessoas assinaram.", encoding="utf-8")
    (pasta / "texto_extraido.txt").write_text(FAKE_TEXT, encoding="utf-8")
    (pasta / "memoria_persistente.json").write_text(json.dumps({"memoria_persistente": {"identificacao": [
        {"campo": "partes", "valor": "duas", "trecho_verbatim": "trecho que não está no documento"}]}}), encoding="utf-8")
    (pasta / "T10_SINTESE_IDENTIFICACAO.json").write_text(
        json.dumps({"sintese_identificacao": {"valor": "Duas pessoas.", "lastro": ["identificacao[0]"]}}), encoding="utf-8")
    set_status(h, "enviada")

    data = client.get(f"/api/t/{h}").json()
    assert data["tarefa"]["status"] == "falhou", "a tela ficaria em branco sem dizer por quê"
    assert data["topicos"] is None and data["resumo_md"] is None and data["questoes"] == []


# ── Uma etapa que devolve lixo não pode seguir como sucesso ───────────────────

class _FakeStream:
    """Cliente de modelo que devolve o texto pedido, em pedaços, como a SDK faz."""

    def __init__(self, texto: str):
        self.texto = texto

    async def create(self, **kwargs):
        texto = self.texto

        class _Delta:
            def __init__(self, c): self.content = c

        class _Choice:
            def __init__(self, c): self.delta = _Delta(c)

        class _Chunk:
            def __init__(self, c): self.choices = [_Choice(c)]

        async def gen():
            for i in range(0, len(texto), 16):
                yield _Chunk(texto[i:i + 16])

        return gen()


def _fake_groq(texto: str):
    class _Groq:
        class chat:  # noqa: N801
            completions = _FakeStream(texto)
    return _Groq()


def _rodar(task: dict, saida: str) -> dict:
    import asyncio

    from core.pipeline_pdf import _run_task
    return asyncio.get_event_loop().run_until_complete(_run_task(task, "", _fake_groq(saida)))


def test_a_task_that_returns_invalid_json_fails_instead_of_passing_text_along():
    """Hoje o texto cru vira o 'parsed' da etapa, é gravado no arquivo dela e entra no contexto da etapa
    seguinte, tudo com ok=True. Uma etapa que não entregou o que prometeu contamina todas as outras."""
    res = _rodar({"id": "T1_TESTE", "tipo_saida": "json", "missao": "x"}, "desculpe, não consegui responder")
    assert res["ok"] is False, "etapa com JSON inválido seguiu como sucesso"
    assert "json" in str(res.get("erro", "")).lower()


def test_a_task_that_misses_a_field_the_protocol_requires_fails():
    task = {"id": "T7_TESTE", "tipo_saida": "json", "missao": "x",
            "schema": {"campos": {"sintese_fatos": {"tipo": "objeto", "obrigatorios": ["campo", "valor", "lastro"]}}}}
    assert _rodar(task, '{"sintese_fatos": {"campo": "sintese_fatos", "valor": "ok", "lastro": []}}')["ok"] is True
    ruim = _rodar(task, '{"sintese_fatos": {"campo": "sintese_fatos", "valor": "ok"}}')
    assert ruim["ok"] is False and "lastro" in str(ruim.get("erro", ""))


def test_a_list_field_checks_the_shape_of_each_item():
    task = {"id": "T1_TESTE", "tipo_saida": "json", "missao": "x",
            "schema": {"campos": {"identificacao": {"tipo": "lista", "itens": ["campo", "valor", "trecho_verbatim"]}}}}
    bom = '{"identificacao": [{"campo": "autor", "valor": "Maria", "trecho_verbatim": "Maria da Silva"}]}'
    assert _rodar(task, bom)["ok"] is True
    ruim = _rodar(task, '{"identificacao": [{"campo": "autor", "valor": "Maria"}]}')
    assert ruim["ok"] is False and "trecho_verbatim" in str(ruim.get("erro", ""))


def test_a_text_task_is_not_judged_as_json():
    """T13 devolve markdown. Exigir JSON dela quebraria o resumo inteiro."""
    res = _rodar({"id": "T13_TESTE", "tipo_saida": "texto", "missao": "x"}, "# Resumo\n\nUma frase.")
    assert res["ok"] is True and res["parsed"].startswith("# Resumo")


# ── O registro é gravado na aprovação, e diz a que documento se refere ────────

def _tarefa_com_documento(hash_: str, pdf: bytes, resumo: str) -> Tarefa:
    t = _tarefa_de_teste(hash_)
    pasta = ws.folder(hash_)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "original.pdf").write_bytes(pdf)
    (pasta / "resumo_humanizado.md").write_text(resumo, encoding="utf-8")
    return t


def test_the_receipt_says_which_document_and_which_explanation_it_is_about():
    """Sem isso o comprovante prova que houve uma tentativa com N acertos, e nada mais. Ele não amarra o
    entendimento ao documento que a pessoa leu, que é a afirmação central do produto."""
    import core.attempts as tn
    from leia.api_citizen import freeze_record, get_attempt
    from leia.registry import sha256_hex

    pdf, resumo = small_pdf("Contrato de teste do registro."), "# Explicação\n\nTexto simples."
    t = _tarefa_com_documento("registro-completo", pdf, resumo)
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)
    freeze_record(t.hash, tent.numero, tent.hash_imutavel)

    a = get_attempt(tent.hash_imutavel)
    assert a["pdf_sha256"] == sha256_hex(pdf), "o comprovante não diz a que documento se refere"
    assert a["resumo_sha256"] == sha256_hex(resumo), "o comprovante não diz que explicação foi lida"


def test_the_record_does_not_change_when_the_database_changes():
    """Registro de consentimento remontado do banco a cada visita não é registro: mudou a linha, mudou a prova,
    e o carimbo de tempo passa a não corresponder a nada."""
    import core.attempts as tn
    from leia.api_citizen import freeze_record

    t = _tarefa_com_documento("registro-imutavel", small_pdf("Outro contrato."), "# Explicação\n\nOutra.")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)
    freeze_record(t.hash, tent.numero, tent.hash_imutavel)

    antes = client.get(f"/verify/{tent.hash_imutavel}?format=json").json()
    from core.db import Tentativa as _Tent

    with Session(engine) as s:
        linha = s.exec(select(_Tent).where(_Tent.hash_imutavel == tent.hash_imutavel)).first()
        linha.acertos = 0
        linha.aprovado = False
        s.add(linha); s.commit()
    depois = client.get(f"/verify/{tent.hash_imutavel}?format=json").json()

    assert antes["canonical"] == depois["canonical"], "mexer no banco mudou o registro publicado"
    assert antes["payloadHash"] == depois["payloadHash"]


def test_an_attempt_recorded_before_this_change_still_verifies():
    """Compatibilidade: comprovante que já circulou não pode parar de abrir."""
    import core.attempts as tn

    t = _tarefa_com_documento("registro-antigo", small_pdf("Contrato antigo."), "# Antiga\n\nx")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)   # sem freeze_record, como antes
    r = client.get(f"/verify/{tent.hash_imutavel}?format=json")
    assert r.status_code == 200 and r.json()["payloadHash"]


# ── autorização: quem vê não é quem manda ─────────────────────────────────

def link_directly(h: str, conta: dict) -> None:
    """Vincula pelo banco, para que estes testes meçam autorização e não o caminho do convite."""
    from core.db import Usuario
    with Session(engine) as s:
        u = s.exec(select(Usuario).where(Usuario.email == conta["usuario"]["email"])).one()
        t = s.exec(select(Tarefa).where(Tarefa.hash == h)).one()
        t.cidadao_id = u.id
        s.add(t); s.commit()


def test_the_answer_key_never_leaves_by_the_artifact_route(lawyer, citizen):
    """A rota pública já protege o gabarito. A de artefato autorizava por quem enxerga o documento,
    então entregava `correta` e `justificativa` a quem ia responder as perguntas."""
    t = create_task(lawyer["token"], "Gabarito")
    fake_artifacts(t["hash"])
    link_directly(t["hash"], citizen)

    r = client.get(f"/tarefas/{t['id']}/artefato/questoes.json", headers=bearer(citizen["token"]))
    assert r.status_code == 403, "a cidadã baixou o gabarito das perguntas que ela vai responder"
    assert client.get(f"/tarefas/{t['id']}/artefato/questoes.json",
                      headers=bearer(lawyer["token"])).status_code == 200, "quem enviou continua conferindo"


def test_the_lawyer_email_is_not_written_into_the_workspace(lawyer):
    """meta.json ficava com o endereço inteiro, baixável. O advogado_id já está no banco."""
    t = create_task(lawyer["token"], "Meta")
    meta = json.loads((ws.folder(t["hash"]) / "meta.json").read_text(encoding="utf-8"))
    assert "@" not in json.dumps(meta), f"e-mail gravado no workspace: {meta.get('advogado')}"


def test_the_review_gate_holds_on_every_route(lawyer, citizen):
    """`/api/t/{hash}` esconde a explicação durante a revisão. Duas rotas ao lado entregavam a mesma coisa."""
    t = create_task(lawyer["token"], "Portão")
    fake_artifacts(t["hash"])
    link_directly(t["hash"], citizen)
    set_status(t["hash"], "pronta")

    d = client.get(f"/api/pdf/{t['hash']}/destilado", headers=bearer(citizen["token"]))
    assert d.status_code == 409, "a cidadã leu a explicação que o advogado ainda não conferiu"

    s = client.get(f"/api/tarefas/{t['id']}/status", headers=bearer(citizen["token"]))
    assert s.status_code == 200 and "advogado_id" not in json.dumps(s.json()), "eventos crus na resposta"

    assert client.get(f"/api/pdf/{t['hash']}/destilado",
                      headers=bearer(lawyer["token"])).status_code == 200, "quem revisa precisa ver"


def test_destructive_legacy_routes_answer_only_to_the_owner(lawyer, citizen):
    """reprocess apaga o resumo que lastreia um comprovante; nova-rodada cria tarefa na conta do advogado."""
    t = create_task(lawyer["token"], "Legado")
    fake_artifacts(t["hash"])
    link_directly(t["hash"], citizen)
    set_status(t["hash"], "pronta")

    for rota in ("reprocess", "nova-rodada"):
        r = client.post(f"/tarefas/{t['id']}/{rota}", headers=bearer(citizen["token"]), follow_redirects=False)
        assert r.status_code == 403, f"{rota} obedeceu a quem só está vinculado ao documento: {r.status_code}"
    assert (ws.folder(t["hash"]) / "resumo_humanizado.md").exists(), "o resumo foi apagado por quem não é dono"


# ── vínculo: ler é aberto, virar dona do documento não ────────────────────

def test_linking_requires_an_invite(lawyer, citizen):
    """Ler fica aberto de propósito, para quem está num telefone emprestado. Mas vincular é virar dona
    do documento, e era por ordem de chegada: qualquer conta com o link ficava com ele para sempre."""
    t = create_task(lawyer["token"], "Sem convite")
    r = client.post(f"/api/t/{t['hash']}/vincular", headers=bearer(citizen["token"]))
    assert r.status_code == 403, "uma conta qualquer se vinculou a um documento sem convite nenhum"
    assert client.get(f"/api/t/{t['hash']}").status_code == 200, "ler continua aberto"

    client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Destinatária", "email": None},
                headers=bearer(lawyer["token"])).raise_for_status()
    assert client.post(f"/api/t/{t['hash']}/vincular", headers=bearer(citizen["token"])).status_code == 200


def test_the_owner_can_undo_a_link(lawyer, citizen):
    """Sem desfazer, um vínculo errado trancava a destinatária legítima para fora do próprio documento."""
    t = create_task(lawyer["token"], "Desvínculo")
    client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Destinatária", "email": None}, headers=bearer(lawyer["token"]))
    client.post(f"/api/t/{t['hash']}/vincular", headers=bearer(citizen["token"]))

    assert client.delete(f"/api/tarefas/{t['id']}/cidadao",
                         headers=bearer(citizen["token"])).status_code in (403, 404), "só quem enviou desfaz"
    assert client.delete(f"/api/tarefas/{t['id']}/cidadao", headers=bearer(lawyer["token"])).status_code == 200

    other = signup("terceira@teste.local", "cidadao", "Joana")
    assert client.post(f"/api/t/{t['hash']}/vincular", headers=bearer(other["token"])).status_code == 200


# ── tentativas: o teto e o hash do comprovante sob concorrência ───────────

def test_concurrent_attempts_respect_the_cap_and_never_share_a_hash(lawyer, monkeypatch):
    """Checar numa sessão e gravar em outra é checar-depois-gravar: o teto que existe para impedir o
    gabarito por tentativa e erro furava, e duas tentativas diferentes saíam com o mesmo
    `hash_imutavel`, que é o identificador público do comprovante."""
    from concurrent.futures import ThreadPoolExecutor

    import core.attempts as tn

    monkeypatch.setenv("QUIZ_MAX_ATTEMPTS", "3")
    t = create_task(lawyer["token"], "Corrida")
    fake_artifacts(t["hash"])
    with Session(engine) as s:
        tarefa = s.exec(select(Tarefa).where(Tarefa.hash == t["hash"])).one()
    questoes = json.loads((ws.folder(t["hash"]) / "questoes.json").read_text(encoding="utf-8"))["questoes"]

    def enviar(_):
        try:
            return tn.record(tarefa, {"1": 0}, questoes)
        except tn.AttemptsExhausted:
            return None

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(enviar, range(12)))

    gravadas = tn.list_all(tarefa.id)
    numeros = sorted(x.numero for x in gravadas)
    hashes = [x.hash_imutavel for x in gravadas]
    assert len(gravadas) <= 3, f"o teto de 3 furou: {len(gravadas)} tentativas, números {numeros}"
    assert len(set(numeros)) == len(numeros), f"número de rodada repetido: {numeros}"
    assert len(set(hashes)) == len(hashes), "duas tentativas com o mesmo hash de comprovante"


def test_undoing_a_link_does_not_hand_the_next_person_the_previous_one_s_record(lawyer, citizen):
    """Desfazer o vínculo resolve o vínculo errado, mas a tentativa pertence à tarefa, não à pessoa.
    Se alguém já respondeu, a próxima conta vinculada herdaria o comprovante da anterior."""
    import core.attempts as tn

    t = create_task(lawyer["token"], "Herança")
    fake_artifacts(t["hash"])
    client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Destinatária", "email": None}, headers=bearer(lawyer["token"]))
    client.post(f"/api/t/{t['hash']}/vincular", headers=bearer(citizen["token"]))

    with Session(engine) as s:
        tarefa = s.exec(select(Tarefa).where(Tarefa.hash == t["hash"])).one()
    questoes = json.loads((ws.folder(t["hash"]) / "questoes.json").read_text(encoding="utf-8"))["questoes"]
    tn.record(tarefa, {"1": 1}, questoes)

    r = client.delete(f"/api/tarefas/{t['id']}/cidadao", headers=bearer(lawyer["token"]))
    assert r.status_code == 409, "desvinculou por cima de um comprovante que afirma que outra pessoa entendeu"
def test_the_citizen_chat_never_puts_document_text_in_the_system_role(citizen):
    """O resumo e a memória são derivados do PDF, e `memoria_persistente.json` carrega `trecho_verbatim`,
    que é cópia literal dele. Texto de origem não confiável no papel system tem precedência sobre a regra
    'use apenas o contexto' escrita logo acima dele."""
    import main

    t = create_task(citizen["token"], "Chat")
    fake_artifacts(t["hash"])
    set_status(t["hash"], "pronta")

    capturado: dict = {}

    class _Completions:
        async def create(self, **kwargs):
            capturado.update(kwargs)
            raise RuntimeError("basta capturar")

    class _Groq:
        class chat:  # noqa: N801
            completions = _Completions()

    anterior, main.groq_client = main.groq_client, _Groq()
    try:
        client.post(f"/api/t/{t['hash']}/chat", json={"mensagem": "Quanto eu pago?"})
    finally:
        main.groq_client = anterior

    mensagens = capturado.get("messages") or []
    assert mensagens, "o chat não chegou a montar as mensagens"
    system = next((m["content"] for m in mensagens if m["role"] == "system"), "")
    assert "honorários de vinte por cento" not in system, "o trecho literal do documento está no papel system"
    assert "CLÁUSULA" not in system and "Resumo em uma linha" not in system, "conteúdo do documento no system"
    juntas = "\n".join(m["content"] for m in mensagens)
    assert "honorários de vinte por cento" in juntas, "o contexto sumiu: o chat deixaria de responder"

    import re
    tag = re.search(r"<(documento_[0-9a-f]{16})>", mensagens[1]["content"]).group(1)
    assert tag in system, "o system não nomeia a etiqueta que ele sorteou, então qualquer forjada passa a valer"
    achadas = set(re.findall(r"</?documento_[0-9a-f]{16}>", mensagens[1]["content"]))
    assert achadas == {f"<{tag}>", f"</{tag}>"}, f"etiqueta forjada sobreviveu no chat: {achadas}"
    assert mensagens[-1]["content"] == "Quanto eu pago?", "a pergunta da pessoa deixou de ser a última mensagem"


def test_a_document_from_the_removed_external_path_fails_loudly(lawyer):
    """Os dois fluxos externos foram removidos. Documento que tenha vindo por eles não pode virar uma tela
    de explicação vazia: a pessoa leria "Explicação indisponível" sem saber por quê, e o advogado aprovaria
    um texto que não existe. Falhar dizendo o motivo é melhor que mostrar nada com ar de normalidade."""
    t = create_task(lawyer["token"], "Legado externo")
    h = t["hash"]
    for nome in ("resumo_humanizado.md", "questoes.json", "memoria_persistente.json", "texto_extraido.txt"):
        (ws.folder(h) / nome).unlink(missing_ok=True)
    (ws.folder(h) / "resumo_estruturado.json").write_text(json.dumps({"processo": {}}), encoding="utf-8")
    set_status(h, "pronta")

    r = client.get(f"/api/t/{h}")
    assert r.status_code == 200, r.text
    assert r.json()["tarefa"]["status"] == "falhou", "documento do caminho removido passou como se estivesse pronto"


def test_the_pass_mark_is_the_one_the_product_declares(monkeypatch):
    """O piso vinha de `int(total * 0.83)`, que trunca: com 6 perguntas o piso virava 4, ou seja **66,7%**,
    enquanto o comentário ao lado dizia 83%. Produção serve 6 perguntas, então quem só chutasse passava em
    10,9% das vezes dentro das três tentativas permitidas. O portão é onde o produto inteiro se apoia."""
    import core.attempts as tn

    monkeypatch.setenv("QUIZ_PASS_RATIO", "0.83")
    for total, minimo in ((3, 3), (6, 5), (10, 9), (12, 10)):
        piso = tn.pass_mark(total)
        assert piso == minimo, f"com {total} perguntas o piso é {piso}, e 83% pede {minimo}"
        assert piso / total >= 0.83, f"piso de {piso}/{total} = {piso/total:.1%}, abaixo dos 83% declarados"


def test_the_pass_mark_never_asks_for_more_than_exists():
    import core.attempts as tn

    assert tn.pass_mark(1) == 1 and tn.pass_mark(0) == 1


def test_the_receipt_says_whether_a_lawyer_reviewed_it(monkeypatch):
    """Dois fluxos produzem o mesmo comprovante e só um passa por advogado. A supervisão humana é metade da
    tese do produto; um comprovante que não distingue supervisionado de não supervisionado apaga essa metade
    justamente no artefato que circula."""
    import core.attempts as tn
    from leia.api_citizen import freeze_record, get_attempt
    from leia.registry import build_payload

    monkeypatch.setenv("QUIZ_PASS_RATIO", "0.83")
    for origem, esperado in (("cidadao", False), ("advogado", True)):
        t = _tarefa_com_documento(f"revisao-{origem}", small_pdf("Contrato."), "# Explicação\n\nTexto.")
        with Session(engine) as s:
            linha = s.exec(select(Tarefa).where(Tarefa.hash == t.hash)).one()
            linha.origem = origem
            s.add(linha); s.commit()
        tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)
        freeze_record(t.hash, tent.numero, tent.hash_imutavel)
        p = build_payload(get_attempt(tent.hash_imutavel))
        assert p["reviewedByLawyer"] is esperado, \
            f"origem {origem}: o comprovante diz revisado={p['reviewedByLawyer']}"


def test_the_receipt_says_what_it_measured(monkeypatch):
    """`understood: true` sozinho é afirmação forte e indefensável: quem lê o JSON não sabe por qual régua.
    Dizer o instrumento e o piso deixa o terceiro julgar o peso, em vez de aceitar ou recusar no escuro."""
    import core.attempts as tn
    from leia.api_citizen import freeze_record, get_attempt
    from leia.registry import build_payload

    monkeypatch.setenv("QUIZ_PASS_RATIO", "0.83")
    t = _tarefa_com_documento("regua", small_pdf("Contrato."), "# Explicação\n\nTexto.")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)
    freeze_record(t.hash, tent.numero, tent.hash_imutavel)
    p = build_payload(get_attempt(tent.hash_imutavel))
    # Desde E12 a palavra mudou junto com o que ela descreve: a pergunta nasce presa a uma cláusula, e medir
    # múltipla escolha sobre narrativa não é a mesma coisa que medir sobre cláusula.
    assert p["instrument"] == "multiple-choice-anchored-in-clause", "o comprovante não diz por qual instrumento mediu"
    assert p["passMark"] == tn.pass_mark(p["answered"]), "o comprovante não diz qual era o piso"
    assert p["answered"] == len(QUESTOES)


def test_a_task_caught_by_a_restart_does_not_stay_stuck_forever():
    """O pipeline roda como BackgroundTask no mesmo processo. Quando a Railway reinicia, e hoje ela reinicia a
    cada deploy, a tarefa em voo fica `processando` para sempre: não há varredura no boot, e `reprocess` recusa
    exatamente esse estado. O dono não reprocessa, não revisa, não aprova. O documento morre em silêncio, e a
    tela da pessoa diz "Estamos preparando a explicação" sem fim."""
    from core.db import recover_orphaned_tasks

    t = _tarefa_de_teste("orfa-do-reinicio")
    set_status(t.hash, "processando")

    recuperadas = recover_orphaned_tasks()
    assert recuperadas >= 1, "a varredura de boot não recuperou a tarefa presa"

    with Session(engine) as s:
        depois = s.exec(select(Tarefa).where(Tarefa.hash == t.hash)).one()
    assert depois.status == "falhou", f"continuou em {depois.status}, e o dono não tem como destravar"

    tipos = [e.get("tipo") for e in ws.read_events(t.hash)]
    assert "interrompida_por_reinicio" in tipos, f"nada no log conta o que aconteceu: {tipos}"


def test_the_sweep_does_not_touch_tasks_that_are_not_running():
    from core.db import recover_orphaned_tasks

    a = _tarefa_de_teste("nao-mexer-pronta"); set_status(a.hash, "pronta")
    b = _tarefa_de_teste("nao-mexer-enviada"); set_status(b.hash, "enviada")
    recover_orphaned_tasks()
    with Session(engine) as s:
        assert s.exec(select(Tarefa).where(Tarefa.hash == a.hash)).one().status == "pronta"
        assert s.exec(select(Tarefa).where(Tarefa.hash == b.hash)).one().status == "enviada"


def test_the_owner_can_retry_a_document_that_failed(lawyer):
    """A varredura de boot tira a tarefa de `processando`, mas ela fica `falhou` e o dono não tinha como
    refazer: a rota antiga é HTML de bastidor, responde 303 e o aplicativo não a chama. Sem isso, documento
    pego por um reinício morre na lista, e a pessoa precisa subir tudo de novo sem saber por quê."""
    t = create_task(lawyer["token"], "Refazer")
    fake_artifacts(t["hash"])
    set_status(t["hash"], "falhou")

    r = client.post(f"/api/tarefas/{t['id']}/reprocessar", headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    with Session(engine) as s:
        depois = s.exec(select(Tarefa).where(Tarefa.hash == t["hash"])).one()
    assert depois.status in ("criada", "processando", "falhou"), depois.status
    tipos = [e.get("tipo") for e in ws.read_events(t["hash"])]
    assert "reprocessar" in tipos, f"nada registra que foi refeito: {tipos}"


def test_only_the_owner_retries_and_never_while_it_runs(lawyer, citizen):
    t = create_task(lawyer["token"], "Refazer restrito")
    link_directly(t["hash"], citizen)
    set_status(t["hash"], "falhou")
    # 404 e não 403, de propósito: para quem não é dono, a rota não confirma nem que o documento existe.
    assert client.post(f"/api/tarefas/{t['id']}/reprocessar",
                       headers=bearer(citizen["token"])).status_code == 404, "quem só está vinculado refez"

    set_status(t["hash"], "processando")
    r = client.post(f"/api/tarefas/{t['id']}/reprocessar", headers=bearer(lawyer["token"]))
    assert r.status_code == 409, "refez por cima de um documento que está rodando"


# ── O carimbo público: a falha deixa rastro e o comprovante diz em que estado está ──

def _stamp_proof(digest_hex: str, height: int | None = None) -> bytes:
    """Prova .ots montada aqui, sem rede: promessa de calendário, ou já ancorada no bloco ``height``."""
    from opentimestamps.core.notary import BitcoinBlockHeaderAttestation, PendingAttestation
    from opentimestamps.core.op import OpSHA256
    from opentimestamps.core.serialize import BytesSerializationContext
    from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp

    stamp = Timestamp(bytes.fromhex(digest_hex))
    stamp.attestations.add(PendingAttestation("https://alice.btc.calendar.opentimestamps.org")
                           if height is None else BitcoinBlockHeaderAttestation(height))
    ctx = BytesSerializationContext()
    DetachedTimestampFile(OpSHA256(), stamp).serialize(ctx)
    return ctx.getbytes()


def _stamp_frozen_attempt(hash_: str):
    """Tentativa aprovada com o registro já congelado, que é o que o carimbo carimba."""
    import core.attempts as tn
    from leia.api_citizen import freeze_record, stored_record

    t = _tarefa_com_documento(hash_, small_pdf(f"Contrato {hash_}."), "# Explicação\n\nTexto simples.")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)
    freeze_record(t.hash, tent.numero, tent.hash_imutavel)
    return t, tent, stored_record(tent.hash_imutavel)["payload_sha256"]


def test_stamp_a_failure_is_written_down_with_the_reason_and_the_count(monkeypatch):
    """O carimbo que não sai não deixava rastro nenhum: só existia evento quando dava certo, então ninguém
    sabia se o comprovante estava sem prova porque os calendários caíram ou porque nunca foi tentado."""
    from leia import api_citizen as ac
    from leia.registry import StampOutcome

    t, tent, _ = _stamp_frozen_attempt("carimbo-falhou")
    monkeypatch.setattr(ac, "ots_stamp",
                        lambda digest: StampOutcome(None, "https://a.pool.opentimestamps.org: timed out", 8, 4))

    ac.stamp_attempt(t.hash, tent.numero, tent.hash_imutavel)

    falhas = [e for e in ws.read_events(t.hash) if e.get("tipo") == "carimbo_falhou"]
    assert falhas, "o carimbo falhou e o comprovante não registra nada disso"
    assert "timed out" in falhas[-1]["motivo"], f"o motivo da falha não chegou ao registro: {falhas[-1]}"
    assert falhas[-1]["tentativas"] == 8, "o registro não diz quantas submissões foram feitas"
    assert not ac._ots_path(t.hash, tent.numero).exists(), "gravou arquivo de prova sem prova nenhuma"
    assert "carimbo_falhou" in [e["tipo"] for e in ac.public_events(ws.read_events(t.hash))], \
        "a tela do cidadão não vê que o carimbo falhou"


def test_stamp_a_proof_that_comes_back_is_saved_and_announced(monkeypatch):
    """O caminho de sucesso grava o arquivo .ots e o evento; sem isso o /verify continua devolvendo 404."""
    from leia import api_citizen as ac
    from leia.registry import StampOutcome, ots_digest

    t, tent, digest = _stamp_frozen_attempt("carimbo-saiu")
    monkeypatch.setattr(ac, "ots_stamp", lambda d: StampOutcome(_stamp_proof(d), "", 2, 1))

    ac.stamp_attempt(t.hash, tent.numero, tent.hash_imutavel)

    caminho = ac._ots_path(t.hash, tent.numero)
    assert caminho.exists(), "o carimbo voltou e a prova não foi gravada"
    assert ots_digest(caminho.read_bytes()) == digest, "a prova gravada não fala do registro congelado"
    assert [e for e in ws.read_events(t.hash) if e.get("tipo") == "carimbo_publico"], "o sucesso não deixou rastro"


def test_stamp_the_receipt_says_which_of_the_three_states_it_is_in(monkeypatch):
    """`ausente`, `pendente` e `confirmado` (ADR-0010): a tela prometia "chega em alguns minutos" mesmo
    quando nada tinha sido carimbado, e não sabia dizer quando a promessa do calendário virou bloco."""
    from leia import api_citizen as ac
    from leia.registry import StampOutcome

    t, tent, digest = _stamp_frozen_attempt("carimbo-estados")
    caminho = ac._ots_path(t.hash, tent.numero)

    assert ac.get_attempt(tent.hash_imutavel)["ots_status"] == {
        "otsState": "ausente", "otsBlockHeight": None, "otsLastAttempt": None}

    caminho.write_bytes(_stamp_proof("f" * 64))
    assert ac.get_attempt(tent.hash_imutavel)["ots_status"]["otsState"] == "ausente", \
        "prova feita sobre outro registro contou como carimbo deste"

    monkeypatch.setattr(ac, "ots_stamp", lambda d: StampOutcome(_stamp_proof(d), "", 1, 1))
    ac.stamp_attempt(t.hash, tent.numero, tent.hash_imutavel)
    pendente = ac.get_attempt(tent.hash_imutavel)["ots_status"]
    assert pendente["otsState"] == "pendente" and pendente["otsBlockHeight"] is None
    assert pendente["otsLastAttempt"] and pendente["otsLastAttempt"].endswith("Z"), \
        f"a data da última tentativa não veio em UTC: {pendente['otsLastAttempt']!r}"

    caminho.write_bytes(_stamp_proof(digest, height=850123))
    confirmado = ac.get_attempt(tent.hash_imutavel)["ots_status"]
    assert confirmado["otsState"] == "confirmado" and confirmado["otsBlockHeight"] == 850123


def test_stamp_the_public_json_publishes_the_state_of_the_stamp(monkeypatch):
    """Quem audita parte só do link do comprovante: `otsPresent` dizia sim ou não e a tela preenchia o resto
    com uma promessa. O JSON público agora diz em que estado o carimbo está, quando foi tentado pela última
    vez e, quando confirmado, em que bloco."""
    from leia import api_citizen as ac
    from leia.registry import StampOutcome

    t, tent, digest = _stamp_frozen_attempt("carimbo-json")
    url = f"/verify/{tent.hash_imutavel}?format=json"

    ausente = client.get(url).json()
    assert ausente["otsPresent"] is False
    assert ausente["otsState"] == "ausente" and ausente["otsBlockHeight"] is None
    assert ausente["otsLastAttempt"] is None

    monkeypatch.setattr(ac, "ots_stamp", lambda d: StampOutcome(_stamp_proof(d), "", 1, 1))
    ac.stamp_attempt(t.hash, tent.numero, tent.hash_imutavel)
    pendente = client.get(url).json()
    assert pendente["otsPresent"] is True and pendente["otsState"] == "pendente"
    assert pendente["otsBlockHeight"] is None and pendente["otsLastAttempt"].endswith("Z")

    ac._ots_path(t.hash, tent.numero).write_bytes(_stamp_proof(digest, height=850124))
    confirmado = client.get(url).json()
    assert confirmado["otsState"] == "confirmado" and confirmado["otsBlockHeight"] == 850124
    assert client.get(f"/verify/{tent.hash_imutavel}/proof.ots").status_code == 200, \
        "o comprovante diz que tem carimbo e a prova não baixa"


# ── The protocol is the contract: the engine may only say what the document says ──

SYNTHESIS_TASKS = ("T7_SINTESE_FATOS", "T8_SINTESE_FUNDAMENTOS", "T9_SINTESE_PEDIDOS",
                   "T10_SINTESE_IDENTIFICACAO", "T11_SINTESE_CONTEXTO")
TERM_FIELDS = ["termo", "explicacao", "trecho", "lastro"]


def running_protocol() -> dict:
    """The protocol the pipeline actually loads, read the same way the pipeline reads it."""
    from core.pipeline_pdf import PROTOCOLO_PDF

    return json.loads(Path(PROTOCOLO_PDF).read_text(encoding="utf-8"))


def protocol_task(task_id: str) -> dict:
    task = {t["id"]: t for t in running_protocol()["tasks"]}.get(task_id)
    assert task, f"a etapa {task_id} sumiu do protocolo"
    return task


def published_catalog() -> tuple[Path, dict]:
    """The newest version in prompts/workflow: the prompt catalog the D3 audit is told to read.

    Newest by version number, not by name, so the historical v0 stays where it is instead of being rewritten.
    """
    import re as _re

    pasta = Path(__file__).resolve().parents[2] / "prompts" / "workflow"
    arquivos = [(int(m.group(1)), p) for p in pasta.glob("v*.json") if (m := _re.match(r"v(\d+)-", p.name))]
    assert arquivos, f"nenhum catálogo publicado em {pasta}"
    caminho = max(arquivos)[1]
    return caminho, json.loads(caminho.read_text(encoding="utf-8"))


def test_protocol_the_published_catalog_is_the_protocol_that_runs():
    """Prompt publicado que ninguém confere vira ficção: 6 dos 16 ids publicados não existiam no protocolo
    que roda, e 8 das 10 missões em comum eram outras. Quem audita a dimensão D3 lê a pasta publicada."""
    caminho, publicado = published_catalog()
    rodando = running_protocol()

    ids_publicados = [t["id"] for t in publicado.get("tasks", [])]
    ids_rodando = [t["id"] for t in rodando["tasks"]]
    assert ids_publicados == ids_rodando, (
        f"{caminho.name} publica etapas que não são as que rodam: "
        f"só publicadas {[i for i in ids_publicados if i not in ids_rodando]}, "
        f"só rodando {[i for i in ids_rodando if i not in ids_publicados]}")

    publicadas = {t["id"]: t for t in publicado["tasks"]}
    divergentes = [tid for tid, t in {t["id"]: t for t in rodando["tasks"]}.items()
                   if (publicadas[tid].get("missao") or "") != (t.get("missao") or "")]
    assert not divergentes, f"{caminho.name} publica outra missão para {divergentes}"
    assert publicado == rodando, (
        f"{caminho.name} e protocolo_pdf.json já não são o mesmo workflow: "
        "cp apps/llm-service/protocolo_pdf.json prompts/workflow/" + caminho.name)


def test_protocol_every_synthesis_ties_its_text_to_a_ground():
    """O contrato só pedia que a chave `lastro` existisse, e lista vazia passava: foi assim que uma síntese
    de fundamentos de 1293 caracteres, citando seis dispositivos, chegou à tela com `lastro: []`.

    A regra é o par, e não o campo isolado: exigir lastro mesmo na síntese vazia matava a tarefa inteira por
    uma seção que o documento legitimamente não tem, porque um contrato de honorários não tem pedidos e o T9
    trabalha só sobre eles."""
    for tid in SYNTHESIS_TASKS:
        campos = (protocol_task(tid).get("schema") or {}).get("campos") or {}
        assert campos, f"{tid} não declara contrato nenhum"
        for nome, regra in campos.items():
            assert regra.get("exige_par") == ["valor", "lastro"], \
                f"{tid} aceita {nome} com texto e lastro vazio: {regra}"


def test_protocol_the_summary_explains_the_document_instead_of_retelling_it_as_a_story():
    """A ordem de virar história simbólica é o que produziu "instância da Cidadania" no lugar de tribunal."""
    missao = protocol_task("T13_HUMANIZACAO")["missao"].lower()
    for ordem in ("contador de histórias", "história simbólica", "criança de 10 anos", "simbologia",
                  "personagens", "era uma vez", "analogia"):
        assert ordem not in missao, f"a missão do T13 ainda manda contar história: {ordem!r}"


def test_protocol_the_summary_keeps_the_numbers_that_change_the_persons_life():
    """Valor, data e prazo eram proibidos na explicação. São exatamente o que a pessoa precisa saber."""
    missao = protocol_task("T13_HUMANIZACAO")["missao"]
    linhas = [linha.lower() for linha in missao.splitlines() if "preserve" in linha.lower()]
    assert any(all(p in linha for p in ("valor", "data", "prazo")) for linha in linhas), \
        f"a missão do T13 não manda preservar valor, data e prazo: {linhas}"
    assert "proibido" not in missao.lower(), "a missão do T13 ainda proíbe o que o documento diz"


def test_protocol_the_summary_spells_a_number_out_beside_it_instead_of_replacing_it():
    """A missão manda copiar o número como ele está e escrever TAMBÉM por extenso. Os exemplos precisam fazer
    isso, senão ensinam o contrário da regra que ilustram.

    Importa porque o trecho literal do documento aparece ao lado da explicação. Quando a explicação escreve a
    data de um jeito e o documento de outro, sobra para a pessoa conferir de cabeça que são a mesma data, que
    é exatamente o trabalho que este produto existe para tirar dela."""
    import re

    missao = protocol_task("T13_HUMANIZACAO")["missao"]
    trocas = re.findall(r'"([^"]+)" vira "([^"]+)"', missao)
    assert trocas, "os exemplos da regra de preservar número sumiram da missão do T13"
    apagados = [(antes, depois) for antes, depois in trocas if antes not in depois]
    assert apagados == [], f"o exemplo apaga o número do documento em vez de explicá-lo ao lado: {apagados}"


def test_protocol_the_summary_returns_each_legal_term_with_its_definition_and_quote():
    """Termo jurídico deixa de ser proibido e passa a ser marcado: é o insumo do termo tocável da tela."""
    task = protocol_task("T13_HUMANIZACAO")
    assert task.get("tipo_saida") == "json", "o T13 ainda devolve só texto, sem lista de termos"

    campos = (task.get("schema") or {}).get("campos") or {}
    assert "resumo_humanizado" in campos, f"o T13 não declara o markdown da explicação: {list(campos)}"
    termos = campos.get("termos") or {}
    assert termos.get("tipo") == "lista", f"o T13 não declara a lista de termos: {termos}"
    assert list(termos.get("itens") or []) == TERM_FIELDS, \
        f"a lista de termos do T13 não traz {TERM_FIELDS}: {termos.get('itens')}"
    for chave in TERM_FIELDS:
        assert f'"{chave}"' in task["missao"], f"a missão do T13 não mostra o campo {chave} ao modelo"


def test_protocol_the_summary_keeps_the_headings_the_citizen_screen_anchors_to():
    """`section_sources()` liga cada seção da explicação às classes de memória pelo título. Título que muda
    sem o mapa mudar junto apaga o trecho literal ao lado da seção, e ninguém fica sabendo."""
    import re as _re

    from leia.api_citizen import _section_key

    task = protocol_task("T13_HUMANIZACAO")
    titulos = {_section_key(t) for t in _re.findall(r"^#{1,2} (.+)$", task["missao"], _re.M)}
    ancoras = {_section_key(k) for k in (task.get("ancoras_por_secao") or {})}
    assert titulos == ancoras, f"títulos da missão e mapa de âncoras não batem: {titulos ^ ancoras}"


def test_protocol_the_declared_summary_contract_refuses_a_term_without_its_quote():
    """O contrato do T13 vale rodando, não só escrito: a etapa cai quando um termo chega sem o trecho que o
    prova, em vez de mandar para a tela um termo que ninguém pode conferir no documento."""
    task = protocol_task("T13_HUMANIZACAO")
    markdown = "# Resumo em uma linha\n\nUm contrato de honorários."
    termo = {"termo": "honorários de sucumbência", "explicacao": "o que quem perde paga ao advogado de quem ganha",
             "trecho": "honorários de sucumbência de vinte por cento", "lastro": "fundamentos[0]"}

    bom = _rodar(task, json.dumps({"resumo_humanizado": markdown, "termos": [termo]}, ensure_ascii=False))
    assert bom["ok"] is True, bom.get("erro")
    assert bom["parsed"]["resumo_humanizado"] == markdown, "o markdown da explicação não sobreviveu ao contrato"

    sem_trecho = {k: v for k, v in termo.items() if k != "trecho"}
    ruim = _rodar(task, json.dumps({"resumo_humanizado": markdown, "termos": [sem_trecho]}, ensure_ascii=False))
    assert ruim["ok"] is False and "trecho" in str(ruim.get("erro", "")), ruim


# ── Porta de fidelidade: nada chega a "pronta" sem o documento sustentar ──────

GATE_MEMORY = {"memoria_persistente": {
    "identificacao": [{"campo": "partes", "valor": "duas", "trecho_verbatim": "O CONTRATANTE pagará honorários de vinte por cento"}],
    "pedidos": [{"campo": "condicao", "valor": "só se ganhar", "trecho_verbatim": "ao final, só se ganhar a ação"}],
}}
GATE_SUMMARY = ("# Resumo em uma linha\n\nVocê paga só se ganhar.\n\n"
                "## 👥 Quem está nesta história\n\nQuem contratou e quem foi contratada.\n\n"
                "## 🤝 O que está sendo pedido\n\nQue o combinado seja respeitado.\n")
GATE_SYNTHESES = {
    "T10_SINTESE_IDENTIFICACAO.json": {"sintese_identificacao": {"valor": "Duas pessoas assinaram.", "lastro": ["identificacao[0]"]}},
    "T9_SINTESE_PEDIDOS.json": {"sintese_pedidos": {"valor": "Paga só se ganhar.", "lastro": ["pedidos[0]"]}},
}


def stage_gate_artifacts(h: str, resumo: str = GATE_SUMMARY, memoria=None, sinteses=None) -> None:
    """Artefatos de uma rodada que terminou, do jeito que a porta de qualidade vai encontrá-los no disco."""
    pasta = ws.folder(h)
    (pasta / "texto_extraido.txt").write_text(FAKE_TEXT, encoding="utf-8")
    (pasta / "resumo_humanizado.md").write_text(resumo, encoding="utf-8")
    (pasta / "memoria_persistente.json").write_text(
        json.dumps(memoria if memoria is not None else GATE_MEMORY, ensure_ascii=False), encoding="utf-8")
    for nome, corpo in (GATE_SYNTHESES if sinteses is None else sinteses).items():
        (pasta / nome).write_text(json.dumps(corpo, ensure_ascii=False), encoding="utf-8")


def status_of(h: str) -> str:
    with Session(engine) as s:
        return s.exec(select(Tarefa).where(Tarefa.hash == h)).one().status


def last_event(h: str, tipo: str) -> dict:
    eventos = [e for e in ws.read_events(h) if e.get("tipo") == tipo]
    assert eventos, f"nenhum evento {tipo} no workspace de {h}"
    return eventos[-1]


def test_gate_a_synthesis_without_lastro_never_reaches_the_citizen(lawyer):
    """Medida em 17/09/2026 no único caso público: a síntese de fundamentos tem 1293 caracteres, cita seis
    dispositivos legais e chega com lastro que não aponta para nada do documento.

    Ela não chega à tela, e é isso que importa. Derrubar a tarefa inteira por causa dela seria punir a cidadã
    por uma seção que o documento dela legitimamente não tem: um contrato de honorários particular não cita
    lei nenhuma, e o protocolo pede fundamentos de todo PDF porque ninguém detecta o tipo do documento."""
    from core.pipeline_pdf import finish_pipeline

    t = create_task(lawyer["token"], "Síntese sem lastro")
    stage_gate_artifacts(t["hash"], sinteses={**GATE_SYNTHESES, "T8_SINTESE_FUNDAMENTOS.json": {
        "sintese_fundamentos": {"valor": SINTESE_SEM_LASTRO, "lastro": ["fundamentos[0]"]}}})

    assert finish_pipeline(t["id"], t["hash"], 1.0) == "pronta"
    evento = last_event(t["hash"], "porta_qualidade")
    assert evento["motivo"] is None, evento
    # Descartada, e o descarte fica escrito: é ele que o advogado revisa.
    assert any("undamentos" in s for s in evento["sinteses_sem_lastro"]), evento
    publicado = json.dumps(client.get(f"/api/t/{t['hash']}/inferencias").json(), ensure_ascii=False)
    assert SINTESE_SEM_LASTRO[:40] not in publicado, "a síntese sem lastro chegou à cidadã"


def test_gate_a_section_with_nothing_checked_never_reaches_the_citizen(lawyer):
    """A seção "O que aconteceu" explica os fatos, e nada na memória sustenta um fato. A landing promete
    trecho literal em toda explicação, então a seção sai da tela. O resto continua: a explicação perde um
    pedaço e o descarte fica registrado para o advogado, em vez de a pessoa ficar sem nada."""
    from core.pipeline_pdf import finish_pipeline

    t = create_task(lawyer["token"], "Seção sem trecho")
    stage_gate_artifacts(t["hash"], resumo=GATE_SUMMARY + "\n## 📖 O que aconteceu\n\nAs partes discutiram o pagamento.\n")

    assert finish_pipeline(t["id"], t["hash"], 1.0) == "pronta"
    evento = last_event(t["hash"], "porta_qualidade")
    assert evento["motivo"] is None, evento
    assert evento["secoes_sem_lastro"] == ["📖 O que aconteceu"], evento
    # A tarefa do advogado espera revisão, então a rota pública ainda não publica tópicos: a conferência é
    # feita pelo mesmo leitor que a tela usa quando ela for liberada.
    from app_gestao import _read_artifact, _read_json
    from leia.api_citizen import SYNTHESIS_FILES, topics_from_summary

    titulos = [x["titulo"] for x in topics_from_summary(
        _read_artifact(t["hash"], "resumo_humanizado.md") or "",
        _read_json(t["hash"], "memoria_persistente.json"),
        _read_artifact(t["hash"], "texto_extraido.txt") or "",
        [(cls, _read_json(t["hash"], nome)) for nome, cls in SYNTHESIS_FILES])]
    assert "📖 O que aconteceu" not in titulos, "seção sem nada conferido chegou à cidadã"


def test_gate_an_explanation_the_document_sustains_reaches_pronta(lawyer):
    """A porta não pode ser uma parede: explicação inteira conferida passa, e o número medido fica gravado
    também quando passa, senão ninguém consegue distinguir uma rodada aprovada de uma porta que não rodou."""
    from core.pipeline_pdf import finish_pipeline

    t = create_task(lawyer["token"], "Com lastro")
    stage_gate_artifacts(t["hash"])

    assert finish_pipeline(t["id"], t["hash"], 2.5) == "pronta"
    assert status_of(t["hash"]) == "pronta"
    evento = last_event(t["hash"], "porta_qualidade")
    assert evento["motivo"] is None and evento["cobertura_secao"] == 1.0 and evento["lastro_sintese"] == 1.0
    assert last_event(t["hash"], "pipeline_done")["elapsed"] == 2.5


def test_gate_the_task_that_fails_says_what_it_measured_where_the_panel_reads(lawyer):
    """Tarefa que falha calada é pior do que tarefa que pede ajuda: o motivo legível e os números medidos
    ficam no log da tarefa no banco, que é de onde o painel lê, e não só no arquivo do workspace."""
    from core.pipeline_pdf import finish_pipeline

    t = create_task(lawyer["token"], "Motivo legível")
    stage_gate_artifacts(t["hash"], memoria={"memoria_persistente": {"identificacao": [
        {"campo": "partes", "valor": "duas", "trecho_verbatim": "cláusula que não está neste contrato"}]}})

    assert finish_pipeline(t["id"], t["hash"], 1.0) == "falhou"
    with Session(engine) as s:
        registros = s.exec(select(LogEvento).where(LogEvento.tarefa_id == t["id"],
                                                   LogEvento.tipo == "porta_qualidade")).all()
    assert registros, "a porta reprovou e o painel não tem como saber por quê"
    payload = json.loads(registros[-1].payload)
    assert payload["motivo"] and "trecho" in payload["motivo"].lower(), payload
    assert payload["cobertura_secao"] == 0.0


def test_gate_the_hidden_text_count_is_recorded_right_after_the_text(lawyer):
    """O PDF hostil desenha texto que ninguém vê e o entrega ao modelo. O que foi descartado é contado, e a
    contagem é gravada sempre, inclusive zerada: evento que só aparece quando sobra algo não deixa distinguir
    documento limpo de extração que não olhou."""
    t = create_task(lawyer["token"], "PDF limpo")

    tipos = [e.get("tipo") for e in ws.read_events(t["hash"])]
    assert "texto_oculto_removido" in tipos, "ninguém registrou o que o PDF escondia"
    assert tipos[tipos.index("texto_extraido") + 1] == "texto_oculto_removido"
    ev = last_event(t["hash"], "texto_oculto_removido")
    assert (ev["caracteres"], ev["trechos"], ev["invisiveis"]) == (0, 0, 0), ev


def test_gate_the_hidden_text_that_was_dropped_is_counted_in_the_event(lawyer, monkeypatch):
    """A conta que a extração devolve precisa chegar inteira ao evento: é ela que prova, na auditoria, que o
    documento com texto escondido produziu a mesma explicação sem repetir uma palavra do que estava escondido."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction("texto visível do contrato", 120, 3, 7))
    t = create_task(lawyer["token"], "PDF hostil")
    # Loop próprio, fechado aqui: asyncio.run deixa a thread sem loop corrente e derruba quem, no resto da
    # bateria, chama asyncio.get_event_loop() depois deste teste.
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _FailingGroq()))
    finally:
        loop.close()

    ev = last_event(t["hash"], "texto_oculto_removido")
    assert (ev["caracteres"], ev["trechos"], ev["invisiveis"]) == (120, 3, 7), ev


def test_gate_a_synthesis_that_declares_an_empty_lastro_fails_the_step_contract():
    """O protocolo já declara `nao_vazios: ["lastro"]` nas cinco sínteses, e `obrigatorios` continua querendo
    dizer só "a chave existe". Sem a regra nova valendo no motor, a etapa entrega `lastro: []` e segue."""
    task = protocol_task("T8_SINTESE_FUNDAMENTOS")
    bom = _rodar(task, json.dumps({"sintese_fundamentos": {"valor": "O caso trata de honorários.",
                                                           "lastro": ["fundamentos[0]"]}}, ensure_ascii=False))
    assert bom["ok"] is True, bom.get("erro")

    vazio = _rodar(task, json.dumps({"sintese_fundamentos": {"valor": SINTESE_SEM_LASTRO, "lastro": []}}, ensure_ascii=False))
    assert vazio["ok"] is False, "síntese com lastro vazio passou pelo contrato da etapa"
    assert "lastro" in str(vazio.get("erro", "")), vazio.get("erro")


class _ScriptedCompletions:
    """Modelo de mentira que responde por etapa: a missão de cada uma chega no papel de sistema."""

    def __init__(self, por_nome: dict):
        self.por_nome = por_nome

    async def create(self, **kwargs):
        sistema = kwargs["messages"][0]["content"]
        texto = next((v for k, v in self.por_nome.items() if k in sistema), "{}")
        return await _FakeStream(texto).create(**kwargs)


def _scripted_groq(por_id: dict):
    tasks = {t["id"]: t for t in running_protocol()["tasks"]}
    por_nome = {tasks[tid].get("nome") or tid: json.dumps(corpo, ensure_ascii=False) for tid, corpo in por_id.items()}
    class _Groq:
        class chat:  # noqa: N801
            completions = _ScriptedCompletions(por_nome)
    return _Groq()


RUN_MEMORY = {"memoria_persistente": {
    "identificacao": [{"campo": "partes", "valor": "duas", "trecho_verbatim": "O CONTRATANTE pagará honorários de vinte por cento"}],
    "datas_valores": [{"campo": "honorarios", "valor": "20%", "trecho_verbatim": "vinte por cento ao final"}],
    "fatos": [{"campo": "combinado", "valor": "pagamento", "trecho_verbatim": "pagará honorários de vinte por cento"}],
    "fundamentos": [{"campo": "condicao", "valor": "êxito", "trecho_verbatim": "só se ganhar a ação"}],
    "pedidos": [{"campo": "pedido", "valor": "cumprir", "trecho_verbatim": "ao final, só se ganhar a ação"}],
}}
RUN_OUTPUTS = {
    "T6_FUSAO_MEMORIA": RUN_MEMORY,
    "T7_SINTESE_FATOS": {"sintese_fatos": {"valor": "As partes combinaram o pagamento.", "lastro": ["fatos[0]"]}},
    "T8_SINTESE_FUNDAMENTOS": {"sintese_fundamentos": {"valor": "O pagamento depende do êxito.", "lastro": ["fundamentos[0]"]}},
    "T9_SINTESE_PEDIDOS": {"sintese_pedidos": {"valor": "Pede que o combinado valha.", "lastro": ["pedidos[0]"]}},
    "T10_SINTESE_IDENTIFICACAO": {"sintese_identificacao": {"valor": "Duas pessoas assinaram.", "lastro": ["identificacao[0]"]}},
    "T11_SINTESE_CONTEXTO": {"sintese_contexto": {"valor": "O contrato está em vigor.", "lastro": ["fatos[0]"]}},
    "T13_HUMANIZACAO": {"resumo_humanizado": GATE_SUMMARY, "termos": []},
    # Quatro perguntas, que é o piso: abaixo dele o motor publica zero e a jornada termina sem comprovante,
    # e uma rodada completa que não exercita a conferência não prova que ela existe.
    "T14_QUESTOES": {"questoes": [
        {"id": 1, "area": "pedidos", "enunciado": "Quando você paga?", "alternativas": ["Sempre", "Só se ganhar"],
         "correta": 1, "justificativa": "Está na cláusula 2.", "dificuldade": "facil",
         "secao": "🤝 O que está sendo pedido", "ref": "pedidos[0]", "trecho_verbatim": "só se ganhar a ação"},
        {"id": 2, "area": "datas_valores", "enunciado": "Quanto são os honorários?",
         "alternativas": ["Vinte por cento", "Metade"], "correta": 0, "justificativa": "Cláusula 2.",
         "dificuldade": "facil", "secao": "🤝 O que está sendo pedido", "ref": "datas_valores[0]",
         "trecho_verbatim": "vinte por cento ao final"},
        {"id": 3, "area": "identificacao", "enunciado": "Quem paga?", "alternativas": ["O CONTRATANTE", "O juiz"],
         "correta": 0, "justificativa": "Cláusula 2.", "dificuldade": "facil",
         "secao": "👥 Quem está nesta história", "ref": "identificacao[0]",
         "trecho_verbatim": "O CONTRATANTE pagará honorários"},
        {"id": 4, "area": "fatos", "enunciado": "Onde isso está escrito?",
         "alternativas": ["Na cláusula 2", "Em lugar nenhum"], "correta": 0, "justificativa": "Cláusula 2.",
         "dificuldade": "facil", "secao": "👥 Quem está nesta história", "ref": "fatos[0]",
         "trecho_verbatim": "CLÁUSULA 2. O CONTRATANTE"}]},
}


def test_gate_a_full_run_the_document_sustains_ends_in_pronta_for_the_citizen(citizen, monkeypatch):
    """A rodada inteira, do texto extraído à explicação publicada, sem nenhuma etapa de mentira além do
    modelo. É o que prova que a porta deixa passar o caso bom e que o passo 6 continua inteiro depois dela,
    inclusive para a tarefa da cidadã, que não tem advogado nenhum entre a porta e a tela."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    t = create_task(citizen["token"], "Rodada completa")
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _scripted_groq(RUN_OUTPUTS)))
    finally:
        loop.close()

    assert status_of(t["hash"]) == "pronta", ws.read_events(t["hash"])[-3:]
    assert last_event(t["hash"], "porta_qualidade")["motivo"] is None
    assert last_event(t["hash"], "pipeline_done")["elapsed"] >= 0

    data = client.get(f"/api/t/{t['hash']}").json()
    assert data["tarefa"]["status"] == "pronta"
    assert [topico["titulo"] for topico in data["topicos"]] == \
        ["Resumo em uma linha", "👥 Quem está nesta história", "🤝 O que está sendo pedido"]
    assert all(topico.get("trecho") in FAKE_TEXT for topico in data["topicos"] if topico["id"] > 1)


def test_gate_a_full_run_drops_the_synthesis_without_ground_and_publishes_the_rest(citizen, monkeypatch):
    """Mesma rodada, com a síntese de fundamentos escrevendo o que ninguém acha no documento. Sem a porta a
    tarefa ia para "pronta", e "pronta" é a tela da cidadã."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    t = create_task(citizen["token"], "Rodada sem lastro")
    saidas = {**RUN_OUTPUTS, "T8_SINTESE_FUNDAMENTOS": {
        "sintese_fundamentos": {"valor": SINTESE_SEM_LASTRO, "lastro": ["fundamentos[3]"]}}}
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _scripted_groq(saidas)))
    finally:
        loop.close()

    # A síntese sem lastro é descartada e o resto da explicação continua: derrubar a rodada inteira por ela
    # seria punir a cidadã por uma seção que o documento dela não sustenta.
    assert status_of(t["hash"]) == "pronta"
    publicado = client.get(f"/api/t/{t['hash']}").json()
    assert publicado["resumo_md"], "a explicação inteira sumiu por causa de uma síntese"
    assert SINTESE_SEM_LASTRO[:40] not in json.dumps(publicado, ensure_ascii=False)


# ── O orçamento de tokens precisa sobrar para a resposta ──────────────────────

def test_the_step_sends_the_reasoning_effort_the_protocol_declares():
    """O protocolo declara reasoning_effort por tarefa e o pipeline nunca enviava esse parâmetro, então o
    modelo de raciocínio decidia sozinho quanto pensar. Declaração que não é enviada é decoração."""
    import inspect
    from core import pipeline_pdf

    fonte = inspect.getsource(pipeline_pdf._run_task)
    assert "reasoning_effort" in fonte, "a etapa não envia o esforço de raciocínio que o protocolo declara"


def test_the_token_budget_leaves_room_for_the_answer():
    """gpt-oss-120b gasta tokens pensando antes de responder. Medido em 17/09/2026 com o contrato de
    exemplo: com teto de 8000 o modelo terminava em finish_reason "length" e conteúdo vazio em 5 de 6
    chamadas, e a tarefa inteira morria. Com 16000 não falhou nenhuma vez."""
    from core import pipeline_pdf

    assert pipeline_pdf.PIPELINE_MAX_TOKENS >= 16000, (
        f"teto de {pipeline_pdf.PIPELINE_MAX_TOKENS} tokens: o raciocínio consome tudo e não sobra resposta"
    )


def test_an_empty_synthesis_is_allowed_but_a_written_one_without_ground_is_not():
    """A regra que interessa é o par, não o campo isolado. Um contrato de honorários não tem pedidos, e o
    T9 manda trabalhar apenas sobre memoria_persistente.pedidos: exigir lastro sempre mataria a tarefa
    inteira por uma seção que o documento legitimamente não tem. O defeito real era texto sem lastro."""
    from core.pipeline_pdf import _schema_problem

    schema = {"campos": {"sintese_pedidos": {"tipo": "objeto",
                                             "obrigatorios": ["valor", "lastro"],
                                             "exige_par": ["valor", "lastro"]}}}

    vazia = {"sintese_pedidos": {"valor": "", "lastro": []}}
    assert _schema_problem(schema, vazia) is None, "a seção que o documento não tem foi tratada como erro"

    escrita = {"sintese_pedidos": {"valor": "A parte pede a condenação ao pagamento.", "lastro": []}}
    assert _schema_problem(schema, escrita), "texto sem lastro passou, que é o defeito que a porta existe para pegar"


def test_gate_does_not_fail_over_a_section_the_document_does_not_have(tmp_path, monkeypatch):
    """Um contrato de honorários particular não tem pedidos nem cita lei, e o protocolo pede as duas seções
    de todo PDF porque não existe detecção de tipo. Medido em 17/09/2026 com o contrato de exemplo: a porta
    reprovava por "O que está sendo pedido" e "Fundamentos", seções que a cidadã nunca veria porque o passo
    anterior já as descarta. Porta que reprova pelo que ninguém publica mede o protocolo, não a explicação."""
    from core import pipeline_pdf

    relatorio = {"cobertura_secao": 0.5, "lastro_sintese": 0.6,
                 "secoes_publicadas": 3, "secoes_com_trecho": 3,
                 "secoes_sem_lastro": ["🤝 O que está sendo pedido"],
                 "sinteses_publicadas": 3, "sinteses_sem_lastro": ["fundamentos"],
                 "resumo_vazio": False}
    assert pipeline_pdf.gate_reason(relatorio) is None, (
        "a porta barrou uma explicação em que tudo o que vai à tela está ancorado"
    )


def test_gate_still_fails_when_a_published_section_has_no_quote(tmp_path, monkeypatch):
    """O que a porta existe para pegar: chegar à tela alguma coisa que ninguém consegue apontar no documento."""
    from core import pipeline_pdf

    nada_ancorado = {"cobertura_secao": 0.0, "lastro_sintese": 1.0,
                     "secoes_publicadas": 4, "secoes_com_trecho": 0,
                     "secoes_sem_lastro": [], "sinteses_publicadas": 2,
                     "sinteses_sem_lastro": [], "resumo_vazio": False}
    assert pipeline_pdf.gate_reason(nada_ancorado), "explicação sem nenhum trecho do documento passou"

    sem_resumo = dict(nada_ancorado, resumo_vazio=True, secoes_com_trecho=3, cobertura_secao=1.0)
    assert pipeline_pdf.gate_reason(sem_resumo), "explicação que não foi produzida passou"

    nada_sobrou = dict(nada_ancorado, secoes_publicadas=0, secoes_com_trecho=0)
    assert pipeline_pdf.gate_reason(nada_sobrou), "explicação sem nenhuma seção passou"


# ── O trecho mostrado é fatia do documento, nunca a transcrição do modelo ─────

def test_the_quote_shown_is_the_slice_of_the_document_at_that_position():
    """Medido em 18/09/2026 num agravo real de 14 páginas: 42 de 60 âncoras não eram literais.

    A extração do PDF quebra palavra ("compa nhia", "fls.\\n52/68"), o modelo normaliza ao transcrever, e o
    `locate` acha assim mesmo pelo estágio normalizado. Só que o item saía com a posição do documento e o
    texto do modelo, então `documento[pos]` não era `trecho`. Num caso o modelo trocou 52/68 por 52/66: a
    pessoa procura no papel dela um trecho que não está lá, e o selo de conferido diz que está.

    A posição continua vindo do `locate` e nunca do modelo. O que muda é que o trecho passa a vir junto
    dela, do documento."""
    from leia.api_citizen import _item
    from core.anchors import norm_map

    documento = "A CONTRATADA prestará serviços, conforme parecer da compa nhia ambiental de 17.11.2014."
    text_norm, idx = norm_map(documento)
    item = _item("fatos", 0, {"campo": "x", "valor": "y",
                              "trecho_verbatim": "parecer da companhia ambiental de 17.11.2014"},
                 documento, text_norm, idx, "#000")

    assert item["conferido"], "o locate deixou de achar o trecho que ele achava antes"
    a, b = item["pos"]
    assert documento[a:b] == item["trecho"], (
        f"o trecho publicado não é o que está no documento naquela posição:\n"
        f"  publicado : {item['trecho']!r}\n"
        f"  documento : {documento[a:b]!r}"
    )
    assert "compa nhia" in item["trecho"], "o trecho foi limpo, então deixou de ser o que a pessoa vê no papel"


# ── O tipo do documento é lido antes, e é ele que escolhe o vocabulário ──────
#
# Medido em 20/09/2026 nos dois casos gravados. O protocolo faz as mesmas catorze perguntas a qualquer
# documento, e cinco delas têm vocabulário fechado de processo judicial. No contrato de honorários o
# `campo` do enum de T1 saiu como `autor` para o CONTRATANTE, e é `campo` que o aplicativo mostra em
# negrito sobre o texto marcado: a pessoa lê "autor: CONTRATANTE" num documento que não tem autor.

CONTRATO_TEXT = ("CONTRATO DE HONORÁRIOS ADVOCATÍCIOS. O CONTRATANTE, João da Silva, e a CONTRATADA, "
                 "Maria Souza, ajustam vinte por cento sobre o proveito econômico da causa.")
T0_QUOTE = "CLÁUSULA 2. O CONTRATANTE"   # trecho literal de FAKE_TEXT, para a classificação ter lastro


def test_the_document_type_is_a_claim_about_the_document_and_carries_its_quote():
    """O tipo é uma afirmação sobre o documento, então obedece à mesma regra de todas as outras: quem acha a
    posição é o `locate`, e o trecho publicado é a fatia do documento naquela posição."""
    from core import document_type as dt
    from core.anchors import norm_map

    text_norm, idx = norm_map(CONTRATO_TEXT)
    lido = dt.read({"tipo": "contrato", "trecho_verbatim": "CONTRATO DE HONORÁRIOS ADVOCATÍCIOS"},
                   CONTRATO_TEXT, text_norm, idx)

    assert lido["tipo"] == "contrato"
    assert lido["conferido"] is True, "o trecho que sustenta a classificação não foi achado no documento"
    a, b = lido["pos"]
    assert CONTRATO_TEXT[a:b] == lido["trecho"], "o trecho do tipo não é a fatia do documento naquela posição"
    assert lido["rotulo"], "o tipo não tem rótulo para a tela"


def test_a_type_outside_the_closed_set_never_travels():
    """O modelo pode escrever qualquer palavra no campo `tipo`, e o que viaja daqui escolhe o vocabulário das
    cinco extrações. Tipo que não está no protocolo vira `indefinido`, que é o vocabulário de hoje."""
    from core import document_type as dt
    from core.anchors import norm_map

    text_norm, idx = norm_map(CONTRATO_TEXT)
    for inventado in ({"tipo": "peticao_de_divorcio"}, {"tipo": ""}, {}, None, "contrato"):
        lido = dt.read(inventado, CONTRATO_TEXT, text_norm, idx)
        assert lido["tipo"] == dt.INDEFINIDO, f"{inventado!r} passou como tipo válido"


def test_the_vocabulary_that_reaches_the_model_is_the_one_of_the_type():
    """Um contrato não tem autor nem réu, tem contratante e contratada. Enquanto o enum é um só, o modelo é
    obrigado a escolher a caixa errada, porque a palavra certa não está na lista que ele recebeu."""
    from core import document_type as dt
    from core.pipeline_pdf import _build_prompt

    t1 = protocol_task("T1_IDENTIFICADOR_PARTES")
    protocolo = running_protocol()

    contrato = _build_prompt(t1, "texto", dt.vocabulary(t1, "contrato", protocolo))[0]["content"]
    assert "contratante" in contrato.lower(), "o vocabulário do contrato não oferece contratante"
    assert "ENUM[autor" not in contrato, "o contrato continua recebendo o enum de processo judicial"

    peca = _build_prompt(t1, "texto", dt.vocabulary(t1, "peca_processual", protocolo))[0]["content"]
    assert "ENUM[autor" in peca, "a peça processual perdeu o vocabulário que ela sempre teve"

    indefinido = _build_prompt(t1, "texto", dt.vocabulary(t1, dt.INDEFINIDO, protocolo))[0]["content"]
    assert "ENUM[autor" in indefinido, "sem tipo reconhecido o vocabulário tem que ser o de hoje"


def test_no_prompt_ever_leaves_with_an_unfilled_placeholder():
    """A substituição é invisível quando dá certo e é texto literal na cara do modelo quando falha."""
    from core import document_type as dt
    from core.pipeline_pdf import MARCADOR_VOCABULARIO, _build_prompt

    protocolo = running_protocol()
    tipos = [dt.INDEFINIDO, *dt.tipos(protocolo)]
    for task in protocolo["tasks"]:
        if not task.get("missao"):
            continue
        for tipo in tipos:
            sistema = _build_prompt(task, "texto", dt.vocabulary(task, tipo, protocolo))[0]["content"]
            assert MARCADOR_VOCABULARIO not in sistema, f"{task['id']} com tipo {tipo} levou marcador cru"


def test_a_classification_that_fails_does_not_take_the_document_down_with_it(citizen, monkeypatch):
    """Antes de existir classificação o documento era explicado. Uma etapa nova que pode matar a rodada é
    regressão para quem só quer entender o próprio papel: sem tipo reconhecido, o vocabulário é o de hoje."""
    import asyncio

    from core import document_type as dt
    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    # Os dois jeitos de a etapa não entregar: a espécie inventada, que passa pelo contrato e não existe, e a
    # saída fora do contrato, que nem chega a ser lida. Os dois terminam igual, e é esse o ponto.
    for titulo, saida in (("Espécie inventada", {"tipo": "isto não é um tipo", "trecho_verbatim": T0_QUOTE}),
                          ("Saída fora do contrato", {"nada": "aqui"})):
        t = create_task(citizen["token"], titulo)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(
                t["id"], _scripted_groq({**RUN_OUTPUTS, "T0_TIPO_DOCUMENTO": saida})))
        finally:
            loop.close()

        assert status_of(t["hash"]) == "pronta", (titulo, ws.read_events(t["hash"])[-3:])
        assert last_event(t["hash"], "tipo_documento")["especie"] == dt.INDEFINIDO, titulo


def test_the_lawyers_correction_replaces_the_classification_and_survives_reprocessing(lawyer, monkeypatch):
    """Classificação errada que a pessoa vê e conserta é barata; a que ninguém vê é a falha silenciosa que o
    produto inteiro existe para não ter. Corrigir só vale se a correção mandar na próxima rodada, e se
    sobreviver ao `reprocessar`, que apaga os arquivos das etapas."""
    import asyncio

    from core import document_type as dt
    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    t = create_task(lawyer["token"], "Tipo corrigido")
    r = client.post(f"/api/tarefas/{t['id']}/tipo-documento", json={"tipo": "contrato"}, headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text

    vistos: list[str] = []
    scripted = _scripted_groq({**RUN_OUTPUTS, "T0_TIPO_DOCUMENTO": {
        # Uma classificação que dá certo, e não uma que falha: vencer o silêncio da máquina não prova nada.
        "tipo": "peca_processual", "trecho_verbatim": T0_QUOTE}})
    original = scripted.chat.completions.create

    async def espiao(**kwargs):
        vistos.append(kwargs["messages"][0]["content"])
        return await original(**kwargs)

    scripted.chat.completions.create = espiao
    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], scripted))
    finally:
        loop.close()

    assert dt.saved(t["hash"])["tipo"] == "contrato", "a correção do advogado não sobreviveu à rodada"
    assert last_event(t["hash"], "tipo_documento")["especie"] == "contrato", "a máquina passou por cima do humano"
    partes = next((s for s in vistos if "Identificador de Partes" in s), "")
    assert "contratante" in partes.lower(), "a correção não chegou ao vocabulário da extração"


def test_only_who_sent_the_document_can_correct_its_type(lawyer, citizen):
    t = create_task(lawyer["token"], "Tipo alheio")
    # O controle positivo vem primeiro de propósito: sem ele, uma rota que nem existe faz o teste de recusa
    # passar com 404 e a proteção some sem ninguém notar.
    dono = client.post(f"/api/tarefas/{t['id']}/tipo-documento", json={"tipo": "contrato"},
                       headers=bearer(lawyer["token"]))
    assert dono.status_code == 200, dono.text

    alheio = client.post(f"/api/tarefas/{t['id']}/tipo-documento", json={"tipo": "peca_processual"},
                         headers=bearer(citizen["token"]))
    assert alheio.status_code in (403, 404), alheio.text
    from core import document_type as dt_

    assert dt_.saved(t["hash"])["tipo"] == "contrato", "a recusa não impediu a gravação"

    invalido = client.post(f"/api/tarefas/{t['id']}/tipo-documento", json={"tipo": "qualquer coisa"},
                           headers=bearer(lawyer["token"]))
    assert invalido.status_code == 422, invalido.text


def test_a_class_the_type_does_not_have_is_not_missing_from_the_explanation():
    """`pedidos: 0` e `fundamentos: 0` num contrato de honorários estão certos, e hoje são indistinguíveis de
    classe vazia por falha do motor. Quem lê o relatório precisa ver a diferença; a porta continua julgando
    só o que chega à tela, e não o que o protocolo pediu."""
    from core import document_type as dt

    assert "pedidos" not in dt.expected_classes("contrato"), "contrato não tem pedido processual"
    assert "pedidos" in dt.expected_classes("peca_processual"), "peça processual sem pedidos é peça incompleta"
    assert dt.expected_classes(dt.INDEFINIDO) == [], "sem tipo reconhecido não dá para cobrar classe nenhuma"

    ausentes = dt.missing_classes("contrato", presentes=["identificacao", "datas_valores"])
    assert "pedidos" not in ausentes and "fatos" in ausentes, ausentes


# ── A pergunta nasce presa a uma cláusula, com trecho literal ─────────────────
#
# O T14 gerava pergunta sobre "a HISTÓRIA" e sobre a "SIMBOLOGIA" dela, e o T13 parou de contar história em
# 19/09. Sobrou uma conferência que mede uma narrativa que o motor não produz mais, e um comprovante que diz
# "você entendeu o documento" a partir dela.

QUESTION_SECTION = "👥 Quem está nesta história"


def _questoes_de(hash_: str) -> list[dict]:
    import json as _json
    from core.workspace import folder
    return _json.loads((folder(hash_) / "questoes.json").read_text(encoding="utf-8")).get("questoes") or []


def test_a_question_must_declare_the_section_and_the_clause_it_came_from():
    """Sem isso a pergunta não tem como ser conferida contra o documento, e a bateria não tem o que medir."""
    task = protocol_task("T14_QUESTOES")
    completa = {"questoes": [{"enunciado": "Quanto você paga?", "alternativas": ["20%", "nada"], "correta": 0,
                              "secao": QUESTION_SECTION, "ref": "pedidos[0]",
                              "trecho_verbatim": "O CONTRATANTE pagará honorários de vinte por cento"}]}
    assert _rodar(task, json.dumps(completa, ensure_ascii=False))["ok"] is True

    for falta in ("secao", "ref", "trecho_verbatim"):
        crua = json.loads(json.dumps(completa))
        del crua["questoes"][0][falta]
        res = _rodar(task, json.dumps(crua, ensure_ascii=False))
        assert res["ok"] is False, f"pergunta sem {falta} passou pelo contrato da etapa"
        assert falta in str(res.get("erro", "")), res.get("erro")


def test_the_quote_beside_a_question_is_the_slice_of_the_document_at_that_position(citizen, monkeypatch):
    """Mesma regra da #88, agora na pergunta: o trecho publicado é a fatia do documento, nunca a transcrição
    do modelo. E a pergunta cujo trecho ninguém acha no documento não chega à cidadã."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    t = create_task(citizen["token"], "Perguntas ancoradas")
    saidas = {**RUN_OUTPUTS, "T14_QUESTOES": {"questoes": [
        {"id": i, "area": "pedidos", "dificuldade": "facil", "enunciado": f"Pergunta {i}?",
         "alternativas": ["Sim", "Não"], "correta": 0, "justificativa": "Está na cláusula 2.",
         "secao": QUESTION_SECTION, "ref": "pedidos[0]", "trecho_verbatim": trecho}
        for i, trecho in enumerate([
            "O CONTRATANTE pagará honorarios de vinte por cento",   # sem acento: o locate acha assim mesmo
            "pagará honorários de vinte por cento ao final",
            "só se ganhar a ação",
            "ao final, só se ganhar a ação",
            "CLÁUSULA 2. O CONTRATANTE pagará",
            "esta frase não está no documento de jeito nenhum",     # esta tem que cair
        ], start=1)]}}
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _scripted_groq(saidas)))
    finally:
        loop.close()

    assert status_of(t["hash"]) == "pronta", ws.read_events(t["hash"])[-3:]
    guardadas = _questoes_de(t["hash"])
    assert len(guardadas) == 5, f"a pergunta sem lastro no documento não foi descartada: {len(guardadas)}"
    for q in guardadas:
        a, b = q["pos"]
        assert FAKE_TEXT[a:b] == q["trecho"], (
            f"o trecho da pergunta não é o que está no documento naquela posição:\n"
            f"  publicado : {q['trecho']!r}\n  documento : {FAKE_TEXT[a:b]!r}")
    ev = last_event(t["hash"], "questoes_ancoradas")
    assert (ev["geradas"], ev["mantidas"]) == (6, 5), ev


def test_too_few_anchored_questions_means_no_conference_instead_of_a_weak_one(citizen, monkeypatch):
    """Duas perguntas de quatro alternativas passam por chute em 6,25% das vezes, e três tentativas levam isso
    a 17,6%. Um comprovante apoiado nisso afirma mais do que mediu. Abaixo do piso o produto já sabe terminar
    sem conferência e sem comprovante (`sem_perguntas`), e é o que ele faz."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    t = create_task(citizen["token"], "Perguntas de menos")
    saidas = {**RUN_OUTPUTS, "T14_QUESTOES": {"questoes": [
        {"id": 1, "area": "pedidos", "dificuldade": "facil", "enunciado": "Vale?", "alternativas": ["Sim", "Não"],
         "correta": 0, "justificativa": "x", "secao": QUESTION_SECTION, "ref": "pedidos[0]",
         "trecho_verbatim": "só se ganhar a ação"},
        {"id": 2, "area": "pedidos", "dificuldade": "facil", "enunciado": "Invenção?", "alternativas": ["Sim", "Não"],
         "correta": 0, "justificativa": "x", "secao": QUESTION_SECTION, "ref": "pedidos[0]",
         "trecho_verbatim": "isto não existe no documento"}]}}
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _scripted_groq(saidas)))
    finally:
        loop.close()

    assert status_of(t["hash"]) == "pronta", "a explicação foi derrubada por causa da conferência"
    assert _questoes_de(t["hash"]) == [], "sobrou conferência fraca em vez de nenhuma"
    publicado = client.get(f"/api/t/{t['hash']}").json()
    assert publicado["resumo_md"], "a explicação sumiu junto com as perguntas"
    assert publicado["sem_perguntas"] is True and publicado["questoes"] == []
    assert last_event(t["hash"], "questoes_ancoradas")["abaixo_do_piso"] is True


def test_the_public_question_carries_the_section_and_the_quote_but_never_the_key():
    """`secao` e `trecho` são o que fazem a pessoa poder voltar ao ponto do documento. `correta` e
    `justificativa` continuam do lado de cá."""
    from leia.api_citizen import _public_questions

    doc = {"questoes": [{"id": 1, "enunciado": "Quanto?", "alternativas": ["20%", "nada"], "area": "pedidos",
                         "correta": 0, "justificativa": "Está na cláusula 2.", "secao": QUESTION_SECTION,
                         "ref": "pedidos[0]", "trecho": "vinte por cento", "pos": [10, 25],
                         "conferencia": {"metodo": "exato", "score": 1.0}}]}
    saiu = _public_questions(doc)[0]
    assert saiu["secao"] == QUESTION_SECTION and saiu["trecho"] == "vinte por cento"
    assert saiu["conferencia"] == {"metodo": "exato", "score": 1.0}
    for gabarito in ("correta", "justificativa"):
        assert gabarito not in saiu, f"o gabarito viajou junto: {gabarito}"


# ── A consulta entra no registro, e o comprovante diz o que mediu (E12-T09/T10) ──

def test_the_attempt_hash_stays_recomputable_for_what_was_already_recorded():
    """Nenhuma tentativa já gravada pode mudar de hash: o hash é o identificador público do comprovante, e
    mudá-lo transforma comprovante emitido em link quebrado. Quem não tem consulta continua em v2."""
    from datetime import datetime as _dt

    from core.attempts import attempt_hash

    quando = _dt(2026, 9, 20, 12, 0, 0)
    antigo = attempt_hash("abc123", 1, '{"1": 0}', quando)
    assert attempt_hash("abc123", 1, '{"1": 0}', quando, consultas=None) == antigo, \
        "tentativa sem consulta mudou de hash"
    assert attempt_hash("abc123", 1, '{"1": 0}', quando, consultas={}) != antigo, \
        "a consulta entrou no registro e não mudou o hash, então ela não está sendo provada"
    assert attempt_hash("abc123", 1, '{"1": 0}', quando, consultas={"1": 2}) != \
        attempt_hash("abc123", 1, '{"1": 0}', quando, consultas={"1": 3}), \
        "duas consultas diferentes produziram o mesmo hash"


def test_the_receipt_says_it_measured_multiple_choice_anchored_in_a_clause():
    """`understood: true` sozinho é afirmação forte demais para o que uma múltipla escolha mede. O terceiro
    que recebe o comprovante precisa da régua: qual instrumento, qual piso, e quantas vezes a pessoa pediu
    para rever o trecho antes de responder."""
    from datetime import datetime as _dt, timezone as _tz

    from leia.registry import PAYLOAD_SCHEMA, build_payload

    payload = build_payload({"tarefa_hash": "abc", "numero": 1, "hash_imutavel": "h", "aprovado": True,
                             "total": 6, "piso": 5, "criada_em": _dt(2026, 9, 20, tzinfo=_tz.utc),
                             "consultas": {"1": 2, "3": 1}})
    assert payload["schema"] == PAYLOAD_SCHEMA and PAYLOAD_SCHEMA.endswith("v4")
    assert "clause" in payload["instrument"], payload["instrument"]
    assert payload["consulted"] == 3, "o comprovante não diz quantas vezes a pessoa precisou rever"
    assert build_payload({"tarefa_hash": "a", "numero": 1, "criada_em": "x"})["consulted"] == 0


# ── O advogado edita a explicação e escolhe o que vai ser perguntado (E12-T05) ──

def _rodada_pronta(token: str, titulo: str, monkeypatch) -> dict:
    """Uma rodada completa de verdade, para a revisão ter o que revisar."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    t = create_task(token, titulo)
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _scripted_groq(RUN_OUTPUTS)))
    finally:
        loop.close()
    assert status_of(t["hash"]) == "pronta", ws.read_events(t["hash"])[-3:]
    return t


def test_the_lawyer_keeps_a_subset_of_the_questions_and_the_citizen_gets_exactly_that(lawyer, monkeypatch):
    """Metade da tese do produto é a supervisão humana, e até aqui ela só podia aprovar ou não aprovar. Quem
    responde por aquele documento precisa poder tirar a pergunta que não serve, sem refazer a rodada."""
    t = _rodada_pronta(lawyer["token"], "Revisão salva", monkeypatch)
    antes = _questoes_de(t["hash"])
    assert len(antes) == 4

    mantidas = [q["id"] for q in antes[:3]] + [antes[3]["id"]]
    r = client.post(f"/api/tarefas/{t['id']}/revisao",
                    json={"resumo_md": "# Resumo em uma linha\n\nTexto que o advogado escreveu.",
                          "questoes": mantidas[:4]},
                    headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text

    from app_gestao import _read_artifact
    assert "Texto que o advogado escreveu." in (_read_artifact(t["hash"], "resumo_humanizado.md") or "")
    assert [q["id"] for q in _questoes_de(t["hash"])] == mantidas[:4]
    assert last_event(t["hash"], "revisao_salva")["questoes"] == 4


def test_the_lawyer_cannot_leave_a_conference_below_the_floor(lawyer, monkeypatch):
    """O mesmo piso que vale para o motor vale para a pessoa: conferência fraca faz o comprovante afirmar
    mais do que mediu, e de onde veio o corte não muda isso. Zero continua valendo, porque zero é a decisão
    explícita de não conferir, e o produto já sabe terminar assim."""
    t = _rodada_pronta(lawyer["token"], "Revisão curta", monkeypatch)
    ids = [q["id"] for q in _questoes_de(t["hash"])]

    curta = client.post(f"/api/tarefas/{t['id']}/revisao", json={"questoes": ids[:2]},
                        headers=bearer(lawyer["token"]))
    assert curta.status_code == 422, curta.text
    assert len(_questoes_de(t["hash"])) == 4, "a recusa não impediu a gravação"

    nenhuma = client.post(f"/api/tarefas/{t['id']}/revisao", json={"questoes": []}, headers=bearer(lawyer["token"]))
    assert nenhuma.status_code == 200, nenhuma.text
    assert _questoes_de(t["hash"]) == []
    # Documento de advogado só chega à cidadã depois de liberado, então a tela dela se olha depois disso.
    assert client.post(f"/api/tarefas/{t['id']}/aprovar", headers=bearer(lawyer["token"])).status_code == 200
    publicado = client.get(f"/api/t/{t['hash']}").json()
    assert publicado["sem_perguntas"] is True and publicado["questoes"] == []
    assert publicado["resumo_md"], "a explicação sumiu junto com as perguntas"


def test_the_review_cannot_be_rewritten_after_the_link_was_released(lawyer, monkeypatch):
    """Depois de liberado, a cidadã pode já ter lido, respondido e recebido comprovante. Reescrever a
    explicação por baixo disso faria o comprovante apontar para um texto que não é o que ela leu."""
    t = _rodada_pronta(lawyer["token"], "Revisão tardia", monkeypatch)
    assert client.post(f"/api/tarefas/{t['id']}/aprovar", headers=bearer(lawyer["token"])).status_code == 200

    tarde = client.post(f"/api/tarefas/{t['id']}/revisao", json={"resumo_md": "outra coisa"},
                        headers=bearer(lawyer["token"]))
    assert tarde.status_code == 409, tarde.text


def test_only_who_sent_the_document_can_save_the_review(lawyer, citizen, monkeypatch):
    t = _rodada_pronta(lawyer["token"], "Revisão alheia", monkeypatch)
    alheio = client.post(f"/api/tarefas/{t['id']}/revisao", json={"resumo_md": "x"},
                         headers=bearer(citizen["token"]))
    assert alheio.status_code in (403, 404), alheio.text


def test_saving_the_review_says_which_sections_lost_their_ground(lawyer, monkeypatch):
    """Editar o texto pode tirar o chão de uma seção sem que ninguém perceba: o vínculo entre seção e classe
    é pelo título, então renomear um título desliga a âncora. A resposta devolve a medida, para a tela
    avisar em vez de o advogado liberar às cegas."""
    t = _rodada_pronta(lawyer["token"], "Revisão medida", monkeypatch)
    r = client.post(f"/api/tarefas/{t['id']}/revisao",
                    json={"resumo_md": "# Título que ninguém mapeou\n\nTexto solto."},
                    headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text
    medida = r.json()["porta_qualidade"]
    assert medida["motivo"], "a explicação ficou sem seção com trecho e a resposta não disse nada"


def test_a_question_about_a_section_the_citizen_never_sees_is_dropped(citizen, monkeypatch):
    """Medido em 20/09/2026 no contrato fictício: 4 das 6 perguntas apontavam para seções que a porta de
    fidelidade tinha descartado por falta de lastro. A pessoa recebia pergunta sobre uma parte da explicação
    que não está na tela dela, e o "não lembro, mostra de novo" abriria o nada.

    Quem decide quais seções existem é a mesma função que monta a tela, e não uma lista paralela."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    t = create_task(citizen["token"], "Pergunta órfã")
    saidas = {**RUN_OUTPUTS,
              # Sem lastro, esta síntese é descartada e a seção "O que está sendo pedido" não é publicada.
              "T9_SINTESE_PEDIDOS": {"sintese_pedidos": {"valor": "", "lastro": []}},
              "T14_QUESTOES": {"questoes": [
                  {**q, "secao": "🤝 O que está sendo pedido"} if q["id"] in (1, 2) else q
                  for q in RUN_OUTPUTS["T14_QUESTOES"]["questoes"]]}}
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _scripted_groq(saidas)))
    finally:
        loop.close()

    secoes = {t_["titulo"] for t_ in client.get(f"/api/t/{t['hash']}").json()["topicos"]}
    assert "🤝 O que está sendo pedido" not in secoes, "a seção sem lastro foi publicada, e o teste mede outra coisa"
    publicadas = client.get(f"/api/t/{t['hash']}").json()["questoes"]
    assert [q["id"] for q in publicadas] == [], \
        "sobraram perguntas, e as que apontavam para a seção descartada deviam cair junto"
    assert last_event(t["hash"], "questoes_ancoradas")["sem_secao"] == 2


def test_the_quote_of_a_published_section_is_the_slice_of_the_document_too():
    """Medido em 20/09/2026 no agravo real: 2 de 5 tópicos mostravam trecho que não está no documento, e a
    `precisao_ancora` caiu para 0.6.

    É a mesma contradição da #88 num caminho vizinho: o `locate` confirma que o trecho existe, e o que vai
    para a tela continua sendo a transcrição do modelo. No contrato fictício os dois coincidem, e foi por
    isso que passou despercebido."""
    from leia.api_citizen import topics_from_summary

    documento = "CLÁUSULA 2. A compa nhia pagará honorários de vinte por cento ao final."
    memoria = {"memoria_persistente": {"pedidos": [
        {"campo": "principal", "valor": "pagamento",
         "trecho_verbatim": "A companhia pagará honorários de vinte por cento"}]}}
    sinteses = [("pedidos", {"sintese_pedidos": {"valor": "Ela paga ao final.", "lastro": ["pedidos[0]"]}})]
    resumo = "# Resumo em uma linha\n\nVocê paga ao final.\n\n## 🤝 O que está sendo pedido\n\nO pagamento é ao final."

    topicos = topics_from_summary(resumo, memoria, documento, sinteses)
    alvo = next(t for t in topicos if "pedido" in t["titulo"])
    assert alvo.get("trecho"), "a seção foi retida, e aí o teste mede outra coisa"
    assert alvo["trecho"] in documento, (
        f"o trecho do tópico não está no documento:\n  publicado : {alvo['trecho']!r}\n  documento : {documento!r}")
    assert "compa nhia" in alvo["trecho"], "o trecho foi limpo, e deixou de ser o que a pessoa vê no papel"


def test_a_synthesis_never_publishes_a_ground_that_reaches_nothing():
    """Medido em 20/09/2026 no agravo real: a síntese de fundamentos declarou `fundamentos[16]` a
    `fundamentos[19]` num documento com 16 itens. A síntese era publicada inteira, com refs válidas e
    inválidas misturadas, e o advogado que clicasse numa das inválidas não achava nada.

    Bastava uma ref boa para a síntese passar, e esse critério continua certo: ele decide se ela é publicada.
    O que não podia continuar é ela **publicar** a ref que não chega a lugar nenhum."""
    from leia.api_citizen import CLASS_LABELS, _syntheses
    from core.anchors import norm_map

    texto = "CLÁUSULA 2. O CONTRATANTE pagará honorários de vinte por cento ao final."
    memoria = {"memoria_persistente": {"pedidos": [
        {"campo": "principal", "valor": "pagamento", "trecho_verbatim": "pagará honorários de vinte por cento"}]}}
    sinteses_raw = [("pedidos", {"sintese_pedidos": {"valor": "Ela paga ao final.",
                                                     "lastro": ["pedidos[0]", "pedidos[7]", "fundamentos[3]"]}})]
    text_norm, idx = norm_map(texto)
    publicadas, _ = _syntheses(sinteses_raw, CLASS_LABELS, memoria, texto, text_norm, idx)

    assert len(publicadas) == 1, "a síntese com uma ref boa deixou de ser publicada"
    assert publicadas[0]["lastro"] == ["pedidos[0]"], (
        f"a síntese publicou lastro que não chega a nada: {publicadas[0]['lastro']}")


# ── O produto para de guardar o que não tem uso (E17-T05, T06, T07) ──────────

def test_the_document_hash_survives_the_document_being_deleted(citizen, monkeypatch):
    """O `documentSha256` do comprovante é o hash do PDF como ele chegou, e hoje ele é recalculado lendo o
    arquivo. Apagar o arquivo sem gravar o hash antes transformaria todo comprovante futuro num registro que
    aponta para nada."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction
    from core.db import Tarefa, engine as _engine
    from sqlmodel import Session as _S, select as _sel
    from leia.api_citizen import _document_sha

    t = create_task(citizen["token"], "Hash do documento")
    with _S(_engine) as s:
        tarefa = s.exec(_sel(Tarefa).where(Tarefa.hash == t["hash"])).one()
        assert tarefa.document_sha256, "o hash do PDF não foi gravado no envio"
        gravado = tarefa.document_sha256

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _scripted_groq(RUN_OUTPUTS)))
    finally:
        loop.close()

    assert not (ws.folder(t["hash"]) / "original.pdf").exists(), "o PDF continua guardado depois da extração"
    assert _document_sha(t["hash"]) == gravado, "o comprovante deixou de conseguir dizer qual documento era"


def test_redoing_a_document_works_without_the_original_pdf(lawyer, monkeypatch):
    """A correção de espécie do advogado só vale na rodada seguinte, e a rodada seguinte é o `reprocessar`.
    Se apagar o PDF tirasse o `reprocessar`, a correção viraria botão que não faz nada. O texto extraído
    continua guardado, e é dele que a rodada nova parte."""
    import asyncio

    from core import pipeline_pdf
    from core.pdf_extract import Extraction

    monkeypatch.setattr(pipeline_pdf, "extract", lambda caminho: Extraction(FAKE_TEXT, 0, 0, 0))
    t = create_task(lawyer["token"], "Refazer sem PDF")
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(pipeline_pdf.run_pdf_pipeline(t["id"], _scripted_groq(RUN_OUTPUTS)))
    finally:
        loop.close()
    assert not (ws.folder(t["hash"]) / "original.pdf").exists()

    r = client.post(f"/api/tarefas/{t['id']}/reprocessar", headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text
    assert (ws.folder(t["hash"]) / "texto_extraido.txt").exists(), \
        "o texto extraído foi apagado junto, e aí não sobra de onde refazer"


def test_the_attempt_stops_carrying_the_network_address(lawyer):
    """As colunas existiam sem ninguém gravar nelas desde a v2 do hash, e o PDF assinado ainda as lia e
    imprimia. Dado sem finalidade não se guarda (art. 6º, III), e dado que ninguém escreve e alguém publica
    é a pior combinação das duas."""
    from core.db import Tentativa

    for morto in ("ip", "user_agent"):
        assert morto not in Tentativa.model_fields, f"a coluna {morto} continua no modelo"

    from app_gestao import _dados_assinatura
    import core.attempts as tn

    t = _tarefa_de_teste("assinatura-sem-ip")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES)
    dados = _dados_assinatura(t, tent)
    assert "ip" not in dados and "user_agent" not in dados, f"o PDF assinado ainda publica: {sorted(dados)}"


# ── Cada trecho diz em que página do documento ele está (E13-T12) ─────────────

def test_every_excerpt_says_which_page_of_the_document_it_is_on():
    """"Está no seu documento" é uma afirmação que a pessoa precisa conferir no papel dela. Sem a página,
    conferir um agravo de 14 folhas custa varrer as 14, e afirmação cara demais de conferir não é conferível
    na prática. O extrator já escreve `===== PÁGINA n =====` no texto, e o dado estava lá sem uso."""
    from leia.api_citizen import _item, page_label, topics_from_summary
    from core.anchors import norm_map

    doc = ("===== PÁGINA 1 =====\n\nCLÁUSULA 1. O CONTRATANTE contrata a CONTRATADA.\n\n"
           "===== PÁGINA 2 =====\n\nCLÁUSULA 2. Pagará vinte por cento ao final.\n")
    assert page_label(doc, doc.index("contrata a")) == "Página 1 de 2"
    assert page_label(doc, doc.index("vinte por cento")) == "Página 2 de 2"

    # Documento sem separador não ganha página inventada.
    assert page_label("Um contrato sem marcação nenhuma.", 5) is None

    text_norm, idx = norm_map(doc)
    item = _item("pedidos", 0, {"campo": "principal", "valor": "pagamento",
                                "trecho_verbatim": "Pagará vinte por cento"}, doc, text_norm, idx, "#000")
    assert item["pagina"] == "Página 2 de 2", item

    memoria = {"memoria_persistente": {"pedidos": [
        {"campo": "principal", "valor": "pagamento", "trecho_verbatim": "Pagará vinte por cento"}]}}
    sinteses = [("pedidos", {"sintese_pedidos": {"valor": "Ela paga ao final.", "lastro": ["pedidos[0]"]}})]
    resumo = "# Resumo em uma linha\n\nPaga ao final.\n\n## 🤝 O que está sendo pedido\n\nO pagamento é ao final."
    topico = next(t for t in topics_from_summary(resumo, memoria, doc, sinteses) if "pedido" in t["titulo"])
    assert topico["pagina"] == "Página 2 de 2", topico


# ── Entrar sem entrar: o link recebido é a credencial (E15) ───────────────────

def test_an_account_can_exist_without_password_or_email(lawyer):
    """A cidadã não cria conta. O link que ela recebeu já prova que é ela: foi endereçado a ela, tem validade
    e pode ser cancelado por quem enviou. Pedir senha depois disso é pedir duas provas da mesma coisa, e cada
    campo a mais é uma pessoa a menos que chega ao fim."""
    from core.auth import open_session
    from core.db import Usuario, engine as _engine
    from sqlmodel import Session as _S

    with _S(_engine) as s:
        u = Usuario(nome="Maria do convite", papel="cidadao")
        s.add(u); s.commit(); s.refresh(u)
        assert u.email is None and u.senha_hash is None, "a conta sem senha não pôde nascer"
        token = open_session(s, u)
        assert token and len(token) > 20

    # E o token abre as rotas de quem está logado, como qualquer outro.
    eu = client.get("/api/auth/me", headers=bearer(token))
    assert eu.status_code == 200, eu.text
    assert eu.json()["usuario"]["nome"] == "Maria do convite"


def test_more_than_one_account_may_have_no_email(lawyer):
    """O e-mail era único. Com várias contas sem e-mail, "único" precisa passar a significar "único entre os
    que têm", senão a segunda cidadã que entrar pelo link colide com a primeira."""
    from core.db import Usuario, engine as _engine
    from sqlmodel import Session as _S

    with _S(_engine) as s:
        for nome in ("Sem email um", "Sem email dois"):
            s.add(Usuario(nome=nome, papel="cidadao"))
        s.commit()   # não pode levantar IntegrityError


def test_a_passwordless_account_refuses_any_password(lawyer):
    """Conta sem senha não é conta com senha vazia. Sem esta guarda, `verify_password` recebe `None` e o
    comportamento passa a depender da biblioteca de hash, que é o pior lugar para uma decisão de acesso."""
    from core.auth import authenticate
    from core.db import Usuario, engine as _engine
    from sqlmodel import Session as _S

    with _S(_engine) as s:
        u = Usuario(nome="Sem senha", papel="cidadao", email="semsenha@teste.local")
        s.add(u); s.commit()
        for tentativa in ("", "qualquer-coisa", "None"):
            assert authenticate(s, "semsenha@teste.local", tentativa) is None, tentativa


def test_the_invite_carries_the_name_of_who_it_is_for(lawyer):
    """O nome é o que a tela vai mostrar para a pessoa confirmar: "Sou eu, Maria". Sem ele não há o que
    confirmar, e o e-mail deixa de ser obrigatório justamente porque ele não é o que identifica."""
    t = create_task(lawyer["token"], "Convite com nome")
    r = client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Maria Souza"},
                    headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == "Maria Souza"

    publico = client.get(f"/api/t/{t['hash']}").json()["convite"]
    assert publico["nome"] == "Maria Souza", publico
    assert publico["enderecado"] is False, "sem e-mail, o convite não é endereçado a um endereço"

    sem_nome = client.post(f"/api/tarefas/{t['id']}/convite", json={}, headers=bearer(lawyer["token"]))
    assert sem_nome.status_code == 422, sem_nome.text


def test_confirming_the_name_creates_the_account_and_opens_the_session(lawyer):
    """O fluxo inteiro, sem campo nenhum para digitar: o advogado manda o link endereçado a Maria, Maria abre
    numa janela anônima, vê "Sou eu, Maria" e toca. A conta nasce ali, sem e-mail e sem senha, o documento
    fica vinculado a ela, e o comprovante passa a poder afirmar que **uma pessoa com nome** entendeu."""
    from core.db import Tarefa, Usuario, engine as _engine
    from sqlmodel import Session as _S, select as _sel

    t = create_task(lawyer["token"], "Confirmação de nome")
    client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Maria Souza"},
                headers=bearer(lawyer["token"])).raise_for_status()

    r = client.post(f"/api/t/{t['hash']}/confirm-name")
    assert r.status_code == 200, r.text
    token = r.json()["token"]

    eu = client.get("/api/auth/me", headers=bearer(token)).json()["usuario"]
    assert eu["nome"] == "Maria Souza" and eu["papel"] == "cidadao"

    with _S(_engine) as s:
        conta = s.exec(_sel(Usuario).where(Usuario.session_token == token)).one()
        assert conta.email is None and conta.senha_hash is None, "nasceu conta com e-mail ou senha"
        tarefa = s.exec(_sel(Tarefa).where(Tarefa.hash == t["hash"])).one()
        assert tarefa.cidadao_id == conta.id, "o documento não ficou vinculado a quem confirmou"

    assert client.get(f"/api/t/{t['hash']}").json()["cidadao_vinculado"] is True


def test_the_second_person_on_the_same_document_is_refused(lawyer):
    """O comprovante afirma que **uma** pessoa entendeu. Se a segunda a abrir o link pudesse se vincular por
    cima, o registro passaria a falar de outra pessoa que não a que respondeu."""
    t = create_task(lawyer["token"], "Segunda pessoa")
    client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Maria Souza"},
                headers=bearer(lawyer["token"])).raise_for_status()

    assert client.post(f"/api/t/{t['hash']}/confirm-name").status_code == 200
    segunda = client.post(f"/api/t/{t['hash']}/confirm-name")
    assert segunda.status_code == 409, segunda.text


def test_confirming_the_name_works_on_an_invite_that_also_carries_an_email(lawyer):
    """O advogado que sabe o e-mail da cliente põe o e-mail no convite, e isso não pode fechar a porta.

    A regra de destinatária comparava ``visitor.email`` com ``inv.email``, então uma conta sem e-mail nunca
    passava, e a conta que a confirmação de nome cria é exatamente essa. O resultado era que pôr o endereço
    no convite desligava o caminho sem digitação — a pessoa via o botão e recebia 403 ao tocar."""
    t = create_task(lawyer["token"], "Convite com endereço")
    client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Maria Souza", "email": "maria@exemplo.local"},
                headers=bearer(lawyer["token"])).raise_for_status()

    r = client.post(f"/api/t/{t['hash']}/confirm-name")
    assert r.status_code == 200, r.text


def test_the_invite_remembers_which_account_claimed_it(lawyer, citizen):
    """Depois que alguém reivindica o convite, destinatária passa a ser aquela conta, não aquele endereço.

    Sem isso a conta recém-criada não teria como provar que é a destinatária: ela não tem e-mail nenhum
    para comparar."""
    from core.db import Invite, Tarefa, Usuario, engine as _engine
    from sqlmodel import Session as _S, select as _sel

    t = create_task(lawyer["token"], "Convite reivindicado")
    client.post(f"/api/tarefas/{t['id']}/convite", json={"nome": "Maria Souza", "email": "maria2@exemplo.local"},
                headers=bearer(lawyer["token"])).raise_for_status()
    token = client.post(f"/api/t/{t['hash']}/confirm-name").json()["token"]

    with _S(_engine) as s:
        tarefa = s.exec(_sel(Tarefa).where(Tarefa.hash == t["hash"])).one()
        inv = s.exec(_sel(Invite).where(Invite.task_id == tarefa.id)).one()
        conta = s.exec(_sel(Usuario).where(Usuario.session_token == token)).one()
        assert inv.usuario_id == conta.id, "o convite não guardou de quem ele passou a ser"

    # E outra conta, com e-mail e tudo, não entra por cima: o convite já tem dona.
    outra = client.post(f"/api/t/{t['hash']}/vincular", headers=bearer(citizen["token"]))
    assert outra.status_code in (403, 409), outra.text


def test_confirming_the_name_needs_a_live_invite(lawyer):
    """Sem convite vivo, o link não prova nada sobre quem o abriu, e criar conta ali seria dar nome de
    destinatária a quem só tem o endereço."""
    t = create_task(lawyer["token"], "Sem convite vivo")
    assert client.post(f"/api/t/{t['hash']}/confirm-name").status_code in (403, 409), "entrou sem convite"
