# Registro de prompts usados na construção

Ordem cronológica. Formato em [README.md](README.md) §2. Vale para todo o time, desde 12/09/2026.

### 2026-09-12 09:30–11:50 · Gemini 3.6 Flash · Vida
**Objetivo:** gerar a primeira versão do texto do canvas (Entrega 1) a partir dos PDFs do briefing e do manual.
**Prompt:** [a transcrever pela autora]
**Resultado:** 7 blocos (problema, indicadores, sem IA, com IA, para quem, dados, ferramentas), usados como base do canvas manuscrito e de `docs/CANVAS.md`.

### 2026-09-12 12:30 · Claude Code · Daniel
**Objetivo:** estruturar o repositório de documentação (arquitetura com serviço de LLM em FastAPI, casos de uso, telas, contrato da API, MVP por entrega, política de prompts, evidências) e transformar o texto de posicionamento em plano com atividades.
**Prompt:** instruções do time em linguagem natural: repositório somente com docs, monorepo dentro do repositório oficial da OAB/PR, LLM em FastAPI, foco em interface e leitura do documento, documentar todos os prompts a partir de agora, sugerir nome.
**Resultado:** este repositório (`README.md`, `docs/*`, `prompts/*`, `evidence/*`).

### 2026-09-12 13:50 · Groq openai/gpt-oss-120b (workflow) · Carlos
**Objetivo:** pipeline do serviço cognitivo: fragmentação com trechos literais e posições, síntese em linguagem simples com lastro, mapa de destaque para a interface, resumo humanizado e questões.
**Prompt:** 14 tarefas em [workflow/v0-carlos.json](workflow/v0-carlos.json) (texto integral das missões).
**Resultado:** revisado em [../docs/LLM-WORKFLOW-REVIEW.md](../docs/LLM-WORKFLOW-REVIEW.md): grounding forte; precisa adaptar as classes de peça processual para contrato, trocar múltipla escolha por perguntas abertas, adicionar avaliação e dúvida, recalcular posições em código.
