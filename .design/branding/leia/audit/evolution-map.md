# Mapa de evolução

> Fase: audit | Marca: LeIA | Gerado: 2026-09-15

---

Entregável principal da auditoria. 45 elementos, decisão elemento a elemento, justificativa amarrada às três personas do [BRIEF](../BRIEF.md): **Cidadã** (principal), **Advogado** (supervisão), **Verificador**.

## Marca verbal

| # | Elemento | Estado atual | Decisão | Justificativa |
|---|---|---|---|---|
| 1 | Nome LeIA | Aplicado em tudo | PRESERVAR | Funciona falado, que é como a Cidadã ouve do Advogado. Imperativo "leia" + assinatura da IA em quatro letras |
| 2 | Tagline "Leia antes de assinar." | `messages/pt-BR.json:4`, invisível na interface | PRESERVAR | Frase mais clara que o produto tem. Para a Cidadã ansiosa, diz o que fazer e quando; falta só usá-la |
| 3 | Subtítulo "Consentimento esclarecido com registro" | `messages/pt-BR.json:5` | SUBSTITUIR | Termo de bioética. A Cidadã de baixa escolaridade não decodifica nenhuma das três palavras |
| 4 | Banner de limite da assistente | `ui.tsx:58`, em toda tela da Cidadã | PRESERVAR | É a única constante visual do produto e cumpre a vedação da Ordem sem nota de rodapé |
| 5 | Voz de erro e de não aprovação | `Journey.tsx:51` e `:240` | PRESERVAR | "Não foi você" e "Vamos ver de novo" protegem a Cidadã com medo de decidir errado. Nenhum concorrente mapeado fala assim |
| 6 | "Rodada", "Tentativa", "acertos", "confiança {pct}%" | `messages/pt-BR.json:266` e `:398`, `Receipt.tsx:31`, `Journey.tsx:157` | SUBSTITUIR | Vocabulário de prova escolar, vetado em `copy-replacements.md:27` e em `docs/design/INDEX.md:44`. Transforma o comprovante da Cidadã em boletim |
| 7 | "Canivete suíço para advogados" | `apps/llm-service/templates/index.html:6`, em produção | SUBSTITUIR | Reposiciona o produto no Advogado e desmonta a tese do cidadão no centro para quem chegar por essa rota |
| 8 | "Responda com suas palavras, do seu jeito" | `messages/pt-BR.json:93` contra múltipla escolha em `Journey.tsx:183-190` | EVOLUIR | A voz promete reflexão e a interface entrega quiz. Alinhar os dois: ou a copy descreve a escolha, ou a escolha vira resposta aberta |

## Identidade gráfica

| # | Elemento | Estado atual | Decisão | Justificativa |
|---|---|---|---|---|
| 9 | Símbolo documento com selo | `logo-mark.svg`, 1 uso na jornada | PRESERVAR | Lê-se sem legenda e sem clichê jurídico. É a representação gráfica do diferencial que o Verificador precisa reconhecer |
| 10 | Wordmark "Le" claro + "IA" teal | 5 usos, via SVG com fonte viva | PRESERVAR | Decisão revista na confirmação: o destaque em "IA" é o que torna o nome legível como Lei mais IA, e sem ele sobra "Leia". O posicionamento de prova mora no comprovante e na verificação, não no wordmark. Converter em curvas continua sendo tarefa técnica, não mudança de decisão |
| 11 | `logo-horizontal-light.svg` | Em `public/`, zero uso em código | EVOLUIR | Só a versão escura é usada, o que força faixa navy em toda tela. Sem versão clara viva, não existe cabeçalho leve para a Cidadã |
| 12 | Ícones do app 192/512/maskable | `manifest.ts:19-23` | PRESERVAR | O piso é celular básico; a instalação como app já funciona e é o caminho de retorno da Cidadã |
| 13 | Favicon 32 px | Não existe; listado como pendente em `README.md:35` | EVOLUIR | A aba do navegador é onde o Verificador e o Advogado guardam o link de conferência |
| 14 | Ícone `Scale`, a balança, para o Advogado | `docs/brand/icons.md:51` | SUBSTITUIR | Clichê jurídico expressamente vetado em `mood-board-direction.md` §1.5 e §4. Contradiz o próprio princípio da marca |
| 15 | Glifo `✓` e 54 emojis | `Journey.tsx:231`; `templates/*.html` | SUBSTITUIR | `icons.md:6` proíbe emoji porque varia por aparelho e o leitor de tela lê de forma inconsistente, o que atinge direto a Cidadã com TalkBack |

## Cor

| # | Elemento | Estado atual | Decisão | Justificativa |
|---|---|---|---|---|
| 16 | Navy `#081820` | 15 usos como classe, tema do PWA | PRESERVAR | Dá gravidade institucional ao artefato que o Verificador confere. Preservar com ressalva: ocupa o mesmo território do Docusign |
| 17 | Paper `#F0F0E8` e paper-2 `#FAF8F4` | 24 usos | PRESERVAR | O papel quente é o que separa o LeIA do branco e do azul dos oito concorrentes, e reduz ofuscamento para a Cidadã que lê no celular |
| 18 | Regra teal claro no escuro, teal escuro no claro | `tokens.css:9-10`, 60 usos | PRESERVAR | Resolve em uma frase o problema de contraste criado pela logo. Medida e aplicada |
| 19 | Teal acumulando marca, ação e verificação | `teal-deep` em 57 usos, incluindo o selo "trecho conferido" | EVOLUIR | Se tudo é teal, "conferido" para de significar. O Verificador precisa de um sinal exclusivo de verificação |
| 20 | Destaque do trecho por cor de fundo | `InferenceMarks.tsx:43` com `no-underline` e cor vinda da API | SUBSTITUIR | Derruba a regra de `README.md:41` e o acerto de `globals.css:21`. Cor sozinha dá 1,09:1 contra o papel: a Cidadã com baixa visão não vê marcação nenhuma |
| 21 | `ink-3 #6B7480` | 1 uso, em `Preparing.tsx:18` | SUBSTITUIR | 4,46:1 sobre paper-2 reprova AA para texto normal, numa tela de espera que a Cidadã olha por minutos |
| 22 | Cinco hexes fora do token | `#195C5C`, `#4FBDBD`, `#8A1C1C`, `#F1F8F8` em 6 linhas | EVOLUIR | Todos passam em contraste, nenhum está no sistema. Promover a token de estado e remover os literais |
| 23 | Bloco `.dark`, 12 variáveis | Acionado por `app/page.tsx:38` apenas | EVOLUIR | Ou vira a superfície profissional do Advogado e do comprovante que o BRIEF promete, ou sai. Manter 12 variáveis para uma seção é custo sem retorno |
| 24 | Paleta dourada sobre preto | `#c9a84c`, `#e8cf82` sobre `#0b0d14` em 7 templates servidos | SUBSTITUIR | Terceira identidade viva em produção. Herança do produto anterior, sem lastro nenhum |

## Tipografia

| # | Elemento | Estado atual | Decisão | Justificativa |
|---|---|---|---|---|
| 25 | Atkinson Hyperlegible no corpo | `layout.tsx:7`, `globals.css:14` | PRESERVAR | Única escolha do sistema que responde a uma restrição real da Cidadã, e não a gosto. Trocar é rebaixar acessibilidade de propósito |
| 26 | Archivo no display | `globals.css:19` | PRESERVAR | Coerente com o wordmark e com a gravidade que o Advogado espera nos títulos |
| 27 | IBM Plex Mono no texto do documento | `InferenceMarks.tsx:41` a `0.92rem`, `Journey.tsx:153` a `0.95rem` | SUBSTITUIR | Cerca de 14,7 px em monoespaçada no objeto central da promessa. A Cidadã chega ali por `Journey.tsx:165`. Mono fica para hash e código |
| 28 | `--font-lawyer` IBM Plex Sans | Declarado em `tokens.css:27`, fonte nunca carregada, zero uso | SUBSTITUIR | Ou carrega e diferencia a superfície do Advogado, ou sai do token. Hoje é promessa morta |
| 29 | Base de 17 px | `globals.css:15` | EVOLUIR | A pesquisa pede 18 px de piso para a Cidadã (`accessibility-patterns.md:76`). Um ponto separa a escolha da conformidade |
| 30 | Escala de 15 tamanhos arbitrários | 149 ocorrências `text-[...]`; `--text-citizen-body` e `--text-citizen-title` com zero uso | SUBSTITUIR | Não existe escala, existe acúmulo. O menor valor, 12,8 px em `DocsShell.tsx:32`, é ilegível para a persona declarada |

## Sistema, layout e artefatos

| # | Elemento | Estado atual | Decisão | Justificativa |
|---|---|---|---|---|
| 31 | `tokens.css` espelhado em docs e app | Arquivos idênticos byte a byte | PRESERVAR | Fonte única de verdade cromática, já provada. Automatizar a cópia, não refazer |
| 32 | Primitivas de `ui.tsx` | `Button`, `Card`, `BottomActionBar`, `StatusChip`, `SpeakButton` | PRESERVAR | `BottomActionBar` e `StatusChip` carregam a regra de no máximo duas ações e de nunca julgar a Cidadã em vermelho |
| 33 | Sistema de largura | 5 valores (`420`, `560`, `680`, `760`, `1100` px) em 6 arquivos, nenhum em token | SUBSTITUIR | 680 px a 17 px dá cerca de 76 caracteres por linha, contra o limite de 60 da pesquisa. E 760 px é tudo o que o Advogado ganha num monitor |
| 34 | 44 usos de breakpoint em 11 arquivos | `DocsShell.tsx` concentra 16; `Journey.tsx` tem 1 | SUBSTITUIR | Sem ponto de virada único, cada tela inventa a sua. A tela mais importante da Cidadã é a menos responsiva do produto |
| 35 | Layout raiz | `app/layout.tsx:25`, sem casca, contêiner ou cabeçalho | EVOLUIR | É o lugar certo para as duas cascas e o contêiner. Está vazio porque nada foi decidido, não porque a decisão foi ser vazio |
| 36 | Alvo de toque | `--size-target: 48px` com zero uso; 18 alvos abaixo (16 em 44 px, 1 em 40, 1 em 36) | SUBSTITUIR | A Cidadã usa uma mão, em pé, com pressa. O piso declarado precisa ser o piso aplicado |
| 37 | Raio | 2 tokens (32 usos) e 4 raios arbitrários (14 usos) | EVOLUIR | O sistema existe e está quase inteiro; falta fechar os quatro vazamentos |
| 38 | Duas cascas, Cidadã e Advogado | Não existem. `Panel.tsx:14` usa a mesma casca, 200 px mais larga | SUBSTITUIR | É a decisão central do BRIEF e nunca foi construída. Hoje o Advogado recebe a interface da Cidadã esticada, sem densidade, sem tabela, sem trilho |
| 39 | Camada i18n | `pt-BR.json` com 401 linhas, 199 chamadas, em 11 de 18 arquivos com texto | EVOLUIR | Metade da jornada está fora, então a voz da marca não tem um lugar único onde ser revisada |
| 40 | Comprovante como artefato de marca | `Receipt.tsx:22-37`: cartão branco, sem navy, sem selo, sem tipografia de documento | SUBSTITUIR | É o que a Cidadã leva embora e o que o Verificador abre. É o ativo que mais poderia gerar equidade e é o menos desenhado do produto |
| 41 | `leia-theme.css` e `leia-icons.svg` | Aplicados em 3 dos 10 templates servidos | EVOLUIR | O trabalho está feito e parado no meio. Terminar custa pouco e apaga a terceira identidade |
| 42 | `buttons.md` contra `ui.tsx` | Anel de foco e botão discreto divergem | EVOLUIR | Dois documentos de marca se contradizem entre si. O código está certo; a documentação precisa alcançá-lo |
| 43 | `icons.md` | 60 mapeamentos para 14 arquivos que importam Lucide | EVOLUIR | Boa base, escrita para um produto com voz e microfone que não existe. Enxugar para o que é real |
| 44 | `copy-replacements.md` | Mapa de 6 templates; violações vivas em `messages/pt-BR.json` | EVOLUIR | Vira regra de revisão contínua da voz, não tabela de mutirão de um dia |
| 45 | `docs/design/` | 14 telas em rotas `/c/{token}` e `/lawyer/...` que não existem | SUBSTITUIR | A arquitetura de informação documentada não é a construída. Documento assim atrapalha mais do que orienta |

## Conflito resolvido na confirmação

Duas pesquisas do projeto divergiam sobre a largura da coluna de leitura. A auditoria apontou 76 caracteres por linha
a 680 px, contra o limite de 60 da pesquisa de acessibilidade; a pesquisa de interface propôs 760 px de coluna de
leitura. Decisão: para a jornada da cidadã vale a coluna estreita, porque a leitura é linear, a persona tem baixa
escolaridade e o piso é celular. Os 760 px servem à documentação, não à jornada. A fase de design recebe isso
resolvido e não deve reabrir.

## Resumo

| Decisão | Itens | Percentual |
|---|---|---|
| PRESERVAR | 14 | 31,1 % |
| EVOLUIR | 14 | 31,1 % |
| SUBSTITUIR | 17 | 37,8 % |
| **Total** | **45** | **100 %** |

Onde a preservação se concentra: marca verbal (4 de 8) e cor de base (3 de 9). Onde a substituição se concentra: sistema de layout (5 de 15) e tipografia (3 de 6). A leitura é direta: **a marca está certa, o sistema que a aplica não existe.**

Sequência sugerida para as fases seguintes: 38 e 33 primeiro, porque as duas cascas e o sistema de largura destravam 34, 35 e 37; depois 40, porque o comprovante é onde a diferenciação vive; depois 30, 29 e 27, que fecham a tipografia; 24, 7 e 15 podem correr em paralelo, já que são limpeza de superfície legada.

---

## Related

- [brand-inventory.md](./brand-inventory.md)
- [coherence-assessment.md](./coherence-assessment.md)
- [market-fit.md](./market-fit.md)
- [equity-analysis.md](./equity-analysis.md)
- [../BRIEF.md](../BRIEF.md)
