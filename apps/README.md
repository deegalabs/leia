# apps

| Pasta | O quê | Stack | Dono |
|---|---|---|---|
| `web/` | interface do advogado e do cliente | Next.js (App Router) + Tailwind; consome o serviço de LLM por HTTP | Daniel |
| `llm-service/` | serviço cognitivo: parse do PDF, explicação com citações, perguntas, avaliação, registro do consentimento | FastAPI (Python) | Carlos |

Contrato entre os dois: [../docs/LLM-API-CONTRACT.md](../docs/LLM-API-CONTRACT.md). Código só a partir de 12/09/2026 (edital, item 5.5).
