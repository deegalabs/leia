# Telas

## Jornada (13/09): do login do advogado ao sucesso do cliente
Web app responsivo, um código, desktop e celular. Sem login no hackathon (anotado como pós-hackathon). Ordem em que acontece; a coluna "hoje" aponta o template do serviço.

| # | Tela | Hoje (templates do serviço) |
|---|---|---|
| L2 | Início: Iniciar chat · Anexar PDF · Painel | tela nova do serviço (captura de 13/09, 8h13); recebe logo e tema, sem landing separada |
| L3 | Anexar PDF com progresso por etapa | `tarefa_nova.html` (bloco "Pipeline em execução" e log de eventos) |
| L4 | Painel: documentos, status, filtros | `index.html` (tema e textos; IP fora da tela) |
| L5 | Revisar: texto simples, trecho original, escolher perguntas | parte de `tarefa_nova.html` (resumo e perguntas); editar e escolher ficam pós-hackathon |
| L6 | Aprovar e gerar link do cliente | `tarefa_nova.html` ("Link da cliente") |
| C1 | Cliente: início, apresentação e limites | `leia/cliente.html`, etapa boas-vindas (substitui `dashboard.html` na rota `/t/{hash}`); espera: `cliente_view.html` |
| C2 | Cliente: tópico n de N | `leia/cliente.html`, etapa "Ponto n de N" com trecho original (usa `topicos` se o serviço enviar; senão divide o `resumo_md`) |
| C3 | Cliente: dúvida | `leia/cliente.html`, gaveta "Tenho uma dúvida" (mesma rota `/api/t/{hash}/chat`) |
| C4 | Cliente: conferindo | `leia/cliente.html`, uma pergunta por tela, múltipla escolha como o serviço gera hoje (abertas: pós-hackathon) |
| C5 | Cliente: confirmação | `leia/cliente.html`, etapa de resultado ("Entendimento registrado" ou "Vamos ver de novo"); o registro acontece no `/quiz` do serviço, então o botão "Confirmo que entendi" fica pós-hackathon |
| C6 | Cliente: comprovante (sucesso) | `leia/comprovante.html` em `/t/{hash_imutavel}/comprovante` (QR, código, o que prova); `pdf-assinado` do serviço pode continuar |
| L7 | Painel: registrado, respostas, prova | tentativas de `tarefa_nova.html` + link para `/verify/{hash_imutavel}` |
| P1 | Verificação pública | `leia/verify.html` em `/verify/{hash_imutavel}` (JSON canônico, hash, prova .ots) |
| Pós | Login do advogado (e-mail e senha ou social) e conferência da OAB: fora do hackathon | `tarefa_detalhe.html` (formulário de entrada do serviço) continua existindo; a auditora recebe as credenciais no README; não entra na jornada |

As specs detalhadas continuam em `design/screen-*.md` (A0–A4 = L1–L7; C0–C6; P1).

### Conciliação com os templates do serviço (13/09, 9h30)
Regra: nenhuma tela além das previstas acima. Cada arquivo recebido do serviço tem um destino; o que a interface
acrescenta são só dois arquivos novos (comprovante e verificação) e a substituição da página da cidadã.

| Template do serviço | O que é | Tela prevista | Destino |
|---|---|---|---|
| `index.html` | painel de tarefas com filtros, reprocessar, chat | L4 | fica; tema, textos, IP fora da lista |
| `tarefa_nova.html` | detalhe da tarefa: pipeline, resumo, perguntas com gabarito, tentativas, PDF | L3, L5, L6, L7 | fica; tema, textos, link "Ver registro público" nas tentativas aprovadas |
| `cliente_view.html` | espera da cidadã ("Preparando seu documento", refresh 5 s) | C1 (estado de espera) | fica; tema e texto |
| `dashboard.html` | página da cidadã inteira numa tela: resumo, 12 questões, modal de resultado, chat | C1 a C6 | substituída por `leia/cliente.html` na mesma rota e com o mesmo contexto; arquivo fica no repositório como referência |
| `login.html` | bancada "AI Forensics": chat investigador, payload, log, memória, contexto, protocolo | nenhuma | fica fora da jornada como **Bastidores**, só para a auditoria (D3: memória persistente, log por etapa); acessível pelo painel, sem link para a cidadã |
| `tarefa_detalhe.html` | formulário de entrada (`/login`) | Pós | fica como está; credenciais da auditoria no README |
| tela "Início" (captura 8h13, sem arquivo em `temp/`) | Iniciar chat, Anexar PDF, Painel | L2 | fica; logo e uma linha de posicionamento; **não** se cria landing separada hoje |

Telas que a interface acrescenta: comprovante (C6) e verificação pública (P1). Nada mais. A confirmação explícita (C5
com botão) fica no roadmap.

### Onde cada tela vive no app (`apps/web`, ADR-0009, 13/09 10h)
| Tela | Rota no app | Componente | Dados |
|---|---|---|---|
| Landing (tela 15) | `/` | `app/page.tsx` | estática |
| C1 a C5 | `/t/{hash}` | `components/Journey.tsx` (etapas: boas-vindas, ponto n de N, dúvida em gaveta, pergunta k de K, resultado) | `GET /api/t/{hash}`, `POST /quiz`, `POST /chat` |
| C6 | `/comprovante/{hash_imutavel}` | `components/Receipt.tsx` | `GET /verify/{hash_imutavel}?format=json` |
| P1 | `/verify/{hash_imutavel}` | `components/Verify.tsx` | idem + `proof.ots` |
| L2 a L7, bastidores, login | serviço (FastAPI) | templates do Carlos com tema e textos | |

A página `apps/llm-service/templates/leia/cliente.html` (mesma jornada, servida pelo FastAPI) é reserva da Entrega 4.

### Telas v3 (13/09 à tarde, pedido do Daniel): contas, painéis, envio pela cidadã, dúvida ao advogado
| Tela | Rota no app | O que faz | Dados |
|---|---|---|---|
| A0/C0 Entrar ou criar conta | `/entrar` | e-mail e senha; papel cidadã ou advogado; token Bearer guardado no aparelho | `POST /api/auth/cadastro`, `/login`, `GET /api/auth/me` |
| A4 Painel do advogado | `/painel` | documentos enviados com estado, link da cliente, respostas e dúvidas abertas; "Enviar um documento" | `GET /api/tarefas` |
| CH Meus documentos (cidadã) | `/painel` | documentos que ela enviou ou abriu; "Continuar", "Ver comprovante"; "Enviar meu documento" | `GET /api/tarefas` |
| A3 Detalhe | `/painel/{id}` | etapa atual, tentativas, dúvidas da cliente com campo de resposta | `GET /api/tarefas/{id}`, `POST .../duvidas/{id}/responder` |
| A1 Enviar documento | `/enviar` | PDF + título; advogado recebe o link da cliente; cidadã vai direto para a jornada | `POST /api/tarefas` |
| C3 Dúvida | gaveta em `/t/{hash}` | além do chat, "Enviar esta dúvida para o advogado" quando a tarefa tem advogado; cai no painel dele | `POST /api/t/{hash}/duvida` |
| Documento e marcações | `/t/{hash}/documento` | texto original com cada trecho marcado por classe (quem é quem, datas e valores, fatos, fundamentos, pedidos), lista das marcações com "Ver no texto", "O que a assistente concluiu" (sínteses com lastro), contagem de conferidas palavra por palavra; ligado da jornada e do detalhe do painel | `GET /api/t/{hash}/inferencias` |
Regra do produto: todo documento passa pela estruturação (workflow) antes do chat; a cidadã pode usar a plataforma
sozinha (sem advogado) ou pelo link do advogado. Contrato: `docs/API-V3-CONTRACT.md`.

## Plataforma e acesso
- **Um web app responsivo** (desktop e celular). Instalar como aplicativo (PWA) é extra, não requisito.
- **Cidadã no celular.** Aplicação web, opcionalmente instalável (manifesto, ícone, tela cheia),
  com service worker que guarda o shell e o conteúdo da sessão já carregado (tópicos, perguntas, áudio): se a rede cair,
  a cidadã continua lendo e ouvindo; respostas ficam em fila e sobem quando voltar. Alvos de toque ≥ 48 px, texto grande,
  navegação inferior com no máximo três ações, uma tela por tópico.
- **Advogado: versão desktop separada.** Layout de painel (barra lateral, tabelas, revisão lado a lado do texto simples e
  do trecho original). Mesmo código, rota e layout próprios (`/lawyer/...`); funciona no celular, mas é desenhado para tela grande.
- **Login social** (Google na V1; Apple e gov.br no roadmap) para os dois perfis, via Auth.js no app web:
  - Advogado: obrigatório. Primeiro acesso pede nome e número da OAB/UF (conferência no Cadastro Nacional dos Advogados
    fica para o roadmap; responde ao "golpe do falso advogado" do canvas).
  - Cidadã: um toque no Android já logado no Google; vincula a sessão à conta para retomar depois e receber o comprovante.
    O link com token continua obrigatório (login não abre sessão de outra pessoa). Decisão pendente do time: manter
    "continuar sem conta" como alternativa de acessibilidade.
  - O serviço FastAPI não faz login: recebe do app web um `user_ref` pseudonimizado (hash do e-mail com pepper) e a chave
    interna do app. No registro público nunca vai e-mail nem nome.

## Regras de tela
Paleta e contraste em [brand/README.md](brand/README.md): marinho `#081820`, off-white `#F0F0E8`, teal da marca `#38A8A8` só
no escuro, teal de ação `#1F7373` nos botões sobre fundo claro.
Um tópico por tela; três ações por tela no máximo; sem tempo limite; texto grande; nada em caixa alta; sem vocabulário de prova ("nota", "errado").
Chamadas de API em [LLM-API-CONTRACT.md](https://github.com/deegalabs/leia/blob/main/LLM-API-CONTRACT.md).

| # | Tela | Rota | Elementos | Chamadas | Entrega |
|---|---|---|---|---|---|
| A0 | Advogado: entrar | `/lawyer/login` | botão "Entrar com Google"; primeiro acesso: nome, OAB/UF | Auth.js | V1 |
| C0 | Cidadã: entrar | `/c/{token}/login` | nome do advogado e do documento; "Entrar com Google" (um toque); por que pedimos (voltar depois, receber o comprovante) | Auth.js | V1 |
| A1 | Advogado: enviar documento | `/lawyer/new` | seletor de tipo, upload, progresso por etapa ("lendo", "separando cláusulas", "escrevendo em linguagem simples") | `POST /documents`, `POST /documents/{id}/explain`, `POST /documents/{id}/questions` | V1 |
| A2 | Advogado: revisar e aprovar | `/lawyer/documents/{id}` | lista de seções (título, texto simples editável, "ver trecho original"), perguntas sugeridas com seleção de 2 a 3, botão "Aprovar e gerar link", link copiável | `POST /sessions` | V1 |
| C1 | Cliente: início | `/c/{token}` | nome do advogado e do documento, apresentação da IA ("sou uma assistente automática; explico o que está escrito; não sou advogada"), botão único "Começar" | `GET /sessions/{id}` | V1 |
| C2 | Cliente: tópico n de N | `/c/{token}/topics/{n}` | ícone e título, texto simples, "ver trecho original" (colapsado), progresso "Tópico 2 de 6", ações: "Entendi, próximo", "Tenho uma dúvida", ouvir (V2) | dados da sessão; V2: `POST /tts` | V1 |
| C3 | Cliente: dúvida | `/c/{token}/ask` | 3 chips de exemplo, campo de texto (V2: microfone), resposta com o trecho citado ou aviso "não está no seu documento, vou anotar para o advogado" | `POST /sessions/{id}/chat` | V1 |
| C4 | Cliente: conferindo o entendimento | `/c/{token}/questions/{k}` | frase de teach-back, pergunta, campo de resposta (V2: voz com transcrição editável), "Não sei, explica de novo", feedback em duas partes e nova explicação quando insuficiente | `POST /sessions/{id}/answers` | V1 |
| C5 | Cliente: confirmação | `/c/{token}/confirm` | lista "o que você entendeu" com ✓, pendências para o advogado, botão "Confirmo que entendi" | `POST /sessions/{id}/confirm` | V1 |
| A3 | Advogado: validar | `/lawyer/sessions/{id}` | respostas, notas, dúvidas anotadas, campo de observações, botão "Validar e gerar registro" | `POST /sessions/{id}/validate`, `POST /sessions/{id}/finalize` | V1 (hash), V2 (ancoragem) |
| C6 | Comprovante | `/c/{token}/receipt` | hash, data e hora, link do registro público, QR, texto "este código prova que você respondeu estas perguntas neste dia; não contém seu documento nem suas respostas", contato do advogado | dados da sessão | V2 |
| P1 | Verificação pública | `/verify/{id}` | hash, JSON canônico, transação, explorer, instrução para recalcular com `sha256sum` | `GET /verify/{id}` | V2 |
| A4 | Advogado: painel | `/lawyer` | lista de sessões com status e pendências | `GET /sessions` | Produto |

Estados comuns: carregando (skeleton, sem spinner acima de 3 s), erro ("deu um problema do nosso lado; seu progresso
está salvo; tentar de novo"), banner fixo com os limites da IA e botão "Falar com o advogado" em todas as telas do cliente.
