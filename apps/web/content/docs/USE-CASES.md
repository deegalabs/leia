# Casos de uso

Atualizado em 13/09/2026 com o produto no ar (v3: contas, painéis, revisão do advogado, dúvidas, comprovante). Os
diagramas usam as rotas e os estados reais do serviço (`docs/API-V3-CONTRACT.md`); a página de documentação do app
desenha cada um e oferece tela cheia.

## Personas
| Persona | Quem é | O que precisa | Como mede sucesso |
|---|---|---|---|
| **Cidadã** (usuária principal) | pessoa que recebeu um documento jurídico (procuração, contrato de honorários, acordo, petição, decisão); baixa escolaridade; celular básico; prefere ouvir a ler; hoje pesquisa no Google ou cola o documento e seus dados no ChatGPT; medo de golpe e de decidir errado | entender o documento antes de decidir, em ambiente seguro, com direito a perguntar, recusar e falar com o advogado | chega ao comprovante em menos de 4 minutos sem instrução; explica com as próprias palavras o que recebeu |
| **Advogado** (supervisão) | pequeno escritório, dativo, Defensoria, núcleo de prática; pouco tempo; dever de informar (CED art. 9º e 48) | revisar o que a assistente extraiu e concluiu, liberar a explicação, ver dúvidas e respostas e ter o registro de que o esclarecimento ocorreu | pendências claras; registro gerado; nada dito pela IA sem trecho do documento |
| **Verificador** | auditor da OAB, juiz, a própria cidadã meses depois | conferir que o registro é íntegro e datado, sem depender do sistema | recalcula o hash e encontra o carimbo de tempo público |

Atores: **Cidadã** (usuária principal; abre o link do advogado sem cadastro, ou cria conta e envia o próprio documento),
**Advogado** (supervisão; conta com papel `advogado`), **Fornecedor** (admin do serviço; vê tudo), **Verificador**
(qualquer pessoa com o QR), **Auditor** (banca da OAB), **Sistema** (app web na Vercel + serviço FastAPI no Railway +
LLM na Groq + calendários OpenTimestamps).

## Diagrama de casos de uso

```mermaid
flowchart LR
  C([Cidadã])
  A([Advogado])
  V([Verificador])
  AU([Auditor])
  subgraph LeIA
    direction TB
    UC01(["UC-01 Entrar ou criar conta"])
    UC02(["UC-02 Enviar o documento"])
    UC03(["UC-03 Acompanhar a preparação"])
    UC04(["UC-04 Revisar e liberar a explicação"])
    UC05(["UC-05 Percorrer o documento"])
    UC06(["UC-06 Tirar dúvida com a assistente"])
    UC07(["UC-07 Encaminhar dúvida ao advogado"])
    UC08(["UC-08 Conferir o entendimento"])
    UC09(["UC-09 Receber o comprovante"])
    UC10(["UC-10 Verificar o comprovante"])
    UC11(["UC-11 Acompanhar documentos e responder dúvidas"])
    UC12(["UC-12 Auditar a fidelidade"])
  end
  C --> UC01 & UC02 & UC03 & UC05 & UC06 & UC08 & UC11
  A --> UC01 & UC02 & UC03 & UC04 & UC11
  V --> UC10
  AU --> UC12
  UC06 -. estende .-> UC07
  UC08 -. gera .-> UC09
  UC09 -. QR .-> UC10
  UC07 -. chega em .-> UC11
```

| # | Caso de uso | Ator | Como funciona hoje | Situação |
|---|---|---|---|---|
| UC-01 | Entrar ou criar conta | Cidadã, advogado | `/entrar`: e-mail e senha; cadastro aberto para cidadã e, com `ADVOGADO_SIGNUP=true`, para advogado; token Bearer guardado no navegador | no ar |
| UC-02 | Enviar o documento | Advogado ou cidadã | `/enviar`: título e PDF (limite `MAX_UPLOAD_MB`, assinatura `%PDF` conferida); a tarefa nasce `criada` e entra na fila | no ar |
| UC-03 | Acompanhar a preparação | Quem enviou; cidadã com o link | 14 etapas com estado e tempo, texto já marcado e score, atualizados enquanto o serviço processa | no ar |
| UC-04 | Revisar e liberar a explicação | Advogado | `/painel/{id}/revisao`: abas Marcações, Texto, Conclusões, Explicação e Perguntas; "Aprovar e liberar" muda `pronta` para `enviada` e libera o link | no ar; documentos enviados pela cidadã não passam por revisão |
| UC-05 | Percorrer o documento | Cidadã | `/t/{hash}`: boas-vindas com o que a assistente faz e não faz, um tópico por vez com o trecho original ao lado, botão Ouvir | no ar |
| UC-06 | Tirar dúvida com a assistente | Cidadã | gaveta "Tenho uma dúvida": resposta em fluxo, só com o que está no documento; fora dele, recusa explícita | no ar |
| UC-07 | Encaminhar dúvida ao advogado | Cidadã | botão na gaveta leva a pergunta e o contexto do chat ao painel do advogado; só quando o documento tem advogado | no ar |
| UC-08 | Conferir o entendimento | Cidadã | perguntas de múltipla escolha, uma por tela; sem nota exibida; se não passou, a assistente explica de novo e repete (nova tentativa) | no ar; perguntas abertas com rubrica 0 a 3: roadmap |
| UC-09 | Receber o comprovante | Cidadã | tentativa aprovada gera o registro: JSON canônico sem dados pessoais, SHA-256, carimbo OpenTimestamps, comprovante com QR | no ar; ancoragem em rede pública (Polygon): roadmap |
| UC-10 | Verificar o comprovante | Verificador | `/verify/{hash}`: recalcula o hash, mostra o JSON canônico, o carimbo e a prova `.ots` para baixar | no ar |
| UC-11 | Acompanhar documentos e responder dúvidas | Advogado; cidadã no próprio painel | `/painel`: lista com status, origem, última tentativa e dúvidas abertas; `/painel/{id}`: eventos, tentativas, dúvidas e resposta | no ar |
| UC-12 | Auditar a fidelidade | Auditor | roteiro em `docs/AUDIT-GUIDE.md`; testes `tests_leia.py` e `tests_v3.py`; artefatos de cada etapa em `workspace/{hash}` (T1 a T14, log por etapa) | roteiro pronto |

Fora de escopo no hackathon: assinatura eletrônica do documento, identificação forte (gov.br), múltiplos escritórios,
cobrança. Ver `docs/ROADMAP.md`.

## Estados de um documento (tarefa)

```mermaid
stateDiagram-v2
  [*] --> criada : POST /api/tarefas
  criada --> processando : extração do texto
  processando --> pronta : 14 etapas concluídas
  processando --> falhou : erro em uma etapa
  pronta --> enviada : advogado aprova (origem advogado)
  pronta --> assinada : cidadã aprovada nas perguntas (origem cidadã)
  enviada --> assinada : cidadã aprovada nas perguntas
  assinada --> [*]
  note left of pronta : Com advogado, GET /api/t/{hash} devolve status revisao e as rotas da cidadã respondem 409
```

## Diagramas de sequência

### UC-01. Entrar ou criar conta
```mermaid
sequenceDiagram
  actor U as Cidadã ou advogado
  participant W as App web (Vercel)
  participant S as Serviço (FastAPI, Railway)
  participant DB as Postgres
  U->>W: /entrar com e-mail e senha (nome e papel no cadastro)
  W->>S: POST /api/auth/cadastro ou POST /api/auth/login (limite por IP)
  S->>DB: cria ou confere o usuário
  S-->>W: token e usuário (papel cidadao, advogado ou fornecedor)
  W->>W: guarda o token (localStorage leia:auth)
  W-->>U: painel ou a página que pediu login
  Note over W,S: As chamadas seguintes levam Authorization: Bearer token. Um login novo invalida o token anterior.
```

### UC-02 e UC-03. Enviar o documento e acompanhar a preparação
```mermaid
sequenceDiagram
  actor A as Advogado ou cidadã
  participant W as App web
  participant S as Serviço
  participant P as Pipeline (14 etapas)
  participant L as LLM (Groq, gpt-oss-120b)
  A->>W: /enviar com título e PDF
  W->>S: POST /api/tarefas (multipart, Bearer)
  S->>S: confere tamanho e assinatura %PDF, cria a tarefa (status criada)
  S-->>W: id, hash, status criada
  S-)P: agenda a tarefa (semáforo PIPELINE_CONCURRENCY)
  P->>P: extrai o texto (texto_extraido.txt), status processando
  loop T1 a T14
    P->>L: prompt da etapa com o texto (o documento é dado, nunca instrução)
    L-->>P: JSON da etapa com o trecho literal de cada informação
    P->>P: grava Tn.json e a linha da etapa em log.jsonl
  end
  P->>P: memoria_persistente, texto_tagueado, resumo_humanizado.md, questoes.json (alternativas embaralhadas)
  P->>S: status pronta (ou falhou se uma etapa deu erro)
  loop enquanto criada ou processando
    W->>S: GET /api/t/{hash} e GET /api/t/{hash}/inferencias (parcial)
    S-->>W: etapas com estado e tempo, texto e marcações já encontradas
    W-->>A: tela de preparação: as 14 etapas, o documento sendo marcado e o score
  end
```

Etapas: T1 partes, T2 datas e valores, T3 fatos, T4 fundamentos, T5 pedidos, T6 fusão da memória, T7 a T11 sínteses
(fatos, fundamentos, pedidos, quem é quem, contexto), T12 marcação do texto, T13 explicação em linguagem simples,
T14 perguntas.

### UC-04. Revisar e liberar a explicação (advogado)
```mermaid
sequenceDiagram
  actor A as Advogado
  participant W as App web
  participant S as Serviço
  A->>W: /painel/{id}/revisao
  W->>S: GET /api/tarefas/{id}/revisao (Bearer, dono ou admin)
  S-->>W: marcações (classes com trecho e posição no texto), texto, sínteses, explicação, perguntas com gabarito
  W-->>A: abas Marcações, Texto, Conclusões, Explicação e Perguntas
  Note over W,S: Enquanto a tarefa está pronta e tem advogado, GET /api/t/{hash} devolve status revisao e as rotas da cidadã respondem 409.
  A->>W: Aprovar e liberar
  W->>S: POST /api/tarefas/{id}/aprovar
  S->>S: pronta para enviada, evento aprovada
  S-->>W: ok, status enviada
  W-->>A: link da cliente (/t/{hash}) para copiar e enviar
```

### UC-05, UC-06 e UC-07. Percorrer o documento, tirar dúvida e encaminhar ao advogado (cidadã)
```mermaid
sequenceDiagram
  actor C as Cidadã
  participant W as App web
  participant S as Serviço
  participant L as LLM
  C->>W: abre /t/{hash} (link do advogado ou documento próprio)
  W->>S: GET /api/t/{hash}
  alt criada ou processando
    S-->>W: etapas em andamento
    W-->>C: preparação visível (UC-03)
  else revisao (advogado ainda não liberou)
    S-->>W: status revisao, sem explicação
    W-->>C: o advogado está revisando, volte em breve
  else pronta, enviada ou assinada
    S-->>W: explicação, tópicos com trecho original, perguntas sem gabarito, eventos públicos
  end
  opt cidadã logada
    W->>S: POST /api/t/{hash}/vincular
    S-->>W: ok (o documento aparece no painel dela)
  end
  W-->>C: boas-vindas com o que a assistente faz e não faz
  loop um tópico por vez
    W-->>C: texto simples, trecho original, botão Ouvir
    opt Tenho uma dúvida
      C->>W: pergunta na gaveta
      W->>S: POST /api/t/{hash}/chat (SSE, limite por IP)
      S->>L: system prompt com o resumo humanizado e a memória do documento
      L-->>S: resposta em fluxo
      S-->>W: data com trechos, depois done
      W-->>C: resposta, ou "isso não está no documento"
      opt Enviar esta dúvida para o advogado (só com advogado)
        W->>S: POST /api/t/{hash}/duvida (texto e contexto do chat)
        S-->>W: id e criada_em (409 se o documento não tem advogado)
        W-->>C: sua dúvida foi para o advogado
      end
    end
  end
```

### UC-08 e UC-09. Conferir o entendimento e receber o comprovante (cidadã)
```mermaid
sequenceDiagram
  actor C as Cidadã
  participant W as App web
  participant S as Serviço
  participant O as OpenTimestamps (calendários públicos)
  C->>W: responde às perguntas, uma por tela
  W->>S: POST /api/t/{hash}/quiz (respostas, limite por IP)
  S->>S: corrige, cria a tentativa n (acertos, total, aprovado por QUIZ_PASS_RATIO) e o hash_imutavel
  alt aprovada
    S->>S: status assinada, evento assinada
    S-)S: stamp_attempt em segundo plano
    S->>S: payload sem dados pessoais, JSON canônico (chaves ordenadas, sem espaços), SHA-256
    S->>O: submit(digest) em cada calendário (8 s de limite)
    O-->>S: prova tentativa_n.ots
    S-->>W: aprovado, acertos, total, comprovante
    W-->>C: Entendimento registrado, botão Ver comprovante
    C->>W: /comprovante/{token}
    W-->>C: código, data, QR para /verify/{hash_imutavel}, o que o comprovante prova e o que não prova
  else não aprovada
    S-->>W: acertos, total e quais perguntas erraram (sem a resposta certa)
    W-->>C: Vamos ver de novo: explica de novo e repete as perguntas (nova tentativa)
  end
```

### UC-10. Verificar o comprovante (verificador)
```mermaid
sequenceDiagram
  actor V as Verificador
  participant W as App web
  participant S as Serviço
  V->>W: lê o QR ou abre /verify/{hash_imutavel}
  W->>S: GET /verify/{hash}?format=json
  S->>S: monta o payload da tentativa, recalcula o JSON canônico e o SHA-256
  S-->>W: payload, canonical, payload_hash, carimbo (prova presente ou pendente)
  W-->>V: hash confere ou não, data, prova para baixar (/verify/{hash}/proof.ots)
  V->>V: pode recalcular o SHA-256 do JSON canônico por conta própria
```

### UC-11. Acompanhar documentos e responder dúvidas (advogado; cidadã no próprio painel)
```mermaid
sequenceDiagram
  actor A as Advogado
  participant W as App web
  participant S as Serviço
  actor C as Cidadã
  A->>W: /painel
  W->>S: GET /api/tarefas (Bearer)
  S-->>W: tarefas com status, origem, última tentativa, dúvidas abertas e link_cliente
  A->>W: abre um documento (/painel/{id})
  W->>S: GET /api/tarefas/{id}
  S-->>W: tarefa, eventos (20 últimos), tentativas, dúvidas com o contexto do chat
  loop enquanto o documento não está concluído
    W->>S: GET /api/tarefas/{id}
  end
  opt dúvida aberta
    A->>W: escreve a resposta
    W->>S: POST /api/tarefas/{id}/duvidas/{duvida_id}/responder
    S-->>W: ok (respondida, respondida_em)
    C->>W: /painel/{id} (documento vinculado à conta dela)
    W-->>C: pergunta, contexto e resposta do advogado
  end
```

### Fluxo externo "Resumo estruturado" (sem as 14 etapas)
```mermaid
sequenceDiagram
  actor A as Advogado
  participant G as Painel interno do serviço
  participant S as Serviço
  participant E as api.resumoestruturado.com.br
  participant W as App web
  actor C as Cidadã
  A->>G: envia o PDF e pede o Resumo estruturado
  G->>S: job externo
  S->>E: envia o documento e consulta o status até concluir
  E-->>S: resumo_estruturado.json (classes com posições e scores, resposta_final)
  Note over S: Esse fluxo não roda as 14 etapas: não há resumo humanizado nem perguntas.
  A->>C: envia o link /t/{hash}
  C->>W: abre o link
  W->>S: GET /api/t/{hash}
  S-->>W: resposta_final como explicação, classes como tópicos com score, sem_perguntas
  W-->>C: explicação e tópicos, a jornada termina sem perguntas e sem comprovante
```

### UC-12. Auditar a fidelidade
Sem diagrama: o auditor segue `docs/AUDIT-GUIDE.md` (perguntas fora do documento, PDF com instrução escondida,
resposta vaga), roda `tests_leia.py` e `tests_v3.py` no serviço e lê, por documento, os artefatos de cada etapa em
`workspace/{hash}` (T1 a T14, `log.jsonl`, `memoria_persistente.json`, `texto_tagueado.json`, `questoes.json`,
`tentativa_n.ots`).
