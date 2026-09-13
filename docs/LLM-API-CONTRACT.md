# Contrato entre a interface e o serviço cognitivo (FastAPI)

Fonte: código do serviço recebido em 13/09 às 10h40 (`temp/src/oab/` na pasta de trabalho: `main.py`, `app_gestao.py`,
`core/`, `templates/`, `protocolo*.json`) e, antes, os templates de 12/09.
A interface da cidadã (`apps/llm-service/templates/leia/cliente.html`) consome **exatamente** essas rotas; o mock em
`apps/llm-service/mock/` as reproduz com dados de exemplo para desenvolver sem o serviço. Base: mesma origem por
padrão; `window.LEIA_API_BASE` aponta para outra origem quando a interface for servida separada (aí o serviço precisa de
CORS para essa origem).

## O que o código do serviço tem hoje (13/09, `app_gestao.py`)
| Rota | O que devolve | Observação |
|---|---|---|
| `GET /t/{hash}` | HTML (`cliente_view.html`) com `tarefa`, `resumo_md`, `questoes`, `ultima_tentativa` | página da cidadã do serviço |
| `POST /api/t/{hash}/quiz` | `{ aprovado, acertos, total, numero, hash_imutavel, erros[] }`; aprova com ≥ 83% (`core/tentativas.py`) | o hash é `sha256("PARA.AI\|tarefa\|numero\|respostas\|ip\|ua\|ts")` |
| `POST /api/t/{hash}/chat` | SSE `data: {"t": ...}` | |
| `GET /api/resumo-estruturado/{hash}/resultado` | JSON `resumo_estruturado.json`: `processo.classe_*[] {campo, sub_tipo, valor, trecho_verbatim}`, `processo.resumo_classe_* {valor, lastro[]}`, `processo.resposta_final.texto` (markdown), `_ui` (posições e score por trecho) | é a fonte natural dos `topicos` |
| `GET /api/resumo-estruturado/{hash}/status`, `GET /api/tarefas/{id}/status`, `GET /api/pdf/{hash}/log` | eventos do job (`log.jsonl`) | página de espera |
| `POST /api/resumo-estruturado/submit`, `POST /api/pdf/destilar`, `POST /tarefas/nova` | criação de tarefa por upload (form) | painel interno |
| `GET /tarefas/{id}/artefato/{nome}` | arquivos do workspace (`resumo_estruturado.json`, `original.pdf`, `log.jsonl`) | |

Mapeamento para o JSON que o app consome (`GET /api/t/{hash}`, a acrescentar no serviço):
- `topicos[]` ← `processo.resumo_classe_*`: `titulo` = rótulo da classe em linguagem simples, `explicacao` = `valor`,
  `trecho` = `lastro[0].trecho_verbatim` (ou o de maior `score_trecho_verbatim` em `_ui`), `clausula` = posição.
- `resumo_md` ← `processo.resposta_final.texto`.
- `questoes[]` ← as 12 questões geradas, sem `correta` e `justificativa`.
- `eventos[]` ← `log.jsonl` (opcional, para a página de espera mostrar "passo n de 14").

## Rotas que o serviço já tem (e a interface usa)
| Método e rota | Entrada | Saída | Uso na interface |
|---|---|---|---|
| `GET /t/{hash}` | | HTML renderizado com o contexto `tarefa {hash, titulo, status}`, `resumo_md` (markdown), `questoes.questoes[]`, `ultima_tentativa` | página da cidadã. O template `leia/cliente.html` usa o mesmo contexto e pode substituir o atual sem mudar a rota |
| `POST /api/t/{hash}/quiz` | `{ "respostas": { "<id>": <índice 0..3> } }` | `{ aprovado, acertos, total, numero, hash_imutavel, erros: [{ id, area, enunciado, escolhida }] }` | envio das respostas; `erros[].enunciado` vira a lista "o que vale ver de novo" |
| `POST /api/t/{hash}/chat` | `{ "mensagem": "..." }` | SSE: `data: {"t": "trecho"}` por token; `data: {"error": "..."}` em falha | dúvida da cidadã, resposta em streaming |
| `GET /t/{hash}/pdf-assinado` | | PDF | substituído pelo comprovante em HTML (abaixo); pode continuar existindo |
| `GET /tarefas/*`, `POST /tarefas/nova`, `/reprocessar`, `/nova-rodada` | | HTML | painel de quem envia o documento; fica como está, só recebe o tema |

Campos do contexto que a interface **não** coloca no HTML da cidadã: `questoes[].correta` e `questoes[].justificativa`
(a avaliação já acontece no servidor em `/quiz`). O template só emite `id`, `enunciado` e `alternativas`.

## Rotas que a interface acrescenta (módulo `leia/registry.py`, uma linha no serviço)
| Método e rota | Saída |
|---|---|
| `GET /t/{hash_imutavel}/comprovante` | HTML: situação, data, código do registro (SHA-256 do JSON canônico), QR para `/verify/...`, o que prova e o que não prova |
| `GET /verify/{hash_imutavel}` | HTML público: JSON canônico, hash, prova OpenTimestamps se existir, passos para conferir; `?format=json` devolve `{ payload, canonical, payloadHash, otsPresent }` |
| `GET /verify/{hash_imutavel}/proof.ots` | prova OpenTimestamps (binária) |

O serviço fornece só um adaptador: `get_attempt(hash_imutavel) -> dict | None` com `tarefa_hash, numero, acertos,
total, aprovado, criada_em, salt` e, opcionalmente, `ots` (bytes gravados após `ots_stamp`). Nada pessoal entra no
JSON canônico (`docs/../SPEC-001` na pasta de trabalho).

## Dois insumos que fariam a interface ficar completa (validação, não correção)
1. **`GET /api/t/{hash}` em JSON** com `tarefa, resumo_md, topicos, questoes (sem correta/justificativa), ultima_tentativa`.
   Hoje a página é renderizada no servidor e isso basta; o JSON só é necessário se a interface for servida em outra origem
   ou para o app pós-hackathon. O mock já responde nesse formato.
2. **`topicos[]` com lastro** no contexto da página: `{ id, titulo, explicacao, trecho, clausula }`, vindos das sínteses com
   `lastro` da fase 3 do workflow e do mapa `_ui`. Com isso a cidadã vê "um ponto por vez" com o botão "Ver o trecho
   original". Sem `topicos`, a interface divide o `resumo_md` pelos títulos `##` e funciona igual, só sem o trecho literal.

## Perguntas para o dono do serviço (para fechar a integração)
1. URL onde o serviço vai rodar durante a auditoria (laptop local ou nuvem) e comando para subir.
2. A resposta de `/quiz` já traz `erros[].enunciado`? (o template atual usa; o mock usa).
3. Formato exato dos eventos SSE de `/chat`: `data: {"t": ...}` e fim por fechamento da conexão, correto?
4. `tarefa.status` durante o processamento: quais valores existem ("concluida" é o final?) para a página de espera.
5. Onde ficam os prompts do workflow no código, para apontar em `prompts/workflow/`.
