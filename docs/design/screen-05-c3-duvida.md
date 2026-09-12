# C3 · Dúvida — `/c/{token}/ask?from={n}`

## Propósito e posição no fluxo

A cidadã pergunta com as próprias palavras, por voz ou texto. A assistente responde só com o que está no documento, sempre com a citação; fora do documento ou pedido de conselho, recusa e anota para o advogado. Entrada: "Tenho uma dúvida" em C2 (ou C4). Saída: "Voltar ao tópico" (mesmo tópico de origem). Várias dúvidas seguidas na mesma tela.

## Layout (mobile-first, 360×740)

```
[AssistantBanner — Dr. João Silva]
[main]
  p  "Sobre: Quanto você paga"                                     15 px muted (tópico de origem)
  h1 "Qual é a sua dúvida?"                                        22 px
  Chips de exemplo (3, rolagem horizontal, 48 px de altura, toque preenche o campo)
    "E se eu perder a causa?"  "Posso pagar parcelado?"  "O que é proveito econômico?"
  Textarea  rótulo "Escreva aqui ou grave sua voz"                 17 px, 3 linhas, cresce
  RecordButton  ● 64 px, centralizado, rótulo abaixo "Gravar minha dúvida"
    gravando: anel pulsando, "Gravando, 0:12", barras de nível, rótulo "Parar de gravar"
    parou: TranscriptEditor "Confira o que você disse" (Textarea preenchida, editável)
  ── após envio: bloco de resposta (Card raio 22) ──
    p  "Você perguntou: 'E se eu perder a causa?'"                 15 px muted
    p  resposta em 1–3 frases simples                              17 px
    QuoteDisclosure aberto: "Cláusula 4ª" + blockquote com <mark>
    ou recusa: ícone Info + texto de recusa + chip "anotei para o Dr. João"
    [▶ Ouvir resposta]  (ghost 48 px)
  Link "Perguntar outra coisa" (limpa o campo, mantém histórico abaixo)
[BottomActionBar]
  [Enviar dúvida]              primário 52 px (desabilitado sem texto)
  [Voltar ao tópico]           secundário 48 px
```

## Componentes (shadcn/ui)

`Textarea`, `Button`, `Badge`, `Card`, `Dialog` (consentimento de voz), `Skeleton`, `Alert`, `Toast`; novos: `RecordButton`, `TranscriptEditor`, `QuoteDisclosure`, `AudioPlayer` (compacto), `AssistantBanner`, `BottomActionBar`.

## Copy exata (pt-BR)

- Contexto: "Sobre: Quanto você paga"
- h1: "Qual é a sua dúvida?"
- Chips: "E se eu perder a causa?" · "Posso pagar parcelado?" · "O que é proveito econômico?" (vêm do backend por seção; fallback genérico: "O que acontece se eu não pagar?" · "Posso desistir?" · "Quem paga as custas?")
- Campo: "Escreva aqui ou grave sua voz"
- Microfone: "Gravar minha dúvida" / "Parar de gravar"; cronômetro "Gravando, 0:12"; transcrição "Confira o que você disse"
- Consentimento (1ª gravação, `Dialog`): "Sua voz será transformada em texto só para conferir se você entendeu. O áudio não vai para o registro público. Você pode pedir para apagar depois." Botão "Continuar"; link "Prefiro escrever".
- Microfone negado: "Sem microfone, tudo bem. Você pode escrever sua resposta aqui."
- Botões: "Enviar dúvida" · "Voltar ao tópico" · "Perguntar outra coisa" · "Ouvir resposta"
- Resposta com citação (exemplo): "Se você perder, não paga os honorários de êxito. O documento diz que eles são devidos só se ganhar." + trecho.
- Fora do documento: "Isso não está escrito neste documento. Anotei para o Dr. João responder." + chip "anotei para o Dr. João"
- Pedido de conselho: "Se vale a pena assinar é uma decisão sua com o Dr. João. Eu só explico o que está escrito." + chip "anotei para o Dr. João"

## Estados

**Default** — campo vazio, chips visíveis, microfone pronto. Dúvidas anteriores desta sessão aparecem abaixo em ordem cronológica (mais recente no topo).

**Vazio (sem chips)** — backend sem sugestões: chips somem; nada mais muda.

**Carregando (resposta)** — botão vira "Conferindo no documento…" com spinner; card de resposta com `Skeleton` de 3 linhas e `aria-busy`. Texto aparece por frase completa (streaming), anunciado só ao fim de cada frase.

**Erro** — `Alert` no card: "Deu um problema do nosso lado, não foi você. Estamos tentando de novo." Retentativa automática 1×; depois botão "Enviar de novo". O texto digitado nunca é apagado.

**Sem conexão** — dúvida entra na fila; card mostra "Sua dúvida está salva. Eu respondo quando a internet voltar." (`OfflineBanner` no topo). Ao reconectar, envia e mostra a resposta.

## Interações

- Chip → preenche o Textarea (não envia); foco vai ao campo.
- RecordButton (toggle, Space/Enter): 1º uso abre o `Dialog` de consentimento → "Continuar" pede permissão do microfone. Gravando: anel pulsa (reduced-motion: anel fixo), cronômetro a cada segundo (anúncio a cada 5 s), limite suave de 90 s com aviso "Pode parar quando quiser". Parar → transcrição aparece no Textarea rotulado "Confira o que você disse", foco vai ao campo; a cidadã edita e toca "Enviar dúvida".
- Permissão negada → toast "Sem microfone, tudo bem. Você pode escrever sua resposta aqui." e foco no Textarea.
- "Enviar dúvida" → `POST /sessions/{id}/chat`; card de resposta entra com fade 150 ms; foco vai ao início da resposta; se `refused`, chip âmbar "anotei para o Dr. João".
- "Ouvir resposta" → player compacto lê a resposta (não lê a citação, salvo toque em "Ouvir o trecho").
- "Voltar ao tópico" → `topics/{from}`; histórico de dúvidas fica salvo e visível em C5 ("2 dúvidas anotadas").

## Acessibilidade

- Foco inicial no h1. Ordem: banner → contexto → h1 → chips (`role="group" aria-label="Exemplos de dúvida"`) → Textarea → microfone → transcrição (quando existir) → resposta → "Perguntar outra coisa" → barra.
- Microfone: `<button aria-pressed>` 64 px; live region "Gravando, 12 segundos"; ao parar, foco na transcrição. Space alterna; Esc cancela a gravação sem apagar o que já estava no campo.
- Resposta em `role="region" aria-label="Resposta da assistente"`; streaming com `aria-live="polite"` por frase; citação em `<blockquote>` com `<mark>`.
- Recusa: ícone + texto + chip; nunca só cor.
- Barra inferior não cobre o Textarea focado (`scroll-padding-bottom`).
- Sem tempo limite; limite de 90 s é aviso, não corte.

## Chamadas de API

- `POST /sessions/{id}/chat` `{ section_id, question_text, input_mode: "voice"|"text" }` → `{ answer, quote { text, clause_ref }, refused, refusal_kind }`.
- V1 voz: `SpeechRecognition` do navegador (pt-BR, `interimResults`) → texto. V2: `MediaRecorder` → `POST /stt` → texto.
- V2 áudio da resposta: `POST /tts { text }` (V1: `speechSynthesis`).

## O que muda na V1 / V2 / Produto

- **V1:** STT/TTS do navegador; chips fixos por tipo de documento; sem histórico persistido além da sessão em cache; consentimento em `Dialog` simples.
- **V2:** `POST /stt` (Whisper) com áudio descartado após transcrição; chips gerados por seção; histórico no servidor e visível ao advogado em tempo real.
- **Produto:** "pedir para apagar" a transcrição a partir desta tela; respostas com áudio pré-gerado para dúvidas frequentes; detecção de dúvida repetida ("Você já perguntou isso; a resposta está aqui").
