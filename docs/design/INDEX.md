# LeIA · Design de telas e fluxos

Tese: "O cidadão entende antes de assinar; o advogado supervisiona; o registro prova."

Este diretório contém 14 telas (chunks) e 6 documentos compartilhados. Tudo em pt-BR. Cada chunk de tela segue a mesma estrutura: propósito e posição no fluxo, layout em palavras, componentes shadcn/ui, copy exata, 4 estados (default, vazio, carregando, erro) mais estados próprios, interações, acessibilidade, chamadas de API e "o que muda na V1 / V2 / Produto".

Significado das versões: **V1** = demo do hackathon (48 h); **V2** = semanas seguintes; **Produto** = versão de produção.

## Telas

| Arquivo | Tela | Rota | Superfície | Entrada → Saída |
|---|---|---|---|---|
| `screen-01-ch-meus-documentos.md` | CH · Meus documentos | `/c` | cidadã, mobile | login / app instalado → retomar sessão, comprovante |
| `screen-02-c0-entrar.md` | C0 · Entrar | `/c/{token}/login` | cidadã, mobile | link do advogado → C1 |
| `screen-03-c1-inicio.md` | C1 · Início | `/c/{token}` | cidadã, mobile | C0 → C2 tópico 1 |
| `screen-04-c2-topico.md` | C2 · Tópico n de N | `/c/{token}/topics/{n}` | cidadã, mobile | C1 / tópico anterior → próximo tópico, C3, C4 |
| `screen-05-c3-duvida.md` | C3 · Dúvida | `/c/{token}/ask?from={n}` | cidadã, mobile | C2 → volta a C2 |
| `screen-06-c4-conferindo.md` | C4 · Conferindo k de K | `/c/{token}/questions/{k}` | cidadã, mobile | último C2 → próxima pergunta, C5 |
| `screen-07-c5-confirmacao.md` | C5 · Confirmação | `/c/{token}/confirm` | cidadã, mobile | C4 → C6 ou rever C2 |
| `screen-08-c6-comprovante.md` | C6 · Comprovante | `/c/{token}/receipt` | cidadã, mobile | C5 / CH → salvar, falar com o advogado |
| `screen-09-a0-entrar.md` | A0 · Entrar | `/lawyer/login` | advogado, desktop | acesso → A4 (1º acesso: nome + OAB/UF) |
| `screen-10-a4-painel.md` | A4 · Painel do advogado | `/lawyer` | advogado, desktop | A0 → A1, A2, A3 |
| `screen-11-a1-enviar.md` | A1 · Enviar documento | `/lawyer/new` | advogado, desktop | A4 → A2 (pipeline por etapas) |
| `screen-12-a2-revisar.md` | A2 · Revisar e aprovar | `/lawyer/documents/{id}` | advogado, desktop | A1 → link gerado → A4 |
| `screen-13-a3-validar.md` | A3 · Validar | `/lawyer/sessions/{id}` | advogado, desktop | A4 → registro (hash, transação, comprovante) |
| `screen-14-p1-verificacao.md` | P1 · Verificação pública | `/verify/{id}` | público, responsivo | QR / link → conferência com sha256sum |

## Compartilhados

| Arquivo | Conteúdo |
|---|---|
| `shared/personas.md` | Cidadã, advogado, verificador; implicações de design por persona |
| `shared/information-architecture.md` | Mapa de rotas, guardas, fluxos, objetos e estados (documento, sessão, seção, pergunta, resposta, dúvida, pendência, registro), rubrica em palavras, persistência local |
| `shared/navigation.md` | Banner fixo da assistente + "Falar com o advogado", barra inferior de ações, comportamento de voltar, banner offline, VLibras; sidebar do advogado; página pública |
| `shared/micro-interactions.md` | Tabela gatilho → animação → duração → easing → reduced-motion; anúncios de live region pareados |
| `shared/responsive.md` | Faixas de largura da cidadã (320–430 e acima), do advogado (≥ 1280 até < 768), pública, zoom 200 %, impressão do comprovante |
| `shared/component-plan.md` | Tokens de tema, shadcn reutilizados, componentes novos com props (AssistantBanner, BottomActionBar, TopicCard, AudioPlayer, RecordButton, QuoteDisclosure, ProgressSteps, StatusChip, ReceiptCard, ClauseSideBySide, PipelineStepper, RubricBadge…) |

## Decisões de design que valem para todas as telas

1. Banner fixo no topo (marinho) com o texto da assistente em 3 linhas curtas e o botão "Falar com o advogado" sempre no mesmo lugar; barra inferior com no máximo 2 botões (primário + secundário). Total de 3 ações por tela.
2. Um tópico por rota; ao navegar, foco no h1 e anúncio "Tópico 2 de 7: Quanto você paga". Player, microfone e trecho original têm o mesmo tamanho e posição em C2, C3 e C4.
3. Todos os tópicos antes das perguntas; cada pergunta começa com o lembrete do essencial do tópico. Máximo 2 tentativas; "Não sei, explica de novo" não consome tentativa (1 vez por pergunta); depois o ponto fica pendente para o advogado e a cidadã segue.
4. Rubrica só em palavras no painel do advogado; a cidadã nunca vê número, "nota" ou "errado". O front bloqueia feedback com palavras proibidas e cai no texto de fallback.
5. Áudio: V1 com `speechSynthesis`/`SpeechRecognition` do navegador; V2 com `POST /tts` (áudio pré-gerado na aprovação) e `POST /stt`. A etapa "Gerando áudio" de A1 só aparece na V2.
6. Registro: JSON canônico sem nome, documento, respostas ou dúvidas; comprovante tem 3 momentos (aguardando o advogado, carimbo pendente, registrado) com polling de 30 s. PDF do comprovante sem metadados.
7. Login Google nos dois lados; token do link continua obrigatório; "Continuar sem conta" desenhado como opção atrás de flag até a decisão da equipe.

## Pendências (decisões abertas para a equipe)

| # | Pergunta | Onde impacta | Proposta do design |
|---|---|---|---|
| 1 | Manter "Continuar sem conta" como alternativa de acessibilidade? | C0, C6, CH | Manter atrás da flag `NEXT_PUBLIC_ALLOW_GUEST`; C6 avisa que o comprovante fica só no celular. |
| 2 | Quem faz o upload do documento: só o advogado ou também a cidadã? | A1, CH | Só o advogado na V1 (a cidadã não cria documentos; CH não tem botão de envio). |
| 3 | Canal de "Falar com o advogado": telefone do escritório, WhatsApp, recado dentro do app? | banner, A0 | V1: folha com nome + OAB + texto; V2: telefone opcional no cadastro (A0) e recado salvo como pendência (`POST /sessions/{id}/notes`, fora do contrato). |
| 4 | Endpoints de listagem não existem no contrato: lista da cidadã (CH) e do advogado (A4). | CH, A4 | V1: ids guardados no Next + `GET /sessions/{id}` por item; V2: `GET /sessions?me=1` e `GET /lawyer/overview`. |
| 5 | Salvar edições e aprovação da explicação (A2) não têm endpoint. | A2 | V1: rascunho no banco do Next e envio das seções no `POST /sessions`; V2: `PUT /documents/{id}/sections` + `POST /documents/{id}/approve`. |
| 6 | Perfil do advogado (nome, OAB/UF) fica no Next ou no FastAPI? | A0 | Next (Auth.js + tabela `lawyer`) na V1. |
| 7 | Progresso da cidadã (`resume_path`, tópicos vistos) é salvo no servidor? | C2, CH | V1 só local; V2 campo `resume_path` aceito em `chat`/`answers`/`confirm`. |
| 8 | Conteúdo exato do JSON canônico (campos e ordem) e regras de canonicalização (JCS?). | C6, A3, P1 | Proposta em `information-architecture.md` › Registro; confirmar com backend antes de gerar o primeiro hash real. |
| 9 | Primeiro nome da cidadã: enviado em `POST /sessions`? Fica só no banco privado? | A2, C1, A4 | Sim em `POST /sessions { client_first_name }`; nunca no JSON canônico. |
| 10 | Número de tópicos vs meta de < 4 min até o comprovante (7 tópicos ≈ 5 min). | C1, C2, A2 | Permitir ao advogado juntar seções em A2; medir no teste com usuária. |
| 11 | "Gerar novo link" invalida o anterior? `POST /sessions` com o mesmo `document_id`. | A4, A2 | Invalidar o anterior e manter o progresso se a sessão já começou (regra de backend). |
| 12 | Haverá allowlist de e-mails de advogados no hackathon? | A0 | Variável de ambiente com lista; sem allowlist, qualquer Google entra. |
| 13 | Retomar o andamento do pipeline após sair de A1 (`GET /documents/{id}` não existe). | A1, A4 | V1: manter a aba aberta; V2: job assíncrono + `GET /documents/{id}`. |
| 14 | Dica de instalação do PWA ("Adicionar à tela inicial"): mostrar em C1 ou CH? | C1, CH | Produto; fora da V1. |
| 15 | Rede de registro na demo: Polygon Amoy (testes). O rótulo "rede de testes" aparece em P1. | P1, C6 | Manter o rótulo até migrar para rede principal. |

## Regras de conteúdo aplicadas (resumo)

- "Você" para a cidadã; "Dr. João" para o advogado. Botões = verbo + resultado.
- Frases ≤ 15 palavras, uma ideia, voz ativa, exemplo em R$; termo técnico só entre parênteses após a explicação.
- Proibido em qualquer tela da cidadã: "errado", "incorreto", "reprovado", "nota", "teste", "prova", "quiz", "tente novamente" sozinho, "você não entendeu".
- Textos fixos usados literalmente: apresentação da assistente (C1), consentimento de voz (C3/C4), enquadramento e feedback do teach-back (C4), 3ª tentativa (C4), status de conexão/erro/recusa (todas), explicação do comprovante (C6).
