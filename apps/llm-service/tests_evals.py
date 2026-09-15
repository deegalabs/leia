"""Testes da bateria de avaliação (evals/).

A bateria existe porque hoje toda mudança no motor é avaliada de cabeça: alguém roda um documento, olha a tela e
decide se melhorou. Esses testes garantem que a bateria reprova o que tem de reprovar. Uma bateria que nunca
reprova é pior que nenhuma, porque dá a sensação de que está tudo conferido.

Rodar: python -m pytest -q
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from evals.regras import avaliar, carregar_casos

CASO = Path(__file__).resolve().parent / "evals" / "casos" / "contrato-honorarios.json"


@pytest.fixture()
def caso() -> dict:
    return json.loads(CASO.read_text(encoding="utf-8"))


# ── Camada 1: o que reprova ───────────────────────────────────────────────────

def test_the_real_case_passes_the_contract_layer(caso):
    """O caso capturado da produção é o piso: se ele começar a violar contrato, alguma mudança quebrou o produto."""
    r = avaliar(caso)
    assert r.violacoes == [], f"o caso real está violando contrato: {r.violacoes}"


def test_a_quote_shown_to_the_citizen_that_is_not_in_the_document_is_a_violation(caso):
    ruim = copy.deepcopy(caso)
    for t in ruim["topicos"]:
        if t.get("trecho"):
            t["trecho"] = "cláusula que este contrato não tem em lugar nenhum"
            break
    r = avaliar(ruim)
    assert any("não está no documento" in v for v in r.violacoes), r.violacoes


def test_an_item_that_claims_a_position_it_does_not_occupy_is_a_violation(caso):
    ruim = copy.deepcopy(caso)
    item = ruim["inferencias"]["classes"][0]["itens"][0]
    item["pos"] = [0, 10]
    r = avaliar(ruim)
    assert any("posição" in v for v in r.violacoes), r.violacoes


def test_the_answer_key_reaching_the_citizen_is_a_violation(caso):
    ruim = copy.deepcopy(caso)
    if not ruim["questoes"]:
        pytest.skip("o caso não tem perguntas")
    ruim["questoes"][0]["correta"] = 2
    r = avaliar(ruim)
    assert any("gabarito" in v for v in r.violacoes), r.violacoes


# ── Camada 2: o que informa, com piso que impede piorar ───────────────────────

def test_the_measured_numbers_are_reported(caso):
    r = avaliar(caso)
    assert 0.0 <= r.metricas["cobertura_ancora"] <= 1.0
    assert r.metricas["itens_conferidos"] == 1.0
    assert r.metricas["precisao_ancora"] == 1.0


def test_losing_anchor_coverage_is_reported_as_a_warning_not_a_violation(caso):
    pior = copy.deepcopy(caso)
    for t in pior["topicos"]:
        t.pop("trecho", None)
        t.pop("conferencia", None)
    r = avaliar(pior)
    assert r.metricas["cobertura_ancora"] == 0.0
    assert any("cobertura" in a for a in r.avisos), r.avisos
    assert r.violacoes == [], "perder cobertura não é violação de contrato, é piora medida"


def test_every_case_in_the_corpus_is_loadable():
    casos = carregar_casos()
    assert casos, "o corpus está vazio: a bateria não mede nada"
    for c in casos:
        assert c.get("documento") and c.get("nome")


def test_the_real_case_does_not_breach_the_floors(caso):
    """O piso só é piso se alguma coisa falhar quando ele é rompido. Piso que nunca reprova é enfeite."""
    r = avaliar(caso)
    assert r.avisos == [], f"o caso real caiu abaixo de um piso: {r.avisos}"


def test_the_runner_reports_and_gates(capsys):
    from evals.run import main

    assert main() == 0
    saida = capsys.readouterr().out
    assert "cobertura_ancora" in saida and "violação" in saida
    assert "camada 3" in saida, "a bateria precisa dizer o que ela ainda não mede"


def test_a_private_corpus_outside_the_repository_is_also_measured(tmp_path, monkeypatch, caso):
    """Documento de verdade não entra no repositório, que é público. Mas a bateria precisa conseguir medir
    sobre ele na máquina de quem tem o arquivo, senão ele não serve de teste nenhum."""
    (tmp_path / "agravo.json").write_text(json.dumps({**caso, "nome": "agravo-privado"}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("LEIA_EVAL_CASES", str(tmp_path))

    nomes = [c["nome"] for c in carregar_casos()]
    assert "contrato-honorarios" in nomes, "os casos públicos pararam de ser medidos"
    assert "agravo-privado" in nomes, "o corpus privado não foi lido"


def test_a_missing_private_corpus_is_not_an_error(monkeypatch):
    monkeypatch.setenv("LEIA_EVAL_CASES", "/caminho/que/nao/existe")
    assert carregar_casos(), "sem o corpus privado a bateria tem que continuar rodando sozinha"
