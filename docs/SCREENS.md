# Telas

Mobile-first para o cliente; desktop para o advogado. Um tópico por tela; três ações por tela no máximo; sem login
para o cliente; sem tempo limite; texto grande; nada em caixa alta; sem vocabulário de prova ("nota", "errado").
Chamadas de API em [LLM-API-CONTRACT.md](LLM-API-CONTRACT.md).

| # | Tela | Rota | Elementos | Chamadas | Entrega |
|---|---|---|---|---|---|
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
