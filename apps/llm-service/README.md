# apps/llm-service

Serviço cognitivo do LeIA (FastAPI + SQLModel + Groq), escrito pelo Carlos, com os acréscimos de integração do app.

```
main.py, app_gestao.py, core/      serviço: login, painel, tarefas, workflow (protocolo_pdf.json), página da cidadã, quiz, chat
leia/api_cliente.py                GET /api/t/{hash} em JSON sem gabarito (tópicos com trecho literal), adaptador do registro,
                                   carimbo OpenTimestamps da tentativa aprovada (arquivo tentativa_N.ots no workspace)
leia/registry.py                   JSON canônico + SHA-256, comprovante com QR (/t/{hash_imutavel}/comprovante),
                                   verificação pública (/verify/{hash_imutavel}, ?format=json, proof.ots)
templates/leia/                    comprovante e verificação (servidos por este serviço); cliente.html é reserva
mock/app.py                        mock das rotas com examples/fixture-honorarios.json (sem chave de modelo)
Dockerfile, railway.toml, .env.example
```

## Variáveis de ambiente
Ver [.env.example](.env.example). Obrigatórias em produção: `GROQ_API_KEY`, `ADMIN_PASSWORD`, `DATA_DIR` (com volume),
`CORS_ORIGINS`, `CLIENT_APP_URL`, `BASE_URL`.

## Rodar
```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env && set -a && . ./.env && set +a
uvicorn main:app --port 8000          # http://localhost:8000/login (ADMIN_EMAIL / ADMIN_PASSWORD)
python -m pytest -q tests_leia.py     # testes do mock e dos add-ons
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
`GET /api/t/{hash}`, `POST /api/t/{hash}/quiz`, `POST /api/t/{hash}/chat` (SSE), `GET /verify/{hash_imutavel}?format=json`,
`GET /verify/{hash_imutavel}/proof.ots`. Contrato completo: [../../docs/LLM-API-CONTRACT.md](../../docs/LLM-API-CONTRACT.md).
