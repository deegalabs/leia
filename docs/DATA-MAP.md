# Mapa de dados: o que a LeIA guarda hoje

Uma linha por dado que **existe em linha de código em 20/09/2026**, lido de
[`apps/llm-service/core/db.py`](../apps/llm-service/core/db.py) e de
[`apps/llm-service/core/workspace.py`](../apps/llm-service/core/workspace.py). É o insumo do ADR sobre base
legal (E17-T02) e dos textos públicos (E17-T03), que são escritos e revisados por quem responde
juridicamente pelo produto.

**A coluna "base legal" é proposta, não decidida.** Ela vem da pesquisa jurídica do projeto
(`docs/research/legal/02-lgpd-e-consentimento.md`, §3 e §11), que não é versionada neste repositório porque
vive no espaço de trabalho da equipe. Essa pesquisa foi escrita para uma arquitetura anterior, com CPF,
voz, cifra por documento e contrato em cadeia, e portanto **não descreve o que roda aqui**. Onde ela supõe
algo que não existe, está dito na linha. Nada desta página deve ser publicado como política antes da
revisão de E17-T02.

**A coluna "prazo" é a mesma coisa, com um agravante:** hoje **nada apaga nada**. Não existe rotina de
retenção, varredura de expiração nem eliminação por prazo em nenhum lugar do serviço. Os únicos `unlink()`
do código são o `reprocessar`, que apaga artefato para refazer a rodada
([`leia/api_tasks.py`](../apps/llm-service/leia/api_tasks.py)), e a limpeza de sessão
([`core/session.py`](../apps/llm-service/core/session.py)). Enquanto E17-T15 não existir, o prazo real de
todo dado desta página é **indefinido**, e é isso que a política tem que dizer, ou ela mente.

## 1. Banco de dados

| Dado | Tabela e campos | Para quê | Quem vê | Base legal proposta | Prazo real hoje |
|---|---|---|---|---|---|
| Conta de quem envia | `Usuario`: `email`, `senha_hash`, `nome`, `papel`, `session_token`, `criado_em` | entrar, saber de quem é cada documento | a própria pessoa e o papel `fornecedor` | art. 7º, V (execução de contrato) | indefinido |
| Documento enviado | `Tarefa`: `titulo`, `pdf_nome`, `document_sha256`, `workspace_path`, `status`, `origem`, `advogado_id`, `cidadao_id`, datas | organizar o trabalho e ligar o documento a quem o enviou e a quem ele diz respeito | quem enviou, a cidadã vinculada, `fornecedor` | art. 7º, V; **art. 11, II, "d"** quando o documento revela dado sensível, que é o caso comum | indefinido |
| Passos da rodada | `LogEvento`: `tipo`, `payload` (até 2000 caracteres), `ts` | mostrar a preparação e auditar o que o motor fez | quem vê a tarefa; a rota pública filtra por `PUBLIC_EVENT_TYPES` | art. 7º, II (dever de informar) | indefinido |
| Conferência | `Tentativa`: `respostas`, `acertos`, `total`, `aprovado`, `consultas`, `hash_imutavel`, `criada_em` | medir a compreensão e sustentar o comprovante | quem vê a tarefa; o comprovante público mostra só o agregado | art. 7º, VI (prova); **art. 11, II, "d"** pelas respostas revelarem o conteúdo do documento | indefinido |
| Registro congelado | `ConsentRecord`: `attempt_hash`, `document_sha256`, `summary_sha256`, `canonical`, `payload_sha256` | permitir que um terceiro confira o comprovante sem pedir nada à equipe | qualquer pessoa com o link do comprovante | art. 7º, VI | indefinido; a pesquisa propõe 5 anos |
| Convite | `Invite`: `email` (opcional), `expires_at`, `revoked_at`, `created_by` | dizer a quem o link foi endereçado e poder cancelá-lo | quem enviou o documento | art. 7º, V | indefinido |
| Dúvida da cidadã | `Duvida`: `texto`, `contexto` (trecho da conversa), `resposta` | levar a pergunta dela a quem enviou o documento | ela e quem enviou | art. 7º, V; **art. 11, II, "d"** pelo contexto citar o documento | indefinido |

## 2. Arquivos no workspace

Tudo abaixo vive em `WORKSPACE_DIR/<hash da tarefa>/`. O `hash` é a credencial do link, então **quem tem o
link alcança o que as rotas públicas expõem**.

A primeira versão desta tabela saiu de ler `core/workspace.py`, que é quem grava quase tudo. Faltou o
`chat_llm_debug.jsonl`, escrito direto pelo `main.py` e por isso invisível para aquela leitura. Levantamento
por um módulo só encontra o que passa por aquele módulo.

| Arquivo | O que é | Para quê | Quem vê | Prazo real hoje |
|---|---|---|---|---|
| `original.pdf` | o documento como chegou, íntegro | extrair o texto, e nada além disso | ninguém: **ele é apagado assim que o texto é gravado** (E17-T06) | existe entre o envio e a extração, medido em segundos |
| `texto_extraido.txt` | o texto do PDF | é o que o motor lê e é contra ele que toda âncora é conferida | quem vê a tarefa; sai na rota de inferências | indefinido |
| `meta.json` | `hash`, `titulo`, nome e id de quem enviou, nome e tamanho do PDF | identificar a pasta | quem enviou (é baixável, e por isso não traz e-mail) | indefinido |
| `log.jsonl` | eventos da rodada | auditoria da preparação | idem `LogEvento`; **não grava endereço de rede nem navegador** | indefinido |
| `T0..T14_*.json`, `memoria_persistente.json`, `texto_tagueado.json` | saída de cada etapa, com trechos literais do documento | montar a explicação e as marcações | quem vê a tarefa | indefinido |
| `tipo_documento.json` e `tipo_documento_revisado.json` | a espécie que o motor leu e a correção do advogado | escolher o vocabulário das extrações | quem vê a tarefa | indefinido |
| `resumo_humanizado.md` e `questoes.json` | a explicação e as perguntas | é o que a pessoa lê e responde | ela, depois de liberado | indefinido |
| `pdf_assinado.pdf` | comprovante em PDF | entregar o registro em papel | quem baixa | indefinido |
| `carimbo_*.ots` | prova OpenTimestamps do `payloadHash` | provar anterioridade | qualquer pessoa pelo link de verificação | permanente por natureza; não contém dado pessoal |
| `chat_llm_debug.jsonl` | o prompt mandado ao modelo e a resposta, texto integral | depurar o chat do orquestrador | quem tem acesso ao disco do serviço | indefinido · ver [#102](https://github.com/deegalabs/leia/issues/102) |

## 3. Quem é controlador, e a pergunta que o ADR precisa responder

A pesquisa (§3) atribui **controlador ao advogado** e **operador à plataforma**. Isso descreve o fluxo em
que o advogado envia o documento, que é a `origem = "advogado"`.

Só que o produto aceita a cidadã enviar o próprio documento sozinha (`origem = "cidadao"`,
[`leia/api_tasks.py::create_task`](../apps/llm-service/leia/api_tasks.py)), e aí **não há advogado nenhum
no circuito**: nesse caminho a Deega Labs decide finalidade e meios, e a pesquisa não cobre o caso.
Responder isso é o ADR-0010 (E17-T02), e é a pergunta mais consequente desta página.

## 4. O que já não é guardado, e vale registrar

- **Endereço de rede e navegador na conferência.** `attempt_hash` v1 os misturava no preimage, então o
  identificador público do comprovante carregava dado pessoal e ninguém conseguia recalculá-lo. A v2 parou
  de gravá-los, as colunas ficaram mortas no esquema, e o PDF assinado seguiu lendo e imprimindo as duas
  até 20/09/2026. **As colunas foram removidas** (E17-T07, issue #30): a migração é a única do serviço que
  apaga dado, e apagar é a intenção.
- **O PDF, depois da extração.** Ele é o dado mais sensível que o produto toca e nada mais o lê depois que
  o texto está gravado: o motor trabalha sobre o texto, as âncoras são conferidas contra o texto, e o
  `documentSha256` do comprovante vem de `Tarefa.document_sha256`, gravado no envio. Refazer um documento e
  abrir uma rodada nova passaram a partir do texto guardado, porque o contrário deixaria a correção de
  espécie do advogado sendo um botão que não faz nada. O mapa de serviço de 17/09 registrava que a tela
  dizia "o PDF em si não é guardado" sem bater com o código: agora bate.
- **O documento não sai para terceiro.** Os dois fluxos que mandavam o PDF para fora foram removidos; o que
  vai ao provedor do modelo é o texto extraído, e a retenção zero na conta do provedor é **E17-T08, ainda
  não confirmada** (issue #38).
- **O e-mail fica fora do `meta.json`**, que é baixável.
- **Nada pessoal vai para o carimbo público:** o que é carimbado é o hash do payload canônico, e o payload
  traz apenas hashes e agregados (`leia.payload.v4`, SPEC-001).
