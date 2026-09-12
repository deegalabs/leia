# Micro-interações

Regras gerais:

- Easing padrão `cubic-bezier(0.2, 0, 0, 1)` (ease-out); saídas com `cubic-bezier(0.4, 0, 1, 1)`.
- Durações: 80–120 ms para feedback de toque, 150–250 ms para transições de estado, 300 ms no máximo para entrada de tela. Nada em loop além de indicadores de progresso e gravação.
- `prefers-reduced-motion: reduce` → todas as transições viram troca instantânea (0 ms) ou fade de 100 ms; loops viram estado estático; nada de deslocamento (`transform`). A preferência também pode ser ligada manualmente em "Recursos de acessibilidade" (guardada em `localStorage`).
- Animação nunca é o único sinal: todo estado tem texto e, quando relevante, anúncio em live region.

## Tabela

| Gatilho | Animação | Duração | Easing | Reduced motion |
|---|---|---|---|---|
| Troca de rota cidadã (C1→C2, C2→C2) | fade-in + translateY 12→0 px do `<main>` | 180 ms | ease-out | fade 100 ms |
| Troca de rota advogado | fade-in do conteúdo | 120 ms | ease-out | instantâneo |
| Toque em botão (todos) | `scale(0.98)` ao pressionar, volta ao soltar | 80 ms | ease-out | sem escala; só mudança de cor |
| Barra de progresso de tópicos (C2) | segmento preenche da esquerda para a direita | 300 ms | ease-in-out | instantâneo |
| "Ver trecho original" (QuoteDisclosure) | altura 0→auto + chevron gira 180° | 200 ms | ease-out | instantâneo |
| Destaque da citação ao abrir o trecho | fundo do `<mark>` de transparente para `#FFF1B8` | 250 ms | ease-out | cor final direta |
| Play do áudio | ícone ▶ → ⏸ com crossfade; barra de progresso avança | 120 ms | linear (barra) | ícone troca; barra avança |
| Sentença em leitura (V2, áudio sincronizado) | fundo `#EAF4F4` na frase atual | 150 ms | ease-out | fundo sem transição |
| Troca de velocidade 0,8×/1×/1,25× | rótulo do botão troca; toast breve "Velocidade 1,25×" | 100 ms | — | igual |
| Início de gravação (RecordButton) | anel externo pulsa (`scale` 1→1.12, opacidade 0.6→0) | 1200 ms loop | ease-in-out | anel estático vermelho + cronômetro |
| Fim de gravação | anel some; card "Confira o que você disse" desliza de baixo 16 px | 200 ms | ease-out | aparece sem deslocar |
| Nível de voz durante gravação | 5 barras verticais com altura do volume | 60 ms por frame | linear | barras fixas em 50 % |
| Envio de resposta / dúvida | botão vira "Conferindo…" com spinner; campo desabilitado | 150 ms | ease-out | igual, spinner estático (três pontos) |
| Resposta em streaming (C3) | texto aparece por frase completa (não por token) | por frase | — | igual |
| Feedback "Isso mesmo" (C4) | ícone check desenha (stroke-dashoffset) + card fade-in | 300 ms | ease-out | check pronto; fade 100 ms |
| Feedback "Vamos ver de novo" (C4) | card em duas partes desliza de baixo 16 px; foco no h3 | 200 ms | ease-out | sem deslocamento |
| Item da lista de C5 marcado | check verde aparece com fade | 150 ms | ease-out | instantâneo |
| "Confirmo que entendi" enviado | botão → "Enviando…"; ao sucesso, círculo com check cresce 0.8→1 | 250 ms | spring leve (overshoot 1.02) | sem escala |
| Comprovante provisório → final (C6/A3/P1) | chip "carimbo pendente" faz crossfade para "registrado"; anúncio em `role="status"` | 200 ms | ease-out | troca direta |
| Copiar hash / link | rótulo "Copiar" → "Copiado" com check; volta após 1,5 s | 100 ms | — | igual |
| Skeleton de carregamento | shimmer horizontal | 1500 ms loop | linear | fundo cinza fixo |
| Etapas do pipeline (A1) | etapa ativa com spinner; ao concluir, check preenche e a próxima ativa | 200 ms | ease-out | check direto |
| Tempo por etapa (A1) | contador "12 s" atualiza a cada segundo | — | — | igual |
| Linha da tabela (A4) hover | fundo `#F4F4F0` | 100 ms | ease-out | igual (cor não é movimento) |
| Sheet / Drawer (todas) | desliza da borda + backdrop 0→40 % | 250 ms | ease-out | fade 100 ms |
| Dialog | `scale` 0.96→1 + fade | 150 ms | ease-out | fade 100 ms |
| Toast (Sonner) | entra de baixo (cidadã) / de cima à direita (advogado); some após 4 s ou ao fechar | 200 ms | ease-out | fade |
| Banner offline | desce do topo | 200 ms | ease-out | aparece |
| Badge "trecho verificado" ao concluir verificação (A2) | fade-in + leve `scale` 0.9→1 | 150 ms | ease-out | fade |
| Mudança de aba de filtro (A4) | sublinhado desliza para a aba ativa | 150 ms | ease-out | troca direta |

## Sons

Nenhum som além do próprio áudio de explicação e de pergunta. Início e fim de gravação têm sinal háptico curto (`navigator.vibrate(30)`) quando disponível; nunca é o único sinal.

## Anúncios (live regions) pareados com animações

| Momento | Região | Texto |
|---|---|---|
| Entrou em tópico | foco no h1 (não live) | "Tópico 2 de 7: Quanto você paga" |
| Gravando | `aria-live="polite"` | "Gravando, 12 segundos" a cada 5 s |
| Parou de gravar | foco na transcrição | rótulo "Confira o que você disse" |
| Conferindo resposta | `aria-busy` no card | "Conferindo sua resposta" |
| Feedback pronto | `role="status"` | primeira frase do feedback |
| Carimbo concluído | `role="status"` | "Registro concluído. O comprovante está completo." |
| Copiado | `role="status"` | "Copiado" |
