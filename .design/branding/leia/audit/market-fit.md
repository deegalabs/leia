# Aderência de mercado

> Fase: audit | Marca: LeIA | Gerado: 2026-09-15

---

## Aviso de procedência

Toda a pesquisa de mercado disponível foi feita em 2026-09-11 para uma marca chamada **ConsentChain**, não LeIA (`docs/research/market/INDEX.md:1`). O nome mudou depois, e a identidade aplicada nasceu de uma logo entregue em 12/09 (`docs/brand/README.md:3`). Ou seja: o sistema visual não foi derivado desta pesquisa. A aderência abaixo é uma verificação a posteriori, não o registro de uma decisão informada.

Estilos visuais de concorrentes marcados `[NÃO VERIFICADO]` na pesquisa continuam não verificados aqui. Não há qualquer medição de reconhecimento de marca do LeIA; nenhuma foi feita e nenhuma é alegada.

## Posição contra concorrentes reais

Da `competitive-audit.md`, os players com estilo visual confirmado:

| Concorrente | Cor dominante | O que faz | Onde o LeIA se separa |
|---|---|---|---|
| Clicksign | Laranja e branco | Assinatura B2B alto volume | O laranja é o único fora do azul; LeIA não disputa esse espaço |
| ZapSign | Azul e branco | Assinatura fácil, WhatsApp | Mesmo azul SaaS de que a pesquisa manda fugir |
| Autentique | Azul e branco | Assinatura no setor público | Idem |
| Docusign BR | Navy e roxo | Desde 01/2026 resume e responde em linguagem simples | **Concorrente direto na promessa e na cor.** Navy contra navy |
| gov.br Assinatura | Azul `#1351B4`, Rawline | Assinatura estatal | Institucional; LeIA empresta a gravidade sem virar app de governo |
| i-agree (UK) | Pêssego e azul | Consentimento com confirmação falada | Mais quente que o LeIA; não avalia compreensão |
| OriginalMy | Clean, muito branco | Prova de integridade em blockchain | LeIA tem superfície mais quente e mais texto |
| Astrea/Aurum | Ilustração, sans acessível | Traduz juridiquês de andamentos | Fala com o cliente pelo advogado, não com o cidadão |

O navy `#081820` é a decisão de cor mais arriscada do sistema. Ele é quase preto (luminância 0,0087) e coloca o LeIA no mesmo território cromático do Docusign, que é o concorrente que acabou de anunciar exatamente a promessa vizinha. A separação real não vem da cor, vem do teal `#38A8A8` do selo e da superfície de papel `#FAF8F4`, que nenhum dos oito acima usa.

## Contra a direção de mood board pesquisada

`mood-board-direction.md` prescreveu papel quente `#FAF8F3`, azul de confiança `#1B4D89`, terracota de voz `#B5502C`, teal de verificação `#0F6B6B`, Atkinson Hyperlegible Next + Lexend, e onda sonora como motivo primário. O que foi aplicado é outra coisa. Checando item a item:

| Princípio pesquisado | Situação |
|---|---|
| Uma coisa por tela | Cumprido. `Journey.tsx` é um passo por vez, sem painel lateral |
| Voz antes do texto | **Meio cumprido.** Há TTS (`ui.tsx:83`) e nenhum STT. A onda sonora, motivo gráfico primário da pesquisa, não existe |
| Calor de papel, sem brilho de app | Cumprido no claro (`#FAF8F4`, sem gradiente, sem vidro) |
| Dignidade institucional no artefato | **Não cumprido.** O comprovante é branco sobre papel (`Receipt.tsx:22-37`), não o cartão de fundo escuro com selo previsto |
| Sem clichês jurídicos, nada de balança | **Violado.** `docs/brand/icons.md:51` atribui `Scale`, a balança, ao advogado |
| Nada de laranja Bitcoin nem hexágono | Cumprido. A cadeia aparece como "código do registro" e "carimbo", nunca como cripto |
| AA como piso, AAA na jornada da cidadã | **Não cumprido.** O par de ação mais usado dá 5,27:1, AA e não AAA; `ink-3` dá 4,46:1 e reprova AA |
| Texto da cidadã ≥ 18 px, alvo ≥ 48 px | **Não cumprido.** Base 17 px; 18 alvos abaixo de 48 px |
| Sem caixa alta | **Violado** em `DocsShell.tsx:32`, `:84` e `globals.css:62` |

A troca de paleta em si defende-se bem: o navy e o teal saíram da logo real, e o teal de verificação da pesquisa (`#0F6B6B`) e o teal de ação aplicado (`#1F7373`) são praticamente o mesmo tom. O que se perdeu foi o acento único de ação por voz, o terracota, que na pesquisa era o que impedia a interface de virar mais um SaaS azul. Hoje o teal acumula três papéis: marca, ação e verificação. Quando tudo é teal, o "verificado" para de significar.

## Tendências

Contra a síntese de `trend-analysis.md:95-101`:

| Tendência | Sinal pedido | LeIA emite? |
|---|---|---|
| Linguagem simples | Frases curtas, ícones funcionais, sem tom infantil | Sim. O FAQ de `page.tsx:20-32` é o melhor artefato de voz do produto |
| Copilotos confiáveis | Citação da cláusula-fonte, "revisado pelo advogado" | Sim, e é o núcleo: `Journey.tsx:148-157` mostra trecho e selo de conferido |
| Prova como carimbo | Selo, QR, verificador em pt-BR, sem jargão de rede | Sim: `Receipt.tsx:32`, `/verify`. Mas `messages/pt-BR.json:200` expõe "Rede de testes (Polygon Amoy)" ao público |
| Voz inclusiva | Microfone central, onda sonora, ouvir de novo | **Não.** Só saída de áudio. Sem microfone, sem onda, sem "ouvir de novo" |
| Consentimento regulado | Escolhas equivalentes, feedback acolhedor | Sim no feedback (`Journey.tsx:240-242`); parcial nas escolhas, já que o caminho sem conta e o com conta não são visualmente equivalentes |

## Lacuna de diferenciação

A pesquisa concluiu que o espaço em branco é o artefato probatório de compreensão, e que ninguém no Brasil o ocupa (`competitive-audit.md` §4). A marca hoje comunica **explicação**, não **prova**:

- O H1 da landing (`page.tsx:45`) vende entendimento. A prova aparece no quarto passo de "Como funciona" (`page.tsx:11`) e no FAQ.
- O ativo que carrega a diferenciação, o comprovante, é a tela com menos investimento de marca de todo o produto: sem navy, sem selo, sem tipografia de documento. Um cartão branco com QR.
- O selo do símbolo, que é literalmente o diferencial desenhado na logo, aparece em tamanho de ícone uma única vez na jornada (`Journey.tsx:111`, 28 px).

Contra o BRIEF, que declara "a marca precisa comunicar prova, não resumo", a execução atual comunica resumo.

## Risco de reposicionamento

`apps/llm-service/templates/index.html:6` serve, em produção, a página com título "LeIA · Canivete suíço para advogados", em dourado sobre preto, com 28 emojis. Qualquer pessoa que chegue por essa rota encontra um produto diferente, para outra persona, com outra identidade. Isso não é dívida de estilo, é contradição de posicionamento com a decisão registrada de que o cidadão está no centro.

---

## Related

- [brand-inventory.md](./brand-inventory.md)
- [coherence-assessment.md](./coherence-assessment.md)
- [equity-analysis.md](./equity-analysis.md)
- [evolution-map.md](./evolution-map.md)
