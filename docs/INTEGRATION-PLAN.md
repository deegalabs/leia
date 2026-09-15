# Stack e plano de desenvolvimento: integração com o serviço do Carlos (13/09, dia 2)

Decisão (ADR-0009 na pasta de trabalho, substitui o ADR-0008): **a interface do produto é o app Next.js em `apps/web`,
separado, responsivo (celular e desktop), consumindo só a API do serviço** (`NEXT_PUBLIC_API_BASE`). Os templates do
Carlos são as telas internas do serviço (painel, detalhe, bastidores, login) e recebem apenas tema e textos. A página
HTML em `apps/llm-service/templates/leia/cliente.html` fica como reserva para a Entrega 4 se a API JSON ou o CORS não
estiverem no serviço real a tempo. Na auditoria rodam dois processos: serviço (`uvicorn`) e app (`pnpm dev`).

## Stack (o que roda hoje)
| Camada | Tecnologia | Dono | Estado |
|---|---|---|---|
| Serviço | Python 3.12, FastAPI, Jinja2, `uvicorn`; templates internos: início, anexar PDF, painel, detalhe, espera, bastidores, login | Carlos | rodando |
| Interface do produto | Next.js 16 (App Router), Tailwind 4, Lucide, `qrcode`; rotas `/`, `/t/{hash}`, `/comprovante/{hash_imutavel}`, `/verify/{hash_imutavel}`; consome só a API | Daniel | rodando contra o mock |
| Motor cognitivo | Groq `openai/gpt-oss-120b`, workflow de 16 tarefas (etiquetar → memória → sintetizar com lastro → resumo → perguntas), temperatura 0, semente fixa; prompts em `prompts/workflow/` | Carlos | rodando |
| Dados | banco do serviço (tarefas, tentativas com hash SHA-256, eventos com tempo por etapa) | Carlos | rodando |
| Marca e acessibilidade | `docs/brand/leia-theme.css` (remapeia as variáveis dos templates), `leia-icons.svg`, logos SVG, `copy-replacements.md`; Tailwind CDN já usado pelos templates | Daniel | pronto para aplicar |
| Segurança do conteúdo | `DOMPurify` (cdnjs) no `marked` da página do cliente; gabarito das perguntas fora do HTML (avaliação no servidor) | Carlos + Daniel | a fazer |
| Registro público | OpenTimestamps (`opentimestamps-client`, sem carteira) sobre o `hash_imutavel` de cada tentativa aprovada; Polygon Amoy com `web3.py` + `ConsentRegistry` só se a carteira estiver financiada | Daniel | a fazer |
| Comprovante e verificação | rota `/t/{hash}/comprovante` (hash, data, QR com `qrcode`, o que prova) e `/verify/{hash}` (JSON canônico, hash, prova OTS ou transação); PDF sem metadados (pypdf) | Daniel | a fazer |
| Entrega ao auditor | `README.md` (rodar em 5 min), `.env.example`, `examples/contrato-honorarios.pdf`, roteiro de auditoria de 10 min, `docker compose up` se der tempo (senão `uvicorn`) | Daniel + Dayane | a fazer |
| Depois do evento | Next.js responsivo (`apps/web`) consumindo a API; login e conferência da OAB; PWA; lote Merkle no registro | | roadmap |

## Como o código entra no repositório
```
apps/llm-service/          código do Carlos (FastAPI, templates, workflow, banco); copiar sem .env, .venv, __pycache__
apps/llm-service/static/   leia-theme.css, leia-icons.svg, logo-mark.svg (copiados de docs/brand/)
prompts/workflow/          workflow JSON versionado (v0 já está; v1 com as mudanças de hoje)
examples/                  PDFs anonimizados de teste
scripts/                   verify-cli.py (recalcula o hash e confere a prova), tag-delivery.sh
```
Contrato entre as partes continua em `docs/LLM-API-CONTRACT.md`; o que existe hoje são as rotas do serviço
(`/tarefas/*`, `/t/{hash}`, `/api/t/{hash}/quiz`, `/api/t/{hash}/chat`). Não criar API paralela hoje.

## Andamento em 13/09 pela manhã: interface primeiro, serviço depois
O código do serviço ainda não chegou às 9h, então a interface foi construída contra o contrato observado nos templates
(`docs/LLM-API-CONTRACT.md`) e testada com um mock que responde às mesmas rotas com um contrato de exemplo
(`apps/llm-service/mock/`, `examples/fixture-honorarios.json`). Quando o serviço chegar, a página da cidadã
(`templates/leia/cliente.html`) entra no lugar da atual usando o mesmo contexto, e o comprovante entra com uma linha
(`include_router`). Se o serviço subir em outra origem, `window.LEIA_API_BASE` aponta para ela (com CORS liberado lá).

## Estado às 11h30: demo hospedada e código do serviço recebido
- App publicado em **https://leia-snowy.vercel.app** com o mock interno (rotas em `apps/web/app/api/*`, mesmas
  formas do serviço). Integrar a API real = definir `NEXT_PUBLIC_API_BASE` no projeto da Vercel e CORS no serviço.
- Código do Carlos chegou em `temp/src/oab/` (FastAPI + SQLModel + Groq; rotas em `app_gestao.py`; workflow em
  `protocolo_pdf.json`). Rotas e formas reais documentadas em `docs/LLM-API-CONTRACT.md`. Entra em
  `apps/llm-service/` na integração (sem `workspace/`, `*.db`, `.env`: o exemplo dele contém um processo real com nomes).

## Estado às 12h50: API real integrada e no ar
- Serviço v2 em `apps/llm-service/` (sem chave no código; tudo por variável de ambiente; `Dockerfile`, `railway.toml`,
  `.env.example`). No ar em **https://llm-service-production-4278.up.railway.app** (Railway, volume em `/data`).
- App em **https://leia-snowy.vercel.app** apontando para o serviço (`NEXT_PUBLIC_API_BASE`); "Ver um exemplo" abre uma
  tarefa real processada pelo workflow a partir de `examples/contrato-honorarios-exemplo.pdf`.
- Jornada completa verificada no site hospedado com uma segunda tarefa real: quiz aprovado, comprovante, prova .ots.
  Capturas em `evidence/04-product/screens-servico-real/`.
- Repositório: https://github.com/deegalabs/leia (privado até a equipe decidir publicar).
- Mapa do serviço v2 lido arquivo por arquivo, com verificação independente: `docs/SERVICE-V2-MAP.md` (todos os valores
  fixos viraram variáveis de ambiente; lista em `apps/llm-service/.env.example`).

## Plano até a Entrega 4 (10h30) e durante a auditoria
| Hora | Atividade | Quem |
|---|---|---|
| 08h30–09h00 | Código do Carlos em `apps/llm-service`; rodar local; conferir as rotas; copiar o kit para `static/`; linkar `leia-theme.css` em cada template e `body.leia-citizen` na página do cliente | Daniel + Carlos |
| 09h00–09h45 | Página da cidadã: **feita** (`templates/leia/cliente.html`, testada no mock); Carlos aponta a rota `/t/{hash}` para ela quando o código chegar. Textos dos templates internos pela tabela (`apply_copy.py`); IP fora do painel | Daniel (página) + Carlos (rota) |
| 09h45–10h15 | Comprovante e verificação: **feitos** (`leia/registry.py`, OTS testado, `scripts/verify_cli.py`); Carlos inclui o router e grava `ots` e `salt` na tentativa aprovada. Daniel testa a jornada no celular contra o mock e ajusta textos | Daniel + Carlos |
| 09h00–10h15 (paralelo) | `examples/contrato-honorarios.pdf` anonimizado; textos em pt-BR revisados; roteiro de auditoria jurídica (o que dizer sobre "não aconselha", CED art. 9º e 48, LGPD); teste com 2 leigos na tela nova | Camila, Caliane |
| 10h15–10h30 | README (instalar, rodar, testar em 5 min), `.env.example`, `MANIFEST.md`, push na pasta oficial, `scripts/tag-delivery.sh token-economy/v0.4.0 "Entrega 4: Produto"` | Dayane + Daniel |
| 10h30–14h30 | Auditoria com roteiro de 10 min (D1: trecho literal e recusa; D2: cliente no celular sem instrução; D3: workflow, prompts, memória persistente nos bastidores). Em paralelo, **sem tocar no que o auditor testa**: tópico por tela na página do cliente usando as seções `##` do resumo (se o Carlos expuser o lastro) | todos |
| 13h00–14h15 | Slides (4) e vídeo da demo de 40 s | Dayane, Caliane |
| 14h30 | Entrega 5: slides na pasta oficial | Dayane |
| 16h30 | Pitch de 2 min | Caliane + Daniel |

## O que não entra hoje (dizer no pitch como próximo passo)
Perguntas abertas com rubrica no lugar da múltipla escolha (exige T15/T16 no workflow), voz, tópico por tela com
trecho original ao toque se o lastro não estiver exposto, login, app Next.js, lote Merkle.

## Riscos de hoje
Groq fora do ar ou cota (ter o segundo provedor no `.env`); OTS sem rede (o comprovante sai com "carimbo pendente");
tempo de pipeline de 75 s na demo (pré-processar os PDFs de exemplo antes da auditoria).
