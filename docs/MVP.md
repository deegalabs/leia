# MVP por entrega

Linha de corte: o que a evidência de cada entrega exige. Nada fora da coluna "escopo" entra antes do prazo.

## V1: sábado 15h30 (Entrega 2, 100 pontos) — protótipo funcional + testes internos
| Frente | Escopo | Dono |
|---|---|---|
| Serviço de LLM | `POST /documents`, `/explain` com `quote` verificado, `/questions`, `/sessions`, `/answers` com rubrica, `/chat` com recusa; hash do payload em `/finalize` (ancoragem se pronta) | Carlos |
| Interface | login Google (A0, C0), telas A1, A2, C1, C2, C3, C4, C5, A3 em texto; manifesto PWA e instalação; service worker fica para a V2 | Daniel |
| Conteúdo | 3 PDFs anonimizados (procuração, honorários, acordo); perguntas e elementos esperados por cláusula; glossário | Camila, Caliane |
| Testes internos | executar [INTERNAL-TESTS.md](INTERNAL-TESTS.md) sobre a V1; prints; relatório | Camila, Caliane, Vida |
| Evidência | vídeo curto da V1 + relatório em `evidence/02-internal-tests/`; publicar na pasta oficial | Vida |

Critério de pronto: um contrato de honorários real passa de A1 a A3 sem intervenção manual; toda seção exibida tem trecho
literal; pergunta fora do documento é recusada; resposta vaga recebe nova explicação; hash gerado e reproduzível.

## V2: sábado 17h30 (Entrega 3, 100 pontos) — validada com testes externos
| Frente | Escopo |
|---|---|
| Voz | leitura por TTS em C2 e C4; entrada por voz com transcrição editável (fallback texto) |
| Registro | ancoragem em Polygon Amoy com OpenTimestamps em paralelo; C6 e P1 (QR e verificação) |
| Testes externos | 3 a 5 leigos no celular sem instrução; tempo até o comprovante; depoimentos com autorização; posts com #hackathonoabpr |
| Evidência | planilha, vídeos e links em `evidence/03-external-tests/` |

## Produto: domingo 10h30 (Entrega 4, 100 pontos) + auditoria (até 300)
Plano detalhado e stack do dia em [INTEGRATION-PLAN.md](INTEGRATION-PLAN.md): interface dentro do FastAPI do Carlos com o kit de marca; Next.js fica para depois.
| Frente | Escopo |
|---|---|
| Documentação | README com execução em 5 minutos (um comando), dados de exemplo, roteiro de auditoria de 10 minutos, relatório da bateria adversarial, `/prompts` versionados, logs de citações |
| Interface | painel A4; acessibilidade (contraste, foco, `aria-live`, alvos ≥ 48 px) |
| Laptop de auditoria | ambiente pronto, chave válida, chain funcionando, PDF adversarial disponível |

## Fora do hackathon
Ver [ROADMAP.md](ROADMAP.md).
