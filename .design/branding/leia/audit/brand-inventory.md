# Inventário da marca LeIA

> Fase: audit | Marca: LeIA | Gerado: 2026-09-15

---

## Marca verbal

| Elemento | Valor | Onde |
|---|---|---|
| Nome | LeIA (Lei + IA) | `apps/web/app/layout.tsx:11`, `messages/pt-BR.json:3` |
| Tagline | "Leia antes de assinar." | `messages/pt-BR.json:4` (não aparece em nenhuma tela) |
| Subtítulo | "Consentimento esclarecido com registro" | `messages/pt-BR.json:5` (não aparece em nenhuma tela) |
| Descrição meta | "Leia antes de assinar. Entenda cada parte do seu documento em linguagem simples, com registro de que você entendeu." | `apps/web/app/layout.tsx:12` |
| H1 da landing | "Entenda o seu documento jurídico em linguagem simples." | `apps/web/app/page.tsx:45` |
| Limite declarado | "Assistente automática. Explica o que está escrito. Não dá conselho jurídico." | `apps/web/components/ui.tsx:58` |
| Título do painel legado | "LeIA · Canivete suíço para advogados" | `apps/llm-service/templates/index.html:6` |

## Identidade gráfica

| Ativo | Descrição | Arquivo |
|---|---|---|
| Símbolo | Documento de cantos 6 px com três linhas de texto em `#F0F0E8` e selo circular teal `#38A8A8` com check navy | `docs/brand/logo-mark.svg` (64×64) |
| Horizontal escura | Símbolo + "Le" em paper e "IA" em teal, Archivo 800, tracking -1 | `docs/brand/logo-horizontal-dark.svg` (260×64) |
| Horizontal clara | Mesma construção em navy + teal-deep | `docs/brand/logo-horizontal-light.svg` |
| Origem | JPG recebido em 12/09/2026, 1280×597 | `docs/brand/logo-dark.jpg` |
| Ícones do app | 192, 512 e 512 maskable | `apps/web/public/icon-*.png`, `apps/web/app/manifest.ts:19-23` |
| Favicon 32 px | Listado como "a produzir", ainda não existe | `docs/brand/README.md:35` |

Uso real: a versão escura aparece 5 vezes (`ui.tsx:57` e `:106`, `page.tsx:42`, `Verify.tsx:24`, `DocsShell.tsx:22`), o símbolo 1 vez (`Journey.tsx:111`). A versão clara está em `public/` e tem **zero** referência em código.

## Cor

`apps/web/app/tokens.css` traz 54 declarações (26 em `@theme`, 16 em `:root`, 12 em `.dark`), não 51 como diz o BRIEF, que contou linhas e não declarações.

| Papel | Hex | Usos como classe |
|---|---|---|
| navy | `#081820` | 15 |
| paper | `#F0F0E8` | 22 |
| paper-2 | `#FAF8F4` | 2 (é o `--background`) |
| teal | `#38A8A8` | 3 |
| teal-deep | `#1F7373` | 57 |
| teal-soft | `#E3F1F1` | 20 |
| ink | `#081820` | 10 |
| ink-2 | `#3F4B58` | 73 |
| ink-3 | `#6B7480` | 1 (`Preparing.tsx:18`) |
| line | `#E3DED6` | 34 |
| surface | `#FFFFFF` | 17 |
| ok / ok-soft | `#1F7A4D` / `#DDF1E6` | 10 / 2 |
| pend / pend-soft | `#7A4800` / `#FFF4DD` | 4 / 2 |
| danger / danger-soft | `#A8323F` / `#F6E4E6` | 9 / 1 |

Fora do sistema, 5 hexes literais em TSX: `#195C5C` (`ui.tsx:9`, `Panel.tsx:73`), `#4FBDBD` (`page.tsx:48`), `#8A1C1C` (`Journey.tsx:193`), `#F1F8F8` (`Journey.tsx:186`, `AuthForm.tsx:65`). Mais as cores de marcação que chegam da API e entram em `style={{ backgroundColor: sg.item.cor }}` (`InferenceMarks.tsx:43`).

Uma terceira paleta vive nos templates FastAPI legados: dourado `#c9a84c` / `#e8cf82` / `#f0c060` sobre quase preto `#0b0d14` / `#10131c` / `#161a26`, em 7 dos 10 templates servidos.

## Tipografia

| Papel | Fonte | Carregada | Usada |
|---|---|---|---|
| Corpo | Atkinson Hyperlegible 400/700 | `layout.tsx:7` | sim, via `body` em `globals.css:14` |
| Display | Archivo 600/700/800 | `layout.tsx:6` | sim, `h1,h2,h3` em `globals.css:19` |
| Dados | IBM Plex Mono 400/500 | `layout.tsx:8` | 17 usos |
| Advogado | IBM Plex Sans (`--font-lawyer`) | **não** | **zero**, só a declaração em `tokens.css:27` |

Base de 17 px (`globals.css:15`). A escala real é composta por 15 tamanhos arbitrários `text-[...]` em 149 ocorrências, de `0.8rem` a `2.6rem`. Os tokens `--text-citizen-body` e `--text-citizen-title` têm zero uso.

## Componentes e forma

19 componentes em `apps/web/components`, primitivas em `ui.tsx`: `Button` (3 variantes), `LinkButton`, `Card` (3 tons), `BottomActionBar`, `ProgressSteps`, `StatusChip` (4 tons), `AssistantBanner`, `AppHeader`, `HashDisplay`, `CopyButton`, `SpeakButton`, `Field`, `Page`.

Raio: `rounded-button` 19 usos, `rounded-card` 13 usos, mais 14 raios arbitrários em 4 valores (`10px`, `12px`, `14px`, `18px`). Alturas mínimas: 6 valores distintos (`36`, `40`, `44`, `48`, `52`, `56` px) em 46 ocorrências; `--size-target: 48px` e `--size-mic: 64px` têm zero uso.

## Voz

401 linhas em `apps/web/messages/pt-BR.json`, 199 chamadas `m.*` em 11 dos 18 arquivos que contêm texto pt-BR. Tabela de substituição de juridiquês em `docs/brand/copy-replacements.md` (60 linhas, 6 templates). Glossário de 35 termos em `docs/research/project/content-strategy.md`. Zero travessões no código da aplicação.

## Documentação de marca

`docs/brand/`: `README.md` (paleta, contraste, ativos), `tokens.css`, `leia-theme.css` (tema para os templates FastAPI), `buttons.md` (hierarquia, tamanhos, 7 estados), `icons.md` (biblioteca Lucide, 60 mapeamentos), `copy-replacements.md` + `.json`, 3 SVGs, 1 sprite de ícones, 1 JPG.

---

## Related

- [coherence-assessment.md](./coherence-assessment.md)
- [market-fit.md](./market-fit.md)
- [equity-analysis.md](./equity-analysis.md)
- [evolution-map.md](./evolution-map.md)
- [../BRIEF.md](../BRIEF.md)
