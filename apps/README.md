# apps

| Pasta | O quê | Stack | Dono |
|---|---|---|---|
| `web/` | interface do produto: landing, jornada da cidadã, comprovante, verificação pública; responsiva (celular e desktop) | Next.js 16 (App Router) + Tailwind 4 + Lucide; consome só a API do serviço (`NEXT_PUBLIC_API_BASE`) | Daniel |
| `llm-service/` | serviço cognitivo (workflow, rotas, painel interno) e os add-ons de registro (`leia/registry.py`), mock com CORS e a página HTML de reserva | FastAPI + Jinja2 | Carlos (serviço), Daniel (add-ons) |

Contrato entre as partes: [../docs/LLM-API-CONTRACT.md](../docs/LLM-API-CONTRACT.md). Rodar: [web/README.md](web/README.md) e [llm-service/README.md](llm-service/README.md).
