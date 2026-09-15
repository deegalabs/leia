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


def signup(email: str, papel: str, nome: str = "Pessoa") -> dict:
    r = client.post("/api/auth/cadastro", json={"nome": nome, "email": email, "senha": "senha-123", "papel": papel})
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
    return signup("Advogada@Teste.local", "advogado", "Dra. Ana")


@pytest.fixture(scope="module")
def citizen() -> dict:
    return signup("cidada@teste.local", "cidadao", "Maria")


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
    assert (ws.folder(lawyer_task["hash"]) / "original.pdf").exists()

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
    assert pub["tem_advogado"] is True and pub["advogado"] == {"nome": "Dra. Ana"} and pub["duvidas_enviadas"] == 0
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
    assert pub["tarefa"]["status"] == "revisao" and pub["tem_advogado"] is True and pub["advogado"] == {"nome": "Dra. Ana"}
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
    assert len(STEP_NAMES) == 14 and list(STEP_NAMES)[0] == "T1_IDENTIFICADOR_PARTES" and list(STEP_NAMES)[-1] == "T14_QUESTOES"
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
    assert [e["id"] for e in etapas] == list(STEP_NAMES) and etapas[0]["nome"] == "Identificar as partes"
    assert etapas[0] == {"id": "T1_IDENTIFICADOR_PARTES", "nome": "Identificar as partes", "estado": "concluida", "tempo": 4.2}
    assert etapas[1]["estado"] == "em_andamento" and etapas[1]["tempo"] is None
    assert all(e["estado"] == "pendente" for e in etapas[2:]) and etapas[13]["nome"] == "Preparar as perguntas"
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
    assert build_steps([{"tipo": "resumo_estruturado_start"}], None) == []


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


EXTERNAL_TEXT = "Processo n. 1. Agravante: Ministério Público.\nO recurso não merece trânsito.\nRequer seja ele provido."


def external_artifacts(h: str) -> None:
    """Workspace of the external "Resumo estruturado" flow: only resumo_estruturado.json and its text."""
    folder = ws.folder(h)
    a = EXTERNAL_TEXT.index("O recurso não merece trânsito.")
    doc = {"processo": {
        "id_manifestacao": "x",
        "classe_i_fatos": [
            {"campo": "partes_qualificadas", "sub_tipo": "recorrente", "valor": "Ministério Público", "trecho_verbatim": "Agravante: Ministério Público", "sintese_relacao": None},
            {"campo": "data", "sub_tipo": "d", "valor": "2019", "trecho_verbatim": "seja ele provido", "sintese_relacao": None}],
        "classe_i_decisao": [
            {"campo": "decidido", "sub_tipo": "sentenca", "valor": json.dumps({"resultado": "IMPROVIDO", "relator": None, "parte_dispositiva": "O recurso não merece trânsito."}),
             "trecho_verbatim": "O recurso não merece trânsito.", "sintese_relacao": None}],
        "classe_v_relevancia": [],
        "resumo_classe_i": {"campo": "resumo_fatos", "valor": "O MP recorreu e perdeu.", "lastro": ["Agravante: Ministério Público"]},
        "resposta_final": {"texto": "## 1. Síntese\nO Ministério Público recorreu e o recurso não passou."},
        "conferencia": {"ok": True}},
        "_ui": {"classe_i_fatos": [{"pos_trecho_verbatim": "0:0", "score_trecho_verbatim": 0.5, "todas_trecho_verbatim": "[]"},
                                   {"pos_trecho_verbatim": "9999:10010", "score_trecho_verbatim": 0.9, "todas_trecho_verbatim": "[]"}],
                "classe_i_decisao": [{"pos_trecho_verbatim": f"{a}:{a + 30}", "score_trecho_verbatim": 1.0, "todas_trecho_verbatim": f"[{a}:{a + 30}]"}]}}
    folder.joinpath("resumo_estruturado.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    folder.joinpath("resumo_estruturado_texto.txt").write_text(EXTERNAL_TEXT, encoding="utf-8")
    ws.record_event(h, "resumo_estruturado_start", tarefa_id=0)
    ws.record_event(h, "resumo_estruturado_done", tokens=10, elapsed=1.0)


def test_external_flow_fallback(citizen):
    """LeIA: a task with only resumo_estruturado.json gets its explanation and topics from it, without questions."""
    task = create_task(citizen["token"], "Fluxo externo")
    h = task["hash"]
    for name in ("resumo_humanizado.md", "questoes.json", "memoria_persistente.json", "texto_extraido.txt"):
        (ws.folder(h) / name).unlink(missing_ok=True)
    staged_log(h, [{"ts": "t", "tipo": "criada", "tarefa_id": task["id"]}])  # no trace of the offline local workflow
    external_artifacts(h)
    set_status(h, "pronta")
    data = client.get(f"/api/t/{h}").json()
    assert data["tarefa"]["status"] == "pronta" and data["etapas"] == []
    assert data["resumo_md"].startswith("## 1. Síntese") and data["questoes"] == [] and data["sem_perguntas"] is True
    topics = data["topicos"]
    assert [t["titulo"] for t in topics] == ["Partes qualificadas", "Data", "Decidido"]
    assert topics[0] == {"id": 1, "titulo": "Partes qualificadas", "explicacao": "Ministério Público", "classe": "classe_i_fatos",
                         "trecho": "Agravante: Ministério Público", "score": 0.5}
    assert topics[2]["explicacao"] == "IMPROVIDO, O recurso não merece trânsito." and topics[2]["score"] == 1.0
    assert all("clausula" not in t for t in topics)
    assert any(e["tipo"] == "resumo_estruturado_done" for e in data["eventos"])

    inf = client.get(f"/api/t/{h}/inferencias").json()
    assert inf["parcial"] is False and inf["texto"] == EXTERNAL_TEXT
    assert [(c["classe"], c["rotulo"]) for c in inf["classes"]] == [("classe_i_fatos", "Fatos"), ("classe_i_decisao", "Decisão"), ("classe_v_relevancia", "Relevância")]
    fatos, decisao = inf["classes"][0]["itens"], inf["classes"][1]["itens"]
    a = EXTERNAL_TEXT.index("O recurso não merece trânsito.")
    assert decisao[0]["pos"] == [a, a + 30] and decisao[0]["conferido"] and decisao[0]["score"] == 1.0  # _ui position used as is
    assert decisao[0]["valor"] == "IMPROVIDO, O recurso não merece trânsito."
    assert fatos[0]["pos"] == [EXTERNAL_TEXT.index("Agravante"), EXTERNAL_TEXT.index("Agravante") + len("Agravante: Ministério Público")]  # 0:0 falls back to search
    assert fatos[1]["pos"] == [EXTERNAL_TEXT.index("seja ele"), len(EXTERNAL_TEXT) - 1] and fatos[1]["score"] == 0.9  # out of range falls back
    assert inf["total"] == 3 and inf["conferidos"] == 3
    assert inf["sinteses"] == [{"classe": "resumo_classe_i", "rotulo": "Fatos e decisão", "texto": "O MP recorreu e perdeu.", "lastro": ["Agravante: Ministério Público"]}]
    # the lawyer review route shares the same body
    r = client.get(f"/api/tarefas/{task['id']}/revisao", headers=bearer(citizen["token"]))
    assert r.status_code == 200 and r.json()["inferencias"]["classes"][1]["itens"][0]["pos"] == [a, a + 30]


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

BACKSTAGE = [("get", "/api/protocolo"), ("get", "/api/help"), ("get", "/api/contexto")]


def test_backstage_routes_require_the_supplier_role(citizen, lawyer):
    for method, path in BACKSTAGE:
        call = getattr(client, method)
        assert call(path).status_code == 401, f"{path} sem credencial"
        for quem, tok in (("cidadã", citizen["token"]), ("advogado", lawyer["token"])):
            r = call(path, headers=bearer(tok))
            assert r.status_code == 403, f"{path} aberta para {quem}: {r.status_code}"
    assert client.post("/api/contexto/limpar", headers=bearer(citizen["token"])).status_code == 403
    assert client.post("/api/protocolo", headers=bearer(citizen["token"]), json={"conteudo": "[]"}).status_code == 403
    assert client.post("/api/chat", headers=bearer(citizen["token"]), json={"mensagem": "oi"}).status_code == 403


def test_backstage_routes_stay_open_to_the_supplier():
    admin = client.post("/api/auth/login", json={"email": "admin@test.local", "senha": "admin-secret-1"}).json()
    for method, path in BACKSTAGE:
        r = getattr(client, method)(path, headers=bearer(admin["token"]))
        assert r.status_code == 200, f"{path} fechada para o fornecedor: {r.status_code}"


# ── Hash da tentativa: reproduzível por terceiro e sem dado pessoal ───────────

def _tarefa_de_teste(hash_: str):
    from core.db import Session as _S, Tarefa as _T, engine as _e
    with _S(_e) as s:
        t = _T(hash=hash_, titulo="Contrato", advogado_id=1, status="enviada")
        s.add(t); s.commit(); s.refresh(t)
        return t


QUESTOES = [{"id": 1, "correta": 0}, {"id": 2, "correta": 1}, {"id": 3, "correta": 2}]


def test_attempt_hash_carries_no_personal_data(lawyer):
    import core.attempts as tn
    t = _tarefa_de_teste("hash-tentativa-1")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES, "203.0.113.7", "Mozilla/5.0 (Android)")
    assert tent.ip is None and tent.user_agent is None, "IP e navegador continuam sendo gravados"


def test_attempt_hash_is_reproducible_from_what_is_stored(lawyer):
    import core.attempts as tn
    t = _tarefa_de_teste("hash-tentativa-2")
    tent = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES, "203.0.113.7", "Mozilla/5.0")
    recalculado = tn.attempt_hash(t.hash, tent.numero, tent.respostas, tent.criada_em)
    assert recalculado == tent.hash_imutavel, "ninguém consegue recalcular o hash a partir do que está gravado"


def test_attempt_hash_does_not_depend_on_the_client(lawyer):
    import core.attempts as tn
    t = _tarefa_de_teste("hash-tentativa-3")
    a = tn.record(t, {"1": 0, "2": 1, "3": 2}, QUESTOES, "203.0.113.7", "Chrome")
    b = tn.attempt_hash(t.hash, a.numero, a.respostas, a.criada_em)
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
    from leia.registry import ots_digest

    chamadas = {"n": 0}
    monkeypatch.setattr(ac, "ots_stamp", lambda digest: chamadas.__setitem__("n", chamadas["n"] + 1) or b"prova-falsa")
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
    r = client.post(f"/api/tarefas/{tarefa_id}/convite", json=corpo, headers=bearer(lawyer["token"]))
    assert r.status_code == 200, r.text
    return r.json()


def test_a_link_without_an_invite_keeps_working(lawyer_task):
    """Compatibilidade: link que já circulou não pode parar de abrir por causa desta mudança."""
    assert client.get(f"/api/t/{lawyer_task['hash']}").status_code == 200


def test_only_whoever_sent_the_document_can_invite_or_revoke(lawyer, citizen):
    t = _nova_tarefa(lawyer)
    r = client.post(f"/api/tarefas/{t['id']}/convite", json={}, headers=bearer(citizen["token"]))
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


def test_the_server_locates_the_quote_instead_of_believing_the_model():
    """O modelo escreve a posição que quiser, e não conta caractere. Se o servidor acreditar nela, o selo de
    conferido aparece apontando para o lugar errado, e a promessa central do produto vira decoração."""
    from leia.api_citizen import build_external_inferences

    doc = {"processo": {"classe_fatos": [{"campo": "honorarios", "valor": "20%",
                                          "trecho_verbatim": "honorários de vinte por cento"}]},
           "_ui": {"classe_fatos": [{"pos_trecho_verbatim": "0:11"}]}}   # mentira plausível: aponta para "CLÁUSULA 3."
    item = build_external_inferences(DOC_TEXT, doc)["classes"][0]["itens"][0]
    assert item["conferido"], "não achou o trecho que está no documento"
    achado = DOC_TEXT[item["pos"][0]:item["pos"][1]]
    assert achado == "honorários de vinte por cento", f"seguiu a posição do modelo e marcou {achado!r}"


def test_a_quote_that_is_not_in_the_document_is_never_sealed():
    from leia.api_citizen import build_external_inferences

    doc = {"processo": {"classe_fatos": [{"campo": "multa", "valor": "R$ 5.000",
                                          "trecho_verbatim": "multa de cinco mil reais por descumprimento"}]},
           "_ui": {"classe_fatos": [{"pos_trecho_verbatim": "12:40"}]}}
    item = build_external_inferences(DOC_TEXT, doc)["classes"][0]["itens"][0]
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


def test_a_section_whose_source_quote_is_not_in_the_document_shows_none():
    from leia.api_citizen import topics_from_summary

    topicos = topics_from_summary(RESUMO_ESTRUTURADO, MEMORIA_ESTRUTURADA, DOC_TEXT, SINTESES_ESTRUTURADAS)
    aconteceu = [t for t in topicos if "O que aconteceu" in t["titulo"]][0]
    assert "trecho" not in aconteceu, "mostrou um trecho que não está no documento"


def test_a_section_with_no_declared_source_shows_no_quote():
    """Resumo em uma linha fala do caso inteiro, não de uma cláusula. Sem fonte declarada, nada é mostrado,
    em vez de pendurar ali o trecho que por acaso tiver mais palavras em comum."""
    from leia.api_citizen import topics_from_summary

    topicos = topics_from_summary(RESUMO_ESTRUTURADO, MEMORIA_ESTRUTURADA, DOC_TEXT, SINTESES_ESTRUTURADAS)
    assert "trecho" not in topicos[0] and topicos[0]["titulo"] == "Resumo em uma linha"
