# Ciente (nome provisório)

Consentimento esclarecido com prova. Equipe **Token Economy**, Hackathon da Cidadania OAB-PR 2026 (6ª edição),
categoria **Inovação Aberta e Cidadania**. Licença MIT. Publicado na pasta da equipe do repositório oficial da OAB/PR.

> Plataforma para o cidadão entender um documento jurídico antes de assinar, em ambiente seguro, com supervisão de
> advogado e registro auditável de que o esclarecimento ocorreu. Não substitui o advogado.

## O que faz
1. O documento (procuração, contrato de honorários ou acordo) entra na plataforma; a IA gera a explicação em linguagem simples, sempre com o trecho literal da cláusula; o advogado aprova antes de o cidadão ver.
2. O cidadão percorre o documento um tópico por vez, tira dúvidas e responde a perguntas abertas de compreensão, avaliadas por rubrica.
3. O advogado revisa as respostas e valida (supervisão humana).
4. O sistema gera o registro do consentimento (JSON canônico → SHA-256) e o ancora em registro público com carimbo de tempo; o comprovante do cidadão traz QR para verificação. Nenhum dado pessoal vai ao registro público.

## O que não faz
Não presta consultoria, não interpreta o caso concreto, não recomenda aceitar ou recusar, não substitui a assinatura do documento. Ver [docs/POSITIONING.md](docs/POSITIONING.md).

## Estado das entregas
Cada entrega é uma tag anotada no git; detalhes e comandos em [docs/DELIVERIES.md](docs/DELIVERIES.md) e [CHANGELOG.md](CHANGELOG.md).

| Entrega | Prazo | Tag | Estado |
|---|---|---|---|
| 1. Canvas | sáb 12h | `token-economy/v0.1.0` | entregue, ver [evidence/01-canvas](evidence/01-canvas/) |
| 2. V1 com testes internos | sáb 15h30 | `token-economy/v0.2.0` | em construção, escopo em [docs/MVP.md](docs/MVP.md) |
| 3. V2 com testes externos | sáb 17h30 | `token-economy/v0.3.0` | planejada |
| 4. Produto + auditoria | dom 10h30 | `token-economy/v0.4.0` | planejada |
| 5. Slides | dom 14h30 | `token-economy/v0.5.0` | planejada |
| Pitch | dom 16h30 | `token-economy/v1.0.0` | planejado |

## Estrutura
```
├── README.md, LICENSE, CHANGELOG.md (uma seção por entrega)
├── docs/          arquitetura, casos de uso, telas, contrato da API do serviço de LLM, MVP, roadmap, testes
├── prompts/       prompts do produto (versionados) e registro dos prompts usados na construção
├── evidence/      evidências de cada entrega e dos pontos extras
├── scripts/       tag-delivery.sh (fecha uma entrega: tag + changelog)
└── apps/          web (interface) e llm-service (FastAPI); código a partir de 12/09/2026
```

## Documentos
- [docs/POSITIONING.md](docs/POSITIONING.md): posicionamento, limites da IA, papel do advogado.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): componentes, fluxo de dados, decisões.
- [docs/LLM-API-CONTRACT.md](docs/LLM-API-CONTRACT.md): contrato entre a interface e o serviço de LLM (FastAPI).
- [docs/LLM-WORKFLOW-REVIEW.md](docs/LLM-WORKFLOW-REVIEW.md): revisão do workflow do serviço (v0) e adaptação ao produto.
- [docs/USE-CASES.md](docs/USE-CASES.md) e [docs/SCREENS.md](docs/SCREENS.md): personas, casos de uso, diagramas de sequência e telas.
- [docs/SCALING.md](docs/SCALING.md): escala para 1, 100 e 1.000 usuários e custo por consentimento.
- [docs/MVP.md](docs/MVP.md) e [docs/ROADMAP.md](docs/ROADMAP.md): escopo por entrega e evolução.
- [docs/INTERNAL-TESTS.md](docs/INTERNAL-TESTS.md): plano e relatório dos testes internos (Entrega 2).
- [docs/CANVAS.md](docs/CANVAS.md): canvas da Entrega 1.
- [prompts/README.md](prompts/README.md): política de prompts.
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md): como subir código, publicar na pasta oficial e fechar uma entrega.

## Como rodar
A preencher com o código (apps/web e apps/llm-service). Meta: um comando, menos de 5 minutos, PDFs de exemplo incluídos.
