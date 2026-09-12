# Correções de acessibilidade priorizadas — LeIA

Companion de `accessibility-audit.md` (IDs entre parênteses remetem aos achados). Entrega: **V2 hoje** = entra na build de hoje; **Produto amanhã** = entra amanhã, antes do teste com usuária; **depois** = backlog. Esforço estimado para uma pessoa que já conhece o código (Next + Tailwind + shadcn).

## Crítico

| # | Tela | Critério | Correção | Esforço | Entrega |
|---|---|---|---|---|---|
| 1 | Todas (T-01) | 2.4.7, 1.4.11, 2.4.13 | Definir o anel de foco no tema: `*:focus-visible { outline: 3px solid #081820; outline-offset: 2px }`; dentro de `AssistantBanner` e `Sidebar` usar `outline-color: #F0F0E8`. Remover o `ring` translúcido do shadcn dos `Button`, links, segmentos do `ProgressSteps`, chips, `<pre tabindex=0>`. Conferir sobre o botão primário teal (3,2:1). | 20 min | V2 hoje |
| 2 | Todas da cidadã (T-02) | 1.4.4, 1.4.10, 2.4.11 | Trocar `height` por `min-height` no banner, no botão "Falar com o advogado" e na `BottomActionBar`; `ResizeObserver` nos dois componentes escrevendo `--banner-h` e `--bar-h` em `:root`; `main { padding-bottom: calc(var(--bar-h) + 16px); scroll-padding-bottom: calc(var(--bar-h) + 16px); scroll-padding-top: var(--banner-h) }`. Testar a 130 % e 200 % de fonte do sistema. | 40 min | V2 hoje |
| 3 | C1 (C1-01) | 1.2.1, 4.1.3 | Antes de renderizar C1, `speechSynthesis.getVoices()` (com `onvoiceschanged`); sem voz `pt-BR`/`pt`: primário vira "Começar lendo", nota visível "Este celular não tem voz em português. O texto está todo aqui.", botões "Ouvir…" com `aria-disabled` e a mesma nota. Guardar em `audio_pref = read`. | 30 min | V2 hoje |
| 4 | C2 (C2-01) | 1.4.2, 4.1.3 | `speechSynthesis.cancel()` no unmount de `AudioPlayer` e na troca de rota. Com autoplay: foco vai para "Pausar" (não para o h1) e o título é anunciado pela `StatusRegion` 600 ms depois; Espaço/toque duplo param. V2: opção "Não tocar o áudio sozinho" na folha de acessibilidade. | 30 min | V2 hoje |
| 5 | C3, C4 (C3-01, C4-02) | 1.2.1, 3.3.1, 4.1.3 | `RecordButton` V1: no `onend` do `SpeechRecognition`, chamar `start()` de novo enquanto o estado for "gravando"; acumular apenas resultados `isFinal` em um buffer; `continuous = true`, `interimResults = true`, `lang = 'pt-BR'`. Live region só no início ("Gravando. Toque de novo quando terminar.") e no fim ("Gravação parada. Confira o que você disse."); cronômetro apenas visual + `vibrate(30)`. Instrução visível "Fale devagar. Pode fazer pausas." | 1 h | V2 hoje |
| 6 | C4, C5, C6, CH, P1, A2, A3, A4 (T-03) | 1.4.3 | Chips e cards âmbar: texto e ícone `#7A4800` sobre fundo `#FFF4DD` com borda 1 px `#B26A00` (7,0:1). Nunca branco sobre `#B26A00` em texto ≤ 18 px. Se precisar de fundo sólido, `#9A5B00`. Atualizar a tabela de contraste do `component-plan.md` (também `#1F7A4D` com branco é 5,3:1, não 5,9). | 15 min | V2 hoje |

## Importante

| # | Tela | Critério | Correção | Esforço | Entrega |
|---|---|---|---|---|---|
| 7 | C4 (C4-01) | 2.4.6, 1.3.1 | h1 passa a ser a pergunta com prefixo oculto: `<h1 aria-describedby="lembrete"><span class="sr-only">Conferindo 1 de 3: </span>{pergunta}</h1>`; "Para eu ter certeza de que expliquei bem:" vira `<p>` acima. Visual inalterado. A pergunta repetida no feedback "Vamos ver de novo" continua `<h3>`. | 15 min | V2 hoje |
| 8 | Todas (T-04) | 2.4.2 | `generateMetadata` por rota: "Tópico 2 de 7: Quanto você paga · LeIA", "Qual é a sua dúvida? · LeIA", "Conferindo 1 de 3 · LeIA", "O que você entendeu · LeIA", "Seu comprovante · LeIA", "Meus documentos · LeIA", "Painel · LeIA", "Revisar explicação · LeIA", "Validar sessão de Maria · LeIA". | 20 min | V2 hoje |
| 9 | C0, C3, C4 (T-05) | 2.2.1, 3.3.1 | Erros nunca em toast: "O login não terminou…" vira `Alert` inline em C0; "Sem microfone, tudo bem…" vira texto persistente sob o microfone com `role="status"`. Toast só para "Copiado", "Link copiado", "Pronto. Vamos começar.". Sonner com `offset` = `var(--bar-h)` para não cobrir o primário. | 20 min | V2 hoje |
| 10 | C2, C3, C4, A2 (T-06, A2-01) | 1.4.1, 1.4.11 | `<mark>`: além de `#FFF1B8`, `text-decoration: underline 2px; font-weight: 600`; dentro do `<mark>`, `<span class="sr-only">início do trecho citado</span>` e `<span class="sr-only">fim do trecho citado</span>`; remover `aria-label` do `<mark>`. | 15 min | V2 hoje |
| 11 | C3 (C3-02) | 1.4.10, 2.1.1 | Chips de exemplo em `flex-wrap` (ou coluna), 48 px cada, sem rolagem horizontal em nenhuma largura. Alinhar `responsive.md` e `screen-05`. | 10 min | V2 hoje |
| 12 | C3, C4, C5 (C3-03, C5-03) | 3.3.1, 4.1.2 | Botões primários "desabilitados sem texto" passam a `aria-disabled="true"` (continuam focáveis) com `aria-describedby` para a frase de ajuda ("Escreva ou grave sua dúvida primeiro" / "Falta ver 2 partes"); ao ativar, a frase aparece sob o botão e recebe `role="status"`. | 20 min | V2 hoje |
| 13 | C0, C1, CH (T-09, C0-03) | LBI art. 63 | V1: símbolo de acessibilidade + link "Recursos de acessibilidade" no rodapé do `<main>` de C0, C1 e CH apontando para `/acessibilidade` (página estática de 1 tela: o que há de áudio, VLibras, como aumentar o texto pelo sistema, "Falar com o advogado"). `AccessibilitySheet` completa na V2. | 30 min | Produto amanhã |
| 14 | C2–C6 (T-08) | COGA, 1.4.10 | Banner compacto a partir de C2: 1 linha "assistente automática · não dá conselho jurídico" (48 px) + botão "Falar com o advogado" no mesmo lugar; texto completo em C0/C1 e na folha de contato. | 30 min | Produto amanhã |
| 15 | CH, C6, P1 (T-07) | 3.2.4, 3.1.5 | Unificar rótulos da cidadã: "carimbo a caminho" (nunca "pendente") e "Conferido pelo Dr. João" (nunca "Validado"). "Pendente" só no painel do advogado. | 10 min | V2 hoje |
| 16 | C1, C2, C4, C6 (T-16) | 3.1.5, 1.2.1 | Função `ttsText(text)` aplicada antes do `speechSynthesis`: `R$ 10.000` → "10 mil reais", `30%` → "30 por cento", `OAB/PR 12345` → "OAB PR 12345", `0:12` não é falado. Conferir no teste de amanhã. | 20 min | Produto amanhã |
| 17 | A4 (A4-01) | 2.1.4 | Remover o atalho `N`; trocar `/` por `Ctrl+K` (ou manter `/` atrás de um toggle "Atalhos de teclado"). `Ctrl+Enter` e `Ctrl+Shift+Enter` ficam. | 10 min | V2 hoje |
| 18 | A1 (A1-01) | 2.2.1 | Retirar o redirecionamento automático de 3 s; ao concluir o pipeline, foco no botão "Revisar explicação" e anúncio "Explicação pronta para revisar". | 10 min | V2 hoje |
| 19 | C0 (T-10) | 3.3.8 | Manter "Continuar sem conta" com a flag ligada como alternativa de acessibilidade (sem conta Google, celular compartilhado). Produto: OTP por telefone. | 0 (decisão) | V2 hoje |

## Polimento

| # | Tela | Critério | Correção | Esforço | Entrega |
|---|---|---|---|---|---|
| 20 | C1–C4, C6 (T-11) | 4.1.2, 2.5.3 | Microfone e player: rótulo visível muda ("Gravar…"/"Parar de gravar", "Ouvir…"/"Pausar") e `aria-pressed` sai; estado vai para a live region. Atualizar `component-plan.md` e `micro-interactions.md`. | 15 min | Produto amanhã |
| 21 | C3, C4 (C3-04) | 2.1.1, 2.5.7 | Botão ghost "Cancelar" (48 px) ao lado do microfone durante a gravação, com o mesmo efeito do Esc (descarta sem apagar o campo). | 15 min | Produto amanhã |
| 22 | C2 (C2-02) | 2.5.8, uma mão | `ProgressSteps`: segmentos não interativos (rever pela lista de C5) ou 2 linhas quando N > 6 com gap ≥ 8 px; segmentos futuros no DOM como texto "Tópico 5, ainda não visto". | 30 min | depois |
| 23 | C2 (C2-03), C4 | 2.4.6 | Prefixo "Tópico 2 de 7: " como `<span class="sr-only">` dentro do h1 em vez de `aria-label`. | 5 min | V2 hoje |
| 24 | C2 (C2-04) | COGA | Link "Voltar para a parte anterior" (48 px) no fim do `<main>` quando n > 1. | 10 min | Produto amanhã |
| 25 | C3, C6, CH, C1 (T-12) | 2.5.8 | Links inline ("Perguntar outra coisa", "Voltar para meus documentos", "Recursos de acessibilidade", "Ver na rede pública", "Prefiro escrever") com `min-height: 48px` e `padding-block: 12px`. | 10 min | V2 hoje |
| 26 | C5, A2, A3 (T-13) | 1.1.1 | SVG de estado com `role="img"` + `aria-label`, ou texto oculto ao lado. | 5 min | V2 hoje |
| 27 | C3 (C3-05) | 4.1.3 | Streaming: não mover o foco durante o `aria-live`; ao concluir, foco no h2 oculto "Resposta" do card. | 15 min | Produto amanhã |
| 28 | C3 (C3-06) | 3.1.5, 3.3.2 | Consentimento: "Eu escuto sua voz e escrevo o que você disse. O áudio não fica guardado. Você pode pedir para apagar." Foco inicial no título do diálogo. | 10 min | Produto amanhã |
| 29 | C3, C4 (C3-07, C4-05) | 3.3.2 | Rótulos fixos "Sua dúvida" / "Sua resposta (escreva aqui)"; "Confira o que você disse" como legenda `aria-describedby`. | 10 min | Produto amanhã |
| 30 | C4 (C4-04) | 3.1.5 | Feedback de exemplo em 3 frases curtas: "Você recebe R$ 10.000. R$ 3.000 ficam com o advogado. R$ 7.000 ficam com você." Manter o limite de 15 palavras na geração. | 5 min | V2 hoje |
| 31 | C6, P1 (C6-02) | 1.3.1, 3.1.5 | Hash com `aria-label="Código do registro, 64 caracteres. Use o botão Copiar."`; datas visíveis por extenso em `<time datetime>` ("12 de setembro de 2026, 15:40"). | 15 min | Produto amanhã |
| 32 | Cidadã (T-14) | 2.4.11 | Montar o widget VLibras só quando ativado em "Recursos de acessibilidade"; `onerror` silencioso no script externo; testar sobreposição em 320 px. | 20 min | Produto amanhã |
| 33 | Cidadã (T-15) | 2.4.1, 2.5.2 | Link "Pular para o conteúdo" como primeiro focável; `touch-action: manipulation` nos botões. | 10 min | V2 hoje |
| 34 | CH (CH-01, CH-02) | 4.1.3, 2.5.1 | `aria-busy` só no contêiner da lista; botão "Atualizar lista" já na V1. | 10 min | Produto amanhã |
| 35 | C0 (C0-01) | 3.3.2 | Nota sob "Continuar sem conta": "Sem conta, o comprovante fica só neste celular." e `aria-describedby` correto. | 5 min | V2 hoje |
| 36 | C5 (C5-02) | 4.1.2 | No modo leitura, itens da lista como texto (não botões); só "Ver dúvidas" interativo. | 10 min | depois |
| 37 | A0, A4 (A0-02, A4-03, A1-02) | 1.4.3, 1.4.11 | Tokens faltantes: `ink.onNavyMuted #A8B4B8` (OAB na sidebar), `danger #B91C1C` (erro ao processar, anel de gravação), borda do dropzone `#6E7377`. | 10 min | V2 hoje |
| 38 | A0 (A0-01) | 1.3.5 | `autocomplete="name"` e `inputmode="numeric"` na OAB. | 5 min | V2 hoje |
| 39 | A4, A2, A3 (A4-02, A2-02, A3-01) | 1.4.13, 1.3.1 | Informação necessária fora de tooltip: texto visível na célula de pendências ("1 conversa · 1 dúvida"), motivo de "juiz: revisar" sob o selo, detalhe da rubrica em `Popover` ou texto. | 30 min | depois |
| 40 | A4 (A4-04) | 4.1.2 | `aria-current="page"` no item ativo da sidebar. | 2 min | V2 hoje |
| 41 | A3 (A3-02), P1 (P1-03) | 1.3.1, eMAG | `<figure>/<figcaption>` nas respostas da cliente; `accesskey="1"` no `<main>` e link "Acessibilidade" no rodapé de P1. | 15 min | depois |

## Ordem sugerida para hoje (≈ 5 h de uma pessoa)

1. Tokens e CSS globais: anel de foco (#1), âmbar e cores faltantes (#6, #37), `<mark>` (#10), links de 48 px (#25), `touch-action` e skip link (#33). ≈ 1 h.
2. Layout fixo: `min-height` + `ResizeObserver` + `scroll-padding` (#2). ≈ 40 min.
3. Áudio: cancelamento e foco no autoplay (#4), detecção de voz pt-BR (#3). ≈ 1 h.
4. Gravação: reinício no `onend`, live region só no início/fim (#5). ≈ 1 h.
5. Semântica e texto: h1 de C4 (#7), títulos por rota (#8), erros inline (#9), chips empilhados (#11), `aria-disabled` (#12), rótulos "carimbo a caminho" (#15), atalhos e redirecionamento do advogado (#17, #18), miúdos (#23, #26, #30, #35, #38, #40). ≈ 1 h 20.

Amanhã, antes do teste com usuária: página `/acessibilidade` e símbolo (#13), banner compacto (#14), `ttsText` (#16), toggle de rótulo do microfone (#20), "Cancelar" na gravação (#21), e o roteiro de 30 minutos do `accessibility-audit.md`.
