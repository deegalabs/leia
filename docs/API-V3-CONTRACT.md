# Contrato v3: contas, painéis, envio pela cidadã, dúvidas ao advogado

Acréscimos ao serviço (`apps/llm-service`) e ao app (`apps/web`) decididos em 13/09 à tarde. JSON, UTF-8, campos em
`snake_case` como no serviço. Autenticação por **token Bearer** (o cookie `sessao` continua para os templates internos).
O app roda em outra origem (Vercel), por isso cookie não serve; o token é o mesmo `Usuario.session_token`.

## Papéis
`papel` em `usuario`: `cidadao` (usa a plataforma por conta própria), `advogado` (envia documentos e responde dúvidas),
`fornecedor` (admin: vê tudo). O admin inicial vem de `ADMIN_EMAIL`/`ADMIN_PASSWORD`. Cadastro aberto para `cidadao`;
para `advogado` só quando `ADVOGADO_SIGNUP=true` (padrão `true` no hackathon).

## Autenticação
| Método e rota | Entrada | Saída |
|---|---|---|
| `POST /api/auth/cadastro` | `{ nome, email, senha, papel: "cidadao" \| "advogado", oab? }` | `{ token, usuario: { id, nome, email, papel } }`; 409 se o e-mail existe; 403 se papel não permitido |
| `POST /api/auth/login` | `{ email, senha }` | `{ token, usuario }`; 401 se inválido |
| `GET /api/auth/me` | Bearer | `{ usuario }` |
| `POST /api/auth/logout` | Bearer | `{ ok: true }` (invalida o token) |

`usuario_atual` passa a aceitar `Authorization: Bearer <token>` além do cookie. Um token por usuário (login novo
invalida o anterior).

## Tarefas (documentos) de quem está logado
| Método e rota | Quem | Entrada | Saída |
|---|---|---|---|
| `GET /api/tarefas` | Bearer | | `{ tarefas: [ { id, hash, titulo, status, criada_em, atualizada_em, link_cliente, origem: "advogado" \| "cidadao", ultima_tentativa: { aprovado, acertos, total, numero } \| null, duvidas_abertas: n, cidadao: { nome } \| null, advogado: { nome } \| null } ] }`. `advogado`/`fornecedor`: as que enviou (`fornecedor`: todas). `cidadao`: as que enviou + as vinculadas a ele |
| `POST /api/tarefas` | Bearer | multipart `titulo`, `pdf` | `{ id, hash, status: "criada" }` e agenda o pipeline. Dono = quem enviou. Se `cidadao`, também `cidadao_id` = ele |
| `GET /api/tarefas/{id}` | Bearer (dono, admin ou cidadã vinculada) | | `{ tarefa: { id, hash, titulo, status, criada_em, atualizada_em, origem }, link_cliente, resumo_md \| null, eventos: [últimos 20], tentativas: [ { numero, acertos, total, aprovado, criada_em, hash_imutavel } ], duvidas: [ { id, texto, contexto, criada_em, respondida, resposta, respondida_em } ], cidadao, advogado }` |
| `POST /api/tarefas/{id}/duvidas/{duvida_id}/responder` | Bearer (dono ou admin) | `{ resposta }` | `{ ok: true }`; marca `respondida=true`, `respondida_em` |
| `POST /api/tarefas/{id}/convite` | Bearer (só quem enviou) | `{ email?, validade_horas? }` | `{ id, email, expira_em, revogado_em, criado_em }`; emitir de novo substitui o convite anterior; validade padrão de 30 dias |
| `DELETE /api/tarefas/{id}/convite` | Bearer (só quem enviou) | | cancela o convite ativo; 404 quando não há convite |

## Cidadã (rotas públicas, governadas pelo convite)

O hash já foi o segredo inteiro: quem tivesse o endereço abria o documento, para sempre, e não havia como
desfazer. Agora o documento pode ter um **convite**, que acrescenta validade, cancelamento e, quando quem
enviou sabe o endereço, uma destinatária única.

Documento **sem convite** se comporta como sempre, para não quebrar link que já circulou. Quem enviou o
documento e a cidadã já vinculada entram sempre.

O convite trabalha em **duas camadas**, e a diferença é deliberada:

| Camada | O que confere | Onde vale |
|---|---|---|
| Validade do link | cancelado, vencido | todas as rotas públicas, com ou sem conta |
| Destinatária declarada | a conta é a do e-mail do convite | só `POST /api/t/{hash}/quiz` e `POST /api/t/{hash}/vincular` |

**Ler e perguntar não exigem conta, de propósito.** Exigir cadastro para ler é barreira justamente para quem
este produto atende, que pode estar num celular emprestado. O que a destinatária protege é o comprovante, que
afirma que **uma pessoa** entendeu o documento. Quem não é ela lê tudo, tira dúvidas, e recebe 403 ao tentar
gravar o registro.

`GET /api/t/{hash}` traz `convite: { enderecado: bool, para: "ma***@exemplo.com" | null, expira_em } | null`,
para a tela avisar antes de a pessoa responder. O endereço vai mascarado: serve para ela reconhecer o próprio
e-mail, não para alguém coletá-lo.

| Método e rota | Entrada | Saída |
|---|---|---|
| `GET /api/t/{hash}` | | como hoje **mais** `advogado: { nome } \| null` (nulo quando o dono é `cidadao`), `tem_advogado: bool`, `cidadao_vinculado: bool`, `duvidas_enviadas: n` |
| `POST /api/t/{hash}/duvida` | `{ texto, contexto?: [ { role: "user" \| "bot", text } ] }` | `{ id, criada_em }`; 409 se a tarefa não tem advogado; limitado por IP |
| `POST /api/t/{hash}/vincular` | Bearer (`cidadao`) | `{ ok: true }`; define `tarefa.cidadao_id` se ainda vazio |
| `GET /api/t/{hash}/inferencias` | | `{ tarefa, texto (texto extraído), classes: [ { classe, rotulo, cor, itens: [ { ref, campo, valor, trecho, pos: [inicio, fim] \| null, conferido, conferencia: { metodo, score } \| ausente, cor } ] } ], sinteses: [ { classe, rotulo, texto, lastro[] } ], total, conferidos }`; 409 enquanto não está pronta |

### Quem confere o trecho

A posição do trecho é **sempre** encontrada pelo serviço, nunca lida do que o modelo escreveu. Modelo de linguagem não conta caractere, então a posição que ele devolve é palpite com cara de fato: pode parecer válida e apontar para a cláusula errada, ou para uma cláusula qualquer quando o trecho foi inventado. Acreditar nela transforma o selo de trecho conferido, que é a promessa central do produto, em decoração.

A busca tem três estágios, e o item diz qual deles achou:

| `metodo` | Como achou | `score` |
|---|---|---|
| `exato` | o trecho está no texto, caractere por caractere | 1.0 |
| `normalizado` | igual, ignorando espaços e maiúsculas | 1.0 |
| `aproximado` | semelhança acima de 0,82 numa janela do texto | a semelhança medida |

Sem nenhum dos três, `conferido` é falso, `pos` é nulo e `conferencia` não vem.

### O registro de consentimento é congelado, não remontado

Quando a tentativa é aprovada, o serviço grava o JSON canônico publicado, o hash dele, o SHA-256 do PDF que a
pessoa recebeu e o SHA-256 da explicação que ela leu. A verificação serve o que foi gravado.

Isso resolve duas coisas ao mesmo tempo. O comprovante passa a dizer **a que documento** se refere, em vez de
provar apenas que houve uma tentativa com N acertos. E a prova para de mudar quando o banco muda: antes o payload
era remontado a cada visita, então alterar uma linha alterava o registro publicado e o carimbo de tempo passava a
vouchar por algo que não existia mais.

Comprovante emitido antes disso não tem registro gravado e continua sendo remontado, para não parar de abrir.

### O contrato de cada etapa do pipeline

Etapa que declara `tipo_saida: json` e devolve algo que não é JSON **falha**, e o documento falha com ela. Antes o
texto cru virava a saída da etapa, era gravado e entrava no contexto da próxima, tudo reportado como sucesso: um
resumo construído sobre lixo é pior que um erro honesto.

Oito etapas declaram também quais campos precisam existir, no campo `schema` do protocolo:

```json
"schema": { "campos": { "sintese_fatos": { "tipo": "objeto", "obrigatorios": ["valor", "lastro"] } } }
```

A verificação é pequena de propósito, e exige só o que o produto consome. Etapa sem `schema` declarado passa
apenas pela checagem de JSON válido.

Uma etapa pode declarar `opcional: true`, e aí a regra acima muda para ela: quando falha, o documento **não** falha
junto. É o caso de `T0_TIPO_DOCUMENTO`. Ela melhora o resto e não pode derrubá-lo: antes de a classificação existir
o documento era explicado, então uma etapa nova capaz de matar a rodada seria regressão para quem só quer entender
o próprio papel. Espécie que não dá para ler vira `indefinido`, que é o vocabulário de sempre.

### De onde vem o trecho de cada tópico

Os títulos das seções do resumo são fixos: quem os define é a tarefa que escreve o resumo, em `protocolo_pdf.json`.
Por isso o vínculo entre seção e trecho é **declarado** ali, no campo `ancoras_por_secao`, e não reconstruído depois
por semelhança de palavras. O trecho sai do `lastro` que a própria síntese daquela classe declara ter usado, e
ainda precisa passar pela conferência acima.

Seção sem fonte declarada não recebe trecho. "Resumo em uma linha" é assim de propósito: ela conta o caso inteiro,
não uma cláusula. Trecho conferido embaixo do assunto errado é uma mentira diferente, e não menos grave. Na jornada, o tópico só recebe `trecho` quando ele foi encontrado, e a frase que a tela exibe muda conforme o método: cópia exata só é afirmada quando foi exata.

## Banco e escala
- `DATABASE_URL` (Postgres, `postgresql+psycopg://...`) quando definido; senão SQLite em `DB_PATH`. Tabelas via
  `SQLModel.metadata.create_all`; as migrações `ALTER TABLE` só rodam no SQLite. Novas colunas: `tarefa.cidadao_id`
  (nulo), `tarefa.origem` (`advogado` \| `cidadao`); nova tabela `duvida` (`id, tarefa_id, texto, contexto (json),
  criada_em, respondida, resposta, respondida_em`).
- Pipelines em paralelo limitados por `PIPELINE_CONCURRENCY` (padrão 3) com semáforo; cada tarefa tem seu próprio
  estado e uma falha não afeta as outras. Rotas públicas de escrita (`/quiz`, `/chat`, `/duvida`, cadastro) com limite por
  IP (`RATE_LIMIT_PER_MINUTE`, padrão 30) em memória.
- Rotas do painel interno (templates) continuam funcionando com cookie.

## App (`apps/web`)
| Rota | Tela |
|---|---|
| `/entrar` | entrar ou criar conta (cidadã ou advogado); token em `localStorage` (`leia:auth`) |
| `/painel` | advogado/admin: lista de documentos com status, link da cliente (copiar), respostas e dúvidas abertas; cidadã: "Meus documentos" (continuar, ver comprovante) |
| `/painel/{id}` | detalhe: eventos, tentativas, dúvidas com campo de resposta (advogado) |
| `/enviar` | enviar um PDF (cidadã ou advogado); depois vai para `/t/{hash}` (advogado: mostra o link para enviar à cliente) |
| `/t/{hash}` | jornada; na gaveta de dúvida, botão "Enviar esta dúvida para o advogado" quando `tem_advogado`; se logada como cidadã, vincula a tarefa |

O navegador nunca chama o serviço direto: ele chama as rotas do próprio app em `app/api/*`, que encaminham para
`SERVICE_URL` acrescentando o `Authorization: Bearer` lido do cookie de sessão. Sem `SERVICE_URL`, essas mesmas rotas
respondem pelo mock interno, com dados em memória do processo.

## Revisão do advogado antes de liberar (13/09, 18h)
Espelha o fluxo "Resumo estruturado" do painel do Carlos (Status → Resumo → Visualizar → Dna): o advogado revisa o que
o workflow extraiu e concluiu antes de a cliente receber o link.
| Método e rota | Quem | Saída |
|---|---|---|
| `GET /api/tarefas/{id}/revisao` | Bearer (dono ou admin) | `{ tarefa: { id, hash, titulo, status, origem }, tipo_documento, tipos_documento, inferencias: <mesmo corpo de GET /api/t/{hash}/inferencias>, resumo_md, questoes: [ { id, area, dificuldade, enunciado, alternativas, correta, justificativa } ], link_cliente }`; 409 enquanto `criada`/`processando`; 404/403 como nas demais |
| `POST /api/tarefas/{id}/aprovar` | Bearer (dono ou admin) | `{ ok: true, status: "enviada" }`; só de `pronta` para `enviada`; grava evento `aprovada` no workspace e `LogEvento`; 409 em outro estado |
| `POST /api/tarefas/{id}/revisao` | Bearer (dono ou admin) | corpo `{ resumo_md?, questoes?: number[] }`; grava a explicação como o advogado a deixou e as perguntas que ele manteve; devolve `{ ok, resumo?, questoes?, porta_qualidade }` com a medida sobre o que acabou de ser gravado, porque renomear um título de seção desliga a âncora dela sem barulho nenhum; 422 com mais de zero e menos de `QUIZ_MIN_QUESTIONS` perguntas marcadas; 409 em `criada`/`processando` e depois de `enviada`/`assinada`, porque aí a cidadã pode já ter lido e recebido comprovante |
| `POST /api/tarefas/{id}/tipo-documento` | Bearer (só o dono) | corpo `{ tipo }` entre as espécies declaradas; devolve `{ ok: true, tipo_documento }`; 422 para espécie que não existe; 404 para quem não enviou o documento. Grava `tipo_documento_revisado.json` ao lado do documento, que **sobrevive ao `reprocessar`** e faz a próxima rodada pular a classificação. Não muda a rodada atual: `aplicado: false` até o documento ser refeito |

Estados: `pronta` = pronta para revisão do advogado; `enviada` = liberada para a cliente; `assinada` = entendimento
registrado. Tarefas com `origem = cidadao` não passam por revisão: `pronta` já libera.

Gate público: para tarefa com advogado (`origem = advogado`) em `pronta`, `GET /api/t/{hash}` devolve
`tarefa.status = "revisao"` com `resumo_md: null, topicos: null, questoes: []` (e `tem_advogado`, `advogado`), e
`GET /api/t/{hash}/inferencias`, `POST .../quiz` e `POST .../chat` respondem 409 "Em revisão pelo advogado". O app mostra
"O advogado está revisando a explicação" na tela de espera.

Tela no app: `/painel/{id}/revisao` com abas Marcações (classes com "Ver no texto" e selo "conferido no texto"), Texto
(documento com destaques por classe), Conclusões (sínteses com lastro), Explicação (o que a cliente vai ler),
Perguntas (com a resposta certa marcada) e o botão "Aprovar e liberar para a cliente".

## Preparação visível e tarefas do fluxo externo (13/09, 18h40)
Pedido do Daniel: a tela de espera deve mostrar todas as etapas do processo (não uma por vez), o documento e o que a
assistente está marcando, com score quando existir; e explicar por que um link gerado pelo fluxo "Resumo estruturado"
chega sem explicação.

**Causa do link sem explicação.** O fluxo "Resumo estruturado" do painel do Carlos manda o PDF a uma API externa e grava
só `resumo_estruturado.json` (o fluxo externo, já removido); a página da cidadã e o nosso JSON leem `resumo_humanizado.md` e
`questoes.json`, que só o pipeline local (T1..T14, fluxo "Anexar PDF" / "Nova tarefa") produz. Resultado: `pronta` sem
explicação nem perguntas ("resumo indisponível", `app_gestao.py:608-610`).

| Método e rota | Mudança |
|---|---|
| `GET /api/t/{hash}` | novo campo `etapas: [ { id, nome, estado: "pendente" \| "em_andamento" \| "concluida" \| "erro", tempo } ]` com as 15 etapas do workflow em pt-BR, derivadas de `log.jsonl` (`task_start`/`task_done`/`task_error`) e da presença dos arquivos `T*.json`; `eventos` passa a trazer todos os eventos do pipeline (até 60), sem ip/ua. **Fallback do fluxo externo**: sem `resumo_humanizado.md` mas com `resumo_estruturado.json`, `resumo_md` = `processo.resposta_final.texto` e `topicos` = itens de `processo.classe_*` (titulo = `campo` humanizado, explicacao = `valor` ou `sintese_relacao`, trecho = `trecho_verbatim`, `score` de `_ui`); `questoes: []` |
| `GET /api/t/{hash}/inferencias` | responde também durante `criada`/`processando` com `parcial: true`, `texto` (se `texto_extraido.txt` existir) e as classes já produzidas (arquivos `T1..T5_*.json`, cada um `{ "<classe>": [itens] }`), para a espera mostrar o documento sendo marcado. Itens ganham `score` quando `_ui` traz `score_trecho_verbatim` (fluxo externo); quando `_ui` traz posição válida (não `0:0`), ela é usada antes da busca por texto |

Cada pergunta de `GET /api/t/{hash}` traz `secao` (o título exato da seção da explicação de onde ela nasceu),
`trecho` (a fatia literal do documento que sustenta a resposta) e `conferencia { metodo, score }`. Nunca traz
`correta` nem `justificativa`. A pergunta cujo trecho o `locate` não acha no documento não é publicada, e
abaixo de `QUIZ_MIN_QUESTIONS` (4) o serviço publica **zero** perguntas em vez de uma conferência fraca: a
jornada termina em `sem_perguntas`, sem comprovante. `POST /api/t/{hash}/quiz` aceita `consultas`, o mapa
`{ id_da_pergunta: vezes }` de quantas vezes ela reabriu o trecho, que entra no preimage do hash da tentativa
(`leia.attempt.v3`) e no comprovante (`leia.payload.v4`, campo `consulted`).

`GET /api/t/{hash}` traz também `tipo_documento: { tipo, rotulo, trecho, pos, conferido, revisado_por_advogado, aplicado }`
ou `null` antes da primeira rodada. É a espécie com que o motor leu o documento, e é ela que escolhe o vocabulário das
extrações: `conferido` diz se `trecho` foi achado no documento pelo `locate`, `revisado_por_advogado` que quem
respondeu foi uma pessoa, e `aplicado` se a explicação na tela foi mesmo produzida com ela.

Nomes das etapas (pt-BR): T0 Reconhecer o tipo do documento · T1 Identificar as partes · T2 Datas e valores · T3 Fatos · T4 Fundamentos, leis e decisões ·
T5 Pedidos · T6 Juntar a memória · T7 Resumir os fatos · T8 Resumir os fundamentos · T9 Resumir os pedidos ·
T10 Quem é quem · T11 Contexto do processo · T12 Marcar o texto · T13 Explicar em linguagem simples ·
T14 Preparar as perguntas.

App: a tela de espera mostra a espécie reconhecida ("Lido como: Contrato"), a lista das 15 etapas com estado e tempo,
barra "n de 15", e abaixo "O que a assistente
está lendo agora": o documento com as marcações parciais e a contagem por classe (atualiza a cada 8 s). Documento sem
perguntas (fluxo externo) termina a jornada em "Você viu todos os pontos", sem conferência e sem comprovante.
