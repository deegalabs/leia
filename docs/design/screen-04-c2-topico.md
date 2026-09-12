# C2 · Tópico n de N — `/c/{token}/topics/{n}`

## Propósito e posição no fluxo

Tela central da explicação: um tópico por rota, layout idêntico em todos. Mostra progresso, ícone + título, 2–4 frases simples com exemplo em R$, áudio e o trecho literal da cláusula. Entrada: C1 ou tópico anterior, C3 (voltando da dúvida) ou C5 ("rever uma parte"). Saída: próximo tópico; no último, C4 pergunta 1; ou C3 (dúvida).

## Layout (mobile-first, 360×740)

```
[AssistantBanner — Dr. João Silva]
[main]
  ProgressSteps  "Tópico 2 de 7"  ▮▮▯▯▯▯▯ (7 segmentos, 8 px, toque ≥ 48 px)
  h1  [💰 aria-hidden] "Quanto você paga"                          22 px
  p   "O advogado só recebe se você ganhar a causa. Se ganhar, ele fica com 30% do que você receber. Por exemplo: de R$ 10.000, R$ 3.000 ficam com ele e R$ 7.000 com você. Se perder, você não paga esses honorários (chamados de honorários de êxito)."   17 px/1.5, ≤ 60 caracteres por linha
  AudioPlayer (card raio 22, fundo branco)
    [▶ Ouvir explicação]  [↺ Ouvir de novo]  [1×]                 botões 48 px
    barra de progresso do áudio (4 px), tempo "0:12 / 0:38"
  QuoteDisclosure (Collapsible fechado)
    [▸ Ver trecho original]                                        48 px, largura total
    ao abrir: "Cláusula 4ª" + blockquote com <mark> em "30% (trinta por cento) sobre o proveito econômico obtido, devidos apenas em caso de êxito"
    selo ✓ "trecho conferido: copiado exatamente do seu documento"  15 px, verde
[BottomActionBar]
  [Entendi, próximo]         primário 52 px   (no último tópico: "Entendi, vamos conferir")
  [Tenho uma dúvida]         secundário 48 px
```

## Componentes (shadcn/ui)

`Card`, `Button`, `Collapsible`, `Progress`, `Skeleton`, `Alert`, `Toast`; novos: `ProgressSteps`, `TopicCard`, `AudioPlayer`, `QuoteDisclosure`, `AssistantBanner`, `BottomActionBar`, `OfflineBanner`.

## Copy exata (pt-BR)

- Progresso: "Tópico 2 de 7"
- Título (exemplo): "Quanto você paga"
- Texto (exemplo): como no layout; regras: 2–4 frases, ≤ 15 palavras cada, um exemplo em R$, termo técnico só entre parênteses depois da explicação.
- Player: "Ouvir explicação" / "Pausar" · "Ouvir de novo" · "0,8×" / "1×" / "1,25×" (toast "Velocidade 1,25×")
- Trecho: "Ver trecho original" / "Fechar trecho original"; rótulo "Cláusula 4ª"; selo "trecho conferido: copiado exatamente do seu documento"
- Botões: "Entendi, próximo" · "Entendi, vamos conferir" (último) · "Tenho uma dúvida"
- Voltando de C5: primário vira "Voltar para o resumo".
- Título da lista de tópicos do exemplo: 1 "O que o advogado vai fazer" · 2 "Quanto você paga" · 3 "Como e quando você paga" · 4 "Até onde vai o trabalho" · 5 "Se houver acordo" · 6 "Os riscos para você" · 7 "Como cancelar".

## Estados

**Default** — tópico carregado; se `audio_pref = listen`, o áudio começa sozinho ao entrar (gesto anterior na mesma sessão SPA) e o botão mostra "Pausar".

**Vazio (tópico sem citação verificada)** — não deve ocorrer (A2 não aprova sem selo); defesa: trecho original mostra "O Dr. João ainda está conferindo este trecho." sem selo, e o texto simples continua visível.

**Carregando** — ProgressSteps e h1 vêm do cache; texto em `Skeleton` (4 linhas), player desabilitado; `aria-busy` no card. Sem cache: skeleton completo e "Carregando o tópico".

**Erro** — `Alert` no lugar do texto: "Deu um problema do nosso lado, não foi você. Estamos tentando de novo." + "Tentar de novo". Barra inferior mantém só "Tenho uma dúvida" desabilitado e "Falar com o advogado" no banner.

**Sem conexão** — conteúdo do cache, `OfflineBanner`; V1 áudio local funciona; V2 áudio só se em cache (senão botão "Ouvir explicação" desabilitado com nota "Áudio precisa de internet").

## Interações

- "Entendi, próximo" → salva `viewed[n] = true`, navega para `topics/{n+1}` (fade 180 ms), foco no novo h1. No último tópico → `questions/1`.
- "Tenho uma dúvida" → pausa o áudio, navega para `/c/{token}/ask?from={n}`.
- Player: Ouvir/Pausar alterna `aria-pressed`; "Ouvir de novo" reinicia do zero e toca; velocidade cicla 0,8× → 1× → 1,25× (persistida para todos os tópicos). V2: a frase em leitura recebe fundo `#EAF4F4`.
- "Ver trecho original" → abre em 200 ms, marca-texto aparece em 250 ms; estado aberto/fechado persiste por tópico.
- Toque em segmento já visto do ProgressSteps → abre aquele tópico (rever); segmentos futuros não são tocáveis.
- Voltar do sistema → tópico anterior; nada é perdido.
- Ao terminar o áudio, nada avança sozinho: a cidadã decide (sem tempo limite).

## Acessibilidade

- Ao navegar, foco vai ao h1 e o leitor anuncia "Tópico 2 de 7: Quanto você paga" (o h1 tem `aria-label` com o prefixo; visualmente só "Quanto você paga").
- Ordem: banner → progresso (`<nav aria-label="Tópicos">`, segmentos como botões "Tópico 1, visto") → h1 → texto → player (Ouvir/Pausar `aria-pressed`, Ouvir de novo, velocidade `aria-label="Velocidade, 1 vez"`) → trecho original (`aria-expanded`) → botões da barra.
- `<blockquote>` do trecho com `cite` = referência da cláusula; `<mark>` com `aria-label="trecho destacado"`; selo com ícone + texto.
- Ícone/emoji do título `aria-hidden`.
- Alvos 48 px; player com espaçamento 8 px; contraste `#1F7373`/branco 5,6:1.
- 200 %: player quebra em 2 linhas; nada some.
- Teclado: Tab na ordem acima; Space no player alterna; Esc fecha o trecho aberto.

## Chamadas de API

- `GET /sessions/{id}` (cache) → `sections[n] { icon, title, plain_text, quote, clause_ref, quote_verified, audio_url? }`.
- Progresso: `POST /sessions/{id}/answers` não é usado aqui; a posição é salva no dispositivo e enviada como `resume_path` junto da próxima chamada (`chat`/`answers`/`confirm`). Ver pendência "endpoint de progresso" no INDEX.
- V2: `POST /tts` só como fallback se `audio_url` faltar.

## O que muda na V1 / V2 / Produto

- **V1:** `speechSynthesis` do navegador; sem destaque de frase; progresso só local; texto vem pronto de A2.
- **V2:** áudio pré-gerado com marcas de tempo por frase (destaque sincronizado); progresso salvo no servidor; velocidade lembrada por conta.
- **Produto:** glossário tocável (termo entre parênteses abre definição curta); versão em Libras por tópico; teste A/B de 2 vs 4 frases por tópico.
