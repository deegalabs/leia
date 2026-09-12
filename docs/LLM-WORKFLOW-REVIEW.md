# Validação do workflow do serviço cognitivo (v0, recebido em 12/09/2026)

> Papel deste documento: validar o desenho do serviço contra o produto, a API e a auditoria, e devolver insumos ao dono
> do serviço. As decisões de implementação são dele.

Fonte: [`prompts/workflow/v0-carlos.json`](../prompts/workflow/v0-carlos.json). Referências: [LLM-API-CONTRACT.md](LLM-API-CONTRACT.md),
[ARCHITECTURE.md](ARCHITECTURE.md), [POSITIONING.md](POSITIONING.md), manual do hackathon (auditoria D1 confiabilidade, D2 usabilidade, D3 sofisticação).

## O que o workflow faz
14 tarefas em 4 fases, Groq `openai/gpt-oss-120b`, `temperature 0`, `seed`, saídas JSON, fan-out paralelo:
1. **Fragmentação** (T1–T5, paralelas): partes, datas e valores, fatos, fundamentos legais, pedidos. Cada item traz
   `campo`, `valor`, `trecho_verbatim` (cópia exata) e `pos_trecho_verbatim` (posições de caractere).
2. **Síntese** (T6–T11): fusão em `memoria_persistente`; textos fluidos por classe com `lastro` (itens da memória que
   sustentam o texto) e `pos_trechos_origem`; regra "trabalha só sobre a memória, não relê o PDF".
3. **Indexação** (T12): mapa `_ui` de posições e cores para destaque na interface.
4. **Humanização e questões** (T13–T14): resumo em markdown com 5 seções (≤ 3.500 caracteres) e 12 questões de
   múltipla escolha com gabarito e justificativa, "como prova de ciência".

## Pontos fortes (manter)
- **Grounding por construção**: `trecho_verbatim` + posições + `lastro` é exatamente o controle explícito de alucinação
  que a Dimensão 1 pede, e o mapa `_ui` permite mostrar o trecho original destacado na tela (nossa "ver trecho original").
- Persona "escrevente forense: transcreve, não interpreta" e "zero fatos fora da memória" alinham com "explicação ≠ orientação".
- Determinismo (`temperature 0`, `seed`), saída estruturada, tarefas atômicas e paralelas: bom para auditar e para escalar.
- Linguagem simples com regras concretas (frases ≤ 25 palavras, sem latim, termos explicados entre parênteses).

## Pontos a considerar para o encaixe no produto (insumo para o dono do serviço)

| # | Ponto | Por que importa | Sugestão |
|---|---|---|---|
| 1 | **Domínio: o workflow é para peças processuais** (autor, réu, juiz, pedidos, fundamentos, "decisão recorrida", número do processo). O produto explica **contrato de honorários, procuração e acordo**. | as classes não existem no documento; T10/T11 vão devolver vazio ou inventar | trocar as 5 classes de fragmentação por: **partes** (contratante/contratado, outorgante/outorgado), **valores e prazos** (honorários, percentual, parcelas, vigência, multa), **poderes e obrigações** (o que cada parte pode e deve fazer; poderes especiais do CPC 105), **condições e riscos** (êxito, sucumbência, rescisão, foro, quitação), **referências legais** (se houver). Seções do resumo: quem são as partes · o que você está autorizando ou contratando · quanto e quando você paga · o que acontece se (perder, desistir, atrasar) · como cancelar ou sair. Tabelas A, B e C de `research/legal/06` (na pasta de trabalho) já listam as cláusulas por tipo. |
| 2 | **12 questões de múltipla escolha** (T14) no lugar de **2 a 3 perguntas abertas** com resposta nas próprias palavras. | múltipla escolha permite chute e vira "prova"; contraria o canvas, o posicionamento e a pesquisa de UX (teach-back); a rubrica 0–3 e a re-explicação não existem | T14 gera perguntas **abertas** com `expected_elements` (nunca exibidos à cidadã), 2 a 3 por documento, sobre as cláusulas de maior consequência; o advogado escolhe. Se quiser manter múltipla escolha, só como autoconferência opcional, nunca como evidência do consentimento. |
| 3 | **Não existe tarefa de avaliação da resposta** nem de **dúvida livre**. | a interface não consegue fechar o loop (nota, feedback, re-explicação) nem responder perguntas | adicionar **T15 avaliar** (entrada: pergunta, elementos esperados, resposta; saída: `score 0..3`, `matched`, `missing`, `feedback_for_client`, `re_explanation`) e **T16 dúvida** (responde só com a memória; se não houver lastro, devolve `NAO_ESTA_NO_DOCUMENTO`). |
| 4 | **Posições de caractere geradas pelo modelo** (`pos_trecho_verbatim`). | modelos de linguagem não contam caracteres com precisão; posições erradas quebram o destaque e a auditoria | o serviço **localiza `trecho_verbatim` no texto por busca** e recalcula as posições em código; item cujo trecho não é encontrado é descartado e registrado. Esse é o `quote_verified` do contrato. |
| 5 | **T13 devolve markdown sem lastro por seção** e proíbe repetir o trecho literal. | a tela de tópicos não consegue ligar cada parágrafo às cláusulas de origem | T13 devolve JSON: `sections[{ order, title, plain_text, lastro[], quotes[] }]`; a interface mostra o texto simples e, ao toque, o trecho original (o texto não repete a citação, a tela sim). |
| 6 | **Sem juiz independente nem defesa contra instrução escondida no PDF.** | nota 5 em D1 exige "controle explícito de alucinação com verificação de fontes" | quote-check em código (item 4) já é o controle principal; adicionar juiz de fidelidade por seção (outro fornecedor, pode ser barato) e pré-scan de injeção (texto do documento é dado, nunca instrução). |
| 7 | **Provedor único (Groq) e modelo aberto** sem fallback. | cota ou indisponibilidade no dia derruba a demo; qualidade em pt-BR jurídico não verificada | manter Groq como padrão (rápido e barato), configurar fallback por variável de ambiente (Anthropic ou OpenAI) e testar com os 3 PDFs reais até 14h. |
| 8 | Transições encadeadas (T1→T2→…) contradizem o fan-out declarado. | ambiguidade de execução | se é paralelo, todas as tarefas da fase apontam para o `join_step`. |
| 9 | 3.500 caracteres em um único resumo. | leigo no celular precisa de um tópico por tela | manter o limite, mas entregar por seção (item 5); 4 a 6 tópicos. |

## Mapeamento para o contrato da API
| Endpoint | Tarefas do workflow |
|---|---|
| `POST /documents` | extração do texto (fora do workflow) + fase 1 (T1–T5) + T6 → `clauses` e `memoria_persistente` |
| `POST /documents/{id}/explain` | T7–T13 → `sections` com `quote`, `quote_verified`, `lastro`; `_ui` (T12) → `highlights` |
| `POST /documents/{id}/questions` | T14 adaptado → perguntas abertas com `expected_elements` |
| `POST /sessions/{id}/answers` | **T15 (novo)** |
| `POST /sessions/{id}/chat` | **T16 (novo)** |
| `POST /sessions/{id}/finalize`, `GET /verify/{id}` | fora do LLM: hash canônico, ancoragem, OpenTimestamps |

## Perguntas para alinhar (além das 10 do contrato)
1. O texto do PDF entra inteiro em cada tarefa da fase 1? Qual o limite de páginas que cabe no contexto do modelo?
2. Já existe execução ponta a ponta com um contrato de honorários? Qual foi o resultado das classes processuais?
3. Aceita trocar as 5 classes pelas de contrato hoje, ou prefere um segundo workflow `contrato` ao lado do `processo`?
4. Quem recalcula as posições dos trechos: o serviço ou a interface? Proposta: o serviço, antes de responder.
5. Perguntas abertas com elementos esperados no T14 e as tarefas T15/T16 entram até 15h?
6. Endpoints: o workflow roda por trás dos endpoints do contrato ou expõe um único `POST /run`? A interface precisa dos endpoints por etapa para mostrar progresso.
