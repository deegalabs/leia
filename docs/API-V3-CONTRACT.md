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
