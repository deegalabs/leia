# apps/web

Interface do LeIA: web app responsivo (celular e desktop) que consome só a API do serviço cognitivo.
Next.js 16 (App Router), Tailwind 4, Lucide, `qrcode`. Textos em `messages/pt-BR.json` e nos componentes.

## Rotas
| Rota | Tela |
|---|---|
| `/` | landing |
| `/t/{hash}` | jornada da cidadã: boas-vindas, um ponto por vez com trecho original, dúvida, perguntas, resultado |
| `/comprovante/{hash_imutavel}` | comprovante com QR e código do registro |
| `/verify/{hash_imutavel}` | verificação pública: JSON canônico, hash, prova OpenTimestamps |

## Rodar
```bash
cp .env.example .env.local        # NEXT_PUBLIC_API_BASE aponta para o serviço (mock: http://localhost:8000)
pnpm install
pnpm dev                          # http://localhost:3000
pnpm build && pnpm start          # produção
```
Serviço mock: `cd ../llm-service && uvicorn mock.app:app --port 8000` (CORS liberado para localhost:3000 por padrão;
`CORS_ORIGINS` para outras origens). Contrato: [../../docs/LLM-API-CONTRACT.md](../../docs/LLM-API-CONTRACT.md).
