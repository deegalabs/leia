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

def test_the_recorded_case_publishes_only_what_it_can_point_at(caso):
    """O caso gravado é a linha de base do motor, e a linha de base não pode carregar violação.

    Até 17/09/2026 ele carregava: era uma captura de 15/09, de antes da porta de fidelidade, com uma síntese
    de 1293 caracteres citando seis dispositivos legais e lastro vazio. Recapturado com
    `scripts/capture_eval_case.py` depois da porta, ele sai limpo. Quando o motor piorar, é aqui que aparece.

    A prova de que a bateria REPROVA saída ruim não mora neste teste e nunca deveria ter morado: ela mora nos
    casos de `casos/planted/`, feitos à mão para ficarem vermelhos. Prova de porta que depende de o caso de
    produção estar quebrado some no dia em que alguém conserta o produto."""
    r = avaliar(caso)
    assert r.violacoes == [], r.violacoes


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
    # A regra confere a posição de quem declara uma: item sem "pos" não promete nada e não pode violar.
    com_pos = [(c, i) for c in ruim["inferencias"]["classes"] for i in (c.get("itens") or []) if i.get("pos")]
    assert com_pos, "o caso gravado ficou sem item com posição: a mutação não prova mais nada"
    com_pos[0][1]["pos"] = [0, 10]
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
    assert r.metricas["cobertura_ancora"] == 1.0, "seção publicada sem trecho do documento"
    assert r.metricas["precisao_ancora"] == 1.0, "trecho mostrado que não está onde diz estar"
    assert r.metricas["sinteses_com_lastro"] == 1.0, "síntese publicada sem lastro"
    # itens_conferidos mede a memória inteira, inclusive o que nunca chega à tela, então ele informa em vez
    # de reprovar: hoje sai em 0.4 no contrato de exemplo, e cair mais do que isso é piora medida.
    assert 0.0 <= r.metricas["itens_conferidos"] <= 1.0


def test_losing_anchor_coverage_is_reported_as_a_warning_not_a_violation(caso):
    pior = copy.deepcopy(caso)
    for t in pior["topicos"]:
        t.pop("trecho", None)
        t.pop("conferencia", None)
    r = avaliar(pior)
    assert r.metricas["cobertura_ancora"] == 0.0
    assert any("cobertura" in a for a in r.avisos), r.avisos
    assert r.violacoes == avaliar(caso).violacoes, "perder cobertura não é violação de contrato, é piora medida"


def test_every_case_in_the_corpus_is_loadable():
    casos = carregar_casos()
    assert casos, "o corpus está vazio: a bateria não mede nada"
    for c in casos:
        assert c.get("documento") and c.get("nome")


def test_the_recorded_case_meets_the_raised_floors(caso):
    """O piso só é piso se alguma coisa falhar quando ele é rompido, e só é honesto se alguma coisa puder
    atingi-lo. O caso recapturado atinge os dois que reprovam, e é isso que os torna piso de verdade em vez
    de aviso permanente que o time aprende a ignorar."""
    r = avaliar(caso)
    assert r.metricas["cobertura_ancora"] == 1.0, r.metricas
    assert r.metricas["sinteses_com_lastro"] == 1.0, r.metricas
    assert not any("cobertura_ancora" in a for a in r.avisos), r.avisos


def test_the_runner_reports_and_gates(capsys):
    """A porta é o código de saída, e ele segue o que foi impresso, não o contrário.

    Enquanto o corpus carregar a síntese sem lastro do caso de 15/09, o runner sai vermelho, e é para sair.
    No dia em que o caso for recapturado com lastro, o mesmo teste passa com saída 0."""
    from evals.run import main

    codigo = main()
    saida = capsys.readouterr().out
    assert "cobertura_ancora" in saida and "sinteses_com_lastro" in saida and "violação" in saida
    assert "camada 3" in saida, "a bateria precisa dizer o que ela ainda não mede"
    assert codigo == (1 if "✗" in saida else 0)


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


# ── Camada 1: a síntese e a pergunta também são afirmação, e também têm que ter lastro ────────────────────

PLANTADOS = Path(__file__).resolve().parent / "evals" / "casos" / "planted"


def plantado(arquivo: str) -> dict:
    return json.loads((PLANTADOS / arquivo).read_text(encoding="utf-8"))


def test_a_synthesis_with_text_and_no_anchor_is_a_violation():
    """A síntese é o texto mais longo que a cidadã lê. Sem lastro, ninguém consegue conferir uma linha dela."""
    r = avaliar(plantado("synthesis-without-anchor.json"))
    assert any("não aponta lastro" in v for v in r.violacoes), r.violacoes


def test_an_anchor_pointing_at_an_item_that_does_not_exist_is_a_violation(caso):
    ruim = copy.deepcopy(caso)
    ruim["inferencias"]["sinteses"][0]["lastro"] = ["fatos[99]"]
    r = avaliar(ruim)
    assert any("não existe nas classes" in v for v in r.violacoes), r.violacoes


def test_an_anchor_may_point_at_another_synthesis_until_it_reaches_an_item(caso):
    """A síntese de contexto se apoia nas outras sínteses, e isso é legítimo enquanto a corrente termina em
    item de memória. Quem só olha o primeiro elo reprova o caso certo."""
    r = avaliar(caso)
    assert not any("contexto" in v and "lastro" in v for v in r.violacoes), r.violacoes


def test_a_chain_of_anchors_that_never_reaches_an_item_is_a_violation(caso):
    ruim = copy.deepcopy(caso)
    ruim["inferencias"]["sinteses"] = [
        {"classe": "fatos", "rotulo": "Fatos", "texto": "", "lastro": []},
        {"classe": "contexto", "rotulo": "Contexto do processo", "texto": "O processo está na fase inicial.",
         "lastro": ["T7_SINTESE_FATOS"]},
    ]
    r = avaliar(ruim)
    assert any("nenhum lastro chega" in v for v in r.violacoes), r.violacoes


def test_a_question_that_declares_a_section_that_was_not_published_is_a_violation(caso):
    ruim = copy.deepcopy(caso)
    ruim["questoes"][0]["secao"] = "Seção que o resumo não publicou"
    r = avaliar(ruim)
    assert any("seção declarada" in v for v in r.violacoes), r.violacoes


def test_a_law_cited_by_a_synthesis_with_no_checked_grounds_item_is_a_violation(caso):
    """Citar lei é afirmar que ela está no documento. A violação repete a lei como a síntese a escreveu,
    senão quem lê o relatório não acha o trecho na tela.

    O caso ruim é montado aqui e não tirado do corpus: enquanto o caso gravado carregava seis dispositivos
    sem fundamento conferido, este teste passava de graça, e teria passado a falhar no dia em que o motor
    parasse de fazer isso."""
    ruim = copy.deepcopy(caso)
    # A classe fundamentos fica, vazia, que é o caso real: o contrato não cita lei nenhuma. O lastro aponta
    # para fatos, no formato que o serviço grava, então o que sobra de errado é a lei sem fundamento conferido.
    ruim["inferencias"]["sinteses"] = [{
        "classe": "fundamentos",
        "texto": "O pedido se apoia no art. 22 da Lei nº 8.906/1994.",
        "lastro": ["fatos[0]"],
    }]
    r = avaliar(ruim)
    aviso = next((v for v in r.violacoes if "fundamentos conferido" in v), "")
    assert aviso, r.violacoes
    assert "Lei nº 8.906/1994" in aviso, aviso


# ── Camada 2: as duas medidas novas ───────────────────────────────────────────

def test_the_share_of_syntheses_with_anchor_is_measured():
    r = avaliar(plantado("synthesis-without-anchor.json"))
    assert r.metricas["sinteses_com_lastro"] == 0.5, r.metricas


def test_the_share_of_questions_declaring_a_published_section_is_measured(caso):
    """O caso gravado não traz seção em pergunta nenhuma, e a medida precisa mostrar isso em vez de calar."""
    assert avaliar(caso).metricas["perguntas_com_secao"] == 0.0
    assert avaliar(plantado("synthesis-without-anchor.json")).metricas["perguntas_com_secao"] == 1.0


# ── E11-T12: os pisos ─────────────────────────────────────────────────────────

def test_the_floors_demand_a_quote_in_every_section_and_an_anchor_in_every_synthesis():
    """A landing promete trecho literal em toda explicação. Piso de 0.60 é a promessa valendo para metade."""
    from evals.regras import PISOS

    assert PISOS["cobertura_ancora"] == 1.0
    assert PISOS["sinteses_com_lastro"] == 1.0


@pytest.mark.parametrize("arquivo", ["hidden-text.json", "invisible-character.json",
                                     "synthesis-without-anchor.json"])
def test_every_planted_case_is_rejected(arquivo):
    r = avaliar(plantado(arquivo))
    assert r.violacoes, f"{arquivo} passou: a bateria parou de pegar o que ele planta"


def test_the_planted_cases_stay_out_of_the_gated_corpus():
    """Eles existem para reprovar. Dentro do corpus que o runner mede, tornariam a porta vermelha para sempre."""
    nomes = [c["nome"] for c in carregar_casos()]
    assert not any(n.startswith("plantado-") for n in nomes), nomes


def test_a_law_written_with_a_short_year_still_counts_as_the_same_law():
    """O documento escreve "Lei 8.906/94" e a síntese escreve "Lei nº 8.906/1994". É a mesma lei, e uma bateria
    que grita aqui vira ruído: quem recebe violação falsa para de ler as verdadeiras."""
    documento = "O contrato invoca a Lei 8.906/94, art. 22, para cobrar os honorários."
    trecho = "a Lei 8.906/94, art. 22"
    inicio = documento.index(trecho)
    caso = {
        "nome": "lei-com-ano-curto",
        "documento": documento,
        "topicos": [],
        "questoes": [],
        "inferencias": {
            "classes": [{"classe": "fundamentos", "rotulo": "Fundamentos", "itens": [
                {"ref": "fundamentos[0]", "campo": "lei", "valor": "Lei 8.906/94, art. 22", "trecho": trecho,
                 "pos": [inicio, inicio + len(trecho)], "conferido": True}]}],
            "sinteses": [{"classe": "fundamentos", "rotulo": "Fundamentos",
                          "texto": "A cobrança se apoia no art. 22 da Lei nº 8.906/1994.",
                          "lastro": ["fundamentos[0]"]}],
        },
    }
    assert avaliar(caso).violacoes == []


def _explicacao_completa() -> dict:
    """O que o motor publica quando a porta de fidelidade deixa passar: toda seção que promete trecho traz um."""
    documento = ("Maria Silva contrata o escritório Alfa. O contrato prevê honorários de 20% sobre o proveito "
                 "econômico. Maria pede a devolução do valor pago a maior.")
    return {
        "nome": "explicacao-completa",
        "documento": documento,
        "topicos": [
            {"id": 1, "titulo": "Resumo em uma linha", "explicacao_md": "Contrato de honorários de Maria."},
            {"id": 2, "titulo": "👥 Quem está nesta história", "explicacao_md": "Maria e o escritório.",
             "trecho": "Maria Silva contrata o escritório Alfa."},
            {"id": 3, "titulo": "🤝 O que está sendo pedido", "explicacao_md": "A devolução.",
             "trecho": "Maria pede a devolução do valor pago a maior."},
        ],
        "questoes": [],
        "inferencias": {
            "classes": [{"classe": "identificacao", "rotulo": "Identificação", "itens": [
                {"ref": "identificacao[0]", "campo": "parte", "valor": "Maria Silva",
                 "trecho": "Maria Silva contrata o escritório Alfa.", "pos": [0, 39], "conferido": True}]}],
            "sinteses": [{"classe": "identificacao", "rotulo": "Identificação",
                          "texto": "Maria contratou o escritório Alfa.", "lastro": ["identificacao[0]"]}],
        },
    }


def test_a_section_the_protocol_links_to_no_class_does_not_hold_the_coverage_down():
    """"Resumo em uma linha" fala do caso inteiro, e o protocolo não a liga a classe nenhuma: ela sai sem
    trecho por desenho, e ``topics_from_summary`` a publica assim de propósito.

    Contá-la no denominador põe o piso de 1.0 fora de alcance, porque a explicação impecável mede 0.8 e o
    aviso passa a aparecer para sempre. Piso que nunca pode ser atingido não mede piora: ensina a ignorar o
    aviso, que é o contrário do que ele existe para fazer. É também a conta que ``fidelity_report`` já faz no
    pipeline, e as duas portas precisam medir a mesma coisa."""
    r = avaliar(_explicacao_completa())
    assert r.metricas["cobertura_ancora"] == 1.0, r.metricas
    assert r.avisos == [], r.avisos
    assert r.violacoes == [], r.violacoes


def test_a_section_that_was_promised_a_quote_and_shows_none_still_lowers_the_coverage():
    """A guarda do teste acima: o denominador encolhe para as seções que prometem trecho, não para as que
    trazem um. Sem isso, apagar o trecho de uma seção mediria 1.0 e a porta viraria enfeite."""
    caso = _explicacao_completa()
    caso["topicos"][2].pop("trecho")
    r = avaliar(caso)
    assert r.metricas["cobertura_ancora"] == 0.5, r.metricas
    assert any("cobertura_ancora" in a for a in r.avisos), r.avisos
