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
                                         │ carimbo OpenTimestamps do payloadHash    │
                                         │ prompts carregados de /prompts           │
                                         └──────────────────────────────────────────┘
                                                        │
                                             SQLite (sessões, respostas, logs)
```
- **Interface** (`apps/web`): fina. Não chama modelo de linguagem; não calcula hash. Exibe, coleta e chama a API.
  Dois layouts no mesmo código: **PWA mobile-first da cidadã** (`/c/...`, instalável, service worker com o conteúdo da
  sessão) e **painel desktop do advogado** (`/lawyer/...`). **Login social** (Google) com Auth.js; o app web chama o serviço
  com chave interna e envia `user_ref` pseudonimizado. Detalhes em [SCREENS.md](/docs/telas).
- **Serviço cognitivo** (`apps/llm-service`): toda a inteligência e o registro. Um processo, sem filas. Contrato em [LLM-API-CONTRACT.md](https://github.com/deegalabs/leia/blob/main/LLM-API-CONTRACT.md).
- **Base de referência** (`prompts/knowledge/`): Estatuto da Advocacia, Código de Ética, tabela de honorários OAB-PR 2026, glossário. Somente leitura, versionada.

## Estratégia de transição da interface
1. **V1 (sáb 15h30):** o serviço FastAPI serve também o **HTML de transição** do Carlos; é a interface testada nos testes
   internos. Nada de segunda interface antes da V1.
2. **V2 (sáb 17h30):** a jornada da cidadã (telas C1 a C5) sai do HTML e passa para `apps/web` (Next.js, mobile-first),
   consumindo os endpoints do serviço; o advogado continua no HTML de transição.
3. **Produto (dom 10h30):** painel do advogado em `apps/web`; PWA e login social se as credenciais estiverem prontas.
   Se o tempo não permitir, o HTML de transição adaptado ao celular é o plano B para a auditoria: a auditoria pontua
   confiabilidade, usabilidade e sofisticação, não o framework.
A regra é uma só: o serviço é o backend de tudo; a interface, qualquer que seja, só consome a API.

## Fluxo de dados
1. Upload do PDF → texto → segmentação por cláusula (`clause_id`, página, texto).
2. Explicação por tópico: `{title, plain_text, quote, clause_id}`; o serviço confere que `quote` é substring da cláusula antes de responder (controle de alucinação verificável).
3. Perguntas abertas por cláusula crítica, com elementos esperados (nunca enviados ao cliente).
4. Respostas do cliente → nota 0 a 3 por rubrica → re-explicação e nova tentativa (máximo 2) → pendência para o advogado.
5. Validação do advogado (obrigatória).
6. Registro: payload canônico (chaves ordenadas, sem espaços) → SHA-256 → carimbo OpenTimestamps sobre esse hash (ADR-0010); comprovante com QR para a página de verificação. Fora do serviço vai só o hash: nenhum dado pessoal, nenhuma rede EVM, nenhum contrato.

## Decisões
| Decisão | Escolha | Motivo |
|---|---|---|
| Serviço de IA | FastAPI (Python) | ecossistema de PDF, LLM e web3 em Python; dono do serviço trabalha em Python |
| Interface | Next.js, Tailwind; PWA para a cidadã, painel desktop para o advogado | rápida de montar, instalável no celular, acessível |
| Acesso | login social Google (Auth.js) para advogado e cidadã; link com token continua obrigatório para a cidadã | um toque no Android; identidade fraca vinculada ao consentimento; sem senha |
| Modelos | Claude Sonnet 5 (explicação, citações), GPT-5.4-mini (juiz) | citações nativas por bloco; juiz de outro fornecedor |
| RAG | documento inteiro no contexto, segmentado por cláusula; sem vector store | documento de 2 a 15 páginas cabe no contexto; citação por cláusula é auditável |
| Recusa | resposta literal `NAO_ESTA_NO_DOCUMENTO` | mensurável em teste |
| Registro | carimbo OpenTimestamps sobre o `payloadHash`; sem contrato e sem rede EVM (ADR-0010) | prova anterioridade e integridade sem carteira, sem chave privada e sem custo; a prova nasce pendente e fecha no Bitcoin em horas |
| Voz | TTS por API, gerado por sentença; entrada por voz com transcrição editável | acessibilidade para leigos; texto continua o caminho principal |
| Dados pessoais | pseudônimos e salt; nada em claro no registro público | LGPD art. 8º §2º (ônus da prova) e art. 18 (eliminação) |

## Escala
Ver [SCALING.md](/docs/escala): o trabalho caro de IA é por documento, não por cidadão; 1, 100 e 1.000 usuários.

## Variáveis de ambiente (previsão)
A lista que o serviço realmente lê está em `apps/llm-service/.env.example`.
```
LLM_SERVICE_URL=http://localhost:8000
ANTHROPIC_API_KEY=            OPENAI_API_KEY=
AUTH_SECRET=                  GOOGLE_CLIENT_ID=            GOOGLE_CLIENT_SECRET=
LLM_SERVICE_API_KEY=          # chave interna app web → serviço
OTS_ENABLED=true              # carimbo OpenTimestamps; não há variável de ancoragem em rede EVM
ID_PEPPER=                    DATABASE_URL=sqlite:///./data/leia.db
```
