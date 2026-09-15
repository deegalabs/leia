"""A bateria de avaliação do motor, em camadas, sobre casos gravados.

Por que gravados e não rodando o pipeline: o pipeline depende de modelo, de chave e de rede, então uma bateria
que o executa mede três coisas ao mesmo tempo e não serve de porta. Aqui o caso é a saída pública que a cidadã e
o advogado de fato veem, capturada de uma tarefa real, e o que se mede é o produto, não a API.

As camadas têm papéis diferentes de propósito:

- **Camada 1, contrato.** Reprova. São afirmações que o produto faz e que ou são verdade ou não são: o trecho
  mostrado está no documento, a posição informada é a posição certa, o gabarito não chega junto com a pergunta.
  Contagem de violação, não média: com conjunto pequeno, média não detecta queda pequena.
- **Camada 2, qualidade.** Informa, com piso. Cobertura e precisão de âncora. Piso existe para impedir piora
  silenciosa, não para dar nota.
- **Camada 3, juiz.** Não implementada. Exige modelo de família diferente da que gerou e um conjunto rotulado à
  mão para calibrar. Fingir que existe seria pior que não ter.
"""
from __future__ import annotations

import json
import os
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

CASOS_DIR = Path(__file__).resolve().parent / "casos"

# Pisos: o que já foi medido e não pode piorar. Subir um piso é decisão, cair é regressão.
PISOS = {
    "cobertura_ancora": 0.60,
    "precisao_ancora": 1.0,
    "itens_conferidos": 1.0,
}
# O gabarito e a explicação da resposta nunca podem viajar com a pergunta.
CAMPOS_DE_GABARITO = ("correta", "justificativa", "resposta_correta")


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


def avaliar(caso: dict) -> Resultado:
    r = Resultado(caso=str(caso.get("nome") or "sem nome"))
    documento = caso.get("documento") or ""
    topicos = caso.get("topicos") or []
    questoes = caso.get("questoes") or []
    classes = (caso.get("inferencias") or {}).get("classes") or []
    itens = [i for c in classes for i in (c.get("itens") or [])]

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

    # ── Camada 2 ──────────────────────────────────────────────────────────────
    com_trecho = [t for t in topicos if t.get("trecho")]
    conferidos = [i for i in itens if i.get("conferido")]
    r.metricas = {
        "cobertura_ancora": round(len(com_trecho) / len(topicos), 3) if topicos else 0.0,
        "precisao_ancora": round(sum(1 for t in com_trecho if _achavel(documento, t["trecho"])) / len(com_trecho), 3) if com_trecho else 1.0,
        "itens_conferidos": round(len(conferidos) / len(itens), 3) if itens else 1.0,
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
    só roda quando alguém o roda."""
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
