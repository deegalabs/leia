# Coerência da marca LeIA

> Fase: audit | Marca: LeIA | Gerado: 2026-09-15

---

## Nota por dimensão

| Dimensão | Nota | Leitura curta |
|---|---|---|
| Coerência da estratégia | 4 | Promessa, postura e limite são uma coisa só e aparecem na interface |
| Estratégia ↔ visual | 3 | O visual nasceu de um JPG, não da estratégia, e acerta por sorte em quase tudo |
| Consistência interna do sistema | 2 | Camada de cor sólida, camadas de tipo, espaço e layout sem sistema |
| Coerência de voz | 3 | Excelente na jornada da cidadã, quebra no painel e no comprovante |
| Documentado ↔ aplicado | 2 | Três superfícies em produção, duas fora da marca |

**Coerência geral: 2,8 / 5.**

## Documentado contra aplicado, token a token

`docs/brand/tokens.css` e `apps/web/app/tokens.css` são **byte a byte idênticos** (`diff` vazio). A hipótese de deriva de token entre marca e código está derrubada: o problema não é divergência de valor, é token declarado e nunca chamado.

Mortos ou quase: `--font-lawyer` (0 usos, e a IBM Plex Sans nem é carregada em `layout.tsx:6-8`), `--text-citizen-body` (0), `--text-citizen-title` (0), `--size-target` (0), `--size-mic` (0), `--color-ink-3` (1). Cinco dos 26 tokens de `@theme` não existem na prática, e o bloco `.dark` inteiro, 12 variáveis, é acionado por uma única classe em `app/page.tsx:38`.

O que a documentação promete e o código não faz:

- `docs/brand/README.md:10` diz navy no "painel do advogado (barra lateral)". Não há barra lateral: `grep '<aside\|sidebar'` só encontra `DocsShell.tsx`, que é a documentação. O painel é `Panel.tsx:14`, `<Page wide>`, fundo `paper-2`, igual ao da cidadã.
- `docs/brand/README.md:35` lista o favicon 32 px como pendente. Continua pendente: `apps/web/public/` tem 3 PNGs de app e nenhum favicon.
- `docs/brand/buttons.md:29` manda anel de foco `teal-deep` no claro. `tokens.css:54` e `globals.css:20` aplicam `--ring: var(--color-ink)`, navy. Os dois documentos de marca se contradizem entre si; o código segue o token.
- `docs/brand/buttons.md:11` define o botão discreto como borda 1 px `line` e texto `ink-3` peso 400. `ui.tsx:11` implementa `ghost` como texto `teal-deep` sublinhado, sem borda, 44 px. É outro componente.
- `docs/brand/buttons.md:20` e `icons.md:14` especificam microfone de 64 px e gravação de resposta. Não existe `Mic` em lugar nenhum do app: a cidadã ouve (`SpeakButton`, `ui.tsx:83`) mas não fala.
- `docs/brand/icons.md:6` proíbe emoji. `Journey.tsx:231` usa o glifo `✓` como ícone enquanto a linha 214, na mesma tela, usa o `Check` do Lucide.
- `docs/brand/leia-theme.css` e `leia-icons.svg` foram copiados para `apps/llm-service/static/`, mas só 3 dos 10 templates servidos os carregam (`templates/leia/cliente.html:8`, `comprovante.html:7`, `verify.html:7`). Os outros 7 continuam com a paleta dourada sobre preto e 54 emojis.
- `docs/brand/copy-replacements.md:27` manda tirar "Rodada N · X/Y acertos" da tela da cidadã. `messages/pt-BR.json:266` mantém `"attemptLine": "Rodada {n}: {acertos} de {total}"` e `Receipt.tsx:31` escreve "Tentativa {n}, {n} perguntas respondidas" no comprovante dela.
- `docs/brand/copy-replacements.md:39` troca caixa alta por sentence case. `DocsShell.tsx:32` e `:84` e `globals.css:62` reintroduzem `uppercase tracking-wide`.
- `docs/design/INDEX.md:11-26` desenha 14 telas em rotas `/c/{token}` e `/lawyer/...`. O produto usa `/t/[hash]`, `/painel`, `/enviar`, `/entrar`, `/comprovante`, `/verify`. A arquitetura de informação documentada não é a construída.
- `docs/design/INDEX.md:44` diz que a cidadã nunca vê número. `Journey.tsx:157` mostra `ScoreChip`, que renderiza "confiança 87%" (`InferenceMarks.tsx:52`).

O que o código faz e a documentação não registra: `.dark` como tema semântico, `docs-prose` inteiro (48 linhas de CSS de documentação em `globals.css:26-66`), `UpdatePrompt`, `Mermaid`, `Preparing` com 14 etapas, e o fluxo sem perguntas (`Journey.tsx:63`).

## A tensão das duas personas

A resposta honesta: **hoje a identidade serve bem uma persona só, a cidadã.**

O BRIEF diz que a tensão é resolvida com duas superfícies, clara para a cidadã e navy para marca, comprovante e trilho profissional. No código não é isso:

- O comprovante não é navy. `Receipt.tsx:22` usa `<Page>`, fundo `paper-2`, e `Card` branco. O navy aparece só na faixa de 56 px do `AssistantBanner`.
- Não existe trilho profissional. O advogado recebe a mesma casca, com 200 px a mais de largura (`ui.tsx:125`, `wide` = 760 px contra 560/680 px).
- `Panel.tsx:48-50` renderiza cartões sempre, para cidadã e advogado. O painel em tabela no computador, prometido no BRIEF, não foi escrito.
- Não há diferenciação tipográfica: `--font-lawyer` existe no token e em lugar nenhum além dele. O advogado lê Atkinson Hyperlegible a 17 px, fonte escolhida para baixa escolaridade, num monitor.
- `buttons.md:21` prevê botão de 40 px e fonte 14 px para o advogado. `Panel.tsx:73` e `:75` usam 48 px e a mesma escala da cidadã.

O resultado não é ruim para o advogado, é indistinto. Ele recebe a interface da cidadã esticada. Para a persona que precisa de "densidade de informação, controle, responsabilidade" isso custa: um painel de trabalho a 760 px em tela de 1440 px devolve leitura linear onde se pedia lista e detalhe lado a lado. A única separação real hoje é de rota, não de identidade.

## Acessibilidade como identidade

Recalculei os pares principais. Três números de `docs/brand/README.md` estão errados, e a própria auditoria interna do repositório já discordava deles:

| Par | README | Recalculado | `accessibility-audit.md` |
|---|---|---|---|
| paper sobre navy | 15,8:1 | 15,78:1 | 15,8:1 |
| teal sobre navy | 6,0:1 | **6,31:1** | 6,3:1 |
| branco sobre teal | 2,9:1 | 2,86:1 | reprova |
| teal sobre off-white | 2,7:1 | **2,50:1** | não consta |
| branco sobre teal-deep | 5,6:1 | 5,59:1 | 5,6:1 |
| teal-deep sobre off-white `#F0F0E8` | 5,3:1 | **4,88:1** | 4,9:1 |
| teal-deep sobre paper-2 `#FAF8F4` | não consta | 5,27:1 | 5,3:1 |
| pend sobre pend-soft | 7,0:1 | 6,98:1 | 7,0:1 |

Nenhum erro inverte um veredito, mas `README.md:23` mistura os dois off-whites: a razão de 5,3:1 vale contra `#FAF8F4`, não contra o `#F0F0E8` que a linha 11 define como off-white. Contra `#F0F0E8` são 4,88:1, ainda AA, sem folga.

Fora da tabela, dois pares não declarados merecem decisão:

- `ink-3 #6B7480` sobre `paper-2` dá **4,46:1** e reprova AA para texto normal. Está vivo em `Preparing.tsx:18`, a tela de espera da cidadã.
- `ok #1F7A4D` sobre `ok-soft #DDF1E6` dá 4,51:1, aprovado por 0,01.

A fonte de corpo não é honrada em todos os lugares. O texto do documento, que é o objeto central da promessa, é renderizado em IBM Plex Mono a `0.92rem`, cerca de 14,7 px (`InferenceMarks.tsx:41`), e a cidadã chega nele pelo botão "Ver o documento com as marcações" (`Journey.tsx:165`). O trecho citado também é mono a `0.95rem` (`Journey.tsx:153`). A pesquisa pede 18 px de piso para essa persona (`docs/research/project/accessibility-patterns.md:76`); a base do produto é 17 px e a menor escala em uso é `0.8rem`, 12,8 px, em `DocsShell.tsx:32`.

Pior: `InferenceMarks.tsx:43` aplica `no-underline` no `<mark>` e pinta o fundo com cor vinda da API. Isso derruba de uma vez a regra de `docs/brand/README.md:41` ("cor de fundo sozinha não basta") e o que `globals.css:21` tinha resolvido certo.

Alvos de toque: 18 elementos abaixo dos 48 px declarados. 16 em 44 px, 1 em 40 px (`DocsShell.tsx:51`), 1 em 36 px (`ReviewView.tsx:147`).

## Sistema de marca contra sistema de layout

Contradição confirmada, com números:

| Camada | Estado |
|---|---|
| Cor | 17 tokens, adoção alta (57 usos de teal-deep, 73 de ink-2), 5 hexes fora do sistema |
| Tipo | 2 tokens de tamanho mortos, 15 tamanhos arbitrários em 149 ocorrências |
| Forma | 2 tokens de raio (32 usos) e 4 raios arbitrários (14 usos) |
| Alvo | 1 token morto, 6 alturas distintas em 46 ocorrências |
| Largura | 5 larguras (`420`, `560`, `680`, `760`, `1100` px) em 6 arquivos, nenhuma em token |
| Breakpoint | 44 usos de `sm:`/`md:`/`lg:` em 11 arquivos, sem ponto de virada único |
| Layout raiz | `app/layout.tsx:25` é `<body className="min-h-full flex flex-col">`, sem casca, sem contêiner, sem cabeçalho |

O BRIEF falava em "44 usos de breakpoint" e "cinco larguras diferentes em oito arquivos". O primeiro número confere exatamente. O segundo é 5 larguras em 6 arquivos, não 8, e a concentração é pior do que parece: `DocsShell.tsx` sozinho detém 16 dos 44 breakpoints, e `Journey.tsx`, a tela mais importante do produto, tem 1.

## Voz

O que funciona e é raro: erro que não culpa ("Deu um problema do nosso lado, não foi você", `Journey.tsx:51`), reprovação que não reprova ("Vamos ver de novo", `Journey.tsx:240`), limite declarado em toda tela, "Você não assina nada aqui" (`Journey.tsx:131`), e as 11 respostas do FAQ em `page.tsx:20-32`, que explicam hash e carimbo de tempo sem uma palavra técnica.

Frases concretas que violam a promessa de português simples:

| Frase | Arquivo e linha | Por quê |
|---|---|---|
| "Consentimento esclarecido com registro" | `messages/pt-BR.json:5` | Termo de bioética, opaco para quem tem ensino fundamental |
| "Rodada {n}: {acertos} de {total}" | `messages/pt-BR.json:266` | Vocabulário de prova, vetado em `copy-replacements.md:27` e `:45` |
| "Tentativa {n}, {n} perguntas respondidas" | `Receipt.tsx:31` | Mesma coisa, na tela de maior carga emocional |
| "confiança {pct}%" | `messages/pt-BR.json:398` via `Journey.tsx:157` | Número de máquina para a cidadã, contra `docs/design/INDEX.md:44` |
| "resposta insuficiente em 2 tentativas" | `messages/pt-BR.json:148` | Julga a pessoa, não a explicação |
| "Canivete suíço para advogados" | `apps/llm-service/templates/index.html:6` | Reposiciona o produto no advogado e desmonta a tese |
| "Responda com suas palavras, do seu jeito" | `messages/pt-BR.json:93` | Promessa de resposta aberta que o produto não cumpre: `Journey.tsx:183-190` é múltipla escolha A/B/C/D |

A última é a mais grave, porque não é escolha de palavra: a voz documentada descreve um produto de reflexão aberta e a interface entrega um quiz.

---

## Related

- [brand-inventory.md](./brand-inventory.md)
- [equity-analysis.md](./equity-analysis.md)
- [evolution-map.md](./evolution-map.md)
- [../BRIEF.md](../BRIEF.md)
