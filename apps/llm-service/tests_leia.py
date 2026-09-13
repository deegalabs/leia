"""Smoke tests for the LeIA add-ons against the mock service. Run from apps/llm-service: python -m pytest -q tests_leia.py"""
import os
import re

os.environ["OTS_ENABLED"] = "false"
from fastapi.testclient import TestClient  # noqa: E402

from mock.app import app, STATE  # noqa: E402

client = TestClient(app)
HASH = STATE["tarefa"]["hash"]


def test_citizen_page_has_no_answer_key():
    r = client.get(f"/t/{HASH}")
    assert r.status_code == 200
    assert "correta" not in r.text and "justificativa" not in r.text
    assert "leia-citizen" in r.text and "Não sou advogada" in r.text


def test_task_json_is_public_only():
    data = client.get(f"/api/t/{HASH}").json()
    assert all("correta" not in q for q in data["questoes"])
    assert data["topicos"][0]["trecho"]


def test_quiz_pass_and_receipt():
    key = {str(q["id"]): q["correta"] for q in STATE["questoes"]["questoes"]}
    r = client.post(f"/api/t/{HASH}/quiz", json={"respostas": key}).json()
    assert r["aprovado"] and r["acertos"] == r["total"] and len(r["hash_imutavel"]) == 64
    page = client.get(f"/t/{r['hash_imutavel']}/comprovante")
    assert page.status_code == 200 and "data:image/png;base64" in page.text
    v = client.get(f"/verify/{r['hash_imutavel']}?format=json").json()
    assert re.fullmatch(r"[0-9a-f]{64}", v["payloadHash"]) and "salt" in v["canonical"]
    assert client.get(f"/verify/{r['hash_imutavel']}").status_code == 200


def test_task_json_after_attempt_is_serializable():
    key = {str(q["id"]): q["correta"] for q in STATE["questoes"]["questoes"]}
    client.post(f"/api/t/{HASH}/quiz", json={"respostas": key})
    r = client.get(f"/api/t/{HASH}")
    assert r.status_code == 200 and r.json()["ultima_tentativa"]["aprovado"] is True
    assert "ots" not in r.json()["ultima_tentativa"] and "salt" not in r.json()["ultima_tentativa"]


def test_quiz_fail_lists_points_to_review():
    r = client.post(f"/api/t/{HASH}/quiz", json={"respostas": {"1": 3, "2": 3}}).json()
    assert not r["aprovado"] and len(r["erros"]) == 12 and r["erros"][0]["enunciado"]


def test_chat_grounded_and_refusal():
    def ask(msg):
        r = client.post(f"/api/t/{HASH}/chat", json={"mensagem": msg})
        return "".join(re.findall(r'"t": "([^"]*)"', r.text))
    assert "20%" in ask("quanto pago se ganhar a ação?") or "cláusula" in ask("quanto pago se ganhar a ação?")
    assert "não está escrito" in ask("posso processar meu vizinho?")
