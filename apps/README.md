# apps

| Pasta | O quê | Stack | Dono |
|---|---|---|---|
| `llm-service/` | serviço cognitivo (workflow, rotas, painel) e, dentro dele, a interface da cidadã, o comprovante e a verificação | FastAPI + Jinja2 + JavaScript simples; add-ons em `llm-service/leia/`, `templates/leia/`, `static/` | Carlos (serviço), Daniel (interface e registro) |
| `web/` | interface responsiva separada, PWA, login e conferência (pós-hackathon) | Next.js (App Router) + Tailwind; consome o serviço por HTTP | Daniel |

Contrato entre as partes: [../docs/LLM-API-CONTRACT.md](../docs/LLM-API-CONTRACT.md). Como rodar sem o serviço: [llm-service/README.md](llm-service/README.md).
