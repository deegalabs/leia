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

## Cidadã (rotas públicas, o hash é o segredo)
| Método e rota | Entrada | Saída |
|---|---|---|
| `GET /api/t/{hash}` | | como hoje **mais** `advogado: { nome } \| null` (nulo quando o dono é `cidadao`), `tem_advogado: bool`, `cidadao_vinculado: bool`, `duvidas_enviadas: n` |
| `POST /api/t/{hash}/duvida` | `{ texto, contexto?: [ { role: "user" \| "bot", text } ] }` | `{ id, criada_em }`; 409 se a tarefa não tem advogado; limitado por IP |
| `POST /api/t/{hash}/vincular` | Bearer (`cidadao`) | `{ ok: true }`; define `tarefa.cidadao_id` se ainda vazio |
| `GET /api/t/{hash}/inferencias` | | `{ tarefa, texto (texto extraído), classes: [ { classe, rotulo, cor, itens: [ { ref, campo, valor, trecho, pos: [inicio, fim] \| null, conferido, cor } ] } ], sinteses: [ { classe, rotulo, texto, lastro[] } ], total, conferidos }`. `pos` vem de busca do `trecho_verbatim` no texto (ignorando espaços), pois o workflow devolve posições `0:0`; 409 enquanto não está pronta |

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
Sem serviço (`NEXT_PUBLIC_API_BASE` vazio), o mock interno em `app/api/*` responde a tudo com dados em memória do processo.

## Revisão do advogado antes de liberar (13/09, 18h)
Espelha o fluxo "Resumo estruturado" do painel do Carlos (Status → Resumo → Visualizar → Dna): o advogado revisa o que
o workflow extraiu e concluiu antes de a cliente receber o link.
| Método e rota | Quem | Saída |
|---|---|---|
| `GET /api/tarefas/{id}/revisao` | Bearer (dono ou admin) | `{ tarefa: { id, hash, titulo, status, origem }, inferencias: <mesmo corpo de GET /api/t/{hash}/inferencias>, resumo_md, questoes: [ { id, area, dificuldade, enunciado, alternativas, correta, justificativa } ], link_cliente }`; 409 enquanto `criada`/`processando`; 404/403 como nas demais |
| `POST /api/tarefas/{id}/aprovar` | Bearer (dono ou admin) | `{ ok: true, status: "enviada" }`; só de `pronta` para `enviada`; grava evento `aprovada` no workspace e `LogEvento`; 409 em outro estado |

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
só `resumo_estruturado.json` (`core/api.py:229`); a página da cidadã e o nosso JSON leem `resumo_humanizado.md` e
`questoes.json`, que só o pipeline local (T1..T14, fluxo "Anexar PDF" / "Nova tarefa") produz. Resultado: `pronta` sem
explicação nem perguntas ("resumo indisponível", `app_gestao.py:608-610`).

| Método e rota | Mudança |
|---|---|
| `GET /api/t/{hash}` | novo campo `etapas: [ { id, nome, estado: "pendente" \| "em_andamento" \| "concluida" \| "erro", tempo } ]` com as 14 etapas do workflow em pt-BR, derivadas de `log.jsonl` (`task_start`/`task_done`/`task_error`) e da presença dos arquivos `T*.json`; `eventos` passa a trazer todos os eventos do pipeline (até 60), sem ip/ua. **Fallback do fluxo externo**: sem `resumo_humanizado.md` mas com `resumo_estruturado.json`, `resumo_md` = `processo.resposta_final.texto` e `topicos` = itens de `processo.classe_*` (titulo = `campo` humanizado, explicacao = `valor` ou `sintese_relacao`, trecho = `trecho_verbatim`, `score` de `_ui`); `questoes: []` |
| `GET /api/t/{hash}/inferencias` | responde também durante `criada`/`processando` com `parcial: true`, `texto` (se `texto_extraido.txt` existir) e as classes já produzidas (arquivos `T1..T5_*.json`, cada um `{ "<classe>": [itens] }`), para a espera mostrar o documento sendo marcado. Itens ganham `score` quando `_ui` traz `score_trecho_verbatim` (fluxo externo); quando `_ui` traz posição válida (não `0:0`), ela é usada antes da busca por texto |

Nomes das etapas (pt-BR): T1 Identificar as partes · T2 Datas e valores · T3 Fatos · T4 Fundamentos, leis e decisões ·
T5 Pedidos · T6 Juntar a memória · T7 Resumir os fatos · T8 Resumir os fundamentos · T9 Resumir os pedidos ·
T10 Quem é quem · T11 Contexto do processo · T12 Marcar o texto · T13 Explicar em linguagem simples ·
T14 Preparar as perguntas.

App: a tela de espera mostra a lista das 14 etapas com estado e tempo, barra "n de 14", e abaixo "O que a assistente
está lendo agora": o documento com as marcações parciais e a contagem por classe (atualiza a cada 8 s). Documento sem
perguntas (fluxo externo) termina a jornada em "Você viu todos os pontos", sem conferência e sem comprovante.
