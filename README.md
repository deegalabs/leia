# Ciente (nome provisório)

Consentimento esclarecido com prova. Equipe **Token Economy**, Hackathon da Cidadania OAB-PR 2026 (6ª edição),
categoria **Inovação Aberta e Cidadania**. Licença MIT.

> O sistema não substitui o advogado. Ele registra e comprova, de forma auditável, que o advogado cumpriu o dever
> de informar o cliente de modo claro, compreensível e verificável (Código de Ética da OAB, art. 9º e 48).

## O que faz
1. O advogado envia o documento (procuração, contrato de honorários ou acordo) e aprova a explicação em linguagem simples gerada pela IA, sempre com o trecho literal da cláusula.
2. O cliente percorre o documento um tópico por vez, tira dúvidas e responde a perguntas abertas de compreensão, avaliadas por rubrica.
3. O advogado revisa as respostas e valida.
4. O sistema gera o registro do consentimento (JSON canônico → SHA-256) e o ancora em registro público com carimbo de tempo; o comprovante traz QR para verificação. Nenhum dado pessoal vai ao registro público.

## O que não faz
Não presta consultoria, não interpreta o caso concreto, não recomenda aceitar ou recusar, não substitui a assinatura do documento. Ver [docs/POSITIONING.md](docs/POSITIONING.md).

## Estado das entregas
| Entrega | Prazo | Estado |
|---|---|---|
| 1. Canvas | sáb 12h | entregue, ver [evidence/01-canvas](evidence/01-canvas/) |
| 2. V1 com testes internos | sáb 15h30 | em construção, escopo em [docs/MVP.md](docs/MVP.md) |
| 3. V2 com testes externos | sáb 17h30 | planejada |
| 4. Produto + auditoria | dom 10h30 | planejada |
| 5. Slides e pitch | dom 14h30 / 16h30 | planejados |

## Estrutura
```
├── README.md, LICENSE
├── docs/          arquitetura, casos de uso, telas, contrato da API do serviço de LLM, MVP, roadmap, testes
├── prompts/       prompts do produto (versionados) e registro dos prompts usados na construção
├── evidence/      evidências de cada entrega e dos pontos extras
└── apps/          web (interface) e llm-service (FastAPI); código a partir de 12/09/2026
```

## Documentos
- [docs/POSITIONING.md](docs/POSITIONING.md): posicionamento, limites da IA, papel do advogado.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): componentes, fluxo de dados, decisões.
- [docs/LLM-API-CONTRACT.md](docs/LLM-API-CONTRACT.md): contrato entre a interface e o serviço de LLM (FastAPI).
- [docs/USE-CASES.md](docs/USE-CASES.md) e [docs/SCREENS.md](docs/SCREENS.md): casos de uso e telas.
- [docs/MVP.md](docs/MVP.md) e [docs/ROADMAP.md](docs/ROADMAP.md): escopo por entrega e evolução.
- [docs/INTERNAL-TESTS.md](docs/INTERNAL-TESTS.md): plano e relatório dos testes internos (Entrega 2).
- [docs/CANVAS.md](docs/CANVAS.md): canvas da Entrega 1.
- [prompts/README.md](prompts/README.md): política de prompts.

## Como rodar
A preencher com o código (apps/web e apps/llm-service). Meta: um comando, menos de 5 minutos, PDFs de exemplo incluídos.
