# Bateria de avaliação

Sem ela, toda mudança no motor é avaliada de cabeça: alguém roda um documento, olha a tela e decide se melhorou.
Aqui a pergunta "melhorou ou piorou" tem resposta em número, e a resposta roda em segundos, sem chave de modelo.

```bash
python -m evals.run     # imprime o que mediu; sai diferente de zero se houver violação de contrato
python -m pytest -q     # a bateria também roda como teste, junto com o resto
```

## O que é um caso

Um arquivo em `casos/` com a **saída pública** de uma tarefa real: o texto extraído do documento, os tópicos que a
cidadã lê, as perguntas que ela responde e as inferências que o advogado revisa. É de propósito a saída pública, e
não os artefatos internos: o que interessa medir é o que as pessoas veem.

Os casos são gravados, não gerados na hora. Rodar o pipeline dentro da bateria mediria três coisas ao mesmo tempo
(modelo, rede e código) e nenhuma delas com precisão, e uma porta que depende de rede não é porta.

## As três camadas, e por que os papéis são diferentes

| Camada | Papel | O que confere |
|---|---|---|
| 1. Contrato | **reprova** | o trecho mostrado está no documento; a posição informada é a posição certa; o gabarito não viaja com a pergunta; a síntese aponta lastro que chega a item de memória; a lei citada na síntese tem item de fundamentos conferido; a pergunta declara seção que foi publicada |
| 2. Qualidade | informa, com piso | cobertura e precisão de âncora, lastro por síntese, seção declarada por pergunta |
| 3. Juiz | não implementada | apoio semântico e clareza |

A camada 1 conta violações em vez de tirar média. Com conjunto pequeno, média não detecta queda pequena: um caso
errado entre trinta some numa média e aparece numa contagem.

O piso da camada 2 existe para impedir piora silenciosa, não para dar nota. Subir um piso é decisão de quem
melhorou o motor; cair abaixo dele é regressão e aparece como aviso.

A camada 3 não existe ainda, e dizer isso é parte do desenho. Ela exige um modelo de família diferente da que
gerou o texto e um conjunto rotulado à mão para calibrar, com a concordância entre o juiz e o humano publicada ao
lado de todo número que ele produzir. Um juiz sem essa calibragem produz número que parece medida e não é.

## Casos plantados

`casos/planted/` guarda o caso feito a mão para provar que a bateria reprova: síntese com texto e lastro vazio,
trecho que só existia na camada escondida do PDF, trecho com caractere invisível dentro da palavra. Eles ficam
fora do corpus que `python -m evals.run` mede, porque existem para ficar vermelhos; quem os roda é
`tests_evals.py`. Bateria que nunca reprova não é porta, é enfeite, e é isso que eles impedem.

## Crescer o corpus

Toda falha vista em uso entra como caso no mesmo commit que a corrige. É assim que a bateria continua informando:
se ela ficar perfeita por muito tempo, parou de medir e precisa de casos mais difíceis.

Nada de documento de pessoa real aqui. Os casos deste diretório saem de documentos fictícios, como o de
`examples/`.

Documento de verdade fica **fora do repositório**, e a bateria o lê por uma pasta indicada em `LEIA_EVAL_CASES`:

```bash
LEIA_EVAL_CASES=~/leia-corpus python -m evals.run
```

A consequência é real: o que roda na integração contínua é só o corpus público. O privado pega o que o público
não pega e só roda quando alguém o roda. A estrutura de cada tipo de peça, que é o conhecimento durável, fica
escrita em [docs/DOCUMENT-TYPES.md](../../../docs/DOCUMENT-TYPES.md).
