# Workflow do serviço cognitivo

`v2-leia.json`: **o workflow que roda hoje**. É cópia exata de
[`../../apps/llm-service/protocolo_pdf.json`](../../apps/llm-service/protocolo_pdf.json), o arquivo que
`core/pipeline_pdf.py` carrega a cada documento. Quem audita a dimensão D3 lê esta pasta, então o que está
publicado aqui precisa ser o que o motor de fato manda ao modelo.

`v1-leia.json`: o workflow de 12 a 19/09/2026, sem a etapa T0. Fica como registro do que o motor de fato
mandou ao modelo naquele período: ele fazia as mesmas catorze perguntas a qualquer documento, com o
vocabulário de peça processual embutido na missão de T1. A revisão de `v0` já apontava isso em 12/09
("precisa adaptar as classes de peça processual para contrato"), e o que fecha a pendência é a T0 de `v2`.

`v0-carlos.json`: workflow recebido do dono do serviço em 12/09/2026 (14 tarefas, 4 fases, Groq
`openai/gpt-oss-120b`). Fica como está, por ser registro histórico: 6 dos 16 ids dele (`T1_CLASSE_IDENTIFICACAO`,
`T6_FUSAO_FRAGMENTOS` e os demais da fase 1) nunca existiram no protocolo que roda, e 8 das 10 missões em comum
já eram outras. Revisão e adaptação ao produto em
[../../docs/LLM-WORKFLOW-REVIEW.md](../../docs/LLM-WORKFLOW-REVIEW.md).

## Ao mudar o protocolo

Mudou `apps/llm-service/protocolo_pdf.json`, republique na mesma hora:

```bash
cp apps/llm-service/protocolo_pdf.json prompts/workflow/v2-leia.json
```

`test_protocol_the_published_catalog_is_the_protocol_that_runs` (em `apps/llm-service/tests_v3.py`) compara os
dois e reprova quando divergem, primeiro pelos ids, depois pelas missões. Versão nova com outro nome
(`v2-*.json`) passa a ser a publicada: o teste sempre lê a de maior número.
