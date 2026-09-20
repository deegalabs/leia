"""A bateria de avaliação do motor, em camadas, sobre casos gravados.

Por que gravados e não rodando o pipeline: o pipeline depende de modelo, de chave e de rede, então uma bateria
que o executa mede três coisas ao mesmo tempo e não serve de porta. Aqui o caso é a saída pública que a cidadã e
o advogado de fato veem, capturada de uma tarefa real, e o que se mede é o produto, não a API.

As camadas têm papéis diferentes de propósito:

- **Camada 1, contrato.** Reprova. São afirmações que o produto faz e que ou são verdade ou não são: o trecho
  mostrado está no documento, a posição informada é a posição certa, o gabarito não chega junto com a pergunta,
  a síntese aponta lastro que existe e a lei que ela cita tem item de fundamentos conferido.
  Contagem de violação, não média: com conjunto pequeno, média não detecta queda pequena.
- **Camada 2, qualidade.** Informa, com piso. Cobertura e precisão de âncora, lastro por síntese e seção
  declarada por pergunta. Piso existe para impedir piora silenciosa, não para dar nota.
- **Camada 3, juiz.** Não implementada. Exige modelo de família diferente da que gerou e um conjunto rotulado à
  mão para calibrar. Fingir que existe seria pior que não ter.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

CASOS_DIR = Path(__file__).resolve().parent / "casos"

# Pisos: o que já foi medido e não pode piorar. Subir um piso é decisão, cair é regressão.
# cobertura_ancora is 1.0 because the product promises a literal quote in every published section, and a floor
# of 0.60 is that promise holding for half of the screen.
PISOS = {
    "cobertura_ancora": 1.0,
    "precisao_ancora": 1.0,
    "itens_conferidos": 1.0,
    "sinteses_com_lastro": 1.0,
    # Pendente desde E11-T12 esperando alguma pergunta declarar `secao`. Desde E12 todas declaram, e a
    # pergunta que não declara nem chega a ser publicada, então o piso pode ser o que o produto promete.
    "perguntas_com_secao": 1.0,
}
# O gabarito e a explicação da resposta nunca podem viajar com a pergunta.
CAMPOS_DE_GABARITO = ("correta", "justificativa", "resposta_correta")

# An anchor written as ``fatos[6]`` names one item of the persistent memory; anything else, such as
# ``T7_SINTESE_FATOS``, names another synthesis and has to be followed until it reaches an item.
ITEM_REF = re.compile(r"^[a-z_]+\[\d+\]$", re.IGNORECASE)

# A statute number is a claim about the world, not about the document. Either a checked ``fundamentos`` item
# carries it, or the model wrote it on its own.
LEGAL_REF = re.compile(
    r"\b(?:art(?:igo|\.)\s*\d+|s[úu]mula\s*(?:n[º°.]*\s*)?\d+|lei\s*(?:n[º°.]*\s*)?[\d.]+\s*/\s*\d{2,4})",
    re.IGNORECASE,
)


@dataclass
class Resultado:
    caso: str = ""
    violacoes: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    metricas: dict[str, float] = field(default_factory=dict)

    @property
    def passou(self) -> bool:
        return not self.violacoes and not self.avisos


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def _achavel(documento: str, trecho: str) -> bool:
    """O trecho existe no documento, ignorando espaçamento e caixa. Mesma tolerância da tela, nem mais nem menos."""
    if not trecho:
        return False
    doc = " ".join(_sem_acento(documento).split())
    q = " ".join(_sem_acento(trecho).split())
    return bool(q) and q in doc


def _na_posicao(documento: str, trecho: str, pos) -> bool:
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        return False
    a, b = pos
    if not (isinstance(a, int) and isinstance(b, int) and 0 <= a < b <= len(documento)):
        return False
    recorte = " ".join(_sem_acento(documento[a:b]).split())
    return recorte == " ".join(_sem_acento(trecho).split())


def _texto_comparavel(s: str) -> str:
    return " ".join(_sem_acento(s or "").split())


def _legal_refs(texto: str) -> dict[str, str]:
    """Every statute the text names, keyed by a canonical form so ``art. 85`` and ``artigo 85`` count as one.

    The key keeps only species and number: what matters here is whether the document itself carries that
    statute, not how the sentence around it was written. The value keeps the wording of the text, because a
    report that renames what it read makes the reader hunt for a sentence that is not there."""
    achados: dict[str, str] = {}
    for bruto in LEGAL_REF.findall(texto or ""):
        plano = _sem_acento(bruto)
        numero = "".join(c for c in plano if c.isdigit() or c in "./").strip("./")
        especie = "art" if plano.startswith("art") else "sumula" if plano.startswith("sumula") else "lei"
        if especie == "lei" and "/" in numero:
            # "Lei 8.906/94" in the document and "Lei nº 8.906/1994" in the synthesis are the same statute.
            # Telling them apart would raise a false violation, and false violations teach people to skip
            # reading the true ones.
            corpo, _, ano = numero.rpartition("/")
            numero = f"{corpo}/{ano[-2:]}"
        canonico = f"{especie} {numero}"
        if numero:
            achados.setdefault(canonico, bruto.strip())
    return achados


def _synthesis_named_by(ref: str, sinteses: list[dict]) -> dict | None:
    """The synthesis this anchor points at, as ``T7_SINTESE_FATOS`` points at the synthesis of ``fatos``.

    An item anchor never names a synthesis, even when the class matches: ``fatos[99]`` claims one item of the
    memory, so it has to be found among the items or it is a dead reference."""
    if ITEM_REF.match(str(ref)):
        return None
    alvo = _sem_acento(str(ref))
    for s in sinteses:
        classe = _sem_acento(str(s.get("classe") or ""))
        if classe and classe in alvo:
            return s
    return None


def _reaches_an_item(sintese: dict, sinteses: list[dict], refs: set[str], vistas: set[str] | None = None) -> bool:
    """Whether some anchor of this synthesis ends on an item of the memory, following anchors between syntheses.

    The chain matters because the synthesis of ``contexto`` leans on the other syntheses instead of on the
    document, and it is legitimate while the chain ends on an item someone can check against the text."""
    vistas = set() if vistas is None else vistas
    classe = str(sintese.get("classe") or "")
    if classe in vistas:
        return False
    vistas.add(classe)
    for ref in sintese.get("lastro") or []:
        if str(ref) in refs:
            return True
        alvo = _synthesis_named_by(ref, sinteses)
        if alvo is not None and _reaches_an_item(alvo, sinteses, refs, vistas):
            return True
    return False


def _sections_that_promise_a_quote(topicos: list[dict]) -> list[dict]:
    """The published sections that promised a literal quote, which is the denominator of the coverage.

    Not every section promises one. The protocol links each heading of the summary to the memory classes it
    explains and links "Resumo em uma linha" to none, because that one talks about the whole case: it is
    published without a quote by design. Counting it puts the floor of 1.0 out of reach, so the warning would
    fire on a flawless explanation and stop meaning anything, which is the opposite of a floor. It is also the
    denominator ``fidelity_report`` already uses in the pipeline, and two gates measuring the same promise
    differently is a gate nobody can act on.

    Only the headings the protocol declares sourceless come out. A heading the protocol does not know is one
    the model invented, and it stays in the denominator: otherwise writing a new heading would be the way to
    dodge the floor.

    The protocol is read through the module that serves the citizen, so the heading normalisation here is the
    one that decides the matter on screen instead of a second copy free to drift from it.
    """
    try:
        from leia.api_citizen import _section_key, section_sources

        fontes = section_sources()
    except Exception:
        fontes = {}
    if not fontes:
        # Unreadable protocol counts every section: a battery that loosens itself when it cannot read tells
        # the reassuring lie instead of the alarming one.
        return list(topicos)
    sem_fonte = {chave for chave, classes in fontes.items() if not classes}
    return [t for t in topicos if _section_key(str(t.get("titulo") or "")) not in sem_fonte]


def avaliar(caso: dict) -> Resultado:
    r = Resultado(caso=str(caso.get("nome") or "sem nome"))
    documento = caso.get("documento") or ""
    topicos = caso.get("topicos") or []
    questoes = caso.get("questoes") or []
    classes = (caso.get("inferencias") or {}).get("classes") or []
    itens = [i for c in classes for i in (c.get("itens") or [])]
    sinteses = [s for s in ((caso.get("inferencias") or {}).get("sinteses") or []) if isinstance(s, dict)]
    refs_de_item = {str(i.get("ref")) for i in itens if i.get("ref")}
    secoes = {_texto_comparavel(t.get("titulo") or "") for t in topicos if t.get("titulo")}
    # The grounds a synthesis may lean on are the checked ones: an item nobody found in the text proves nothing.
    fundamentos_conferidos = " ".join(
        f"{i.get('trecho') or ''} {i.get('valor') or ''}"
        for c in classes if c.get("classe") == "fundamentos" for i in (c.get("itens") or []) if i.get("conferido")
    )
    leis_conferidas = set(_legal_refs(fundamentos_conferidos))

    # ── Camada 1 ──────────────────────────────────────────────────────────────
    for t in topicos:
        trecho = t.get("trecho")
        if trecho and not _achavel(documento, trecho):
            r.violacoes.append(f"tópico {t.get('id')}: o trecho mostrado não está no documento")
        if t.get("conferencia") and not trecho:
            r.violacoes.append(f"tópico {t.get('id')}: diz que conferiu e não mostra trecho nenhum")

    for it in itens:
        if not it.get("conferido"):
            continue
        if not _na_posicao(documento, it.get("trecho") or "", it.get("pos")):
            r.violacoes.append(f"item {it.get('ref')}: a posição informada não contém o trecho")

    for q in questoes:
        vazados = [c for c in CAMPOS_DE_GABARITO if c in q]
        if vazados:
            r.violacoes.append(f"pergunta {q.get('id')}: o gabarito viaja junto ({', '.join(vazados)})")
        secao = str(q.get("secao") or "").strip()
        if not secao:
            r.violacoes.append(f"pergunta {q.get('id')}: não diz de qual seção da explicação ela veio")
        elif _texto_comparavel(secao) not in secoes:
            r.violacoes.append(f"pergunta {q.get('id')}: a seção declarada não foi publicada ({secao})")
        # A pergunta é o que vira comprovante, e o comprovante afirma que a pessoa entendeu o **documento**.
        # Pergunta sem trecho mede a lembrança de uma conversa; pergunta com trecho que ninguém acha no
        # documento mede uma frase que o modelo escreveu. As duas fazem o comprovante afirmar demais.
        trecho = str(q.get("trecho") or "").strip()
        if not trecho:
            r.violacoes.append(f"pergunta {q.get('id')}: não mostra trecho nenhum do documento")
        elif not _achavel(documento, trecho):
            r.violacoes.append(f"pergunta {q.get('id')}: o trecho mostrado não está no documento")

    # The synthesis is the longest text the citizen reads, and until now the battery looked at none of them:
    # that is how the recorded case publishes 1293 characters of grounds, citing six statutes, with no anchor.
    for sint in sinteses:
        classe = sint.get("classe") or "sem classe"
        texto = str(sint.get("texto") or "").strip()
        lastro = [str(x) for x in (sint.get("lastro") or [])]
        if texto and not lastro:
            r.violacoes.append(f"síntese {classe}: tem texto e não aponta lastro nenhum")
        for ref in lastro:
            if ref not in refs_de_item and _synthesis_named_by(ref, sinteses) is None:
                r.violacoes.append(f"síntese {classe}: o lastro {ref} não existe nas classes")
        if texto and lastro and not _reaches_an_item(sint, sinteses, refs_de_item):
            r.violacoes.append(f"síntese {classe}: nenhum lastro chega a item de memória")
        sem_conferencia = [como_escrito for chave, como_escrito in _legal_refs(texto).items()
                           if chave not in leis_conferidas]
        if sem_conferencia:
            r.violacoes.append(
                f"síntese {classe}: cita lei sem item de fundamentos conferido ({', '.join(sem_conferencia)})"
            )

    # ── Camada 2 ──────────────────────────────────────────────────────────────
    com_trecho = [t for t in topicos if t.get("trecho")]
    prometem_trecho = _sections_that_promise_a_quote(topicos)
    cumpriram = [t for t in prometem_trecho if t.get("trecho")]
    conferidos = [i for i in itens if i.get("conferido")]
    publicadas = [s for s in sinteses if str(s.get("texto") or "").strip()]
    com_lastro = [s for s in publicadas if _reaches_an_item(s, sinteses, refs_de_item)]
    com_secao = [q for q in questoes if q.get("secao") and _texto_comparavel(str(q["secao"])) in secoes]
    r.metricas = {
        "cobertura_ancora": round(len(cumpriram) / len(prometem_trecho), 3) if prometem_trecho else 0.0,
        "precisao_ancora": round(sum(1 for t in com_trecho if _achavel(documento, t["trecho"])) / len(com_trecho), 3) if com_trecho else 1.0,
        "itens_conferidos": round(len(conferidos) / len(itens), 3) if itens else 1.0,
        "sinteses_com_lastro": round(len(com_lastro) / len(publicadas), 3) if publicadas else 1.0,
        "perguntas_com_secao": round(len(com_secao) / len(questoes), 3) if questoes else 1.0,
    }
    for nome, piso in PISOS.items():
        medido = r.metricas.get(nome, 0.0)
        if medido < piso:
            r.avisos.append(f"{nome} caiu para {medido}, abaixo do piso {piso}")
    return r


def carregar_casos() -> list[dict]:
    """Os casos públicos do repositório, mais os privados de ``LEIA_EVAL_CASES`` quando essa pasta existe.

    Documento de verdade não entra aqui: o repositório é público e a regra do projeto é que nenhum dado pessoal
    real seja versionado, nem em exemplo. Mas um documento que não pode ser medido não serve de teste, então a
    bateria lê também uma pasta de fora, que fica na máquina de quem tem o arquivo. A consequência, e ela é
    real: o que roda na integração contínua é só o corpus público. O privado pega o que o público não pega, e
    só roda quando alguém o roda.

    ``casos/planted/`` fica de fora de propósito, e o ``glob`` não desce em subpasta: os casos de lá existem
    para ser reprovados, e dentro do corpus medido deixariam a porta vermelha para sempre, sem dizer nada sobre
    o motor. Quem os mede é ``tests_evals.py``."""
    pastas = [CASOS_DIR]
    extra = os.getenv("LEIA_EVAL_CASES", "").strip()
    if extra:
        pastas.append(Path(extra))
    casos: list[dict] = []
    for pasta in pastas:
        if not pasta.is_dir():
            continue
        for arquivo in sorted(pasta.glob("*.json")):
            casos.append(json.loads(arquivo.read_text(encoding="utf-8")))
    return casos
