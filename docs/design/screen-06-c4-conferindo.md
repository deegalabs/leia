# C4 · Conferindo k de K — `/c/{token}/questions/{k}`

## Propósito e posição no fluxo

Teach-back: a cidadã explica com as próprias palavras um ponto essencial; a rubrica (0–3) decide se seguimos ou se "vemos de novo". Máximo 2 tentativas por pergunta; depois o ponto fica pendente para o advogado e a cidadã segue. Entrada: último C2 ou pergunta anterior. Saída: próxima pergunta; na última, C5. Layout idêntico em todas as perguntas.

## Layout (mobile-first, 360×740)

```
[AssistantBanner — Dr. João Silva]
[main]
  ProgressSteps  "Conferindo 1 de 3"  ▮▯▯
  Card lembrete (fundo #EAF4F4, 15 px)
    "Lembrando: o advogado fica com 30% só se você ganhar."     (= section.essential)
  h1 "Para eu ter certeza de que expliquei bem:"                 19 px, peso normal
  h2 "Se você ganhar a causa, quanto do dinheiro fica com o advogado?"   22 px semibold
  p  "Pode responder com suas palavras."                          17 px
  [▶ Ouvir a pergunta]  (ghost 48 px)
  RecordButton ● 64 px, rótulo "Gravar minha resposta"
  Textarea rótulo "Ou escreva aqui"                               17 px, 3 linhas
  (após gravar) TranscriptEditor "Confira o que você disse"
  ── estado de feedback substitui o bloco de resposta (ver Estados) ──
[BottomActionBar]
  [Enviar resposta]              primário 52 px (desabilitado sem texto)
  [Não sei, explica de novo]     secundário 48 px
```

## Componentes (shadcn/ui)

`Card`, `Textarea`, `Button`, `Dialog` (consentimento, se ainda não dado), `Skeleton`, `Alert`; novos: `ProgressSteps`, `RecordButton`, `TranscriptEditor`, `FeedbackCard`, `QuoteDisclosure`, `AudioPlayer`, `AssistantBanner`, `BottomActionBar`.

## Copy exata (pt-BR)

- Progresso: "Conferindo 1 de 3"
- Lembrete: "Lembrando: o advogado fica com 30% só se você ganhar."
- Enquadramento (fixo): "Para eu ter certeza de que expliquei bem:"
- Pergunta (exemplo): "Se você ganhar a causa, quanto do dinheiro fica com o advogado?" + "Pode responder com suas palavras."
- Botões: "Ouvir a pergunta" · "Gravar minha resposta" / "Parar de gravar" · "Enviar resposta" · "Não sei, explica de novo" · "Próxima pergunta" · "Ver o resumo" (última) · "Responder de novo"
- Feedback "isso mesmo" (score ≥ 2): "Isso mesmo. O advogado fica com 30% só se você ganhar." (frase gerada em `feedback_for_client`, ≤ 15 palavras)
- Feedback "vamos ver de novo" (1ª tentativa, score < 2), h3 "Vamos ver de novo", duas partes:
  - "O que você acertou": "Você acertou que o advogado recebe uma parte só se ganhar."
  - "Uma coisa está diferente no documento": "A parte é de 30%, não de 10%. Se você receber R$ 10.000, R$ 3.000 ficam com o advogado e R$ 7.000 com você."
  - Repetição: "Pode me dizer de novo, com suas palavras, quanto fica com o advogado se você ganhar?"
- Após 2ª tentativa insuficiente: "Vou deixar este ponto marcado para o Dr. João conversar com você. Podemos seguir para o próximo tópico." Botão "Seguir para a próxima" (última: "Ver o resumo").
- "Não sei": h3 "Tudo bem. Vamos ver de novo." + texto simples do tópico + trecho original + a mesma pergunta.
- Microfone negado: "Sem microfone, tudo bem. Você pode escrever sua resposta aqui."

Palavras proibidas em qualquer feedback: errado, incorreto, reprovado, nota, teste, prova, quiz, "tente novamente" sozinho, "você não entendeu". O front bloqueia a exibição se `feedback_for_client` contiver uma delas e mostra o texto de fallback "Vamos ver de novo" + `re_explanation`.

## Estados

**Default** — pergunta k, tentativa 1, campo vazio.

**Vazio** — sessão sem perguntas (advogado escolheu 0; A2 impede): pula direto para C5 com toast "Sem perguntas nesta explicação."

**Carregando (conferindo)** — botão "Conferindo sua resposta…" com spinner; campo desabilitado; `aria-busy`; anúncio "Conferindo sua resposta". Nunca mostra número.

**Erro** — `Alert`: "Deu um problema do nosso lado, não foi você. Estamos tentando de novo." Resposta permanece no campo; botão "Enviar de novo".

**Sem conexão** — resposta entra na fila com "Sua resposta está salva. Eu confiro quando a internet voltar."; botão primário vira "Seguir para a próxima" (a conferência acontece depois; se insuficiente, a pergunta reaparece em C5 como "para ver de novo").

**Feedback: isso mesmo** — `FeedbackCard kind=right`: check verde + frase; primário "Próxima pergunta"/"Ver o resumo".

**Feedback: vamos ver de novo** — `FeedbackCard kind=again` em duas partes + nova explicação (`re_explanation`, com trecho original aberto) + a mesma pergunta repetida abaixo com novo campo/microfone. Primário "Enviar resposta". Secundário some (só 1 tentativa extra).

**Feedback: pendente** — `FeedbackCard kind=pending` âmbar com o texto do Dr. João; primário "Seguir para a próxima".

## Interações

- Gravação idêntica a C3 (consentimento, cronômetro, transcrição editável, Space/Esc).
- "Enviar resposta" → `POST /sessions/{id}/answers` → conforme `score`: ≥ 2 → "isso mesmo"; < 2 e `attempt = 1` → "vamos ver de novo" (card desliza 200 ms, foco no h3); < 2 e `attempt = 2` → "pendente".
- "Não sei, explica de novo" → não consome tentativa; permitido 1 vez por pergunta; mostra a nova explicação e repete a pergunta; na 2ª vez o botão já não aparece.
- "Próxima pergunta" → `questions/{k+1}`; "Ver o resumo" → C5.
- Voltar do sistema em estado de feedback → não repete envio; volta para a pergunta anterior já respondida em modo leitura (mostra a resposta dada e o resultado), sem reenviar.

## Acessibilidade

- Foco no h1 ao entrar; anúncio "Conferindo 1 de 3" + enquadramento + pergunta (h1 e h2 lidos em sequência).
- Ordem: banner → progresso → lembrete → h1 → h2 → p → ouvir a pergunta → microfone → Textarea → transcrição → barra.
- Microfone 64 px `aria-pressed`; live region "Gravando, 12 segundos"; ao parar, foco em "Confira o que você disse".
- Feedback em `role="status"`; a nova explicação recebe foco no seu h3 ("Vamos ver de novo"); a pergunta repetida é um novo h2 com o mesmo texto.
- Duas partes do feedback com ícones distintos (check verde / seta âmbar) + títulos de texto.
- Sem tempo limite; sem cronômetro de resposta.
- 200 %: lembrete e feedback refluem; microfone mantém 64 px.

## Chamadas de API

- `GET /sessions/{id}` (cache) → `questions[k] { id, text, section_id }`, `sections[section_id].essential`.
- `POST /sessions/{id}/answers` `{ question_id, attempt, text, input_mode }` → `{ score, matched[], missing[], feedback_for_client, re_explanation }`.
- Voz: V1 `SpeechRecognition`; V2 `POST /stt`. Áudio da pergunta: V1 `speechSynthesis`; V2 `audio_url` da pergunta ou `POST /tts`.

## O que muda na V1 / V2 / Produto

- **V1:** rubrica síncrona; `re_explanation` = texto simples do tópico + trecho; fila offline só guarda e reenvia.
- **V2:** `re_explanation` gerada a partir de `missing[]` (explica só o que faltou); STT servidor; conferência offline adiada com reaparecimento em C5.
- **Produto:** perguntas adaptativas por tipo de documento; opção de o advogado ouvir o áudio original (com consentimento explícito da cidadã); métrica de "entendeu na 1ª" por escritório.
