# Arquitetura de informação

## Mapa de rotas

```
/                              → redireciona: cidadã logada → /c; advogado logado → /lawyer; senão → /lawyer/login
/c                             CH  Meus documentos (cidadã, após login)
/c/{token}/login               C0  Entrar
/c/{token}                     C1  Início
/c/{token}/topics/{n}          C2  Tópico n de N
/c/{token}/ask                 C3  Dúvida (volta para o tópico de origem via ?from={n})
/c/{token}/questions/{k}       C4  Conferindo k de K
/c/{token}/confirm             C5  Confirmação
/c/{token}/receipt             C6  Comprovante
/lawyer/login                  A0  Entrar (Google) + primeiro acesso
/lawyer                        A4  Painel do advogado
/lawyer/new                    A1  Enviar documento
/lawyer/documents/{id}         A2  Revisar e aprovar
/lawyer/sessions/{id}          A3  Validar
/verify/{id}                   P1  Verificação pública
```

Regras de guarda:

- `/c/{token}/*` exige token válido. Se a sessão está ligada a uma conta Google e a cidadã não está logada, redireciona para C0.
- `/c/{token}` com sessão já iniciada redireciona para a última posição salva (`resume_path` em `GET /sessions/{id}`).
- `/lawyer/*` exige conta com nome + OAB/UF completos; senão A0 abre o passo de cadastro.
- `/verify/{id}` é público, sem cookies, indexável com `noindex` (não há por que aparecer em busca).

## Fluxo principal da cidadã (linear, com desvios)

```
C0 entrar → C1 início → C2 tópico 1 … C2 tópico N → C4 pergunta 1 … C4 pergunta K → C5 confirmação → C6 comprovante
                         ↕ C3 dúvida (a partir de qualquer C2; volta para o mesmo tópico)
                                                                        ↕ C5 "Quero rever uma parte" → C2 tópico n → volta a C5
```

Ordem decidida: todos os tópicos antes das perguntas. Cada C4 começa com uma frase-lembrete do essencial do tópico (regra cognitiva: repetir o essencial antes de perguntar).

## Fluxo do advogado

```
A0 entrar → A4 painel → A1 enviar (pipeline por etapas) → A2 revisar e aprovar → (link gerado) → A4 acompanhar → A3 validar → registro
```

## Objetos e estados

### Documento (`document`)

| Estado backend | Rótulo no painel (A4) | Ação |
|---|---|---|
| `processing` | processando | ver etapas (A1) |
| `review` | aguardando revisão | Revisar (A2) |
| `approved` | link enviado | Copiar link |

### Sessão (`session`)

| Estado backend | Rótulo advogado (A4/A3) | Rótulo cidadã (CH) | Ação principal |
|---|---|---|---|
| `created` | link enviado | a começar | cidadã: Começar |
| `in_progress` | em andamento | em andamento | cidadã: Continuar |
| `confirmed` | aguardando validação | entendido | advogado: Validar |
| `finalized` + `anchor == null` | registrado (carimbo pendente) | comprovante disponível | Ver comprovante |
| `finalized` + `anchor` | registrado | comprovante disponível | Ver comprovante |

Uma linha do painel A4 representa um documento; quando existe sessão, a linha mostra o estado da sessão.

### Seção / tópico (`section`)

`{ id, order, icon, title, plain_text, essential, quote, clause_ref, quote_verified, lastro: { judge: "fiel" | "revisar", notes }, audio_url? }`

- `essential` = uma frase (≤ 15 palavras) usada em C4 (lembrete) e C5 (resumo).
- `quote_verified` = citação encontrada literalmente no texto do PDF.

### Pergunta (`question`)

`{ id, order, section_id, text, expected_elements[], max_attempts: 2 }`

### Resposta (`answer`)

`{ question_id, attempt, text, input_mode: "voice" | "text", score 0–3, matched[], missing[], feedback_for_client, re_explanation }`

Rubrica em palavras (usada em A3, nunca mostrada à cidadã):

| Situação | Rótulo |
|---|---|
| score 3 na 1ª tentativa | entendeu e citou a consequência |
| score 2 na 1ª tentativa | entendeu o essencial |
| score ≥ 2 na 2ª tentativa | entendeu na 2ª tentativa |
| score < 2 nas 2 tentativas | pendente: conversar com a cliente |
| "Não sei, explica de novo" (não conta tentativa, 1 por pergunta) | pediu nova explicação |

### Dúvida (`chat`)

`{ id, section_id, question_text, answer_text, quote, refused: bool, refusal_kind: "fora_do_documento" | "conselho" | null }`

Toda dúvida com `refused = true` vira pendência para o advogado.

### Pendência (`pending`)

Tipos: `question_pending` (2 tentativas insuficientes), `doubt_refused` (dúvida fora do documento ou pedido de conselho), `note` (recado pela folha "Falar com o advogado", V2).

### Registro (`record`)

`{ session_id, payload_hash (sha256 hex), canonical_json, anchor: { tx_hash, explorer_url, block_time } | null, validated_at }`

O JSON canônico não contém nome, documento, respostas nem dúvidas. Conteúdo proposto (confirmar com backend, ver INDEX › Pendências): versão do esquema, `session_id`, `document_type`, `document_sha256`, `topics_count`, `questions[] { id, outcome, attempts }`, `confirmed_at`, `validated_at`.

## Persistência local (PWA da cidadã)

- Service worker (Workbox): cache das rotas `/c/{token}/*` e do payload de `GET /sessions/{id}` após o primeiro carregamento; áudios (V2) em cache sob demanda.
- Fila de envio (IndexedDB): `POST /sessions/{id}/answers`, `POST /sessions/{id}/chat`, `POST /sessions/{id}/confirm`. Reenvio automático ao voltar a conexão; banner de estado (ver navigation.md).
- Progresso (`resume_path`, respostas rascunho, transcrições não enviadas) salvo a cada mudança.
