# Arquitetura

## Componentes
```
[Advogado]  [Cliente]
     │           │  navegador (celular ou desktop)
     ▼           ▼
┌───────────────────────────────┐        ┌──────────────────────────────────────────┐
│ apps/web (Next.js)            │  HTTP  │ apps/llm-service (FastAPI, Python)       │
│ telas do advogado e do cliente│ ─────▶ │ parse do PDF → cláusulas                 │
│ sem lógica de IA              │  JSON  │ explicação com citações (RAG de documento│
│                               │ ◀───── │ único + base de referência OAB)          │
└───────────────────────────────┘        │ perguntas → avaliação por rubrica        │
                                         │ juiz de fidelidade, recusa literal       │
                                         │ registro: JSON canônico → SHA-256 →      │
                                         │ ancoragem (Polygon Amoy; OpenTimestamps) │
                                         │ prompts carregados de /prompts           │
                                         └──────────────────────────────────────────┘
                                                        │
                                             SQLite (sessões, respostas, logs)
```
- **Interface** (`apps/web`): fina. Não chama modelo de linguagem; não calcula hash. Exibe, coleta e chama a API.
  Dois layouts no mesmo código: **PWA mobile-first da cidadã** (`/c/...`, instalável, service worker com o conteúdo da
  sessão) e **painel desktop do advogado** (`/lawyer/...`). **Login social** (Google) com Auth.js; o app web chama o serviço
  com chave interna e envia `user_ref` pseudonimizado. Detalhes em [SCREENS.md](SCREENS.md).
- **Serviço cognitivo** (`apps/llm-service`): toda a inteligência e o registro. Um processo, sem filas. Contrato em [LLM-API-CONTRACT.md](LLM-API-CONTRACT.md).
- **Base de referência** (`prompts/knowledge/`): Estatuto da Advocacia, Código de Ética, tabela de honorários OAB-PR 2026, glossário. Somente leitura, versionada.

## Fluxo de dados
1. Upload do PDF → texto → segmentação por cláusula (`clause_id`, página, texto).
2. Explicação por tópico: `{title, plain_text, quote, clause_id}`; o serviço confere que `quote` é substring da cláusula antes de responder (controle de alucinação verificável).
3. Perguntas abertas por cláusula crítica, com elementos esperados (nunca enviados ao cliente).
4. Respostas do cliente → nota 0 a 3 por rubrica → re-explicação e nova tentativa (máximo 2) → pendência para o advogado.
5. Validação do advogado (obrigatória).
6. Registro: payload canônico (RFC 8785) → SHA-256 → ancoragem do hash em registro público; comprovante com QR para a página de verificação. On-chain vai apenas o hash com salt; dados ficam no serviço.

## Decisões
| Decisão | Escolha | Motivo |
|---|---|---|
| Serviço de IA | FastAPI (Python) | ecossistema de PDF, LLM e web3 em Python; dono do serviço trabalha em Python |
| Interface | Next.js, Tailwind; PWA para a cidadã, painel desktop para o advogado | rápida de montar, instalável no celular, acessível |
| Acesso | login social Google (Auth.js) para advogado e cidadã; link com token continua obrigatório para a cidadã | um toque no Android; identidade fraca vinculada ao consentimento; sem senha |
| Modelos | Claude Sonnet 5 (explicação, citações), GPT-5.4-mini (juiz) | citações nativas por bloco; juiz de outro fornecedor |
| RAG | documento inteiro no contexto, segmentado por cláusula; sem vector store | documento de 2 a 15 páginas cabe no contexto; citação por cláusula é auditável |
| Recusa | resposta literal `NAO_ESTA_NO_DOCUMENTO` | mensurável em teste |
| Registro | Polygon Amoy (contrato `ConsentRegistry`), OpenTimestamps em paralelo, Polygon mainnet como reserva | confirmação em segundos; prova durável; custo R$ 0,01 |
| Voz | TTS por API, gerado por sentença; entrada por voz com transcrição editável | acessibilidade para leigos; texto continua o caminho principal |
| Dados pessoais | pseudônimos e salt; nada em claro no registro público | LGPD art. 8º §2º (ônus da prova) e art. 18 (eliminação) |

## Escala
Ver [SCALING.md](SCALING.md): o trabalho caro de IA é por documento, não por cidadão; 1, 100 e 1.000 usuários.

## Variáveis de ambiente (previsão)
```
LLM_SERVICE_URL=http://localhost:8000
ANTHROPIC_API_KEY=            OPENAI_API_KEY=
AUTH_SECRET=                  GOOGLE_CLIENT_ID=            GOOGLE_CLIENT_SECRET=
LLM_SERVICE_API_KEY=          # chave interna app web → serviço
ANCHOR_CHAIN=amoy             AMOY_RPC_URL=https://polygon-amoy.drpc.org
ANCHOR_PRIVATE_KEY=           CONSENT_REGISTRY_ADDRESS=
ID_PEPPER=                    DATABASE_URL=sqlite:///./data/ciente.db
```
