# Marca LeIA

Logo recebida em 12/09/2026: documento com três linhas e selo de verificação em teal, wordmark "Le" em off-white e "IA"
em teal, sobre azul-marinho. Arquivo: [logo-dark.jpg](logo-dark.jpg) (1280 × 597). Leitura: o documento é o contrato; o
selo é a verificação de que foi entendido; "IA" em destaque diz onde a inteligência artificial entra.

## Paleta (extraída da logo)
| Papel | Hex | Uso |
|---|---|---|
| Marinho | `#081820` | fundo da marca, tela de abertura, ícone do aplicativo, painel do advogado (barra lateral) |
| Off-white | `#F0F0E8` | texto sobre marinho; fundo claro da jornada da cidadã pode usar `#FAF8F4` (mesma família) |
| Teal da marca | `#38A8A8` | "IA" do wordmark, selo, destaques sobre fundo escuro |
| Teal de ação | `#1F7373` | botões primários e links sobre fundo claro (tom escurecido do teal da marca) |

## Contraste (WCAG 2.2)
| Combinação | Razão | Resultado |
|---|---|---|
| off-white sobre marinho | 15,8:1 | AAA |
| teal da marca sobre marinho | 6,0:1 | AA texto normal |
| branco sobre teal da marca `#38A8A8` | 2,9:1 | reprova para texto: não usar em botão com texto branco |
| teal da marca sobre off-white | 2,7:1 | reprova para texto: só para ícones grandes ou decoração |
| branco sobre teal de ação `#1F7373` | 5,6:1 | AA texto normal: botões primários |
| teal de ação sobre off-white | 5,3:1 | AA: links e rótulos |

Regra: o teal claro da logo vive no escuro; no claro, a ação usa o teal escuro. Marinho e off-white fazem o resto.

## Ativos a produzir
- Versão para fundo claro (wordmark em marinho, "IA" em `#1F7373`).
- Ícone do aplicativo (PWA): quadrado marinho com o selo, 192 e 512 px, `purpose: maskable`.
- Favicon 32 px com o selo.
- Somente o símbolo (documento + selo) para espaços pequenos.

## Ajustes após a auditoria de acessibilidade (12/09)
- Pendência (âmbar): texto `#7A4800` sobre `#FFF4DD` (7,0:1). O `#B26A00` com texto branco reprova (4,2:1).
- Anel de foco: `outline: 3px solid #081820; outline-offset: 2px` no claro; `#F0F0E8` sobre marinho. O `ring` translúcido do shadcn reprova.
- Destaque do trecho citado: cor de fundo sozinha não basta (1,07:1 contra o papel); combinar com sublinhado ou negrito e texto oculto para leitor de tela.
- Relatórios: `docs/design/critique/accessibility-audit.md` e `accessibility-fixes.md`.
