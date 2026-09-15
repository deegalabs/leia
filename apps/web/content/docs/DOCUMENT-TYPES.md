# Tipos de documento que o motor precisa atravessar

O pipeline não lê "um PDF". Ele lê peças com convenções próprias de redação e de diagramação, e é nessas
convenções que ele quebra, não no assunto. Este documento registra, por tipo, o que o motor encontra pela frente,
o que ele precisa extrair e onde ele costuma falhar.

Serve para duas coisas. Antes de atender um tipo novo, é a lista do que precisa funcionar. Depois de uma falha em
uso, é onde a falha vira conhecimento em vez de virar conserto pontual.

## Como os documentos de verdade são tratados

**Documento real não entra neste repositório.** Ele é público, e a regra do projeto é que nenhum dado pessoal real
seja versionado, nem em exemplo. Então o arquivo fica de fora, na máquina de quem o tem, e a bateria de avaliação
o lê por uma pasta indicada em `LEIA_EVAL_CASES`:

```bash
LEIA_EVAL_CASES=~/leia-corpus python -m evals.run
```

A consequência é real e não dá para esconder: **o que roda na integração contínua é só o corpus público**, com
documentos fictícios. O corpus privado pega o que o público não pega, e só roda quando alguém o roda. Por isso o
que fica escrito aqui é a **estrutura** de cada tipo, que é o conhecimento durável; o arquivo é descartável.

Quando um documento real vira caso, ele passa antes por anonimização: fora nome, documento de identidade, número
de processo, endereço, valores identificáveis e datas exatas. O que precisa sobreviver é a forma, não a identidade.

## Contrato de honorários advocatícios

| | |
|---|---|
| **Estrutura** | preâmbulo com qualificação das partes, cláusulas numeradas, assinaturas e testemunhas ao final |
| **O que o motor extrai** | quem contrata e quem é contratado, forma e percentual de pagamento, hipótese de êxito, despesas e custas, rescisão |
| **Onde costuma falhar** | percentual escrito por extenso e em número na mesma frase; cláusula de êxito condicional lida como pagamento garantido; qualificação das partes em bloco único sem pontuação |
| **No corpus** | `evals/casos/contrato-honorarios.json`, do PDF fictício em `examples/` |

## Procuração

| | |
|---|---|
| **Estrutura** | outorgante, outorgado, poderes gerais e poderes especiais em lista corrida |
| **O que o motor extrai** | quem dá poderes a quem, quais poderes especiais, prazo e limites |
| **Onde costuma falhar** | a lista de poderes é uma frase só, longuíssima, e o motor precisa separar o que é cláusula ad judicia do que é poder especial de transigir, receber e dar quitação, que é o que muda a vida da pessoa |

## Petição inicial

| | |
|---|---|
| **Estrutura** | endereçamento, qualificação, dos fatos, do direito, dos pedidos, do valor da causa |
| **O que o motor extrai** | quem pede o quê contra quem, a linha do tempo dos fatos, o que está sendo pedido em cada item |
| **Onde costuma falhar** | a seção do direito é densa em citação e o motor tende a resumi-la como se fosse fato; pedidos alternativos e subsidiários viram um pedido só |

## Decisão, sentença e acórdão

| | |
|---|---|
| **Estrutura** | relatório, fundamentação, dispositivo; acórdão traz ementa e voto |
| **O que o motor extrai** | o que foi decidido, para quem, e o que ainda cabe fazer |
| **Onde costuma falhar** | o dispositivo é o que importa para a pessoa e é a menor parte do texto; a fundamentação cita teses que **não** foram acolhidas, e resumir sem distinguir isso inverte o resultado |

## Peça recursal (agravo, apelação)

| | |
|---|---|
| **Estrutura** | referência à decisão recorrida, razões, pedido de reforma |
| **O que o motor extrai** | o que a decisão anterior decidiu, o que se quer mudar e por quê |
| **Onde costuma falhar** | o documento fala o tempo todo de **outro** documento, e o motor precisa não confundir o que a decisão anterior disse, o que o precedente citado diz e o que a parte afirma agora |
| **No corpus** | privado, um agravo em recurso especial de 14 páginas |

Medido nesse agravo, e os números valem mais que a impressão:

| O que medi | Resultado | Consequência |
|---|---|---|
| Camada de texto | presente, 25 mil caracteres em 14 páginas | não é caso de digitalização |
| Cabeçalho do órgão | repetido nas 14 páginas | vira ruído no texto extraído ([#50](https://github.com/deegalabs/leia/issues/50)) |
| Citação de outra decisão | 26,5% do documento | três vozes para distinguir ([#51](https://github.com/deegalabs/leia/issues/51)) |
| Espaço inserido dentro de palavra pelo extrator | frequente (`no s arts`, `o se u provimento`) | a busca exata falha, a aproximada acha com 0,98 |
| Âncora literal sobre 60 frases do documento | nenhuma perdida | o desenho em três estágios era necessário, não enfeite |

O quarto item é o que justifica a existência do estágio aproximado. O extrator devolve `o se u provimento`, o
modelo devolve `o seu provimento`, e nenhuma normalização de espaço junta `se` com `u`. Sem o terceiro estágio,
toda frase com essa quebra perderia a âncora, e a tela deixaria de mostrar o trecho. Com ele, a frase é achada e a
tela diz a verdade sobre como: "com pequenas diferenças de digitação", em vez de afirmar cópia exata.

## Acordo

| | |
|---|---|
| **Estrutura** | partes, objeto, obrigações de cada lado, prazos, cláusula de quitação |
| **O que o motor extrai** | quem paga o quê, quando, e o que a pessoa deixa de poder cobrar depois |
| **Onde costuma falhar** | a quitação é a cláusula de maior consequência e a de redação mais discreta |

## Casos patológicos

Esses não são tipos de peça, são formas de o arquivo estar quebrado. Rendem mais defeito por caso do que qualquer
documento bem formado, e são construídos, não coletados.

| Caso | O que precisa acontecer |
|---|---|
| PDF digitalizado, sem camada de texto | recusa explicada, em vez de uma explicação sobre nada |
| PDF com texto invisível carregando instrução | a instrução é ignorada; o texto do documento é dado, nunca comando |
| Reconhecimento de texto ruim | o trecho literal continua sendo encontrado, ou o item não recebe selo |
| Diagramação em duas colunas ou tabela pesada | a ordem de leitura não embaralha frases de colunas diferentes |
| Documento muito longo | o pipeline não estoura o contexto em silêncio |
