# Telas

## Jornada (13/09): do login do advogado ao sucesso do cliente
Web app responsivo, um código, desktop e celular. Sem login no hackathon (anotado como pós-hackathon). Ordem em que acontece; a coluna "hoje" aponta o template do serviço.

| # | Tela | Hoje (templates do serviço) |
|---|---|---|
| L2 | Início: Iniciar chat · Anexar PDF · Painel | tela nova (captura de 13/09, 8h13) |
| L3 | Anexar PDF com progresso por etapa | `tarefa_nova.html` + `cliente_view.html` |
| L4 | Painel: documentos, status, filtros | `index.html` |
| L5 | Revisar: texto simples, trecho original, escolher perguntas | parte de `tarefa_nova.html` (falta editar e escolher) |
| L6 | Aprovar e gerar link do cliente | `tarefa_nova.html` ("Link cliente") |
| C1 | Cliente: início, apresentação e limites | topo de `dashboard.html` |
| C2 | Cliente: tópico n de N | resumo de `dashboard.html` (hoje inteiro numa página) |
| C3 | Cliente: dúvida | chat lateral de `dashboard.html` |
| C4 | Cliente: conferindo (perguntas abertas) | questões de `dashboard.html` (hoje múltipla escolha) |
| C5 | Cliente: confirmação | não existe |
| C6 | Cliente: comprovante (sucesso) | bloco "assinatura" de `dashboard.html` |
| L7 | Painel: registrado, respostas, prova | tentativas de `tarefa_nova.html` |
| P1 | Verificação pública | não existe |
| Pós | Login do advogado (e-mail e senha ou social) e conferência da OAB: fora do hackathon; acesso aberto durante o evento | `tarefa_detalhe.html` existe, não entra na jornada |

As specs detalhadas continuam em `design/screen-*.md` (A0–A4 = L1–L7; C0–C6; P1).

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
Chamadas de API em [LLM-API-CONTRACT.md](LLM-API-CONTRACT.md).

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
