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
pnpm install
pnpm dev                          # http://localhost:3000, com o mock interno (app/api/*)
pnpm build && pnpm start          # produção
```
Para apontar ao serviço cognitivo (ou ao mock Python com carimbo OpenTimestamps), crie `.env.local` com
`NEXT_PUBLIC_API_BASE=http://localhost:8000` e suba `cd ../llm-service && uvicorn mock.app:app --port 8000`
(CORS liberado para localhost:3000; `CORS_ORIGINS` para outras origens). Contrato:
[../../docs/LLM-API-CONTRACT.md](../../docs/LLM-API-CONTRACT.md).

## Mock interno (hospedagem sem serviço)
`app/api/t/[hash]`, `.../quiz`, `.../chat` (SSE) e `app/api/verify/[attempt]` reproduzem as rotas do serviço com
`data/fixture-honorarios.json` (cópia de `examples/`). Sem banco: o comprovante viaja como token na URL e o hash é
recalculado (`lib/registry.ts`, mesmos campos e canonicalização do `leia/registry.py`). Sem carimbo OpenTimestamps
nessa versão; o mock Python faz o carimbo de verdade.

## Publicar na Vercel
```bash
vercel link --yes --project leia --scope danielgorgonhas-projects
vercel deploy --prod --yes --scope danielgorgonhas-projects
```
Produção: https://leia-snowy.vercel.app (protection de deploy só nos previews). Variáveis de produção: `NEXT_PUBLIC_API_BASE`
(URL do serviço no Railway) e `NEXT_PUBLIC_DEMO_HASH` (hash da tarefa de exemplo usada em "Ver um exemplo").
