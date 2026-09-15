# Mapa de integração do serviço v2 (FastAPI do Carlos)

Fonte: código recebido em 13/09 às 10h40, lido em `temp/oab-v2/` na pasta de trabalho. Toda referência
`arquivo:linha` abaixo aponta para esse diretório, salvo quando marcada como `repo:` (cópia já adaptada em
`apps/llm-service/`). Nada aqui foi inferido de documentação: o que não está no código está dito como ausente.

Situação da cópia no repositório: `diff -rq` entre `temp/oab-v2/` e `apps/llm-service/` mostra que só `main.py`,
`app_gestao.py`, `core/db.py`, `core/workspace.py`, `.gitignore` e `requirements.txt` diferem (as mudanças são nossas:
variáveis de ambiente, CORS, rota JSON da cidadã, comprovante). Os demais arquivos são idênticos. Ou seja, a v2 é a
mesma base que já está no repositório; este mapa descreve a v2 tal como veio e marca o que a cópia já resolveu.

## 1. Visão geral

O serviço é um monólito FastAPI com três fluxos sobre um mesmo SQLite (`gestao.db`) e uma mesma pasta de arquivos
(`workspace/{hash}/`):

1. **Destilação local de PDF** (`app_gestao.py:140-198` e `:538-586`): a pessoa logada envia um PDF, uma
   `BackgroundTask` roda `protocolo_pdf.json` em 14 chamadas sequenciais à Groq (`core/pipeline_pdf.py:199-358`) e grava
   `memoria_persistente.json`, `texto_tagueado.json`, `resumo_humanizado.md` e `questoes.json`.
2. **Dois jobs em APIs externas** ("Resumo Estruturado" em `core/api.py`, "Jurisprudência" em
   `core/api_caselaw.py`): o PDF ou texto é enviado sem autenticação a `api.resumoestruturado.com.br` ou
   `api.jurisprudencia.com.br`, com polling até concluir.
3. **Página pública da cidadã** `GET /t/{hash}` (`app_gestao.py:815-857`): resumo em markdown, quiz de múltipla escolha,
   chat em SSE e download de um PDF "assinado" após aprovação.

Além disso, `main.py:471-563` serve o chat de bastidores para quem está logado (`index.html`), com agentes definidos em
`protocolo.json` e uma memória de sessão por login (`core/session.py`).

Módulos:

| Arquivo | Papel |
|---|---|
| `main.py` | cria o app (`:44`), monta `/static` (`:47-48`), `init_db()` e usuário admin em tempo de import (`:58-70`), inclui o router de gestão (`:70`), rotas do chat de bastidores (`:471-563`), entrypoint `uvicorn` (`:569-571`) |
| `app_gestao.py` | login/sessão, painel, tarefas, jobs externos, memória de sessão, página e APIs da cidadã, PDF assinado |
| `core/db.py` | modelos SQLModel `Usuario`, `Tarefa`, `LogEvento`, `Tentativa` (`:16-59`), engine SQLite (`:9-10`), migrações idempotentes (`:71-109`) |
| `core/auth.py` | PBKDF2 (`:10-16`), login que gira `session_token` (`:30-36`), dependência `usuario_atual` por cookie `sessao` (`:44-53`) |
| `core/workspace.py` | pasta por tarefa, `meta.json`, `log.jsonl` (`:6-37`) |
| `core/session.py` | memória de sessão em `workspace/_sessoes/{token}.json` (`:29-35`), anexo compartilhado do chat (`:111-121`) |
| `core/attempts.py` | grava tentativa do quiz, calcula `aprovado` e `hash_imutavel` (`:21-72`), lista erros (`:93-117`) |
| `core/pipeline_pdf.py` | executa `protocolo_pdf.json` (`:246-358`), uma chamada Groq por task (`:84-114`) |
| `core/pdf_extract.py` | extração de texto com pypdf (`:8-19`); sem OCR |
| `core/pdf_sign.py` | carimbo na página 1 e página de assinatura com reportlab + pypdf (`:20-168`) |
| `core/api.py`, `core/api_caselaw.py` | clientes httpx dos jobs externos |
| `protocolo.json` | 1 agente do chat de bastidores (`:1-9`) |
| `protocolo_pdf.json` | workflow T1..T14 (`:19-185`) |
| `protocolo_jurisprudencia.json` | 8 agentes; nenhum arquivo `.py`/`.html` o referencia (não está ligado) |
| `templates/*.html` | `index.html` (bastidores), `login.html`, `dashboard.html`, `tarefa_nova.html`, `tarefa_detalhe.html`, `cliente_aguarde.html`, `cliente_view.html` |
| `static/` | `logo.svg`, `logo_inline.svg` |
| `_legacy/app_orquestrador_groq.py`, `protocolo.json.bak_historia_infantil`, `core/pd_extract.py` (0 bytes, removido) | não importados por nada |

Como sobe hoje:

- `python main.py` executa `uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)` (`main.py:571`). `PORT` não é
  lido em lugar nenhum; `reload=True` está fixo.
- Dependências pip puras (`requirements.txt:1-9`: fastapi, uvicorn[standard], jinja2, python-multipart, groq, sqlmodel,
  pypdf, reportlab, httpx). Não há `python-dotenv`, `Dockerfile`, `Procfile`, `runtime.txt` nem `pyproject`.
- Só três leituras de ambiente em todo o código: `API_KEY` (`main.py:26-29`), `RESUMO_ESTRUTURADO_API_BASE`
  (`core/api.py:25-28`) e `JURISPRUDENCIA_API_BASE` (`core/api_caselaw.py:19-22`).
- Caminhos relativos ao diretório de trabalho (CWD): `gestao.db` (`core/db.py:9-10`), `workspace/`
  (`core/workspace.py:6-7`, criado no import), `workspace/_sessoes/` (`core/session.py:29-30`), `protocolo_pdf.json`
  (`core/pipeline_pdf.py:38`) e `templates` em `app_gestao.py:30`. Já `main.py` resolve `templates`, `static`,
  `protocolo.json`, `help.md` e `contexto_persistente.json` contra `BASE_DIR` (pasta do arquivo, `main.py:39-48`). Rodar
  com CWD diferente da raiz do serviço divide o app em dois.
- No import: `init_db()` cria tabelas e aplica `ALTER TABLE` (`core/db.py:71-109`, chamado em `main.py:58`), e cria
  `admin@local / trocar123` com `papel="fornecedor"` se não existir, registrando a senha em claro no log (`main.py:60-68`).
- `help.md` não existe na árvore; `GET /api/help` devolve o texto padrão de `main.py:166`.

## 2. Rotas

Convenções: "cookie" = cookie `sessao` obrigatório via `Depends(usuario_atual)`; sem cookie válido a resposta é
HTTP 303 com `Location: /login` (`core/auth.py:48-52`), não 401. `_permite_ver` = tarefa própria, ou qualquer tarefa
quando `papel != "advogado"` (`app_gestao.py:60-61`).

### 2.1 Sessão e login

| Método | Rota | Auth | Entrada | Saída | Efeitos |
|---|---|---|---|---|---|
| GET | `/login` (`app_gestao.py:67-73`) | nenhuma | query `erro` opcional | HTML `login.html` | nenhum |
| POST | `/login` (`:76-87`) | nenhuma | form `email`, `senha` | 303 para `/dashboard` com `Set-Cookie: sessao=<token_urlsafe(32)>; HttpOnly; SameSite=Lax` (`:86`, sem `Secure`, sem `Max-Age`); falha: 303 para `/login?erro=credenciais` (`:84`) | grava `Usuario.session_token` (`core/auth.py:34-35`) |
| POST | `/logout` (`:90-104`) | cookie lido à mão (`:95`) | nenhuma | 303 para `/login`, cookie apagado | `session_token=None`; apaga `workspace/_sessoes/{token}.json` (`core/session.py:102-104`) |

### 2.2 Painel

| Método | Rota | Auth | Entrada | Saída | Efeitos |
|---|---|---|---|---|---|
| GET | `/` (`main.py:471-482`) | cookie | nenhuma | HTML `index.html` com `protocolo_init`, `help_init`, `usuario` | nenhum |
| GET | `/dashboard` (`app_gestao.py:110-134`) | cookie | nenhuma | HTML `dashboard.html` com `usuario`, `tarefas` (só as próprias se `papel == "advogado"`, `:117-118`), `contagem {total, <status>: n}`; `<meta refresh 5>` enquanto houver `criada`/`processando` (`dashboard.html:11-13`) | nenhum |
| GET | `/static/*` (`main.py:47-48`) | nenhuma | caminho | arquivos de `static/` | nenhum |
| GET | `/docs`, `/redoc`, `/openapi.json` | nenhuma | | padrão do FastAPI; `main.py:44` não desliga | expõe a lista de rotas sem login |

### 2.3 Tarefas (destilação local)

| Método | Rota | Auth | Entrada | Saída | Efeitos |
|---|---|---|---|---|---|
| POST | `/api/pdf/destilar` (`app_gestao.py:140-198`) | cookie | multipart `pdf` (nome deve terminar em `.pdf`, `:156`) | `{"tarefa_id": int, "hash": str}` (`:198`) | grava `workspace/{hash}/original.pdf` (`:163`), `Tarefa(status="criada", titulo=nome do arquivo[:200])` (`:165-173`), `meta.json` com `advogado {id, email, nome}`, `pdf_bytes`, `origem: "chat_destilacao"` (`:176-184`), `log.jsonl` `criada` e `pdf_salvo` (`:185-186`); agenda `executar_pipeline_pdf(t.id, groq_client, "", session_token)` (`:195`) |
| GET | `/api/pdf/{hash}/destilado` (`:201-222`) | cookie + `_permite_ver` (404) | | `{"status", "titulo", "memoria": <memoria_persistente.json ou null>, "resumo": <resumo_humanizado.md ou null>}`; `questoes` não vem, apesar do docstring (`:207-212`) | nenhum |
| GET | `/api/pdf/{hash}/log` (`:225-248`) | cookie + `_permite_ver` | | `{"status", "eventos": [...]}` filtrado a `tipo` em `pipeline_start, texto_extraido, task_start, task_done, task_error, erro_extracao, erro_protocolo, pipeline_done` (`:242-246`) | nenhum |
| GET | `/tarefas/nova` (`:529-535`) | cookie | | HTML `tarefa_nova.html` | nenhum |
| POST | `/tarefas/nova` (`:538-586`) | cookie | multipart `titulo`, `pdf` | 303 para `/tarefas/{id}` | igual a `/api/pdf/destilar`, mas `meta.json` sem `origem` e pipeline sem `session_token` (`:583`) |
| GET | `/tarefas/{id}` (`:592-652`) | cookie; 404/403 (`:600-603`) | | HTML `tarefa_detalhe.html` com `tarefa`, `eventos`, `link_cliente = base_url + /t/{hash}` (`:623`), `resumo_md`, `texto_extraido`, `questoes`, `memoria`, `texto_tagueado`, `num_questoes`, `historico`, `melhor_tent`, `tentativas_erros`; recarrega a cada 3 s enquanto `criada`/`processando` (`tarefa_detalhe.html:299-301`) | nenhum |
| POST | `/tarefas/{id}/reprocessar` (`:658-697`) | cookie + `_permite_ver`; 409 se `processando` (`:670-671`) | | 303 para `/tarefas/{id}` | apaga `texto_extraido.txt`, `memoria_persistente.json`, `texto_tagueado.json`, `resumo_humanizado.md`, `questoes.json`, `pdf_assinado.pdf` e `T*.json` (`:673-682`); `status="criada"`; reagenda o pipeline (`:694`) |
| POST | `/tarefas/{id}/nova-rodada` (`:703-758`) | cookie + `_permite_ver` | | 303 para `/tarefas/{novo.id}` | copia `original.pdf` para um novo hash (`:724`); nova `Tarefa(clone_de, rodada+1, titulo + " · rodada N")` (`:726-735`); pipeline com `variacao` "Gere 12 questões COMPLETAMENTE DIFERENTES" (`:750-754`) |
| GET | `/tarefas/{id}/artefato/{nome}` (`:764-788`) | cookie + `_permite_ver` | `nome` em `texto_extraido.txt, memoria_persistente.json, texto_tagueado.json, resumo_humanizado.md, questoes.json, log.jsonl, meta.json` ou qualquer nome começando com `T` (`:777-782`) | `FileResponse` chamado `{hash}_{nome}` | nenhum |
| GET | `/api/tarefas/{id}/status` (`:794-809`) | cookie + `_permite_ver` | | `{"status", "atualizada_em": iso, "eventos_recentes": [últimos 8 do log.jsonl]}` | nenhum |
| GET | `/tarefas/{id}/pdf-assinado` (`:1022-1050`) | cookie + `_permite_ver`; 403 sem tentativa aprovada | | mesmo PDF da rota pública | regenera `pdf_assinado.pdf`; `log.jsonl` `pdf_assinado_admin` |

### 2.4 Resumo estruturado (API externa)

| Método | Rota | Auth | Entrada | Saída | Efeitos |
|---|---|---|---|---|---|
| POST | `/api/resumo-estruturado/submit` (`app_gestao.py:257-316`) | cookie | multipart `pdf` e/ou form `texto`; 400 "Envie um PDF ou um texto." (`:273`); 400 se o nome não termina em `.pdf` (`:274-275`) | `{"tarefa_id", "hash"}` | `original.pdf` se houver PDF (`:285`); `meta.json` `origem: "resumo_estruturado_api_externa"` (`:298-305`); agenda `executar_resumo_estruturado` (`:312-313`). Se há PDF, o `texto` não é enviado (`core/api.py:59-62`) |
| GET | `/api/resumo-estruturado/{hash}/status` (`:319-334`) | cookie + `_permite_ver` | | `{"status", "eventos": [tipo começa com "resumo_estruturado"]}` | nenhum |
| GET | `/api/resumo-estruturado/{hash}/resultado` (`:337-353`) | cookie + `_permite_ver` | | `{"status", "titulo", "dados_llm": <resumo_estruturado.json ou null>, "doc_text": <resumo_estruturado_texto.txt ou null>}` | nenhum |
| POST | `/api/resumo-estruturado/{hash}/rerun/{step_id}` (`:356-377`) | cookie + `_permite_ver` | | JSON repassado de `POST /jobs/{job_id}/rerun/{step_id}` externo; 409 sem `job_id` (`:371`); 502 em erro (`:377`) | chamada externa (`core/api.py:89-95`) |

Tarefas criadas por este fluxo nunca rodam o pipeline local: não têm `resumo_humanizado.md` nem `questoes.json`, e
`GET /t/{hash}` mostra "*(resumo indisponível)*" sem quiz (`app_gestao.py:832`).

### 2.5 Jurisprudência (API externa)

| Método | Rota | Auth | Entrada | Saída | Efeitos |
|---|---|---|---|---|---|
| POST | `/api/jurisprudencia/submit` (`app_gestao.py:384-448`) | cookie | multipart `pdf` e/ou form `texto` e/ou form `consulta`; 400 se nenhum (`:400-401`) | `{"tarefa_id", "hash"}` | `meta.json` `origem: "jurisprudencia_api_externa"` com `consulta` (`:429-437`); agenda `executar_jurisprudencia` (`:444-445`) |
| GET | `/api/jurisprudencia/{hash}/status` (`:451-466`) | cookie + `_permite_ver` | | `{"status", "eventos": [tipo começa com "jurisprudencia"]}` | nenhum |
| GET | `/api/jurisprudencia/{hash}/resultado` (`:469-485`) | cookie + `_permite_ver` | | `{"status", "titulo", "dados_llm": <jurisprudencia_resultado.json>, "doc_text": <jurisprudencia_texto.txt>}` | nenhum |

### 2.6 Cidadã (públicas, sem autenticação; o hash de 22 caracteres é o único segredo)

| Método | Rota | Auth | Entrada | Saída | Efeitos |
|---|---|---|---|---|---|
| GET | `/t/{hash}` (`app_gestao.py:815-857`) | nenhuma | | 404 "Link inválido ou expirado" (`:822-823`); se `status` não está em `("pronta", "enviada", "assinada")` (`:825`): HTML `cliente_aguarde.html` com `<meta http-equiv="refresh" content="5">` (`cliente_aguarde.html:7`); senão HTML `cliente_view.html` com `tarefa`, `resumo_md`, `questoes` (JSON completo, inclusive `correta` e `justificativa`), `memoria`, `ultima_tentativa` (a última por `numero`, `:836-837`), `erros_ultima`, `historico` | `log.jsonl` `cliente_abriu {ip, ua[:200]}` (`:841-843`) |
| POST | `/api/t/{hash}/quiz` (`:863-908`) | nenhuma | JSON `{"respostas": {"<id da questão como string>": <índice 0-3>}}`; 404 hash inválido (`:872`); 409 "Questões não disponíveis" (`:877`) | `{"numero": int, "acertos": int, "total": int, "aprovado": bool, "hash_imutavel": sha256 hex, "ts": iso, "erros": [{"id", "area", "enunciado", "escolhida", "correta", "justificativa", "alternativas"}], "pode_baixar_pdf": bool}` (`:899-908`; `erros` em `core/attempts.py:93-117`) | grava `Tentativa` com `ip` e `user_agent` (`:880-883`); `log.jsonl` `tentativa`; primeira aprovação muda `status` para `"assinada"` e grava `LogEvento` (`:891-897`). Sem limite de tentativas |
| POST | `/api/t/{hash}/chat` (`:914-973`) | nenhuma | JSON `{"mensagem": str}`; 400 se vazia (`:926`) | `text/event-stream`: `data: {"t": "<token>"}\n\n` por token (`:962-963`), depois `data: {"done": true}\n\n` (`:964`); em exceção `data: {"error": "..."}\n\n` (`:966-967`); cabeçalhos `Cache-Control: no-cache`, `X-Accel-Buffering: no` (`:972`) | chamada Groq `openai/gpt-oss-120b`, `temperature=0.3`, `max_completion_tokens=1500` (`:949-955`); system prompt fixo + `resumo_humanizado.md` + `memoria_persistente.json[:12000]` (`:928-942`); um turno só; nada é gravado |
| GET | `/t/{hash}/pdf-assinado` (`:993-1019`) | nenhuma; 403 a menos que a melhor tentativa (maior `acertos`, `core/attempts.py:84-90`) esteja aprovada (`:1002-1004`) | | `application/pdf` chamado `{hash}_assinado.pdf`: PDF original com carimbo na página 1 e página final com `titulo`, hash da tarefa, rodada, `ts`, `acertos/total`, IP, navegador (`user_agent[:70]`) e `hash_imutavel` (`core/pdf_sign.py:99-122`) | regenera `pdf_assinado.pdf` a cada download (`:1011-1012`); `log.jsonl` `pdf_assinado_baixado` |

Observação: a página `cliente_view.html` usa a **última** tentativa (`app_gestao.py:837`) para o cartão de assinatura,
mas o PDF usa a **melhor** (`:1001`); `melhor` não tem desempate (`core/attempts.py:84-90`).

### 2.7 Bastidores e chat de quem está logado

| Método | Rota | Auth | Entrada | Saída | Efeitos |
|---|---|---|---|---|---|
| GET | `/api/protocolo` (`main.py:488-490`) | cookie | | `{"conteudo": <texto de protocolo.json>}` | nenhum |
| POST | `/api/protocolo` (`:493-495`, `:169-177`) | cookie | JSON `{"conteudo": <texto JSON>}` | `{"message": "✅ Protocolo salvo (N agentes)"}` ou `"❌ Erro JSON: ..."` | **sobrescreve `protocolo.json` no diretório do código** (`:172`) |
| GET | `/api/help` (`:498-500`) | cookie | | `{"conteudo": str}` | nenhum |
| GET | `/api/contexto` (`:503-505`) | cookie (qualquer usuário) | | `{"contexto": [{role, content, timestamp, agent?}]}` de um arquivo global | nenhum |
| POST | `/api/contexto/limpar` (`:508-510`) | cookie | | `{"message"}` | grava `[]` em `contexto_persistente.json` para todos (`:198`) |
| POST | `/api/chat` (`:513-563`) | cookie; cookie também lido à mão (`:539`) | multipart `texto` (obrigatório), `objetivo`, `protocolo_json` (se não for lista JSON não vazia cai em `protocolo.json`, `:526-532`), `anexos[]` (decodificados como texto, `:217-224`) | `text/event-stream` com `data: <json>\n\n`; `type` em `error, user, agent_start, agent_payload, agent_token, agent_think, agent_done, stop, agent_error, final` (`:352-465`); `final` traz `elapsed` só em `done`/`stopped` | uma chamada Groq por agente (`temperature=1`, `max_completion_tokens=6048`, `top_p=1`, `:289-292`), `asyncio.sleep(0.2)` entre agentes (`:403`); anexa cada turno ao `contexto_persistente.json` global (`:365-370`, `:447-454`); injeta `workspace/_sessoes/{token}.json` como `<anexo_sessao_destilado>` (`:538-551`) |
| GET | `/api/sessao/memoria` (`app_gestao.py:494-508`) | cookie | | `{"processadas": [{aba, hash, titulo, processado_em}], "anexo": {jurisprudencia, resumo_estruturado, chat} ou null}` | nenhum |
| POST | `/api/sessao/memoria/limpar` (`:511-526`) | cookie | form `aba` opcional em `jurisprudencia, resumo_estruturado, chat` (400 se inválida) | `{"message"}` | apaga ou reescreve `workspace/_sessoes/{token}.json` |

## 3. Formas de dados

### 3.1 Modelos do banco (`core/db.py:16-59`)

| Tabela | Campos |
|---|---|
| `usuario` (`:16-23`) | `id`, `email` (único, minúsculas), `senha_hash` (`pbkdf2_sha256$200000$<salt>$<dk>`, `core/auth.py:13-16`), `nome`, `papel` (padrão `"advogado"`; o admin nasce `"fornecedor"`, `main.py:66`), `session_token` (texto em claro, uma sessão por usuário), `criado_em` |
| `tarefa` (`:26-37`) | `id`, `hash` (`secrets.token_urlsafe(16)`, `core/workspace.py:10-12`), `titulo` (<= 200), `advogado_id`, `status`, `pdf_nome`, `workspace_path` (ex.: `workspace/<hash>`, relativo ao CWD), `clone_de`, `rodada` (padrão 1), `criada_em`, `atualizada_em` |
| `logevento` (`:40-45`) | `id`, `tarefa_id`, `ts`, `tipo`, `payload` (texto JSON, cortado em 2000 em `core/pipeline_pdf.py:179`) |
| `tentativa` (`:48-59`) | `id`, `tarefa_id`, `numero` (sequencial por tarefa), `respostas` (JSON `{"<id>": idx}` com `sort_keys`), `acertos`, `total` (= `len(questoes)`), `aprovado`, `hash_imutavel`, `ip`, `user_agent` (<= 300), `criada_em` |

Valores de `status` efetivamente gravados: `criada` (`app_gestao.py:169, 291, 422, 559, 684, 730`), `processando`
(`core/pipeline_pdf.py:228`, `core/api.py:162`, `core/api_caselaw.py:129`), `pronta` (`pipeline_pdf.py:338`,
`api.py:235`, `api_caselaw.py:202`), `falhou` (`pipeline_pdf.py:236, 251, 297`; `api.py:170, 178, 191, 211, 224`;
`api_caselaw.py:137, 145, 158, 178, 191`), `assinada` (`app_gestao.py:892`). `enviada` só aparece na tupla de
`app_gestao.py:825` e nunca é gravado. Não existe `concluida`.

Datas são `datetime.utcnow()` sem fuso (naive UTC) em todos os modelos.

### 3.2 Tentativa e `hash_imutavel` (`core/attempts.py:21-72`)

```
aprovado = acertos >= max(1, int(total * 0.83))                       # :49, comentário diz "10/12"; int(12*0.83) = 9
hash_imutavel = sha256("PARA.AI|{tarefa_hash}|{numero}|{respostas_json}|{ip}|{ua}|{ts}")   # :25-26
```

Com 3 questões aprova com 2, com 6 com 4, com 12 com 9. O hash não tem salt e inclui IP, user-agent e timestamp: é
recalculável a partir dos campos impressos no PDF assinado. `ip` vem de `request.client.host` (`app_gestao.py:880`), sem
tratar `X-Forwarded-For`.

### 3.3 `questoes.json` (saída da T14, `protocolo_pdf.json:165-174`; gravado em `core/pipeline_pdf.py:333-334`)

```json
{"questoes": [{"id": 1, "area": "identificacao|fatos|fundamentos|pedidos|contexto",
               "enunciado": "<= 120 chars, termina em ?", "alternativas": ["4 x <= 80 chars"],
               "correta": 0, "justificativa": "<= 120 chars", "dificuldade": "facil"}]}
```

A quantidade é inconsistente no próprio prompt: nome "T14 · 3 Perguntas Fáceis" (`:167`), missão "GERE 3 PERGUNTAS",
"DISTRIBUIÇÃO OBRIGATÓRIA (total: 3)" cujos itens somam 3+4+2+2+1 = 12, contrato "id: inteiro sequencial 1 a 6" e
"EXATAMENTE 6 objetos". A nova rodada pede 12 (`app_gestao.py:752`); a página diz "10 de 12" (`cliente_view.html:248, 497`)
e "≥ 10/12" (`:310`). A correção usa `len(questoes)` em tempo de execução (`core/attempts.py:40`).

### 3.4 `memoria_persistente.json` (saída da T6, `protocolo_pdf.json:77-85`; gravado em `core/pipeline_pdf.py:317-319`)

```json
{"memoria_persistente": {"identificacao": [item], "datas_valores": [item], "fatos": [item],
                         "fundamentos": [item], "pedidos": [item], "total_fragmentos": 0}}
item = {"campo": "<enum por classe>", "valor": "...", "trecho_verbatim": "<cópia exata do texto>",
        "pos_trecho_verbatim": "1234:1280", "sintese_relacao": null}
```

Enums de `campo`: identificacao `autor|reu|juiz|advogado_autor|advogado_reu|ministerio_publico|testemunha|perito`
(`:29`); datas_valores `data_fato|data_contrato|data_decisao|data_intimacao|prazo|valor_pedido|valor_contrato|valor_dano|valor_multa|valor_deposito`
(`:40`); fatos `acontecimento_principal|fato_secundario|contexto|consequencia|dano` (`:51`); fundamentos
`artigo_lei|artigo_cf|sumula|tema_repetitivo|jurisprudencia|principio|doutrina` (`:62`); pedidos
`principal|sucessivo|subsidiario|liminar|expediente|custas|honorarios` (`:73`). O texto da regra escreve a posição como
`"[inicio:fim]"` e o exemplo obrigatório como `"1234:1280"` (`:29`); nenhum código em `core/` lê esse campo, e nenhum
código confere que `trecho_verbatim` é substring de `texto_extraido.txt`.

### 3.5 Sínteses com lastro T7..T11 (`protocolo_pdf.json:88-140`)

Uma por classe, gravada só como `T7_SINTESE_FATOS.json` ... `T11_SINTESE_CONTEXTO.json` (`core/pipeline_pdf.py:304`),
sem consolidação e sem rota JSON; só via `GET /tarefas/{id}/artefato/T7_SINTESE_FATOS.json` com cookie (`app_gestao.py:781`).

```json
{"sintese_fatos": {"campo": "sintese_fatos", "valor": "<1 a 3 parágrafos em linguagem simples>",
                   "lastro": ["fatos[0]", "fatos[1]", "datas_valores[0]"], "pos_trechos_origem": ["1234:1280"]}}
```

`lastro` indexa itens de `memoria_persistente` (é o elo tópico -> trecho literal). `resumo_estruturado.json` da API
externa é outra fonte, com outro esquema (3.7); `processo.resumo_classe_*` citado em `docs/LLM-API-CONTRACT.md` pertence
a essa API externa, não ao pipeline local.

### 3.6 `resumo_humanizado.md` (T13, `tipo_saida: "texto"`, `protocolo_pdf.json:154-162`; `core/pipeline_pdf.py:325-331`)

Markdown de até 2800 caracteres com seções fixas: `# Resumo em uma linha`, `## 👥 Quem está nesta história`,
`## 📖 O que aconteceu`, `## 💭 O que a pessoa sente e busca`, `## 🤝 O que está sendo pedido`,
`## 🧭 Onde a história está agora`. O prompt proíbe artigos, datas, número de processo, termos jurídicos e frases com
mais de 15 palavras; dado ausente vira "não foi informado". Persona: história para uma criança de 10 anos (`:161`).
Se o modelo devolver um dict, o código usa `.resumo_humanizado` ou `.texto` (`pipeline_pdf.py:327-330`).

### 3.7 `resumo_estruturado.json` e `jurisprudencia_resultado.json` (API externa)

Esquema definido pela API externa; o que o `index.html` espera (`:1437-1443, 1531, 1640-1642, 2064-2069`):

```json
{"processo": {"classe_<x>": [{"campo", "sub_tipo", "valor", "trecho_verbatim", "sintese_relacao"}],
              "resposta_final": {"texto": "<markdown com seções ##>"}, "conferencia": "..."},
 "_ui": {"classe_<x>": [{"pos_trecho_verbatim": "a:b", "score_trecho_verbatim": 0.0}]}}
```

Com fallback para o layout `{identificacao, datas_valores, fatos, fundamentos, pedidos}` ou chave/valor genérico.

### 3.8 Job externo (`core/api.py:41-107`; `core/api_caselaw.py:35-74`)

| Chamada | Corpo | Resposta |
|---|---|---|
| `POST /submit` | multipart `file=(nome, bytes, application/pdf)` ou `text=<str>`; resumo acrescenta `enable_synthesis="true"`, `reasoning_effort="medium"`, `modo_disparo="paralelo"` (`api.py:45-57`); jurisprudência acrescenta `consulta` (`api_caselaw.py:45-47`) | `{"job_id": str, "total_steps": int}` gravado em `resumo_estruturado_job.json` / `jurisprudencia_job.json` |
| `GET /status/{job_id}` | | `{"status": "done"\|"error"\|outro, "current_step", "step_index", "total_steps", "tokens_total", "elapsed", "error"}` |
| `GET /result/{job_id}` | | `{"dados_llm", "doc_text", "tokens_total", "elapsed"}` gravado em `resumo_estruturado.json` + `resumo_estruturado_texto.txt` (ou `jurisprudencia_resultado.json` + `jurisprudencia_texto.txt`) |
| `POST /jobs/{job_id}/rerun/{step_id}` | | repassado |
| `POST /export-pdf` (`api.py:98-107`) | | sem chamador em lugar nenhum |

### 3.9 Eventos `log.jsonl` (`core/workspace.py:27-30`)

Linha `{"ts": iso utc, "tipo": str, ...extras}`. Tipos: `criada{tarefa_id, advogado_id}`, `pdf_salvo{nome, bytes}`,
`pipeline_start{tarefa_id}`, `texto_extraido{chars}`, `task_start{id, idx, total}`, `task_done{id, tempo}`,
`task_error{id, erro}`, `erro_extracao{erro}`, `erro_protocolo{erro}` (só em `LogEvento`), `pipeline_done{elapsed}`,
`reprocessar`, `clonada{origem, rodada}`, `cliente_abriu{ip, ua}`, `tentativa{numero, acertos, total, aprovado, hash}`,
`pdf_assinado_baixado{tentativa}`, `pdf_assinado_admin{tentativa}`, `resumo_estruturado_start|job|status|erro|done`,
`jurisprudencia_start|job|status|erro|done`. Em `task_*` o campo é `id` (`T1_IDENTIFICADOR_PARTES` ... `T14_QUESTOES`), não `step`.

### 3.10 Outros arquivos

- `meta.json` (`app_gestao.py:176-184, 298-305, 429-437, 566-573, 738-745`): `{hash, titulo, advogado: {id, email, nome}, pdf_nome, pdf_bytes?, consulta?, criada_em, origem?}`; clones: `{hash, titulo, clone_de, clone_hash, rodada, criada_em}`.
- `workspace/_sessoes/{token}.json` (`core/session.py:26-35, 62-87`): `{jurisprudencia, resumo_estruturado, chat}`, cada parte `null` ou `{hash, titulo, processado_em, resumo_estruturado}`; na aba `chat`, `resumo_estruturado = {memoria_persistente, resumo_humanizado}` (`core/pipeline_pdf.py:344-356`).
- `contexto_persistente.json` (`main.py:180-202`): lista global `{role, content ("[USUARIO] ..." ou "[<agente>] ..."), timestamp, agent?}`; hoje contém `[]`.
- `texto_tagueado.json` (T12, `protocolo_pdf.json:143-151`): `{"_ui": {classe: [{pos: "a:b", categoria, cor}]}}` com cores fixas por classe.

## 4. Workflow `protocolo_pdf.json`

Cabeçalho (`:2-17`): `workflow.start = "T1_IDENTIFICADOR_PARTES"`, `workflow.output = {wrapper_key: "processo", id_key: "id_processo"}`,
`workflow.defaults = {provider: "groq", modelo: "openai/gpt-oss-120b", max_completion_tokens: 10000, temperature: 0.0, stream: true, loop: true, parallel: false}`.
O executor lê apenas `tasks` e `workflow.start` (`core/pipeline_pdf.py:255, 261`) e, por task, `id, nome, missao, modelo,
tipo_saida, contexto_adicional, temperature, max_completion_tokens, transitions[0].target` (`:86-98, 264, 283, 313`).
`defaults`, `output`, `provider`, `fase` e `reasoning_effort` não são lidos. Padrões reais por task: `temperature 0.0`,
`max_completion_tokens 8000` (`:97-98`), `top_p=1`, `stream=True`, `reasoning_format="parsed"` com fallback se o SDK
recusar (`:99-108`). Provedor: só Groq, via `AsyncGroq` criado em `main.py:30` e passado ao pipeline.

| Ordem | id | Fase | Saída | Contexto | O que faz |
|---|---|---|---|---|---|
| 1 | `T1_IDENTIFICADOR_PARTES` (`:22-30`) | 1 | json | `texto_bruto` (texto inteiro em `<data_user>`, `pipeline_pdf.py:145-146`) | partes transcritas ao pé da letra em `identificacao[]` |
| 2 | `T2_IDENTIFICADOR_DATAS_VALORES` (`:33-41`) | 1 | json | `texto_bruto` | datas, prazos e valores como escritos em `datas_valores[]` |
| 3 | `T3_IDENTIFICADOR_FATOS` (`:44-52`) | 1 | json | `texto_bruto` | um item atômico por fato narrado em `fatos[]` |
| 4 | `T4_IDENTIFICADOR_FUNDAMENTOS` (`:55-63`) | 1 | json | `texto_bruto` | um item por lei, artigo, súmula ou precedente em `fundamentos[]` |
| 5 | `T5_IDENTIFICADOR_PEDIDOS` (`:66-74`) | 1 | json | `texto_bruto` | um item por pedido em `pedidos[]` |
| 6 | `T6_FUSAO_MEMORIA` (`:77-85`) | 2 | json | `outputs_anteriores` (`:148-155`) | funde as cinco listas em `memoria_persistente` + `total_fragmentos` |
| 7 | `T7_SINTESE_FATOS` (`:88-96`) | 2 | json | anteriores | narrativa cronológica simples dos fatos com `lastro` |
| 8 | `T8_SINTESE_FUNDAMENTOS` (`:99-107`) | 2 | json | anteriores | fundamentos em palavras simples, referência legal entre parênteses |
| 9 | `T9_SINTESE_PEDIDOS` (`:110-118`) | 2 | json | anteriores | uma frase curta por pedido |
| 10 | `T10_SINTESE_IDENTIFICACAO` (`:121-129`) | 2 | json | anteriores | quem é quem, juízo, número do processo |
| 11 | `T11_SINTESE_CONTEXTO` (`:132-140`) | 2 | json | anteriores | fase processual, decisão anterior, o que se discute |
| 12 | `T12_PROCESSAMENTO` (`:143-151`) | 3 | json | anteriores | mapa `_ui` de posições e cores por classe |
| 13 | `T13_HUMANIZACAO` (`:154-162`) | 4 | texto | anteriores | história em markdown para uma criança de 10 anos (3.6) |
| 14 | `T14_QUESTOES` (`:165-174`, `max_completion_tokens 12000`) | 4 | json | anteriores | perguntas "absurdamente fáceis" de múltipla escolha (3.3) |
| fim | `END_SUCCESS` (`:176-179`), `END_FAILURE` (`:181-184`, nunca alvo) | | | | `type: "end"` |

Execução (`core/pipeline_pdf.py:199-358`): `status="processando"`; extração com pypdf; erro de extração ou de parse do
protocolo -> `falhou`; loop sequencial seguindo `transitions[0].target`; cada task grava `{id}.json`; qualquer task com
erro -> `falhou` e retorno (`:296-298`); ao final consolida `memoria_persistente.json` (T6), `texto_tagueado.json` (T12),
`resumo_humanizado.md` (T13) e `questoes.json` (T14) por id fixo (`:317-334`, renomear uma task no JSON descarta o
artefato em silêncio); `status="pronta"`; registra a aba `chat` na memória de sessão apenas quando `session_token` foi
passado (`:344-356`), o que só `/api/pdf/destilar` faz. Sem retry, sem timeout, sem retomada: se o processo cair no meio,
a tarefa fica `processando` para sempre e `reprocessar` responde 409 (`app_gestao.py:670-671`). O texto do PDF entra como
dado dentro de `<data_user>` e uma instrução fixa pede "Execute a missão agora" (`:57-59, 146`); é a única defesa contra
injeção de prompt.

Job externo (`core/api.py:135-249`, `core/api_caselaw.py:101-216`): `POST /submit` sem autenticação ("API pública,
sem chave", `api.py:22`); polling `GET /status/{job_id}` a cada 1,5 s até `done`/`error` ou 600 s (`api.py:30-31`), erros de
status são engolidos e o loop continua; depois `GET /result/{job_id}` e gravação dos arquivos. Timeouts httpx de 60 s
(submit/result) e 30 s (status/rerun). Os hosts padrão não foram verificados como existentes.

## 5. Valores fixos que viram variável de ambiente

| Arquivo:linha | Valor atual | Variável | Obrigatória | Padrão sugerido | Estado na cópia `repo:` |
|---|---|---|---|---|---|
| `main.py:26-29` | `os.getenv("API_KEY", "gsk_…")` (chave Groq real de 56 caracteres como fallback; também em `__pycache__/main.cpython-312.pyc`) | `GROQ_API_KEY` | sim | nenhum; falhar no boot se vazia | feito: `GROQ_API_KEY` ou `API_KEY`, sem fallback (`repo:main.py:27`) |
| `main.py:63-66` | `admin@local`, `trocar123`, `Administrador`, `fornecedor` (senha logada em `:68`) | `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME` | sim (`ADMIN_PASSWORD`) | sem padrão para a senha | feito (`repo:main.py:67-69`); `papel` continua fixo |
| `main.py:37`, `core/pipeline_pdf.py:39`, `app_gestao.py:949`, `protocolo.json:5`, `protocolo_pdf.json:10` | `openai/gpt-oss-120b` | `GROQ_MODEL` | não | `openai/gpt-oss-120b` | feito só em `repo:main.py:35`; `pipeline_pdf.py:39` e `app_gestao.py:949` continuam literais |
| `main.py:571` | `host="0.0.0.0", port=8000, reload=True` | `PORT` (Railway injeta), `HOST`, `UVICORN_RELOAD` | não | `8000`, `0.0.0.0`, `false` | contornado pelo start command (`repo:railway.toml:7`); o bloco `__main__` continua |
| `core/db.py:9-10` | `Path("gestao.db")` relativo ao CWD | `DB_PATH` (ou `DATA_DIR`) | não | `$DATA_DIR/gestao.db`, com `DATA_DIR=/data` no Railway | feito (`repo:core/db.py:10`) |
| `core/workspace.py:6` | `Path("workspace")` relativo ao CWD | `WORKSPACE_DIR` (ou `DATA_DIR`) | não | `$DATA_DIR/workspace` | feito (`repo:core/workspace.py:7`) |
| `core/session.py:29` | `Path("workspace") / "_sessoes"` (re-hardcoda `workspace`) | derivar de `WORKSPACE_DIR` | não | `$WORKSPACE_DIR/_sessoes` | **pendente**: com `DATA_DIR=/data` os arquivos de sessão ainda caem em `./workspace/_sessoes` |
| `core/pipeline_pdf.py:38` | `Path("protocolo_pdf.json")` relativo ao CWD | `PDF_PROTOCOL_FILE` | não | `<BASE_DIR>/protocolo_pdf.json` | pendente (funciona se o CWD for a raiz do serviço) |
| `main.py:32-34` | `protocolo.json`, `help.md`, `contexto_persistente.json` em `BASE_DIR` (`protocolo.json` é reescrito por `POST /api/protocolo`) | `CHAT_PROTOCOL_FILE`, `HELP_FILE`, `PERSISTENT_CONTEXT_FILE` | não | mover os dois graváveis para `$DATA_DIR` | pendente |
| `app_gestao.py:30` vs `main.py:46` | `Jinja2Templates("templates")` (CWD) e `BASE_DIR/"templates"` | `TEMPLATES_DIR` | não | `<BASE_DIR>/templates` | pendente (só importa se o CWD mudar) |
| `main.py:44` e `app_gestao.py` inteiro | sem `CORSMiddleware` | `CORS_ORIGINS` | sim para o app Next | `http://localhost:3000` | feito (`repo:main.py:44-49`) |
| `app_gestao.py:623` | `link_cliente = request.base_url + /t/{hash}` | `CLIENT_APP_URL` | não | vazio = o próprio serviço | feito (`repo:app_gestao.py:624`) |
| `core/auth.py:45`, `app_gestao.py:86, 95, 192, 310, 442, 504, 524`, `main.py:539` | cookie `sessao`; `httponly=True, samesite="lax"`, sem `secure`, sem `max_age` | `SESSION_COOKIE_SECURE` | não | `true` atrás de HTTPS | pendente |
| `core/attempts.py:49` | `0.83` (`int(total*0.83)`) | `QUIZ_PASS_RATIO` | não | `0.83` (alinhar com a cópia "10 de 12" de `cliente_view.html:248, 310, 497`) | pendente |
| `core/attempts.py:25` | prefixo `PARA.AI\|` do hash | `ATTEMPT_HASH_PREFIX` | não | `LEIA\|` (decisão de produto: ver seção 9) | pendente |
| `app_gestao.py:954-955` | `temperature=0.3`, `max_completion_tokens=1500` (chat da cidadã) | `CITIZEN_CHAT_TEMPERATURE`, `CITIZEN_CHAT_MAX_TOKENS` | não | `0.3`, `1500` | pendente |
| `app_gestao.py:930` | `[:12000]` da memória no system prompt | `CITIZEN_CHAT_MEMORY_CHARS` | não | `12000` | pendente |
| `app_gestao.py:932-942` | system prompt do chat da cidadã inline | `CITIZEN_CHAT_PROMPT_FILE` (versionar em `prompts/`) | não | arquivo em `prompts/workflow/` | pendente |
| `core/pipeline_pdf.py:97-98` | `temperature 0.0`, `max_completion_tokens 8000` | `PIPELINE_TEMPERATURE`, `PIPELINE_MAX_TOKENS` | não | `0.0`, `8000` | pendente |
| `main.py:291`, `:205`, `:249`, `:35-36` | `temperature=1`, `max_completion_tokens=6048`; limites 12000/12 e 15000/20; `DELAY_ENTRE_AGENTES=0.2`; `STOP_PIPELINE:` | `CHAT_TEMPERATURE`, `CHAT_MAX_TOKENS`, `CHAT_CONTEXT_MAX_CHARS`, `CHAT_CONTEXT_MAX_MSGS`, `AGENT_DELAY_SECONDS` | não | os atuais | pendente (bastidores, baixa prioridade) |
| `core/api.py:25-28` | `https://api.resumoestruturado.com.br` | `RESUMO_ESTRUTURADO_API_BASE` | não | já lida do ambiente | ok |
| `core/api_caselaw.py:19-22` | `https://api.jurisprudencia.com.br` | `JURISPRUDENCIA_API_BASE` | não | já lida do ambiente | ok |
| `core/api.py:30-31`, `core/api_caselaw.py:24-25` | `POLL_INTERVAL=1.5`, `POLL_TIMEOUT=600.0` | `EXTERNAL_POLL_INTERVAL`, `EXTERNAL_POLL_TIMEOUT` | não | `1.5`, `600` | pendente |
| `core/api.py:64, 73, 82, 91, 103`; `core/api_caselaw.py:54, 62, 70` | httpx `timeout=60.0` / `30.0` | `EXTERNAL_HTTP_TIMEOUT` | não | `60` | pendente |
| `core/api.py:45-47` | `enable_synthesis=True`, `reasoning_effort="medium"`, `modo_disparo="paralelo"` | `RESUMO_REASONING_EFFORT`, `RESUMO_MODO_DISPARO` | não | os atuais | pendente |
| `core/auth.py:10` | `_ITERS = 200_000` | `PBKDF2_ITERATIONS` | não | `200000` | pendente |
| `main.py:18-22` | `logging.basicConfig(level=INFO)` | `LOG_LEVEL` | não | `INFO` | pendente |
| `core/pdf_sign.py:38, 69, 127-128`; `templates/cliente_view.html:6, 229, 317`; `login.html:58`; `dashboard.html:6, 324`; `tarefa_nova.html:6` | `Para.AI`, `AI Forensics`, "Documento gerado automaticamente" | `BRAND_NAME` (o rodapé do PDF é decisão de conteúdo) | não | `LeIA` | pendente (o `title` do app já é "LeIA · serviço cognitivo" em `repo:main.py:43`) |
| `app_gestao.py:750-754` | "Gere 12 questões COMPLETAMENTE DIFERENTES" | `QUIZ_QUESTION_COUNT` (e corrigir a T14) | não | `12` | pendente |
| `app_gestao.py:842, 880` | `request.client.host` como IP do signatário | n/a: passar `--proxy-headers --forwarded-allow-ips='*'` ao uvicorn | | | pendente no `repo:railway.toml:7` |
| `templates/*.html` | `cdn.tailwindcss.com`, `cdnjs.cloudflare.com/.../marked/12.0.2`, `fonts.googleapis.com` | n/a (a página da cidadã sai do serviço; ver seção 8) | | | |

Lista consolidada de variáveis (nome, obrigatória, padrão, o que substitui):

| Variável | Obrigatória | Padrão | Substitui |
|---|---|---|---|
| `GROQ_API_KEY` | sim | nenhum | `main.py:26-29` (aceitar `API_KEY` como legado) |
| `GROQ_MODEL` | não | `openai/gpt-oss-120b` | `main.py:37`, `core/pipeline_pdf.py:39`, `app_gestao.py:949` |
| `ADMIN_EMAIL` | não | `admin@local` | `main.py:63` |
| `ADMIN_PASSWORD` | sim | nenhum | `main.py:64` |
| `ADMIN_NAME` | não | `Administrador` | `main.py:65` |
| `DATA_DIR` | não | `.` (Railway: `/data`) | raiz de `gestao.db` e `workspace/` |
| `DB_PATH` | não | `$DATA_DIR/gestao.db` | `core/db.py:9-10` |
| `WORKSPACE_DIR` | não | `$DATA_DIR/workspace` | `core/workspace.py:6`, `core/session.py:29` |
| `PORT` | não (Railway injeta) | `8000` | `main.py:571` |
| `CORS_ORIGINS` | sim para o app | `http://localhost:3000` | ausência de `CORSMiddleware` |
| `CLIENT_APP_URL` | não | vazio (usa `request.base_url`) | `app_gestao.py:623` |
| `BASE_URL` | não | `http://localhost:8000` | URL pública no QR do comprovante (`leia/registry.py`, já nosso) |
| `OTS_ENABLED` | não | `true` | carimbo OpenTimestamps (`leia/registry.py`, já nosso) |
| `SESSION_COOKIE_SECURE` | não | `true` em produção | `app_gestao.py:86` |
| `QUIZ_PASS_RATIO` | não | `0.83` | `core/attempts.py:49` |
| `ATTEMPT_HASH_PREFIX` | não | `PARA.AI` | `core/attempts.py:25` |
| `CITIZEN_CHAT_TEMPERATURE`, `CITIZEN_CHAT_MAX_TOKENS`, `CITIZEN_CHAT_MEMORY_CHARS` | não | `0.3`, `1500`, `12000` | `app_gestao.py:954-955, 930` |
| `PIPELINE_TEMPERATURE`, `PIPELINE_MAX_TOKENS` | não | `0.0`, `8000` | `core/pipeline_pdf.py:97-98` |
| `PDF_PROTOCOL_FILE` | não | `<BASE_DIR>/protocolo_pdf.json` | `core/pipeline_pdf.py:38` |
| `RESUMO_ESTRUTURADO_API_BASE`, `JURISPRUDENCIA_API_BASE` | não | os hosts atuais | já lidas |
| `EXTERNAL_POLL_INTERVAL`, `EXTERNAL_POLL_TIMEOUT`, `EXTERNAL_HTTP_TIMEOUT` | não | `1.5`, `600`, `60` | `core/api.py:30-31, 64-103`; `core/api_caselaw.py:24-25, 54-70` |
| `LOG_LEVEL` | não | `INFO` | `main.py:18-22` |
| `BRAND_NAME` | não | `LeIA` | strings `Para.AI` / `AI Forensics` |

## 6. Armazenamento e persistência

| O quê | Caminho (v2) | Onde no código | Volume? |
|---|---|---|---|
| SQLite: usuários e hashes de senha, tokens de sessão, tarefas, eventos, tentativas com IP e user-agent | `./gestao.db` (CWD) | `core/db.py:9-10, 106-109` | **sim** |
| Workspace por tarefa: `original.pdf`, `meta.json`, `log.jsonl`, `texto_extraido.txt`, `T1_...T14_*.json`, `memoria_persistente.json`, `texto_tagueado.json`, `resumo_humanizado.md`, `questoes.json`, `pdf_assinado.pdf`, `resumo_estruturado_job.json`, `resumo_estruturado.json`, `resumo_estruturado_texto.txt`, `jurisprudencia_job.json`, `jurisprudencia_resultado.json`, `jurisprudencia_texto.txt` (e, na cópia, `tentativa_N.ots`) | `./workspace/{hash}/` (CWD; `Tarefa.workspace_path` guarda esse caminho relativo) | `core/workspace.py:6-30`; `app_gestao.py:163, 285, 413, 553, 724, 1011, 1043`; `core/pipeline_pdf.py:241, 304, 318, 322, 331, 334`; `core/api.py:184, 229, 231`; `core/api_caselaw.py:151, 196, 198` | **sim** (sem ele todo `/t/{hash}` morre a cada deploy) |
| Memória de sessão por login | `./workspace/_sessoes/{session_token}.json` | `core/session.py:29-35, 90-99` | não (apagada no logout) |
| Histórico global do chat de bastidores | `<BASE_DIR>/contexto_persistente.json` | `main.py:34, 180-202` | não |
| Protocolo do chat, reescrito em tempo de execução | `<BASE_DIR>/protocolo.json` | `main.py:32, 169-177` | só se a edição por `POST /api/protocolo` tiver que sobreviver ao deploy |
| Workflow do PDF (leitura) | `./protocolo_pdf.json` (CWD) | `core/pipeline_pdf.py:38, 248` | não (parte da imagem) |
| Templates e estáticos | `<BASE_DIR>/templates`, `<BASE_DIR>/static` (main) e `./templates` (gestão) | `main.py:46-48`; `app_gestao.py:30` | não |
| Logs | stdout apenas (`logging.basicConfig`) | `main.py:18-23` | não |
| `__pycache__` cpython-312 na árvore | `./__pycache__`, `./core/__pycache__` (contém a chave Groq em `main.cpython-312.pyc`) | `.gitignore:1-4` | não versionar |

`Tarefa.workspace_path` guarda `str(Path("workspace") / hash)` (`app_gestao.py:171` e equivalentes): se o diretório base
mudar entre deploys, os registros antigos apontam para o caminho velho.

## 7. Deploy no Railway

O que a cópia em `apps/llm-service/` já traz: `Dockerfile` (python:3.12-slim, `WORKDIR /app`, `DATA_DIR=/data`,
`CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`) e `railway.toml` (builder Dockerfile, `startCommand`
`uvicorn main:app --host 0.0.0.0 --port $PORT`, `healthcheckPath = "/login"`, `restartPolicyType = "ON_FAILURE"`).
Para a v2 pura, os pontos são:

- **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips='*'`.
  Nunca `python main.py` (`main.py:571` fixa 8000 e `reload=True`). `--proxy-headers` é o que faz `request.client.host`
  (`app_gestao.py:842, 880`) e `request.base_url` (`:623`) enxergarem o IP real e `https` atrás do proxy do Railway; sem
  isso todo `hash_imutavel` e todo PDF assinado registram o IP interno do proxy.
- **Porta**: só via `$PORT` no comando; o código não lê `PORT`.
- **Workers**: exatamente 1 processo e 1 instância. `BackgroundTasks` rodam no processo web (`app_gestao.py:195, 312, 444,
  583, 694, 755`), SQLite é arquivo, o bootstrap do admin roda no import (`main.py:58-70`) e a memória de sessão é arquivo
  local. Um restart no meio do pipeline deixa a tarefa em `processando` sem recuperação.
- **CWD**: `/app` (raiz do serviço), por causa dos caminhos relativos listados na seção 1.
- **Volume**: montar em `/data` e apontar `DATA_DIR=/data` (cópia) ou, na v2 pura, fazer o CWD ser o volume e copiar
  `templates/`, `static/` e `protocolo_pdf.json` para lá. Sem volume, cada deploy apaga banco, PDFs, tentativas e usuários.
- **Estáticos**: `/static` só monta se `static/` existir ao lado de `main.py` (`main.py:47-48`); `dashboard.html:7` aponta
  para `/static/img/beeroot_ico.png`, que não existe (404 inofensivo). As páginas carregam Tailwind, marked e Google
  Fonts de CDN; o navegador precisa de saída para esses hosts.
- **Primeira execução**: automática. `init_db()` cria tabelas e aplica `ALTER TABLE` idempotentes (`core/db.py:71-109`);
  `criar_usuario_inicial` insere o admin (`main.py:60-68`). Não há rota de cadastro: outros usuários entram direto no
  SQLite com `core.auth.hash_senha`. Trocar a senha antes de expor a URL.
- **Variáveis mínimas**: `GROQ_API_KEY` (na v2, `API_KEY`), `ADMIN_PASSWORD`, `DATA_DIR`, `CORS_ORIGINS` (origem do app
  na Vercel), `CLIENT_APP_URL` (para o painel gerar o link da cidadã apontando ao app), `BASE_URL`. Sem dotenv: definir
  nas variáveis do serviço.
- **Health check**: `GET /login` responde 200 sem cookie (`app_gestao.py:67-73`). As rotas com cookie respondem 303, não 401.
- **CORS**: a v2 não tem `CORSMiddleware` em nenhum arquivo; a cópia adiciona com `CORS_ORIGINS` (`repo:main.py:44-49`).
  Sem isso o app Next em outra origem não consegue chamar `/api/t/{hash}`, `/quiz` nem `/chat` pelo navegador. As rotas
  com cookie `SameSite=Lax` não funcionam cross-site de qualquer forma; o app Next não as usa.
- **SSE**: `/api/t/{hash}/chat` e `/api/chat` são POST com `text/event-stream` e `X-Accel-Buffering: no`
  (`app_gestao.py:972`, `main.py:562`); manter o proxy sem buffer. `EventSource` não serve (é POST): usar `fetch` +
  `ReadableStream`, como `apps/web/lib/api.ts:44-68` já faz.
- **Python**: `__pycache__` é cpython-312 e o código usa `int | str` em anotações (`core/pipeline_pdf.py:203`); 3.11+
  serve, 3.12 testado localmente. Sem pacotes de sistema (pypdf e reportlab são puros).
- **Duração**: 14 chamadas sequenciais à Groq com 8k a 12k tokens por task e o texto inteiro em T1..T5; contar minutos
  por PDF e limites de taxa da Groq. Pré-processar os PDFs de exemplo antes da auditoria.
- **Hosts externos**: `api.resumoestruturado.com.br` e `api.jurisprudencia.com.br` são padrões não verificados; se
  inacessíveis, a tarefa termina `falhou` após o erro de submit (`core/api.py:166-172`). O app Next não depende deles.
- **Escrita no diretório do código**: `POST /api/protocolo` reescreve `protocolo.json` (`main.py:172`) e `/api/chat`
  anexa a `contexto_persistente.json` (`main.py:190`); ambos somem no próximo deploy e exigem filesystem gravável.

## 8. Página da cidadã hoje e o que o app Next precisa

### 8.1 O que a v2 entrega hoje

- Espera: `GET /t/{hash}` devolve `cliente_aguarde.html` (spinner, `tarefa.status`, `<meta refresh 5>`) enquanto o status
  não é `pronta`/`enviada`/`assinada` (`app_gestao.py:825-830`). Não há rota JSON pública de status: `/api/tarefas/{id}/status`
  e `/api/pdf/{hash}/log|destilado` exigem o cookie de quem enviou (`app_gestao.py:204, 228, 797`).
- Página (`cliente_view.html`): cabeçalho com marca e `tarefa.titulo` (`:228-232`); cartão 1 com `resumo_md` renderizado
  por `marked` no navegador (`:235-238, 357-368`); cartão 2 com o quiz, inclusive `data-correta` (`:253`) e
  `justificativa` (`:268`) no HTML; cartão 3 "Assinatura digital" com `hash_imutavel`, data, `numero`, `acertos/total` e
  link para `/t/{hash}/pdf-assinado` quando a última tentativa foi aprovada (`:290-314`); gaveta de chat (`:322-345`).
- Não existe na v2 nenhum JSON público com a tarefa (título, status, resumo, questões, última tentativa). Esses valores
  só entram no HTML em `app_gestao.py:845-857`.

### 8.2 O que o app Next (`apps/web`) consome e de onde sai

O cliente em `apps/web/lib/api.ts` espera:

| Chamada do app | Tipo esperado (`api.ts`) | Fonte na v2 | Fonte na cópia `apps/llm-service` |
|---|---|---|---|
| `GET {API_BASE}/api/t/{hash}` (`api.ts:31-34`) | `Task {tarefa {hash, titulo, status}, resumo_md, topicos \| null, questoes [{id, enunciado, alternativas, area}], ultima_tentativa \| null, eventos?}` | **não existe** | `repo:leia/api_citizen.py:80-93`: monta exatamente esse JSON a partir de `Tarefa`, `resumo_humanizado.md`, `questoes.json` (sem `correta`/`justificativa`, `:27-30`), `memoria_persistente.json` e `tn.listar` (última tentativa); `eventos` = últimos 8 do `log.jsonl` (`:85`); antes de pronta devolve `resumo_md: null, topicos: null, questoes: []` (`:86-87`) |
| `POST /api/t/{hash}/quiz` (`api.ts:36-41`) | `QuizResult = Attempt & {comprovante_token?, erros [{id, area?, enunciado?, escolhida?}]}` | `app_gestao.py:863-908` devolve tudo isso e mais: `ts`, `pode_baixar_pdf` e, em cada erro, `correta`, `justificativa`, `alternativas` (gabarito) | igual |
| `POST /api/t/{hash}/chat` (`api.ts:44-68`) | SSE `{t}` e `{error}`; ignora o resto | `app_gestao.py:958-967` envia `{t}`, `{done: true}`, `{error}` | igual |
| `GET /verify/{hash_imutavel}?format=json` (`api.ts:70-74`) | `{payload, canonical, payloadHash, otsPresent}` | **não existe** | `repo:leia/registry.py:160-167` com adaptador `get_attempt` (`repo:leia/api_citizen.py:100-111`) |
| `topicsOf(task)` (`api.ts:81-89`) | `topicos[]` ou divisão de `resumo_md` por `#`/`##` | só o markdown da T13 | `topics_from_summary` (`repo:leia/api_citizen.py:57-77`): seções `##` da história + o `trecho_verbatim` da memória com mais palavras em comum (>= 3), sem `clausula` |

Para onde apontar: `NEXT_PUBLIC_API_BASE` = URL do serviço no Railway (`apps/web/.env.example`), e `CORS_ORIGINS` no
serviço com a origem da Vercel.

### 8.3 Tópicos com trecho literal: de onde tirar

1. `memoria_persistente.json` (T6): cinco classes de itens `{campo, valor, trecho_verbatim, pos_trecho_verbatim}`; o
   `trecho_verbatim` é o que o app mostra como "trecho original".
2. `T7_SINTESE_FATOS.json` ... `T11_SINTESE_CONTEXTO.json`: um texto simples por classe com `lastro` apontando para os itens
   de (1). É o elo tópico -> trecho que o app precisa; hoje fica só em arquivo, sem rota JSON, e não é consolidado
   (`core/pipeline_pdf.py:304, 317-334`).
3. `resumo_humanizado.md` (T13): seis seções `##` já em linguagem simples, sem nomes de lei nem datas; é o que a cópia usa
   como tópicos, com um casamento heurístico ao trecho (8.2).

Nenhum código (v2 ou cópia) verifica que `trecho_verbatim` é substring de `texto_extraido.txt`. A frase do app "Trecho
conferido: copiado exatamente do seu documento" (`apps/web/components/Journey.tsx:147`) hoje não tem lastro em código;
precisa de uma checagem server-side (substring, ou `pos_trecho_verbatim` contra o texto) antes de ser exibida.

### 8.4 Lacunas para o app Next

- `GET /api/t/{hash}` público: ausente na v2; presente na cópia (`repo:leia/api_citizen.py`). Precisa entrar na v2 do
  Carlos ou a cópia é o que vai ao ar.
- CORS: ausente na v2; presente na cópia.
- Resposta do quiz vaza o gabarito (`erros[].correta`, `justificativa`, `alternativas`) e a página do serviço embute
  `data-correta` no HTML. Para o app Next basta não renderizar, mas o JSON continua público: remover no servidor
  (`core/attempts.py:108-116`).
- Sem status de falha exposto de forma útil: com `falhou`, a cópia devolve `questoes: []` e `topicos: null`
  (`repo:leia/api_citizen.py:86-87`) e o app fica repetindo a espera a cada 8 s (`Journey.tsx:63`).
- `eventos[]` da espera trazem `id` (`T1_...` a `T14_...`), `idx` e `total`; o app lê `step` (`Journey.tsx:80`), que não existe.
- `ultima_tentativa` é a última por `numero` (`repo:leia/api_citizen.py:93`, como em `app_gestao.py:837`), enquanto o PDF
  assinado usa a melhor. O app só olha `aprovado` (`Journey.tsx:42`), então funciona, mas os dois cartões podem divergir.
- Chat sem citação: a resposta é texto livre, a recusa ("não foi informado") depende só do prompt (`app_gestao.py:932-942`)
  e nada é gravado. ADR-0004 (citação literal e recusa explícita) não é atendido pelo serviço; o app não tem como
  mostrar `sourceQuote` na resposta.
- Quantidade de questões indefinida (3, 6 ou 12, seção 3.3): o app já lê `total` da resposta, o que basta.
- `titulo` da tarefa criada por `/api/pdf/destilar` é o nome do arquivo (`app_gestao.py:167`); o app o exibe em
  "Vou explicar o documento "{titulo}"" (`Journey.tsx:104`).
- Títulos das seções da T13 começam com emoji (`## 👥 ...`); viram `titulo` dos tópicos e são lidos em voz alta pelo
  `SpeakButton` (`Journey.tsx:137`).
- Sem rubrica, sem pergunta aberta, sem laço de reexplicação: "assinatura" = primeira tentativa de múltipla escolha que
  atinge o limiar (`app_gestao.py:891-897`). O app trata a reprovação com "Ler a explicação de novo" (`Journey.tsx:223`),
  que é o que dá para fazer com o que existe.

## 9. Privacidade e LGPD

| Dado | Onde é coletado | Onde fica | Quem vê |
|---|---|---|---|
| IP e user-agent da cidadã | ao abrir a página (`app_gestao.py:841-843`) e a cada tentativa (`:880-883`, `core/attempts.py:53-54, 66-68`) | `log.jsonl` (`ua[:200]`), tabela `tentativa` (`ua[:300]`), preimage do `hash_imutavel` (`attempts.py:25`) e **em claro na página de assinatura do PDF** (`core/pdf_sign.py:105-106`) | quem baixa o PDF: a cidadã (`/t/{hash}/pdf-assinado`, público) e quem enviou (`/tarefas/{id}/pdf-assinado`) |
| PDF original e texto extraído | upload (`app_gestao.py:163, 285, 413, 553`), extração (`core/pipeline_pdf.py:241`) | `workspace/{hash}/original.pdf`, `texto_extraido.txt`, copiados a cada nova rodada (`:724`); embutidos no PDF assinado | quem tem o link; `index.html:1892` diz "o PDF em si não é guardado", o que não bate com o código |
| Nomes das partes, datas, valores, fatos | T1..T5 transcrevem ao pé da letra (`protocolo_pdf.json:22-74`) | `T1_...T6_*.json`, `memoria_persistente.json`, a história da T13 (usa nomes próprios, `:161`), o system prompt do chat (`app_gestao.py:928-942`), a memória de sessão (`core/session.py:62-87`) | texto inteiro vai à Groq (`core/pipeline_pdf.py:145-146`); nos fluxos externos, o PDF inteiro vai sem autenticação a terceiros (`core/api.py:59-65`, `core/api_caselaw.py:49-55`) |
| Identidade de quem enviou (id, e-mail, nome) | `meta.json` (`app_gestao.py:179, 301, 432, 569`) | `workspace/{hash}/meta.json`, baixável por `/tarefas/{id}/artefato/meta.json` | usuários logados |
| Perguntas de quem está logado ao chat de bastidores | `main.py:365-370, 447-454` | `contexto_persistente.json`, um arquivo para todos | qualquer usuário logado via `GET /api/contexto` (`main.py:503-505`) |
| Tokens de sessão | `core/auth.py:34` | em claro no banco e como nome de arquivo em `workspace/_sessoes` (`core/session.py:33-35`); cookie sem `Secure` e sem validade (`app_gestao.py:86`) | |
| Chave Groq e senha do admin | `main.py:28`, `main.py:63-68` | no fonte, no `.pyc` e no log | quem lê o repositório |

Pontos de decisão para o produto:

- O `hash_imutavel` inclui IP e user-agent sem salt (`core/attempts.py:25`): quem tiver o PDF recalcula o hash, e o
  hash "prova" dados pessoais. Diverge de SPEC-001 (hash salgado sem nada pessoal). A cópia contorna gerando um payload
  canônico próprio (`repo:leia/registry.py:48-72`) com `salt = hash_imutavel[:40]` (`repo:leia/api_citizen.py:110`), mas
  o `hash_imutavel` original continua sendo gravado e impresso.
- O link `/t/{hash}` e suas APIs (quiz, chat, PDF) não expiram e não têm autenticação: quem tem o hash pode enviar
  tentativas que mudam o status para `assinada`, conversar sobre o documento e baixar o PDF com IP e navegador da
  pessoa que respondeu.
- O gabarito viaja ao navegador (`cliente_view.html:253, 268`) e na resposta do quiz (`core/attempts.py:108-116`).
- O chat público é um endpoint de LLM sem limite e sem autenticação (`app_gestao.py:914-973`), com custo e superfície
  de injeção (o resumo e a memória derivados do PDF entram no system prompt).
- O PDF assinado sai do pypdf/reportlab com metadados padrão (`core/pdf_sign.py:140-168` nunca toca `writer.metadata`)
  e com o rodapé "Documento gerado automaticamente" (`:127`): contraria a regra da pasta de trabalho sobre metadados e
  marcadores de geração automática.
- Transcrições do chat da cidadã não são guardadas (`app_gestao.py:946-967`): não há registro do que ela perguntou nem
  do que foi respondido, além da linha da tentativa.

O que não deve ir ao repositório público (`repos/leia`): `main.py` com a chave (`main.py:28`), qualquer `__pycache__`
(a chave está em `main.cpython-312.pyc`), `gestao.db`, `workspace/` (contém PDFs reais; o exemplo do Carlos tem um
processo real com nomes), `.env`, `_legacy/`, `protocolo.json.bak_historia_infantil` (não referenciado). O `.gitignore`
da v2 já cobre `.env`, `*.db`, `workspace/`, `_legacy/` e `__pycache__/` (`.gitignore:1-8`), mas não protege a chave que
está no fonte: rotacionar a chave na Groq antes do primeiro push.

## 10. Perguntas em aberto para o Carlos

1. A v2 é a mesma base que já está em `apps/llm-service/` (só nossos 4 arquivos diferem). Podemos publicar a cópia com
   `GET /api/t/{hash}`, CORS e variáveis de ambiente, ou você prefere aplicar essas mudanças na sua árvore e reenviar?
2. Quantas questões a T14 deve gerar de fato (3, 6 ou 12)? O prompt diz as três coisas (`protocolo_pdf.json:167-173`), a
   nova rodada pede 12 (`app_gestao.py:752`) e a página diz "10 de 12" (`cliente_view.html:248`). Com 12 o limiar
   `int(12*0.83)` aprova com 9, não 10 (`core/attempts.py:49`).
3. Podemos tirar `correta`, `justificativa` e `alternativas` de `erros[]` na resposta do quiz (`core/attempts.py:108-116`)
   e `data-correta` do HTML? O app não precisa deles e o JSON é público.
4. Podemos expor as sínteses T7..T11 (com `lastro`) e a `memoria_persistente` em uma rota JSON pública sem dados de quem
   enviou, ou consolidá-las em um `topicos.json` no fim do pipeline (`core/pipeline_pdf.py:313-334`)? É o que dá ao app o
   "trecho original" por tópico com lastro real, no lugar do casamento por palavras da cópia.
5. Aceita adicionar no pipeline uma conferência de que cada `trecho_verbatim` existe em `texto_extraido.txt` (substring
   ou `pos_trecho_verbatim`), marcando os que falham? Hoje nada confere (`core/`), e o app promete "copiado exatamente".
6. `hash_imutavel` com IP, user-agent e timestamp sem salt (`core/attempts.py:21-26`), e IP e navegador impressos no
   PDF (`core/pdf_sign.py:105-106`): podemos trocar pelo payload canônico salgado de SPEC-001 e tirar IP/UA do PDF? E
   manter `ip`/`user_agent` só no banco, ou nem isso?
7. `request.client.host` (`app_gestao.py:842, 880`) atrás do proxy do Railway vira o IP interno a menos que o uvicorn suba
   com `--proxy-headers --forwarded-allow-ips='*'`. Você concorda com esse start command?
8. As tarefas de `/tarefas/nova`, `reprocessar` e `nova-rodada` não passam `session_token` ao pipeline
   (`app_gestao.py:583, 694, 755`), então não atualizam a aba `chat` da memória de sessão; é intencional?
9. Os hosts `api.resumoestruturado.com.br` e `api.jurisprudencia.com.br` existem e respondem hoje? Se não, tiramos as
   abas do painel para a auditoria ou deixamos com aviso?
10. `protocolo_jurisprudencia.json`, `_legacy/`, `protocolo.json.bak_historia_infantil` e `core/pd_extract.py` (0 bytes, removido)
    não são usados por nada; podemos deixar fora do repositório público?
11. `POST /api/protocolo` reescreve `protocolo.json` no diretório do código (`main.py:172`) e `GET /api/contexto` mostra o
    histórico de todos os usuários (`main.py:180-185, 503-505`): manter assim para a demo ou desligar as duas rotas?
12. Chat da cidadã: aceita que a resposta traga o `trecho_verbatim` usado (ou um `{"cita": ...}` no SSE) e uma recusa
    explícita quando a resposta não está na memória, e que a conversa seja gravada em `log.jsonl` para virar transcrição?
13. Status: confirma que os valores finais são `pronta` e `assinada`, que `enviada` não é gravado por nada
    (`app_gestao.py:825`) e que `falhou` deve aparecer para a cidadã como "não deu certo, fale com quem enviou"?
14. Onde ficam os prompts do workflow para apontarmos em `prompts/workflow/` (hoje só `protocolo_pdf.json:19-185` e o
    system prompt inline em `app_gestao.py:932-942`)?
