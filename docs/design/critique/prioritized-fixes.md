# Correções priorizadas — LeIA

Base: `./critique.md`. Entregas: **V2 hoje** (17h30, fluxo da cidadã com voz, ancoragem e verificação) · **Produto amanhã** (10h30) · **depois** (fora do hackathon). Esforço em minutos de implementação, estimado para quem já tem o componente na mão. Nenhuma correção cria tela nova.

## Crítico — resolver antes da V2 de hoje (≈ 2 h 25 min)

| # | Tela | Problema | Correção | Esforço | Entrega |
|---|---|---|---|---|---|
| C1 | C0, C6 | Login do Google é a primeira tela; a pesquisa pede link sem login e a demo D2 entrega o celular a um jurado sem instrução. | Trocar "C0 obrigatória" por "link abre C1 direto" (`NEXT_PUBLIC_ALLOW_GUEST` ligada por padrão). Mover o Google para C6 como secundário "Entrar com Google para guardar o comprovante"; C0 fica só para link já ligado a uma conta. | 30 | V2 hoje |
| C2 | C3 | O contrato devolve `answer = "NAO_ESTA_NO_DOCUMENTO"` quando `refused = true` e não tem `refusal_kind`; a tela pode mostrar o token cru. | No cliente: se `refused` ou `answer` começa com `NAO_`, nunca renderizar `answer`; mostrar o texto fixo "Isso não está escrito neste documento. Anotei para o Dr. João responder." + chip. Pedir `refusal_kind` ao backend; até lá, tratar tudo como "fora do documento". | 15 | V2 hoje |
| C3 | C3, C4 | Ordem microfone/campo invertida (C3: campo → mic; C4: mic → campo) e rótulos diferentes, contra a regra 2 do INDEX. | Trocar a ordem de C3 por: chips → `RecordButton` "Gravar minha dúvida" → `Textarea` "Ou escreva aqui". Mesmo rótulo de campo nas duas telas. | 20 | V2 hoje |
| C4 | C2, C3, C4 | Sem estado para voz indisponível: `speechSynthesis` sem voz pt-BR (autoplay em silêncio com botão "Pausar"), `SpeechRecognition` ausente (Firefox, iOS) ou offline (Chrome manda o áudio para a nuvem). | Detectar na carga. Sem voz pt-BR → esconder autoplay e mostrar nota "Áudio indisponível neste celular. Você pode ler." Sem STT ou offline → esconder o microfone e mostrar "Sem internet para a voz. Escreva sua resposta aqui." com foco no campo. | 40 | V2 hoje |
| C5 | C6 | Após confirmar, Maria cai em "aguardando o Dr. João" com polling de 30 s; na demo ao vivo a jurada espera sem sinal de vida. | Trocar polling de 30 s por 5 s enquanto `status = confirmed` e a aba está visível. Texto: "O Dr. João está conferindo agora. Esta tela atualiza sozinha." Ensaiar A3 no outro laptop em < 30 s. | 20 | V2 hoje |
| C6 | INDEX, todas as seções "O que muda" | Rótulos V1/V2/Produto do design (V1 = 48 h, V2 = semanas) não batem com as entregas reais (V2 hoje, Produto amanhã). | Re-rotular: "V1" do design → "V2 hoje"; itens baratos da "V2" do design (polling automático, AccessibilitySheet mínimo, conferência no navegador em P1) → "Produto amanhã"; resto → "depois". | 20 | V2 hoje |

## Importante — V2 hoje se sobrar tempo; Produto amanhã sem falta

| # | Tela | Problema | Correção | Esforço | Entrega |
|---|---|---|---|---|---|
| I1 | C1 | Tela de boas-vindas com 3 parágrafos + 2 cards + nota + link + 2 botões; a pesquisa pede "uma frase + botão, sem tour". | Remover o card "Como funciona". Manter "Oi, Maria.", 1 frase do documento, o card da assistente (obrigatório pelo CFOAB) e os 2 botões. | 15 | V2 hoje |
| I2 | C5 | `AlertDialog` "Confirmar que você entendeu?" duplica o botão "Confirmo que entendi" e o card âmbar; toque extra em ação não destrutiva. | Remover o dialog. Manter o card âmbar; se houver pendência, acrescentar nele "2 pontos ficam com o Dr. João." | 10 | V2 hoje |
| I3 | C2 | Selo "trecho conferido" só aparece com o Collapsible aberto; a prova de D1 fica atrás de um toque. | Trocar o rótulo do gatilho "Ver trecho original" por "Ver trecho original · ✓ conferido no documento" (ícone + texto, mesma linha). | 5 | V2 hoje |
| I4 | C3 | Consentimento de voz em voz passiva e com finalidade errada em C3 ("só para conferir se você entendeu" numa dúvida). | Texto único para C3/C4: "Sua voz vira texto aqui no aplicativo. O áudio não vai para o registro público. Você pode pedir para apagar depois." | 5 | V2 hoje |
| I5 | C3 | Após a resposta, o primário continua "Enviar dúvida" desabilitado; o passo natural é o secundário. | Com resposta na tela: primário "Voltar ao tópico", secundário "Perguntar outra coisa". Ao tocar no secundário, volta ao par original. | 10 | V2 hoje |
| I6 | C4 | Com `audio_pref = listen`, lembrete e pergunta não tocam sozinhos (C2 toca). | Ao entrar com `listen`, tocar lembrete + pergunta em sequência; botão "Ouvir a pergunta" vira "Pausar" com `aria-pressed`. | 15 | V2 hoje |
| I7 | C4 | h1 (19 px, enquadramento) menor que h2 (22 px, pergunta); título da página para leitor de tela é o enquadramento. | Enquadramento vira `<p>`; pergunta vira `h1` com `aria-label="Conferindo 1 de 3: {pergunta}"`. | 10 | V2 hoje |
| I8 | Navegação (OfflineBanner) | "é só tocar em Continuar" cita botão que não existe em C2/C4. | Trocar por "A conexão caiu. Suas respostas estão salvas. Quando a internet voltar, eu envio tudo sozinha." | 5 | V2 hoje |
| I9 | C2 | Player mostra "0:12 / 0:38" e barra, mas `speechSynthesis` não tem duração. | Enquanto o áudio for do navegador: sem tempo; estado "Falando…" com barra indeterminada; "Ouvir de novo" e velocidade continuam. | 15 | V2 hoje |
| I10 | A2 | "juiz: fiel" — para advogado, "juiz" é o magistrado. | Trocar por "segunda leitura (IA): fiel" / "segunda leitura: revisar"; tooltip mantém o motivo. | 5 | V2 hoje |
| I11 | C6 | "Salvar comprovante" = `window.print()`; o diálogo de impressão do Chrome Android é hostil para leiga. | Trocar por "Compartilhar comprovante" com Web Share API: link de verificação + PNG do `ReceiptCard` gerado no cliente (canvas, sem EXIF). Fallback "Salvar como PDF" só se `navigator.share` faltar. | 45 | Produto amanhã |
| I12 | A2, A3 | `prompt_version` e `model` (contrato) não aparecem em lugar nenhum; D3 pede visibilidade. | Linha discreta no cabeçalho de A2 e no card "Registro gerado" de A3: "explicação gerada com prompt v{prompt_version} · {model}". | 10 | Produto amanhã |
| I13 | A3 | `matched[]`/`missing[]` do juiz só em tooltip; o plano D1 pede o JSON visível. | Sob cada resposta, duas linhas: "Citou: 30%, só se ganhar" / "Faltou: consequência se perder" + Collapsible "Ver avaliação completa (JSON)". | 20 | Produto amanhã |
| I14 | P1 | "Conferir aqui no navegador" (`crypto.subtle`) adiado; é a demonstração mais forte de D1. | Botão que hasheia `canonical_json` (bytes exatos) e mostra "Confere" / "Não confere" ao lado do hash. | 30 | Produto amanhã |
| I15 | Navegação, todas C | Banner 76 px + barra 132 px = 28 % de 360×740; com zoom 200 % sobram ~270 px. | A partir de C2, banner de 1 linha (48 px): "assistente automática · não dá conselho jurídico" + botão; texto completo ao tocar. Com `100dvh < 600px`, barra só com o primário e o secundário vai ao fim do `<main>`. | 40 | Produto amanhã |
| I16 | C1, A2 | 7 tópicos + 3 perguntas ≈ 5 min contradiz a meta de < 4 min; C1 anuncia "uns 5 minutos". | A2: linha "Tempo estimado para a cliente: 5 min (meta 4)" no rodapé + botão "Juntar com a anterior" por seção; padrão de 2 perguntas. PDF de demo com 5 seções. | 30 | Produto amanhã |
| I17 | A2 | Índice de legibilidade (Flesch-pt ≥ 60, recommendations §2.7) ausente das dicas. | Acrescentar "Leitura fácil: 68" à linha de dicas, calculado no cliente; abaixo de 60 vira dica âmbar "Frases mais curtas ajudam." | 30 | Produto amanhã |

## Polimento — quando couber

| # | Tela | Problema | Correção | Esforço | Entrega |
|---|---|---|---|---|---|
| P1 | C2 | Texto usa "honorários" antes de explicar. | Trocar por "Se perder, você não paga nada ao advogado por esse trabalho (isso se chama honorários de êxito)." | 2 | V2 hoje |
| P2 | C4 | Frase de feedback com 16 palavras. | Trocar por "Se você receber R$ 10.000, R$ 3.000 são do advogado. R$ 7.000 ficam com você." | 2 | V2 hoje |
| P3 | C4 | "Podemos seguir para o próximo tópico." quando o próximo é uma pergunta. | Trocar por "Podemos seguir para a próxima pergunta." (última: "Podemos ver o resumo.") | 1 | V2 hoje |
| P4 | A2 | "Para aprovar: 1 seção com trecho não encontrado, escolha ao menos 2 perguntas." | Trocar por "Para aprovar: resolva 1 trecho não encontrado e escolha ao menos 2 perguntas." | 1 | V2 hoje |
| P5 | C2 | Três botões de 48 px em 328 px úteis: "Ouvir explicação" não cabe em 360 px. | Aplicar os rótulos curtos ("Ouvir", "De novo", "1×") abaixo de 400 px, não só em 320; ou "Ouvir explicação" em linha própria. | 10 | V2 hoje |
| P6 | C1, CH | Link "Recursos de acessibilidade" aparece, mas o design diz que a `AccessibilitySheet` não existe na primeira versão. | Ou esconder o link até a folha existir, ou entregar folha mínima (tamanho do texto 100/150/200 % + VLibras). | 20 | Produto amanhã |
| P7 | CH, C5 | Botões só com verbo: "Continuar", "Fechar", "Sair"/"Ficar". | Trocar por "Continuar a explicação", "Fechar lista", "Sair da conta"/"Ficar na conta". | 5 | Produto amanhã |
| P8 | C2, C4 | Barras de progresso reiniciam ("Tópico 7 de 7" → "Conferindo 1 de 3"); sem tempo restante. | Rótulo "Perguntas: 1 de 3"; acrescentar "faltam uns 2 minutos" ao lado do progresso (pesquisa §6). | 10 | Produto amanhã |
| P9 | C2, A2 | Emoji como ícone de tópico renderiza diferente por Android e destoa do lucide. | Mapear `section.icon` para lucide (Coins, CalendarClock, Route, Handshake, AlertTriangle, XCircle) 24 px em círculo `#EAF4F4`. | 15 | Produto amanhã |
| P10 | P1 | "(rede de testes)" — "teste" numa página que a cidadã abre pelo QR; rodapé com frase de 35 palavras. | Trocar por "(rede de demonstração)". Quebrar o rodapé: "Este código existia neste horário. Ele foi gerado a partir do JSON acima. O JSON descreve uma sessão validada por um advogado: tópicos, perguntas e resultados." | 5 | Produto amanhã |
| P11 | A1 | Stepper não mostra a segunda leitura (juiz, outro fornecedor) nem a checagem de instrução escondida. | Sub-linha em "Conferindo trechos": "7 de 7 encontrados · segunda leitura: 7 fiéis · instruções escondidas: nenhuma" (se o backend expõe). | 15 | Produto amanhã |
| P12 | C3, C4 | Estado "transcrição ruim" da pesquisa (content-strategy §4) ausente. | Se a transcrição tiver < 3 palavras: "Acho que não ouvi direito. Pode falar de novo ou escrever aqui?" com foco no campo. | 10 | Produto amanhã |
| P13 | C2 | Destaque de frase em leitura adiado por depender de TTS com marcas de tempo. | Com `speechSynthesis`, enfileirar uma `utterance` por frase e destacar a atual no `onstart`; efeito de legenda sem servidor. | 30 | Produto amanhã |
| P14 | Navegação, A2 | Atalho Ctrl+Enter significa "aprovar" em navigation.md e "marcar conferida" em A2. | Adotar A2 (Ctrl+Enter marca e avança; Ctrl+Shift+Enter aprova) e corrigir navigation.md. | 2 | depois |
| P15 | Tokens | Sem sombras; player e FeedbackCard competem em pé de igualdade com cards estáticos. | Uma sombra tingida única `0 1px 2px rgba(8,24,32,.06), 0 4px 12px rgba(8,24,32,.04)` só em player, FeedbackCard e ReceiptCard. | 10 | depois |
| P16 | A2 | `risk_level` e `why_it_matters` do contrato não aparecem. | Chip "risco: alto" ao lado do título da seção; `why_it_matters` como sugestão pré-preenchida da "Frase essencial". | 15 | depois |
| P17 | A0 | Sem `tabular-nums` nas tabelas do painel; sem tracking negativo nos títulos de 20–22 px. | `font-variant-numeric: tabular-nums` em A4/A3; `letter-spacing: -0.01em` nos h1. | 5 | depois |
