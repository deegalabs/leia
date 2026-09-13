# apps/llm-service

Serviço cognitivo do LeIA (FastAPI + SQLModel + Groq), escrito pelo Carlos, com os acréscimos de integração do app.

```
main.py, app_gestao.py, core/      serviço: login, painel, tarefas, workflow (protocolo_pdf.json), página da cidadã, quiz, chat
leia/api_cliente.py                GET /api/t/{hash} em JSON sem gabarito (tópicos com trecho literal), adaptador do registro,
                                   carimbo OpenTimestamps da tentativa aprovada (arquivo tentativa_N.ots no workspace)
leia/registry.py                   JSON canônico + SHA-256, comprovante com QR (/t/{hash_imutavel}/comprovante),
                                   verificação pública (/verify/{hash_imutavel}, ?format=json, proof.ots)
leia/api_auth.py                   contas do app (Bearer): /api/auth/cadastro, login, me, logout
leia/api_tarefas.py                documentos de quem está logado: GET/POST /api/tarefas, GET /api/tarefas/{id},
                                   POST /api/tarefas/{id}/duvidas/{duvida_id}/responder
leia/pipeline.py                   semáforo (PIPELINE_CONCURRENCY) em volta do workflow; falha fica só na tarefa dela
leia/ratelimit.py                  limite por IP em memória (RATE_LIMIT_PER_MINUTE) nas rotas públicas de escrita
templates/leia/                    comprovante e verificação (servidos por este serviço); cliente.html é reserva
mock/app.py                        mock das rotas com examples/fixture-honorarios.json (sem chave de modelo)
Dockerfile, railway.toml, .env.example
```

## Variáveis de ambiente
Ver [.env.example](.env.example). Obrigatórias em produção: `GROQ_API_KEY`, `ADMIN_PASSWORD`, `DATA_DIR` (com volume),
`CORS_ORIGINS`, `CLIENT_APP_URL`, `BASE_URL`.

Novas na v3:
- `DATABASE_URL`: Postgres (`postgresql://...`, normalizado para `postgresql+psycopg://`). Vazio = SQLite em `DB_PATH`.
  As tabelas saem de `SQLModel.metadata.create_all`; as migrações `ALTER TABLE` só rodam no SQLite. O `workspace/`
  (PDFs e artefatos) continua em disco mesmo com Postgres: mantenha o volume.
- `ADVOGADO_SIGNUP` (padrão `true`): `false` fecha o cadastro de advogados; cidadã sempre pode se cadastrar.
- `PIPELINE_CONCURRENCY` (padrão 3): quantos workflows rodam ao mesmo tempo. Cada tarefa tem pasta e linha próprias;
  uma falha marca só aquela tarefa como `falhou`.
- `RATE_LIMIT_PER_MINUTE` (padrão 30): limite por IP (primeiro endereço de `X-Forwarded-For`) em `/api/t/{hash}/quiz`,
  `/chat`, `/duvida`, `/api/auth/cadastro` e `/api/auth/login`; excesso responde 429.

## Rodar
```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env && set -a && . ./.env && set +a
uvicorn main:app --port 8000          # http://localhost:8000/login (ADMIN_EMAIL / ADMIN_PASSWORD)
python -m pytest -q tests_leia.py tests_v3.py   # mock e add-ons; contas, documentos, dúvidas, vínculo, limite por IP
```

## Railway
Projeto `leia`, serviço `llm-service`, volume em `/data`, domínio `https://llm-service-production-4278.up.railway.app`.
```bash
railway link                          # projeto leia, serviço llm-service
railway up --service llm-service --detach
railway variable list --service llm-service
```
O build usa o `Dockerfile` (Python 3.12). Health check em `/login`.

## Rotas que o app consome
Públicas (o hash é o segredo): `GET /api/t/{hash}` (agora com `advogado`, `tem_advogado`, `cidadao_vinculado`,
`duvidas_enviadas`), `POST /api/t/{hash}/quiz`, `POST /api/t/{hash}/chat` (SSE), `POST /api/t/{hash}/duvida`,
`GET /verify/{hash_imutavel}?format=json`, `GET /verify/{hash_imutavel}/proof.ots`.

Com `Authorization: Bearer <token>` (o token vem de `/api/auth/cadastro` ou `/api/auth/login`; um por usuário, login novo
invalida o anterior): `GET /api/auth/me`, `POST /api/auth/logout`, `GET /api/tarefas`, `POST /api/tarefas` (multipart
`titulo` + `pdf`), `GET /api/tarefas/{id}`, `POST /api/tarefas/{id}/duvidas/{duvida_id}/responder`,
`POST /api/t/{hash}/vincular` (papel `cidadao`). Sem credencial as rotas `/api/*` respondem 401; as páginas do painel
continuam redirecionando para `/login` e também aceitam o Bearer.

Contratos: [../../docs/LLM-API-CONTRACT.md](../../docs/LLM-API-CONTRACT.md) e
[../../docs/API-V3-CONTRACT.md](../../docs/API-V3-CONTRACT.md).
