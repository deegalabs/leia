# Como o painel do Carlos revisa o resumo estruturado e como o chat usa esse contexto

Leitura de `oabv5 (3)/oab/templates/index.html`, `main.py` e `app_gestao.py` (versão de 13/09, 12h21), feita para
reproduzir o comportamento no app. Referências `arquivo:linha` apontam para essa versão.

## 1. O fluxo "Resumo estruturado" em cinco telas (`index.html:847-925`, `:1849-2080`)

| Tela | O que mostra | De onde vem |
|---|---|---|
| Enviar | PDF ou texto | `POST /api/resumo-estruturado/submit` (`app_gestao.py:257-316`), que manda o arquivo a `api.resumoestruturado.com.br` |
| Status | anel de progresso e eventos do job (`step`, `idx`, `total`, `tokens`, `elapsed`) | `GET /api/resumo-estruturado/{hash}/status` a cada 1,5 s (`index.html:1898-1945`) |
| Resumo | cartões por classe (`classe_i_fatos`, `classe_i_decisao`, `classe_ii_base_legal`, ...): cada item com rótulo = `campo`, `valor`, `sintese_relacao`, selo `score` e botão "Ver no texto" | `GET .../resultado` → `dados_llm.processo.classe_*[]` e `dados_llm._ui[classe][i].score_trecho_verbatim` (`index.html:1483-1512`) |
| Visualizar | texto do documento com os trechos destacados, uma cor por classe; "Ver no texto" troca de tela, rola até o trecho e pulsa | posições `_ui[classe][i].pos_trecho_verbatim` no formato `inicio:fim` (várias separadas por vírgula); `parsePos` descarta `0:0` (`index.html:1404-1416, 1454-1482, 1562-1580`) |
| Dna | seções em markdown leve ("Síntese dos Fatos", "Fundamentos", "Pedidos") | `dados_llm.processo.resposta_final.texto` (`index.html:1978-2010`) |

Pontos que importam para o nosso app:
- O rótulo do item é o `campo` com `_` trocado por espaço; o valor é `valor`; a síntese curta é `sintese_relacao`
  (`index.html:1375-1394`). Sem posição válida, o cartão mostra "sem trecho localizado no texto-fonte" (`:1503`).
- As cores são uma paleta por índice de classe (`HL_PALETTE`, `:1362`). Spans sobrepostos são resolvidos por ordenação
  de pontos de início e fim (`buildHighlightedHtml`, `:1454-1482`).
- Esse fluxo usa a API externa, que devolve posições reais. O pipeline local (14 tarefas na Groq, o que a cidadã usa)
  devolve `pos_trecho_verbatim = "0:0"` em todos os itens; por isso o nosso `GET /api/t/{hash}/inferencias` acha a posição
  procurando o `trecho_verbatim` no `texto_extraido.txt` (ignorando diferenças de espaço) e troca o `score` pelo selo
  "conferido no texto".

## 2. Como o chat usa o resumo estruturado como contexto

Há dois chats no serviço:

**Chat da cidadã** (`POST /api/t/{hash}/chat`, `app_gestao.py:958-1020`): um turno só. O system prompt fixo diz para
usar apenas o contexto, não inventar, linguagem simples, e encaminhar pedidos de conselho ao advogado. O contexto é
`=== RESUMO DO PROCESSO ===` com o `resumo_humanizado.md` (T13) e `=== MEMÓRIA ESTRUTURADA ===` com o
`memoria_persistente.json` (T6) cortado em 12 000 caracteres. Modelo `openai/gpt-oss-120b`, temperatura 0,3, 1 500
tokens, resposta em SSE `data: {"t": ...}` e `data: {"done": true}`. Nada é gravado. É esse chat que o app usa.

**Chat de bastidores** (`POST /api/chat`, `main.py:590-640`): para quem está logado no painel. A memória de sessão
(`core/sessao.py`, arquivo `workspace/_sessoes/{token}.json`) guarda o T6 da última destilação feita pelo fluxo
"Anexar PDF" da mesma sessão; `anexo_compartilhado(token)` devolve `{titulo, processo, hash}` (`core/sessao.py:112-136`)
e o objetivo da pergunta recebe `PROCESSO:` seguido do JSON do T6 (`main.py:606-621`). O agente `RESPOSTA_DOCUMENTO`
(`protocolo.json`) responde só com base nesse processo. `limitar_timeline` (`main.py:207-243`, corrigido na v5) garante
que a pergunta atual nunca é cortada do orçamento de contexto; cada chamada é gravada em
`workspace/{hash}/chat_llm_debug.jsonl` para depuração. Na v5, os fluxos externos (Resumo estruturado e Jurisprudência)
deixaram de alimentar essa memória: só o pipeline local entra no chat.

Consequência para o produto: o chat da cidadã responde com o que está no T6 e no resumo humanizado, não com o texto
integral do PDF; se o T6 não capturou um trecho, o chat "não foi informado". Por isso a revisão do advogado antes de
liberar importa: é onde se vê o que o workflow capturou e concluiu.

## 3. O que aplicamos no app

- `/painel/{id}/revisao` (advogado): abas Marcações (classes, item a item, "Ver no texto", selo conferido), Texto
  (documento com destaques), Conclusões (sínteses T7..T11 com lastro), Explicação (o que a cliente vai ler), Perguntas
  (com a resposta certa marcada) e "Aprovar e liberar para a cliente".
- Estados: `pronta` = pronta para revisão; `enviada` = liberada; a cidadã que abre o link antes vê "O advogado está
  revisando a explicação". Tarefas enviadas pela própria cidadã não passam por revisão.
- Contrato em `docs/API-V3-CONTRACT.md` (seção "Revisão do advogado antes de liberar").
