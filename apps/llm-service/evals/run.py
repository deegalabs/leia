"""Roda a bateria sobre os casos gravados e imprime o que mediu.

    python -m evals.run

Sai com código diferente de zero quando há violação de contrato, para servir de porta em automação.
Piso de qualidade aparece como aviso: ele informa piora, não reprova entrega.
"""
from __future__ import annotations

import sys

from evals.regras import PISOS, avaliar, carregar_casos


def main() -> int:
    casos = carregar_casos()
    if not casos:
        print("nenhum caso em evals/casos: a bateria não mede nada")
        return 1

    violacoes = avisos = 0
    for caso in casos:
        r = avaliar(caso)
        print(f"\n■ {r.caso}")
        for nome, valor in r.metricas.items():
            piso = PISOS.get(nome)
            marca = " " if piso is None or valor >= piso else "!"
            print(f"  {marca} {nome:20} {valor:>6}   piso {piso if piso is not None else '-'}")
        for v in r.violacoes:
            print(f"  ✗ {v}")
        for a in r.avisos:
            print(f"  ! {a}")
        violacoes += len(r.violacoes)
        avisos += len(r.avisos)

    print(f"\n{len(casos)} caso(s) · {violacoes} violação(ões) de contrato · {avisos} aviso(s) de qualidade")
    print("camada 3 (juiz) não implementada: exige modelo de outra família e conjunto rotulado à mão")
    return 1 if violacoes else 0


if __name__ == "__main__":
    sys.exit(main())
