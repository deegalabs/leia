# Situação do LeIA em 13/09/2026

Inventário verificado em produção e no código no dia 13/09/2026, entre 12h e 16h30 (horário de Brasília).
Fontes: app publicado em https://leia-snowy.vercel.app, serviço em
https://llm-service-production-4278.up.railway.app, repositório `repos/leia` em HEAD `e9b7eb2`
(a build em produção passou de `dev` para `589da62` no meio da revisão). Capturas de tela e logs da
revisão ficaram em `/tmp/leia-review/screens/`, `/tmp/leia-review/flows/` e `/tmp/leia-review/*.json`
(fora do repositório). Nenhum segredo foi lido ou copiado para este arquivo.

Regra de leitura: "verificado" significa observado em produção com captura de tela ou resposta HTTP;
"código" significa que a rota ou estado existe no código, mas não foi exercitado em produção.

## 1. O que temos

| Funcionalidade | Onde roda | Situação |
|---|---|---|
| Landing pública com "Como funciona", "Para quem", "Por que confiar" e link para a demo | Next.js na Vercel (`apps/web/app/page.tsx`) | Verificado |
| Cadastro e login de cidadã e advogado (Bearer em `localStorage`, `leia:auth`) | Web (`apps/web/components/AuthForm.tsx`) + serviço (`apps/llm-service/leia/api_auth.py`) | Verificado |
| Upload de PDF por advogado (gera link da cliente) ou por cidadã (vai direto para a explicação) | Web (`apps/web/components/Upload.tsx`) + serviço (`leia/api_tarefas.py`) | Verificado, pipeline de 70 a 108 s |
| Pipeline de 16 nós (T1 a T14 + END) no Groq `openai/gpt-oss-120b`: extração, memória, sínteses, humanização, questões | Serviço Railway (`apps/llm-service/core/pipeline_pdf.py`, `protocolo_pdf.json`) | Verificado, saída não determinística (ver pendências) |
| Jornada da cidadã: boas-vindas, um ponto por vez, "Ouvir" (Web Speech), "Ver trecho original" quando existe | Web (`apps/web/components/Journey.tsx`) | Verificado |
| Gaveta "Tenho uma dúvida" com resposta em streaming (SSE) e recusa fora do documento | Web (`ChatSheet.tsx`) + serviço `POST /api/t/{hash}/chat` | Verificado |
| Encaminhar dúvida ao advogado e resposta do advogado no painel | Web (`ChatSheet.tsx`, `TaskDetailView.tsx`) + serviço `POST /api/t/{hash}/duvida`, `.../responder` | Verificado |
| Conferência de entendimento: 6 perguntas de múltipla escolha, aprovação por `QUIZ_PASS_RATIO` | Web (`Journey.tsx`) + serviço `POST /api/t/{hash}/quiz` (`core/tentativas.py`) | Verificado (com gabarito trivial, ver pendências) |
| Comprovante com QR, código SHA-256 e carimbo público OpenTimestamps (.ots) | Web (`Receipt.tsx`) + serviço (`leia/registry.py`) | Verificado, `.ots` de 237 bytes baixado |
| Verificação pública `/verify/{attempt}` com JSON canônico e prova | Web (`Verify.tsx`) + serviço `GET /verify/{attempt}?format=json` | Verificado, `sha256(canonical) == payloadHash` |
| Documento com marcações e inferências por classe (quem é quem, datas, fatos, fundamentos, pedidos) | Web (`DocumentView.tsx`) + serviço `GET /api/t/{hash}/inferencias` | Verificado |
| Painel do advogado (lista, detalhe, etapas, rodadas, dúvidas) e painel da cidadã ("Meus documentos") | Web (`Panel.tsx`, `TaskDetailView.tsx`) + serviço `GET /api/tarefas` | Verificado |
| Vínculo automático da cidadã logada à tarefa ao abrir o link | Web (`Journey.tsx:37-41`) + serviço `POST /api/t/{hash}/vincular` | Verificado |
| PWA: manifest, service worker, banner "Nova versão do LeIA disponível." | Web (`public/sw.js`, `UpdatePrompt.tsx`) | Verificado |
| Painel interno legado do serviço (login por cookie, dashboard, chat de bastidores, resumo estruturado) | Serviço Railway (`main.py`, `app_gestao.py`, `templates/`) | Parcial: rotas respondem, fluxos não exercitados |
| Página HTML própria do serviço `/t/{hash}` e PDF assinado | Serviço Railway (`templates/cliente_view.html`, `core/pdf_sign.py`) | Responde, mas expõe gabarito (ver pendências) |
| Rate limit por IP (30/min) nas rotas públicas e de conta | Serviço (`leia/ratelimit.py`) | Verificado (429 com `Retry-After`) |
| Testes do serviço (`tests_leia.py`, `tests_v3.py`) | Local, venv | 18 passed em 3,5 s |

## 2. Telas

Todas as telas foram verificadas a 390 px e 1280 px sem overflow horizontal, `lang="pt-BR"`, sem
exceção JS não tratada (`/tmp/leia-review/events-*.json`). Data de verificação: 13/09/2026.

| Rota | Quem usa | O que faz | Estados | Verificado em produção (13/09/2026) |
|---|---|---|---|---|
| `/` | Público | Apresenta o produto; links "Ver um exemplo" (`/t/0SVal1OCE4IHpiRHo-rsNA`), `/enviar`, `/entrar`; rodapé com licença e versão | Estático; variante logado com "Meu painel" e "Sair" | Sim: `01-landing-390/1280.png`, `17-landing-logado-390.png`; rodapé "LeIA v0.4.0 · 589da62" |
| `/entrar` | Cidadã e advogado | Abas "Entrar" e "Criar conta" (papel, OAB opcional); `?modo=cadastro`; `?next=` filtrado por `safeNext` | Campos vazios, 401, 409, já logado, carregando; 403 e erro genérico só no código | Sim: `02-entrar-*.png`, `20-entrar-erro-409-390.png`, `17-entrar-ja-logado-390.png` |
| `/enviar` | Advogado e cidadã | Nome + PDF, `POST /api/tarefas`; advogado vê link da cliente, cidadã vai para `/t/{hash}` | Anônimo redireciona para `/entrar?next=%2Fenviar`; sem arquivo; escolhido; enviado; erro genérico | Sim: `03-enviar-anon-redirect-390.png`, `12-enviar-*.png`, `21-enviar-cidada-390.png`, `16-enviar-invalido-resultado-390.png`; redirecionamento da cidadã visto no fluxo F1.2 (`flows/f1-04-wait-screen.png`) |
| `/painel` (advogado) | Advogado | Lista `GET /api/tarefas` com chip de status, rodada, dúvidas abertas, "Copiar link da cliente", "Ver detalhes"; repolling 4 s | Preparando, Pronto para a cliente, Entendimento registrado; loading; erro genérico; vazio não observado | Sim: `10-painel-advogado-*.png`, `14-painel-com-preparando-390.png`, `31-*`, `33-*`; `flows/f2-20-lawyer-painel-duvida.png` |
| `/painel` (cidadã) | Cidadã | "Meus documentos": Continuar, Ver comprovante (só se última tentativa aprovada), Ver detalhes | Vazio; com documento aprovado; após rodada reprovada perde "Ver comprovante" | Sim: `20-painel-cidada-vazio-*.png`, `29-painel-cidada-*.png`, `36-painel-cidada-apos-rodada2-390.png` |
| `/painel/[id]` (advogado) | Advogado | `GET /api/tarefas/{id}`: link da cliente, etapas, respostas por rodada, dúvidas com textarea "Responder" | Preparando, pronto, com dúvida, respondida, duas rodadas, 404, anônimo redireciona; "falhou" não observado | Sim: `11-*`, `14-painel-detalhe-preparando-390.png`, `15-*`, `32-*`, `33-*`, `37-*`, `17-painel-detalhe-404-390.png` |
| `/painel/[id]` (cidadã) | Cidadã | Mesma rota sem link da cliente nem textarea; mostra resposta do advogado | Aprovado com dúvida aguardando; com resposta; duas rodadas | Sim: `30-*`, `34-*`, `36-painel-detalhe-cidada-rodada2-390.png`; `flows/f2-31-citizen-detalhe-resposta.png` |
| `/t/[hash]` (carregando e erro) | Cidadã | `GET /api/t/{hash}`; "Carregando sua explicação." | Qualquer erro, inclusive 404, mostra "Estamos tentando de novo." e refaz a cada 4 s | Sim: `09-t-naoexiste-390.png` (loop de 404) |
| `/t/[hash]` (espera) | Cidadã | "Estamos preparando a explicação do seu documento", "Etapa atual: {tipo bruto}", repolling 8 s | Único estado | Sim: `13-t-espera-*.png`, `flows/f1-04-wait-screen.png`; troca sozinha para boas-vindas ao terminar |
| `/t/[hash]` (falhou) | Cidadã | "Não deu certo desta vez" | Único estado | Não: nenhuma tarefa chegou a `falhou` (PDF inválido é recusado com 400 no upload) |
| `/t/[hash]` (boas-vindas) | Cidadã | Título com nome do documento, quem está falando, "Ouvir", "Você não assina nada aqui.", "Começar a explicação"; cidadã logada é vinculada | Anônimo; logada e vinculada; reabrir após aprovação vai direto ao resultado | Sim: `04-t-welcome-*.png`, `22-t-welcome-cidada-390.png`, `flows/f2-10-citizen-link.png` |
| `/t/[hash]` (ponto n de N) | Cidadã | Explicação em parágrafos, "Ouvir explicação", "Ver trecho original" (só quando há `trecho`), "Entendi, próximo", "Ver o documento com as marcações", "Tenho uma dúvida" | Ponto 1, intermediário com trecho, último | Sim: `05-t-topic*.png`, `23-t-topic1-cidada-390.png`, `flows/f1-11-topic-5-trecho.png`; trecho em 1 de 6 pontos (demo) e 0 ou 1 de 6 nas tarefas novas |
| `/t/[hash]` (gaveta de dúvida) | Cidadã | Dialog inferior com 3 exemplos, input, resposta em streaming, "Enviar esta dúvida para o advogado" quando `tem_advogado` | Aberta; respondida; fora do documento; enviada ao advogado; fechada por Esc; falha de envio só no código | Sim: `06-t-duvida-*.png`, `24-t-duvida-*.png`, `flows/f1-13-duvida-resposta.png`, `f2-12-citizen-duvida-enviada.png` |
| `/t/[hash]` (conferindo k de K) | Cidadã | Enunciado, alternativas A a D, "Ouvir a pergunta", "Próxima pergunta", "Enviar minhas respostas"; respostas em `localStorage` `leia:{hash}` | Sem escolha; escolhida; última; erro de envio só no código | Sim: `07-t-question*.png`, `flows/f1-14-pergunta-1.png`; envio real só nas tarefas criadas na revisão |
| `/t/[hash]` (resultado aprovado) | Cidadã | Chip "Entendimento registrado", "O que você viu", "Ver meu comprovante", "Rever a explicação" | Único estado | Sim: `26-t-resultado-aprovado-*.png`, `flows/f1-15-resultado.png` |
| `/t/[hash]` (resultado "Vamos ver de novo") | Cidadã | Chip, lista dos enunciados errados sem nota, "Ler a explicação de novo" | Único estado | Sim: `35-t-resultado-ver-de-novo-*.png` (rodada 2, 0 de 6) |
| `/t/[hash]/documento` | Cidadã e advogado | `GET /api/t/{hash}/inferencias`: chips conferidas/não localizadas, sínteses com lastro, texto com marcas, cartões por classe | Loading; 404; 409 "ainda sendo preparada" só no código | Sim: `08-t-documento-*.png`, `09-t-naoexiste-documento-390.png`, `flows/f1-19-documento.png`, `f2-23-lawyer-documento.png` |
| `/comprovante/[attempt]` | Cidadã | `GET {API}/verify/{attempt}?format=json` a cada 30 s: chip, data, tentativa, QR, código, "Salvar comprovante", "Conferir o registro" | Registrado; 404; "Carimbo pendente", texto de demo e impressão não verificados | Sim: `27-comprovante-*.png`, `09-comprovante-naoexiste-390.png`, `flows/f1-16-comprovante.png` |
| `/verify/[attempt]` | Público, auditor | Chip "registrado em", código SHA-256, "Baixar prova (.ots)", JSON canônico, "Como conferir por conta própria" | Registrado; 404; "carimbo pendente" não verificado | Sim: `28-verify-*.png`, `09-verify-naoexiste-390.png`, `flows/f1-17-verify.png`; `.ots` baixado por curl (237 bytes) |
| Rota inexistente | Público | 404 padrão do Next, em inglês, sem layout | Único estado | Sim: `09-rota-inexistente-390.png` |
| Banner "Nova versão do LeIA disponível." | Todos | Registra `/sw.js`, checa a cada 60 s, mostra versão e "Atualizar" / "Agora não" | Aparece quando há SW em espera | Sim, durante deploy no meio da revisão: `09-rota-inexistente-390.png`, `08-t-documento-390.png`, `flows/f1-16-comprovante.png` |

## 3. API do serviço

Base: https://llm-service-production-4278.up.railway.app. Rotas verificadas com curl em 13/09/2026.
"Bearer" é o token de `POST /api/auth/login`; "cookie" é a sessão `sessao` do painel interno.
Rotas do painel interno aceitam Bearer também (`core/auth.py`).

### 3.1 Rotas consumidas pelo app (v3)

| Rota | Auth | Quem chama | Situação |
|---|---|---|---|
| `POST /api/auth/cadastro` | Nenhuma, rate limit | `apps/web/lib/auth.ts:52` | Verificado: 200, 403 para papel `fornecedor`, 409 duplicado, 422 sem `@` |
| `POST /api/auth/login` | Nenhuma, rate limit | `auth.ts:47` | Verificado: 200 `{token, usuario}`, 401 JSON, 429 após o 30.o pedido limitado por IP. Rotaciona o token anterior |
| `GET /api/auth/me` | Bearer | `auth.ts:64` (nunca chamado por tela) | Verificado: 200, 401 sem token, 401 após logout |
| `POST /api/auth/logout` | Bearer | `auth.ts:57` | Verificado: `{ok:true}` |
| `GET /api/tarefas` | Bearer | `lib/api.ts:123-127` | Verificado: chaves iguais a `docs/API-V3-CONTRACT.md:90`; `link_cliente` aponta para a Vercel |
| `POST /api/tarefas` | Bearer, rate limit | `api.ts:128-134` | Verificado: 201 em ~1 s, 400 "Este arquivo não é um PDF." para PDF inválido |
| `GET /api/tarefas/{id}` | Bearer | `api.ts:135-138` | Verificado: 200, 404 desconhecido, 403 sem permissão |
| `POST /api/tarefas/{id}/duvidas/{duvida_id}/responder` | Bearer | `api.ts:139-142` | Verificado no fluxo F2.8 (`duvida_respondida por=2`) |
| `GET /api/t/{hash}` | Nenhuma | `api.ts:37-40` | Verificado: 200 sem `correta`/`justificativa`; 404 `Link inválido ou expirado`; devolve últimos 8 eventos brutos (ver pendências) |
| `POST /api/t/{hash}/quiz` | Nenhuma, rate limit | `api.ts:42-47` | Verificado nas tarefas da revisão (6/6 e 0/6); 404 hash inválido; devolve `correta` das erradas (ver pendências) |
| `POST /api/t/{hash}/chat` | Nenhuma, rate limit | `api.ts:50-74` | Verificado: SSE, TTFB 0,34 s, total 1,27 s; recusa fora do documento |
| `POST /api/t/{hash}/duvida` | Nenhuma, rate limit | `api.ts:143-146` | Verificado: 200, 409 sem advogado, 429 com balde esgotado |
| `POST /api/t/{hash}/vincular` | Bearer (cidadã) | `api.ts:147-150` | Verificado: 200, 403 para advogado, 409 vinculada a outra conta |
| `GET /api/t/{hash}/inferencias` | Nenhuma | `api.ts:160-163` | Verificado: 200 (demo 18/18, novas 2/2 e 22/24), 404; 409 antes de pronta só no código |
| `GET /verify/{attempt}[?format=json]` | Nenhuma | `api.ts:76-80` | Verificado: 200 com `payload, canonical, payloadHash, otsPresent`; 404 |
| `GET /verify/{attempt}/proof.ots` | Nenhuma | `api.ts:82` | Verificado: 200, 237 bytes |
| `GET /t/{attempt}/comprovante` | Nenhuma | Página do serviço e links | Verificado só o 404 |

### 3.2 Rotas do painel interno e da página própria do serviço

| Rota | Auth | Quem chama | Situação |
|---|---|---|---|
| `GET /login`, `POST /login`, `POST /logout` | Nenhuma / cookie | `templates/login.html`, `dashboard.html`; healthcheck do Railway em `/login` | Verificado: 200, 303 com cookie `HttpOnly; SameSite=lax; Secure`; `POST /login` sem rate limit |
| `GET /`, `GET /dashboard` | Cookie ou Bearer | Painel interno | Verificado: 303 sem credencial, 200 com Bearer |
| `GET/POST /api/protocolo` | Cookie ou Bearer | `index.html:2420` | GET verificado; POST sobrescreve `protocolo.json` no diretório do código (código) |
| `GET /api/help` | Cookie ou Bearer | Ninguém | Código |
| `GET /api/contexto`, `POST /api/contexto/limpar` | Cookie ou Bearer | `index.html:2291, 2299` | GET verificado; histórico global compartilhado por todos os usuários |
| `POST /api/chat` | Cookie ou Bearer | `index.html:2112` | Código (Groq) |
| `GET /static/*` | Nenhuma | Templates | Verificado |
| `GET /docs`, `/redoc`, `/openapi.json` | Nenhuma | Ninguém | Verificado: 404 (`DOCS_ENABLED` desligado) |
| `POST /api/pdf/destilar`, `GET /api/pdf/{hash}/destilado`, `GET /api/pdf/{hash}/log` | Cookie ou Bearer | `index.html:1806, 1828, 1816` | Código |
| `POST /api/resumo-estruturado/submit`, `GET .../{hash}/status`, `GET .../{hash}/resultado` | Cookie ou Bearer | `index.html:1889, 1919, 1951` | Código; envia o PDF a host externo sem auth (`core/api.py:25`) |
| `POST /api/resumo-estruturado/{hash}/rerun/{step_id}` | Cookie ou Bearer | Ninguém | Código |
| `POST /api/jurisprudencia/submit`, `GET .../{hash}/status`, `GET .../{hash}/resultado` | Cookie ou Bearer | Ninguém | Código; envia a host externo sem auth |
| `GET /api/sessao/memoria`, `POST /api/sessao/memoria/limpar` | Cookie ou Bearer | `index.html:2319, 2354` | GET verificado |
| `GET/POST /tarefas/nova` | Cookie ou Bearer | `tarefa_nova.html:61` | Código; sem rate limit |
| `GET /tarefas/{id}` | Cookie ou Bearer | Dashboard | Código; HTML inclui gabarito para o remetente |
| `POST /tarefas/{id}/reprocessar`, `POST /tarefas/{id}/nova-rodada` | Cookie ou Bearer | `dashboard.html:293`, `tarefa_detalhe.html:152, 157, 208` | Código |
| `GET /tarefas/{id}/artefato/{nome}` | Cookie ou Bearer | Ninguém | Código; `meta.json` expõe id, e-mail e nome do remetente |
| `GET /api/tarefas/{id}/status` | Cookie ou Bearer | Ninguém | Verificado: 303 sem cookie, 200 com Bearer |
| `GET /t/{hash}` (HTML do serviço) | Nenhuma | `cliente_view.html` | Verificado: 200 com 6 `data-correta`/`justificativa` no DOM; grava `cliente_abriu {ip, ua}` a cada abertura |
| `GET /t/{hash}/pdf-assinado`, `GET /tarefas/{id}/pdf-assinado` | Nenhuma / cookie ou Bearer | `cliente_view.html:303`, `tarefa_detalhe.html:163` | Verificado 403 sem tentativa aprovada; PDF inclui IP e user agent (`core/pdf_sign.py`) |

Comportamentos transversais verificados: CORS libera `https://leia-snowy.vercel.app` e
`http://localhost:3000` (preflight de `https://evil.example` recebe 400 sem `allow-origin`); rate
limit de 30 req/min por IP num único balde compartilhado por quiz, chat, dúvida, cadastro, login e
`POST /api/tarefas`; `X-Forwarded-For` falso não contorna o limite.

## 4. Infraestrutura

| Item | Valor |
|---|---|
| App (Next.js 15, PWA) | https://leia-snowy.vercel.app, projeto Vercel no scope pessoal citado em `apps/web/README.md:45-46`; deploy com `vercel deploy --prod` (README:46) |
| Serviço (FastAPI, uvicorn `--proxy-headers`) | https://llm-service-production-4278.up.railway.app, projeto Railway `llm-service`; `railway.toml` (healthcheck `/login`), `Dockerfile` (`DATA_DIR=/data`) |
| Repositório | `git remote origin` = github.com/deegalabs/leia (responde 404: privado); tag única `token-economy/v0.1.0`; HEAD `e9b7eb2` |
| Modelo | Groq `openai/gpt-oss-120b` (`apps/llm-service/.env.example:3`); `PIPELINE_TEMPERATURE` padrão 0.0 no código, valor efetivo no Railway não lido |
| Carimbo público | OpenTimestamps (`OTS_ENABLED`), prova em `/verify/{attempt}/proof.ots`; nenhuma ancoragem em blockchain (nenhum `ANCHOR_*`/`AMOY` em `apps/`) |
| Banco | SQLite (`DB_PATH` ou `DATABASE_URL`) em `DATA_DIR`; tabelas de usuários (um `session_token` por usuário), tarefas, tentativas, dúvidas (`core/db.py`) |
| Arquivos por tarefa | `WORKSPACE_DIR/{hash}/`: `meta.json`, `log.jsonl`, `T*.json`, `questoes.json`; sessões do painel em `workspace/_sessoes/{token}.json`; contexto global em `contexto_persistente.json` |
| Volume | `DATA_DIR=/data` no `Dockerfile:7`; existência e montagem do volume Railway não verificadas nesta revisão (variáveis do Railway não foram lidas de propósito) |
| Variáveis do serviço (nomes, todas em `apps/llm-service/.env.example`) | `GROQ_API_KEY`, `GROQ_MODEL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME`, `ADVOGADO_SIGNUP`, `DATA_DIR`, `DB_PATH`, `WORKSPACE_DIR`, `DATABASE_URL`, `PIPELINE_CONCURRENCY`, `PIPELINE_TEMPERATURE`, `PIPELINE_MAX_TOKENS`, `PDF_PROTOCOL_FILE`, `PERSISTENT_CONTEXT_FILE`, `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_TRUST_XFF`, `CORS_ORIGINS`, `CLIENT_APP_URL`, `BASE_URL`, `OTS_ENABLED`, `SESSION_COOKIE_SECURE`, `LOG_LEVEL`, `QUIZ_PASS_RATIO`, `ATTEMPT_HASH_PREFIX`, `CITIZEN_CHAT_TEMPERATURE`, `CITIZEN_CHAT_MAX_TOKENS`, `CITIZEN_CHAT_MEMORY_CHARS`, `RESUMO_ESTRUTURADO_API_BASE`, `JURISPRUDENCIA_API_BASE`, `EXTERNAL_*`, `BRAND_NAME`, `DOCS_ENABLED`, `MAX_UPLOAD_MB`, `PORT` (só no comando uvicorn); `API_KEY` legado só em comentário; `LEIA_FIXTURE` só no mock |
| Estado observado em produção | `CLIENT_APP_URL` aponta para a Vercel; `CORS_ORIGINS` inclui Vercel e localhost:3000; `DOCS_ENABLED` desligado; `SESSION_COOKIE_SECURE` ligado; `RATE_LIMIT_PER_MINUTE` coerente com 30; `OTS_ENABLED` ligado |
| Variáveis do app | `SERVICE_URL` (Railway, sem `NEXT_PUBLIC_`), `NEXT_PUBLIC_DEMO_HASH` (`0SVal1OCE4IHpiRHo-rsNA`), `NODE_ENV`; `GIT_COMMIT_SHA` em build (fallback `dev`, `next.config.ts:7`) |
| Mock interno do app | `apps/web/app/api/*` e `apps/web/lib/mock.ts`; na Vercel `/api/t/{hash}` responde 404 porque o app aponta para o Railway |
| Demo intacta | `/t/0SVal1OCE4IHpiRHo-rsNA` (tarefa 1, "Contrato de honorários advocatícios (exemplo)", status `pronta`, 1 dúvida aberta não respondida, sem tentativa) |
| Tarefas criadas na revisão | ids 2, 3 e 4 (`AUHYNFsnGOhI0QziN1NZEw`, `5e5xqKOQNM2GBGw9bx86iw`, `illjOdH9CowLew-2_PZKJQ`), contas de teste `@example.com` e `@leia.local` |

## 5. Pontas soltas confirmadas

Ordem: alta, media, baixa. "Onde" cita arquivo:linha no repositório ou URL. Itens duplicados entre as
frentes de verificação (telas, API, fluxos, documentação) foram unidos.

| Sev. | Título | Onde | Como corrigir |
|---|---|---|---|
| alta | Pipeline inventa fatos sobre o contrato e o quiz certifica a invenção (D1) | `GET /api/t/AUHYNFsnGOhI0QziN1NZEw`: tópicos "Carlos", "Ana", "A Justiça já decidiu... Carlos ainda recorre", síntese "fase de recurso (apelação)", "Art. 85 CPC"; texto do PDF só cita CONTRATANTE/CONTRATADA. Causa: `apps/llm-service/protocolo_pdf.json:161` (T13 "história para uma criança"), `app_gestao.py:986-988` (chat trata todo documento como "o processo dele"), `leia/api_cliente.py:80` (trecho só com score >= 3) | Reescrever T13/T14 para explicar só o que está no texto, sem personagens nem fase processual; exigir `trecho_verbatim` por tópico e descartar tópico sem âncora; trocar o enquadramento do system prompt do chat por "este documento"; validar com o PDF de exemplo antes do pitch |
| alta | Gabarito é sempre a alternativa A | `protocolo_pdf.json:173` (T14 pede "a correta é LITERALMENTE o que a história contou"), `core/pipeline_pdf.py:336-337` (salva como veio), `core/tentativas.py:43-48` (compara índice fixo); tarefas 2 e 3: 6/6 com A, 0/6 com B; demo segue o mesmo padrão | Embaralhar alternativas no serviço ao salvar `questoes.json` (seed derivada do hash) e guardar o índice correto; opcionalmente pedir ao modelo posição variada |
| alta | JSON público expõe IP e user agent de quem abriu o documento | `leia/api_cliente.py:109` devolve os 8 últimos eventos de `log.jsonl` sem filtro; `app_gestao.py:890-892` grava `cliente_abriu {ip, ua}` a cada abertura de `/t/{hash}` do serviço; o hash da demo está na landing (`apps/web/app/page.tsx:32`) | Filtrar `eventos` por lista de tipos do pipeline (como `/api/pdf/{hash}/log`, `app_gestao.py:324-331`) e remover `ip`/`ua`; avaliar não gravar IP/UA; mesmo cuidado em `GET /api/tarefas/{id}` e no PDF assinado (`core/tentativas.py:219-220`, `core/pdf_sign.py`) |
| alta | Resposta do quiz devolve o gabarito das questões erradas | `core/tentativas.py:109-117` monta `erros[]` com `correta`, `justificativa`, `alternativas`; `app_gestao.py:959` devolve sem filtro em rota pública | Devolver só `{id, area, enunciado, escolhida}` como em `docs/LLM-API-CONTRACT.md:32`; a UI já não usa o resto |
| media | Quase nenhum ponto traz o trecho original (sourceQuote) | `leia/api_cliente.py:73-81` (casamento heurístico, score >= 3); `apps/web/components/Journey.tsx:151-162`; landing promete "Toda explicação mostra o trecho literal" (`page.tsx:13`); demo 1 de 6, tarefa 3: 0 de 6, tarefa 2: 1 de 6 | Fazer o modelo devolver o trecho literal por tópico e conferir por substring exata no texto extraído; tópico sem trecho não vai para a cidadã; ou ajustar a promessa da landing |
| media | Mesmo PDF gera saídas diferentes e uma rodada quase vazia foi entregue como "pronta" | Tarefa 4 (`illjOdH9CowLew-2_PZKJQ`): 2 inferências, sínteses vazias, ponto 1 "não há registro de nenhum fato"; demo 18 e tarefa 2 com 24 para o mesmo texto de 1600 chars; `core/pipeline_pdf.py:341` marca `pronta` sem checagem; landing promete "mesmo documento, mesma explicação" (`page.tsx:15`) | Porta de qualidade antes de `pronta` (mínimo de fatos, tópicos com trecho, sínteses não vazias), senão `falhou` com reprocessamento; fixar seed/temperatura e confirmar `PIPELINE_TEMPERATURE` no Railway; em demo ao vivo usar a tarefa fixa |
| media | Payload canônico com `documentSha256` e `summarySha256` vazios e salt derivado do próprio hash | `leia/api_cliente.py:166-170` nunca passa `pdf_sha256`/`resumo_sha256`; `leia/registry.py:60-61` usa `""`; salt = `hash_imutavel[:40]` (`api_cliente.py:169`) publicado em `/verify` (`registry.py:163-165`); contraria `docs/specs/SPEC-001` | Calcular SHA-256 do PDF e do resumo exibido, salt aleatório guardado só no comprovante; regenerar payload |
| media | Datas e horas do painel 3 h adiantadas | `core/db.py:55-56,65,81,90` (`utcnow` sem fuso), `leia/api_tarefas.py:65-72,131`, `core/workspace.py:28` emitem ISO sem `Z`; `apps/web/lib/api.ts:97-101` interpreta como hora local; "16:02" no painel contra "13:02" no comprovante | Emitir timestamps com `Z` (ou `datetime.now(timezone.utc)`) no serviço, ou tratar string sem fuso como UTC no `formatDateTime` |
| media | Nomes internos do pipeline expostos à cidadã e ao advogado | `Journey.tsx:93` ("Etapa atual: task start (T1_IDENTIFICADOR_PARTES, 2 de 16)"); `TaskDetailView.tsx:22-23` e `messages/pt-BR.json:278-286` só mapeiam tipos do mock; serviço emite `task_start`, `task_done`, `pipeline_done`, `tentativa`, `carimbo_publico`, `cliente_abriu`, `duvida_enviada` | Mapear os tipos reais e os ids `T1..T14` para frases em pt-BR simples; esconder o que não tiver tradução |
| media | Link inválido fica em "Estamos tentando de novo" para sempre | `Journey.tsx:54-58` trata 404 como erro genérico com retry a cada 4 s; serviço responde `Link inválido ou expirado` (`api_cliente.py:86-89`); `Receipt`, `Verify` e `DocumentView` já distinguem 404 | Tratar 404 como "Este link não existe ou expirou" sem retry; manter retry só para erros de rede/5xx |
| media | Sessão revogada vira erro genérico; segundo login derruba o primeiro aparelho | Um `session_token` por usuário, rotacionado a cada login (`core/auth.py:34`, `leia/api_auth.py:66-73`); `Panel.tsx:29`, `TaskDetailView.tsx:34,131` e `Session.tsx:27-33` não tratam 401 nem chamam `me()` | No app: em 401 limpar `leia:auth` e redirecionar para `/entrar?next=`; no serviço: permitir vários tokens por usuário ou avisar no login |
| media | Respostas do chat com listas em itálico, travessões e recusa em jargão | `app_gestao.py:986-996` (prompt sem regras de formato); `apps/web/components/Inline.tsx:3` (regex trata `* item` como itálico); `pt-BR.json:82` (`c3.notInDocument`) não é usado; `ChatSheet.tsx:14` tem texto próprio | Instruir "sem markdown, sem travessão, frases curtas" no prompt; renderizar listas; padronizar a recusa com a frase prevista e oferecer o encaminhamento ao advogado |
| media | PDF inválido vira "Deu um problema do nosso lado, não foi você." | Serviço responde 400 "Este arquivo não é um PDF." (`app_gestao.py:94-95`); `lib/api.ts:33` descarta o corpo; `Upload.tsx:40` mapeia todo erro para `systemError` | Propagar `detail` dos 4xx e mostrar mensagem específica; checar magic `%PDF` no cliente antes do envio |
| media | Cartão da cidadã perde "Ver comprovante" após rodada reprovada posterior | Serviço aceita nova rodada depois de `assinada` sem reverter status (`app_gestao.py:912-951`); listagem expõe só `ultima_tentativa` (`api_tarefas.py:90-101`); `Panel.tsx:81` vs `TaskDetailView.tsx:47` | Expor `melhor_tentativa` ou `comprovante_token` na listagem; ou bloquear nova rodada após aprovação |
| media | Documento com marcações: cartões vazios, botões de lastro pequenos com nomes internos e sem âncora, página muito longa | `DocumentView.tsx:69-84` (classe com 0 itens ainda renderiza), `:53` (refs `identificacao[0]`, `T7_SINTESE_FATOS` sem `min-h`, refs `T7..T10` sem `mark-*` no DOM), `:62` (texto inteiro em mono) | Ocultar classes vazias; rotular lastro com texto humano e só quando houver âncora; alvo de toque 44 px; texto em fonte normal e recolhido por padrão |
| media | Página HTML própria do serviço `/t/{hash}` embute o gabarito | `templates/cliente_view.html:253` (`data-correta`), `:268` (`justificativa`); rota `app_gestao.py:864-906`; `docs/LLM-API-CONTRACT.md:37-38` afirma o contrário | Remover os atributos e corrigir no servidor, ou desligar a rota HTML legada em produção (o app não a usa) |
| media | Rate limit único por IP para todas as rotas limitadas; `POST /api/tarefas` limitado sem documentação | `leia/ratelimit.py:19-26,64,67`; rotas em `app_gestao.py:912,968`, `api_cliente.py:122`, `api_auth.py:46,64`, `api_tarefas.py:106`; `apps/llm-service/README.md:32-33` e `docs/API-V3-CONTRACT.md:45-46` desatualizados; sala de auditoria atrás de um NAT esgota o balde junto | Baldes por rota (chat mais folgado, login/cadastro mais restrito); documentar; considerar chave por usuário para rotas Bearer |
| media | `POST /login` (form) sem rate limit | `app_gestao.py:149-161` sem `Depends(rate_limit)`; mesmo PBKDF2 de `core/auth.py:30-36`; 6 tentativas erradas responderam 303 com o balde esgotado | Adicionar `Depends(rate_limit)` ou remover o login por formulário |
| media | Rotas sem chamador expostas atrás do cookie/Bearer; `artefato/meta.json` expõe e-mail do remetente; submit externo sem auth | `main.py:586`; `app_gestao.py:440, 468, 535, 553, 813-838, 843`; `core/api.py:25-28,90-93`; `core/api_jurisprudencia.py:19-22` | Remover ou desligar por flag antes da auditoria; se mantiver `artefato`, filtrar `meta.json`; questões ao dono do serviço em `docs/SERVICE-V2-MAP.md:564-568` |
| media | Entregas 2, 3 e 4 sem tag, sem CHANGELOG e sem MANIFEST; prazo da Entrega 4 (dom 10h30) já passou | `git tag`: só `token-economy/v0.1.0`; `CHANGELOG.md:16-29` "A preencher"; nenhum `evidence/*/MANIFEST.md`; `README.md:26-30` lista entregas como "planejada"/"em construção"; política em `docs/DELIVERIES.md:3-6` e `docs/CONTRIBUTING.md:20-22` | Rodar `scripts/tag-delivery.sh` (árvore está limpa), preencher CHANGELOG, criar `MANIFEST.md` em `evidence/02..04` e atualizar a tabela do README |
| media | `evidence/` quase vazia e testes internos sem resultado | `evidence/01-canvas`, `02-internal-tests`, `03-external-tests`, `05-slides`, `extras` com 0 arquivos (pastas vazias nem existem no remoto: `README.md:25` e `docs/CANVAS.md:3` viram links quebrados); `evidence/04-product` só com 20 PNG; `docs/INTERNAL-TESTS.md` com 0 de 13 casos preenchidos e casos T03, T08-T10 que pressupõem rubrica de resposta aberta inexistente | Subir canvas, prints e planilhas com `MANIFEST.md`; preencher INTERNAL-TESTS com os resultados desta revisão (as capturas em `/tmp/leia-review` servem) e alinhar os casos ao quiz de múltipla escolha |
| media | Prompts que rodam não estão registrados em `prompts/` (D3) | `prompts/README.md:19-20` prevê catálogo inexistente; `prompts/workflow/v0-carlos.json` difere do `apps/llm-service/protocolo_pdf.json` que roda (ids, tokens, seed, parallel); system prompt do chat inline em `app_gestao.py:986-996`; `prompts/build-log.md` sem entrada de 13/09 apesar de 31 commits | Copiar `protocolo_pdf.json` para `prompts/workflow/v1-*.json` (ou apontar o README para o arquivo real), extrair o prompt do chat para arquivo versionado (`CITIZEN_CHAT_PROMPT_FILE` já é citado na doc mas não lido), atualizar o build-log |
| media | Documentação e contratos defasados em relação ao produto | `docs/LLM-API-CONTRACT.md:5-6,14-15,21,32-33,52-57` (rota "a acrescentar" que existe, campos `explicacao`/`clausula`, SSE sem `done`, mock que não reproduz v3); `docs/SERVICE-V2-MAP.md:71,89,325-348,423` (coluna "pendente" já feita, `/docs` exposto, 303 vs 401); `docs/SCREENS.md`, `MVP.md`, `USE-CASES.md`, `ARCHITECTURE.md`, `SCALING.md`, `AUDIT-GUIDE.md`, `INTEGRATION-PLAN.md` descrevem rotas `/documents`, `/sessions`, `/lawyer/*`, login Google, Polygon Amoy, modelos Claude/GPT que nunca existiram; `.env.example` da raiz com 8 chaves não lidas; `docs/REUSE.md:9` expõe caminhos locais e repositório privado | Marcar SERVICE-V2-MAP e design como históricos; reescrever LLM-API-CONTRACT a partir de `API-V3-CONTRACT.md` (este está correto); corrigir AUDIT-GUIDE (nome do PDF, OTS em vez de testnet, 14 tarefas + END); apagar `.env.example` da raiz; remover caminhos locais de REUSE.md |
| baixa | Página 404 padrão do Next em inglês | `apps/web/app` sem `not-found.tsx` | Criar `not-found.tsx` com cabeçalho e link para `/` |
| baixa | Plural fixo "1 dúvidas abertas" | `messages/pt-BR.json:244`, `Panel.tsx:69` (`fmt` sem plural) | Duas chaves (singular/plural) ou `Intl.PluralRules` |
| baixa | Emoji nos títulos vindos do serviço; "Ouvir" recebe o título bruto | `protocolo_pdf.json:161` exige cabeçalhos com emoji; `api_cliente.py:71-79` copia o cabeçalho; `Journey.tsx:148` limpa no h1 mas `:150` monta o texto do TTS sem `cleanTitle` | Tirar emoji do prompt e limpar também no serviço; usar `cleanTitle` no texto falado |
| baixa | Status `enviada` aceito pelo serviço mas não pelo app | `leia/api_cliente.py:29`, `api_tarefas.py:24`, `app_gestao.py:874` vs `apps/web/lib/status.ts:8-13`; nenhum caminho grava `enviada` hoje | Remover o valor de `READY_STATUSES` ou adicionar em `status.ts` |
| baixa | Identidade de build inconsistente e banner cobre a barra inferior | `vercel deploy --prod` sem `--build-env GIT_COMMIT_SHA` cai no fallback `dev` (`next.config.ts:7`, `scripts/gen-sw.mjs:6-7`); link do rodapé aponta para github.com/deegalabs/leia/commit/589da62 (404, repositório privado) e para o pai do commit publicado; a 390 px o toast (`UpdatePrompt.tsx:36`, `bottom-3 z-50`) cobre "Conferir o registro" no comprovante | Passar `GIT_COMMIT_SHA` no deploy (documentar no README); esconder o link do commit enquanto o repositório for privado; posicionar o toast acima da `BottomActionBar` |
| baixa | `.env.example` do serviço com padrões inseguros e duas lacunas | `ADMIN_PASSWORD=trocar123`, `SESSION_COOKIE_SECURE=false`, `ADVOGADO_SIGNUP=true` (fallback `"true"` em `api_auth.py:43`: qualquer pessoa cria conta de advogado e consome cota Groq); `API_KEY` só em comentário; `LEIA_FIXTURE` ausente | Padrões seguros no exemplo; decidir `ADVOGADO_SIGNUP=false` em produção ou exigir OAB validada |
| baixa | Arquivos indevidos versionados | `apps/llm-service/app_gestao.py.rej` (hunk já aplicado), `contexto_persistente.json` (estado de runtime, `[]`), `core/pd_extract.py` (0 bytes), `protocolo_jurisprudencia.json` (sem referência); entram na imagem via `COPY . .` | `git rm`, acrescentar ao `.gitignore` e `.dockerignore` |
| baixa | Estados existentes no código e não verificados em produção | `Journey.tsx:82-85` (falhou); `Receipt.tsx:28,36` e `Verify.tsx:31,39` (carimbo pendente; ramo "demo" é inalcançável com o serviço real); `ChatSheet.tsx:74` (falha ao encaminhar dúvida); `AuthForm.tsx:36` (403); `Upload.tsx:34` (não PDF por extensão); `Receipt.tsx:44` (impressão); download do `registro.json` | Exercitar num ambiente de teste com `OTS_ENABLED=false` e um PDF que faça o pipeline falhar; remover o ramo "demo" morto |

## 6. Descartadas na verificação

- Botão flutuante "Tenho uma dúvida" cobre "Rever a explicação" no celular: pela geometria de `Journey.tsx:101` e `ui.tsx:9-10,30` o FAB (96 a 148 px do rodapé) sobrepõe a borda do botão primário, não do secundário; não reproduzido visualmente. Vale conferir a sobreposição com "Próxima pergunta".
- Primeiro cadastro de cidadã falhou com erro genérico (15:49:47Z): não reproduzido em 6 tentativas; causa provável é `AuthForm.tsx:36` mostrar a mensagem genérica para 422 (senha curta), 429 ou falha de rede; logs do Railway inacessíveis (MCP sem login).
- "Copiar link da cliente" não confirmou "Copiado": limitação do Chrome headless sem permissão de clipboard; com permissão, `ui.tsx:73-79` copia o link e troca o rótulo por 2 s.
- Suíte de testes não rodou no python do sistema: rodou numa venv de scratch, 18 passed (77 avisos de `utcnow` depreciado); limitação de ambiente, não defeito.
- Árvore do repositório mudou durante a revisão (commit `e9b7eb2` trocou `PwaRegister.tsx` por `UpdatePrompt.tsx`): observação de processo; árvore atual limpa e consistente.

## 7. Como testar em 5 minutos

1. Abrir https://leia-snowy.vercel.app no celular ou a 390 px. Clicar em "Ver um exemplo": é a demo
   fixa `/t/0SVal1OCE4IHpiRHo-rsNA`. Não enviar o quiz nem encaminhar dúvida nela se quiser mantê-la
   intacta para o pitch.
2. Na demo: "Começar a explicação", passar pelos 6 pontos (o ponto 3 tem "Ver trecho original"),
   abrir "Tenho uma dúvida" e perguntar "Quanto eu pago se perder?" (resposta com valores do contrato)
   e depois "Qual é a capital da França?" (recusa).
3. Criar uma conta de advogado em `/entrar?modo=cadastro`, ir em `/enviar` e subir
   `examples/contrato-honorarios-exemplo.pdf`. Esperar 1 a 2 minutos na tela de espera (atualiza
   sozinha). Copiar o link da cliente.
4. Em outra janela anônima, criar uma conta de cidadã, abrir o link (a tarefa fica vinculada), ler os
   pontos, encaminhar uma dúvida ao advogado, responder as 6 perguntas (hoje a alternativa A acerta
   todas) e abrir "Ver meu comprovante" e "Conferir o registro". Baixar a prova `.ots`.
5. Voltar à janela do advogado: em `/painel` o cartão mostra "Rodada 1: 6 de 6" e "1 dúvidas abertas";
   em "Ver detalhes" responder a dúvida. Na janela da cidadã, `/painel` > "Ver detalhes" mostra a
   resposta.
6. Conferir por conta própria: `curl -s "$API/verify/<attempt>?format=json" | python3 -c "import json,sys,hashlib; d=json.load(sys.stdin); print(hashlib.sha256(d['canonical'].encode()).hexdigest()==d['payloadHash'])"`
   com `API=https://llm-service-production-4278.up.railway.app`.
7. Testes do serviço: `cd apps/llm-service && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt pytest && python -m pytest -q tests_leia.py tests_v3.py` (18 passed).

Atenção ao rate limit: 30 requisições por minuto por IP num único balde; várias pessoas atrás do mesmo
Wi-Fi contam juntas.
