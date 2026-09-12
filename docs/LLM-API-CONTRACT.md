# Contrato da API do serviço de LLM (FastAPI)

Proposta da interface para o serviço. Vale até o dono do serviço confirmar ou ajustar. JSON, UTF-8, `snake_case`.
Base: `http://localhost:8000/api/v1`. Sem autenticação na PoC (rede local); CORS liberado para a origem da interface.
Erros: `{ "error": { "code": "...", "message": "..." } }` com HTTP 4xx/5xx.

## Endpoints mínimos para a V1 (texto)
| Método e rota | Entrada | Saída | Usado por |
|---|---|---|---|
| `GET /health` | | `{ "status": "ok", "models": [...] }` | interface, auditor |
| `POST /documents` | `multipart/form-data`: `file` (PDF com texto), `document_type` (`procuracao` \| `contrato_honorarios` \| `acordo`) | `{ document_id, pages, clauses: [{ clause_id, index, page, text }] }` | tela do advogado |
| `POST /documents/{document_id}/explain` | `{ }` | `{ sections: [{ section_id, order, clause_id, title, plain_text, why_it_matters, quote, quote_verified, risk_level }], prompt_version, model }` | tela do advogado (revisão) e do cliente (tópicos) |
| `POST /documents/{document_id}/questions` | `{ "n": 3 }` | `{ questions: [{ question_id, clause_id, question, expected_elements: [...] }] }` (`expected_elements` só para o advogado) | tela do advogado |
| `POST /sessions` | `{ document_id, lawyer_id, question_ids: [...] }` | `{ session_id, client_token }` | tela do advogado (aprovar e gerar link) |
| `GET /sessions/{session_id}` | | `{ status, document_type, sections, questions (sem expected_elements), answers, pending_for_lawyer }` | ambas |
| `POST /sessions/{session_id}/answers` | `{ question_id, answer_text, attempt }` | `{ score: 0..3, matched_elements, missing_elements, feedback_for_client, re_explanation }` | tela do cliente |
| `POST /sessions/{session_id}/chat` | `{ message }` | `{ answer, clause_id, quote, refused: bool }` (`refused=true` → `answer` = `NAO_ESTA_NO_DOCUMENTO`) | tela do cliente |
| `POST /sessions/{session_id}/confirm` | `{ }` | `{ status: "confirmed" }` | tela do cliente |
| `POST /sessions/{session_id}/validate` | `{ approved: bool, notes }` | `{ status: "validated" }` | tela do advogado |
| `POST /sessions/{session_id}/finalize` | `{ }` | `{ payload, canonical, payload_hash, anchor: { chain_id, tx_hash, explorer_url, block_time, ots_pending } \| null }` | tela do advogado |
| `GET /verify/{session_id}` | | `{ payload_hash, canonical, anchor, validation_summary }` (público) | página de verificação |

## Endpoints da V2
| Método e rota | Entrada | Saída |
|---|---|---|
| `POST /tts` | `{ text }` | áudio (`audio/mpeg`) |
| `POST /stt` | `multipart`: `audio` | `{ text }` |
| `POST /sessions/{id}/chat` com `Accept: text/event-stream` | idem | resposta em streaming (opcional) |

## Regras que a interface assume
1. Toda `section` tem `quote` presente no texto da cláusula (`quote_verified = true`); se `false`, a interface não exibe a seção.
2. `expected_elements` nunca chega à tela do cliente (o serviço omite em `GET /sessions/{id}` para `client_token`).
3. `score < 2` devolve `re_explanation` e a mesma pergunta é repetida; na segunda tentativa insuficiente, o serviço marca `pending_for_lawyer`.
4. `finalize` só funciona após `validate` com `approved = true`.
5. O serviço grava `logs/citations.jsonl` e `logs/judge.jsonl` (auditoria) e expõe `prompt_version` em toda resposta gerada.

## Perguntas ao dono do serviço (responder hoje até 13h30)
1. Quais desses endpoints já existem ou existirão até 15h? Quais nomes/campos mudam?
2. Comando para subir o serviço, porta, variáveis de ambiente e chave de modelo usada.
3. O parse aceita PDF ou só texto? Qual o limite de páginas? PDF escaneado é recusado?
4. A explicação devolve `quote` e `clause_id` por seção e verifica a substring? Se não, quando entra?
5. A rubrica 0 a 3 e a re-explicação estão no serviço ou a interface precisa fazer o loop?
6. Recusa literal `NAO_ESTA_NO_DOCUMENTO` implementada? Qual o tratamento de pergunta fora do documento?
7. Hash, canonicalização e ancoragem ficam no serviço (Python: `hashlib`, `rfc8785`, `web3`, `opentimestamps-client`) ou na interface? Proposta: no serviço.
8. Latência esperada por chamada; precisa de streaming na V1?
9. Onde ficam os prompts? Precisam estar em `prompts/` com `name` e `version` (auditoria da Dimensão 3).
10. O que precisa de nós: PDFs de exemplo, banco de perguntas, rubrica, glossário, base de referência.
