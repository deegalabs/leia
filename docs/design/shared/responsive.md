# Responsividade

## Cidadã (`/c/...`) — mobile-first

| Faixa | Comportamento |
|---|---|
| 320–359 px | Base mínima. Banner em 3 linhas + botão de 2 linhas. Texto 17 px mantém ≤ 40 caracteres por linha. Player de áudio com rótulos curtos ("Ouvir", "De novo", "1×"). |
| 360–429 px (referência 360×740) | Layout de referência de todos os mocks. Banner 76 px, barra inferior 132 px com 2 botões. |
| 430–767 px | Mesma coluna, padding lateral 24 px. Banner em 2 linhas (64 px). |
| ≥ 768 px (tablet ou desktop abrindo o link) | Coluna centralizada `max-width: 480px`, fundo lateral `#F0F0E8`. Barra inferior continua fixa, mas restrita à coluna. Nada muda de ordem. |

Regras:

- Unidades de texto em `rem`; `html { font-size: 100% }`. Com zoom de 200 % (WCAG 1.4.4) e largura 320 px, o conteúdo reflui sem rolagem horizontal (WCAG 1.4.10): botões viram coluna única (já são), player quebra em duas linhas, chips de exemplo (C3) empilham.
- Botões da barra inferior: `min-height: 48px` (primário 52 px), largura 100 %. Nunca lado a lado abaixo de 430 px.
- Microfone: 64 px de diâmetro fixo; a área de toque não encolhe com zoom.
- Altura útil: `100dvh` (não `100vh`) para não perder a barra atrás da barra de endereço do Chrome Android quando não instalado.
- `viewport-fit=cover` e `env(safe-area-inset-bottom)` na barra inferior.
- Orientação paisagem no celular (altura < 480 px): a barra inferior perde o botão secundário, que vai para o final do `<main>`; o banner reduz para 1 linha com o botão ao lado. Sem bloqueio de orientação (WCAG 1.3.4).
- Imagens: nenhuma. Ícones em SVG (lucide), 24 px, `aria-hidden`. Emoji do título do tópico com `aria-hidden` e `font-size` igual ao h1.
- QR (C6/P1): 200 px em ≥ 360 px, 160 px em 320 px, `max-width: 60vw`.

## Advogado (`/lawyer/...`) — desktop-first

| Faixa | Comportamento |
|---|---|
| ≥ 1280 px | Sidebar 240 px expandida. A2 em três colunas: lista de seções 260 px, cláusula original e texto simples lado a lado (50/50) no restante; painel de perguntas abaixo. A3 em duas colunas (resumo 320 px + conteúdo). |
| 1024–1279 px | Sidebar 240 px. A2: lista de seções vira `Tabs` horizontais acima; original e texto simples continuam lado a lado. A3: coluna única, resumo como cards no topo. |
| 768–1023 px | Sidebar colapsa para 64 px (ícones + tooltips). A2: original e texto simples empilhados, com o original em `Collapsible` aberto por padrão. Tabelas com rolagem horizontal dentro de `ScrollArea` e coluna "Ações" fixa à direita. |
| < 768 px | Layout de emergência: sidebar vira `Sheet` acionada por botão de menu. Todas as telas funcionam em coluna única; A1 (upload) e A4 (painel) ficam confortáveis; A2 fica utilizável mas com aviso "Revisar é mais fácil numa tela maior." (`Alert` informativo, fechável). |

Regras:

- Densidade: linhas de tabela 44 px; alvos de ação em tabela ≥ 32 × 32 px com espaçamento 8 px (WCAG 2.5.8 Tamanho mínimo do alvo) e ≥ 44 px em toque.
- Textarea de texto simples (A2) cresce com o conteúdo até 60 % da altura da viewport, depois rola.
- Zoom 200 % em 1280 px equivale a 640 px: cai na regra de < 768 px, sem perda de função.
- Sem rolagem horizontal de página; só dentro de `ScrollArea` de tabelas.

## Público (`/verify/{id}`)

- Coluna única `max-width: 720px`. Hash e JSON em blocos `<pre>` com `overflow-wrap: anywhere` (hash) e rolagem horizontal interna só no JSON. Botões "Copiar" ao lado de cada bloco.
- Mobile: passos de conferência em lista numerada; comandos em blocos de largura total.

## Impressão (C6 "Salvar comprovante", V1)

- `@media print`: some banner, barra inferior, VLibras; fica ReceiptCard com hash completo, QR 40 mm, data/hora, nome do advogado e OAB, e o texto "Este código prova…". Página A4 ou A5 em coluna única. Sem cabeçalho/rodapé do navegador (`@page { margin: 16mm }`).
- O PDF gerado não pode carregar metadados (Producer/Creator/Author/datas); ver nota em screen-08.
