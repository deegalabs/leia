"""Tests for the v3 API (accounts, documents of the signed-in user, doubts, linking, rate limit).

Run from apps/llm-service: python -m pytest -q tests_leia.py tests_v3.py
SQLite in a temporary DATA_DIR, no OpenTimestamps, no Groq key: the workflow fails fast and the task ends
in "falhou", which is enough to check creation, visibility and the public JSON.
"""
from __future__ import annotations

import os

os.environ["RATE_LIMIT_TRUST_XFF"] = "true"  # tests simulate different clients through X-Forwarded-For

import io
import json
import os
import tempfile

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
from core.db import Tarefa, engine  # noqa: E402
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
    r = fresh.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"  # templates keep redirecting
    r = fresh.get("/dashboard", headers=bearer("nao-existe"), follow_redirects=False)
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/json")
    r = fresh.get("/dashboard", headers=bearer(lawyer["token"]))
    assert r.status_code == 200  # Bearer also opens the panel
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
    assert (ws.pasta(lawyer_task["hash"]) / "original.pdf").exists()

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
    assert any(e["tipo"] == "duvida_enviada" for e in ws.ler_eventos(h))
    assert client.get("/api/t/nao-existe").status_code == 404

    detail = client.get(f"/api/tarefas/{lawyer_task['id']}", headers=bearer(lawyer["token"])).json()
    assert len(detail["duvidas"]) == 1 and detail["duvidas"][0]["respondida"] is False
    assert detail["duvidas"][0]["contexto"] == [{"role": "user", "text": "oi"}, {"role": "bot", "text": "ola"}]
    lst = client.get("/api/tarefas", headers=bearer(lawyer["token"])).json()["tarefas"]
    assert [t for t in lst if t["id"] == lawyer_task["id"]][0]["duvidas_abertas"] == 1

    # the doubt also shows in the internal panel (cookie session)
    panel = TestClient(main.app)
    panel.post("/login", data={"email": "advogada@teste.local", "senha": "senha-123"}, follow_redirects=False)
    page = panel.get(f"/tarefas/{lawyer_task['id']}")
    assert page.status_code == 200 and "Dúvidas da cliente" in page.text and "Quanto pago se perder?" in page.text
    panel.close()
    # one token per user: the cookie login above rotated it, so the app signs in again
    lawyer["token"] = client.post("/api/auth/login", json={"email": "advogada@teste.local", "senha": "senha-123"}).json()["token"]

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


def test_public_json_never_leaks_the_answer_key(lawyer_task):
    h = lawyer_task["hash"]
    folder = ws.pasta(h)
    (folder / "resumo_humanizado.md").write_text("# Resumo em uma linha\nVocê paga só se ganhar.\n\n## O que aconteceu\nUm contrato.", encoding="utf-8")
    (folder / "questoes.json").write_text(json.dumps({"questoes": [
        {"id": 1, "area": "pedidos", "enunciado": "Quando você paga?", "alternativas": ["Sempre", "Só se ganhar", "Nunca", "Antes"],
         "correta": 1, "justificativa": "Está na cláusula 2.", "dificuldade": "facil"}]}), encoding="utf-8")
    with Session(engine) as s:
        t = s.exec(select(Tarefa).where(Tarefa.hash == h)).one()
        t.status = "pronta"
        s.add(t); s.commit()
    r = client.get(f"/api/t/{h}")
    assert r.status_code == 200
    assert "correta" not in r.text and "justificativa" not in r.text
    data = r.json()
    assert data["questoes"][0]["enunciado"] == "Quando você paga?" and data["resumo_md"].startswith("# Resumo")
    assert data["tem_advogado"] is True


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
    assert any(e["tipo"] in ("task_error", "erro_pipeline") for e in ws.ler_eventos(a["hash"]))


def test_inferences_are_verified_by_substring(tmp_path=None):
    """LeIA: inferences endpoint finds quotes with whitespace differences and reports unverified ones."""
    from leia.api_cliente import build_inferences
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
    from leia.api_cliente import public_events
    doc = {"questoes": [{"id": i, "alternativas": ["certa", "b", "c", "d"], "correta": 0} for i in range(1, 7)]}
    out = _embaralhar_alternativas(doc, "abc")
    assert all(q["alternativas"][q["correta"]] == "certa" for q in out["questoes"])
    assert any(q["correta"] != 0 for q in out["questoes"])
    same = _embaralhar_alternativas({"questoes": [{"id": i, "alternativas": ["certa", "b", "c", "d"], "correta": 0} for i in range(1, 7)]}, "abc")
    assert [q["correta"] for q in same["questoes"]] == [q["correta"] for q in out["questoes"]]
    ev = public_events([{"tipo": "cliente_abriu", "ip": "1.2.3.4", "ua": "x"}, {"tipo": "task_done", "id": "T1", "ip": "9.9.9.9"}])
    assert ev == [{"tipo": "task_done", "id": "T1"}]
