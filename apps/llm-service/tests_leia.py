"""Smoke tests for the LeIA add-ons against the mock service. Run from apps/llm-service: python -m pytest -q tests_leia.py"""
import os
import pathlib
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
    assert re.fullmatch(r"[0-9a-f]{64}", v["payloadHash"]) and "salt" not in v["canonical"]
    assert "documentRef" in v["canonical"] and STATE["tarefa"]["hash"] not in v["canonical"]
    assert sha256_hex(v["canonical"]) == v["payloadHash"]   # terceiro recalcula sem depender do serviço
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


# ── Registro público: o comprovante circula, o link da cidadã não pode ir junto ──
from datetime import datetime, timezone  # noqa: E402

from leia.registry import build_payload, payload_hash, sha256_hex  # noqa: E402

LINK = "segredo-do-link-da-cidada"
ATTEMPT = {"hash_imutavel": "a" * 64, "tarefa_hash": LINK, "numero": 1,
           "acertos": 5, "total": 6, "aprovado": True,
           "criada_em": datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)}


def test_payload_does_not_leak_the_document_link():
    payload = build_payload(ATTEMPT)
    canonical, _ = payload_hash(payload)
    assert "documentToken" not in payload, "o token do documento não pode estar no payload"
    assert LINK not in canonical, "o link da cidadã vazou no JSON publicado"


def test_payload_identifies_the_document_without_revealing_it():
    payload = build_payload(ATTEMPT)
    assert payload["documentRef"] == sha256_hex(LINK)


def test_payload_has_no_decorative_salt():
    payload = build_payload(ATTEMPT)
    canonical, _ = payload_hash(payload)
    assert "salt" not in payload and "salt" not in canonical


def test_payload_is_reproducible_by_a_third_party():
    canonical, digest = payload_hash(build_payload(ATTEMPT))
    assert sha256_hex(canonical) == digest
    again, digest2 = payload_hash(build_payload(dict(ATTEMPT)))
    assert canonical == again and digest == digest2, "o mesmo registro precisa dar sempre o mesmo código"


# ── O PDF do comprovante: o que ele afirma e o que ele carrega ────────────────
def test_signed_pdf_makes_no_false_claim_and_carries_no_personal_data(tmp_path):
    from pypdf import PdfReader as _R

    from core.pdf_sign import build_signed_pdf

    origem = pathlib.Path(__file__).resolve().parents[2] / "examples" / "contrato-honorarios-exemplo.pdf"
    assert origem.exists(), "o PDF de exemplo sumiu do repositório"
    saida = tmp_path / "assinado.pdf"
    build_signed_pdf(origem, saida, {
        "tarefa_hash": "hash-da-tarefa", "numero": 1, "acertos": 5, "total": 6,
        "hash_imutavel": "b" * 64, "ts": "2026-09-15T12:00:00+00:00",
        "ip": "200.201.202.203", "user_agent": "Mozilla/5.0 (Android 10)",
    })
    texto = "\n".join((p.extract_text() or "") for p in _R(str(saida)).pages)
    assert "inequívoca" not in texto.lower(), "o PDF afirma provar algo que não prova"
    assert "200.201.202.203" not in texto, "o endereço de rede da cidadã está impresso no comprovante"
    assert "Mozilla" not in texto, "o navegador da cidadã está impresso no comprovante"
    r = _R(str(saida))
    assert r.metadata in (None, {}), f"o PDF gerado carrega metadados: {r.metadata}"
