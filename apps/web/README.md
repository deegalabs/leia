# apps/web

Interface do LeIA: web app responsivo (celular e desktop) que consome só a API do serviço cognitivo.
Next.js 16 (App Router), Tailwind 4, Lucide, `qrcode`. Textos em `messages/pt-BR.json` e nos componentes.

## Rotas
| Rota | Tela |
|---|---|
| `/` | landing |
| `/t/{hash}` | jornada da cidadã: boas-vindas, um ponto por vez com trecho original, dúvida (com envio ao advogado quando há um), perguntas, resultado |
| `/comprovante/{hash_imutavel}` | comprovante com QR e código do registro |
| `/verify/{hash_imutavel}` | verificação pública: JSON canônico, hash, prova OpenTimestamps |
| `/entrar` | entrar ou criar conta (cidadã ou advogado); sessão em `localStorage` (`leia:auth`) |
| `/painel` | advogado: documentos, status, link da cliente, respostas e dúvidas abertas; cidadã: "Meus documentos" |
| `/painel/{id}` | detalhe: link da cliente, etapas, respostas, dúvidas com campo de resposta (advogado) |
| `/enviar` | enviar um PDF; advogado recebe o link da cliente, cidadã vai direto para `/t/{hash}` |

Contas, painéis e dúvidas seguem [../../docs/API-V3-CONTRACT.md](../../docs/API-V3-CONTRACT.md) (`lib/auth.ts`, `lib/api.ts`).

## Rodar
```bash
pnpm install
pnpm dev                          # http://localhost:3000, com o mock interno (app/api/*)
pnpm build && pnpm start          # produção
```
Para apontar ao serviço cognitivo (ou ao mock Python com carimbo OpenTimestamps), crie `.env.local` com
`SERVICE_URL=http://localhost:8000` e suba `cd ../llm-service && uvicorn mock.app:app --port 8000`
(CORS liberado para localhost:3000; `CORS_ORIGINS` para outras origens). Contrato:
[../../docs/LLM-API-CONTRACT.md](../../docs/LLM-API-CONTRACT.md).

## Mock interno (hospedagem sem serviço)
`app/api/t/[hash]`, `.../quiz`, `.../chat` (SSE) e `app/api/verify/[attempt]` reproduzem as rotas do serviço com
`data/fixture-honorarios.json` (cópia de `examples/`). Sem banco: o comprovante viaja como token na URL e o hash é
recalculado (`lib/registry.ts`, mesmos campos e canonicalização do `leia/registry.py`). Sem carimbo OpenTimestamps
nessa versão; o mock Python faz o carimbo de verdade.

As rotas v3 (`app/api/auth/*`, `app/api/tarefas*`, `.../duvida`, `.../vincular`) guardam contas, documentos, respostas e
dúvidas em memória do processo (`lib/mock.ts`): tudo some ao reiniciar e instâncias serverless não compartilham o estado.
Qualquer cadastro funciona. Um documento enviado reaproveita o conteúdo do exemplo e fica "pronto" 8 segundos depois.
Contas de demonstração (senha `leia1234`): `advogada@exemplo.leia` (advogado, dona do documento `demo`) e
`cidada@exemplo.leia` (cidadã).

## Publicar na Vercel
```bash
pnpm dlx vercel@latest link --yes --project leia --scope danielgorgonhas-projects
pnpm dlx vercel@latest deploy --prod --yes --scope danielgorgonhas-projects --build-env GIT_COMMIT_SHA=$(git rev-parse HEAD)
```
Use sempre a CLI atual via `pnpm dlx vercel@latest`: a versão 54 instalada globalmente falha com "experimentalServices".
`GIT_COMMIT_SHA` alimenta o selo de versão da landing e o nome do cache do service worker (sem ele a build usa
`VERCEL_GIT_COMMIT_SHA`, que só existe em deploys a partir do GitHub).
Produção: https://leia-snowy.vercel.app (protection de deploy só nos previews). Variáveis de produção: `SERVICE_URL`
(URL do serviço no Railway) e `NEXT_PUBLIC_DEMO_HASH` (hash da tarefa de exemplo usada em "Ver um exemplo").
