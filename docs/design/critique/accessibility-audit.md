# Auditoria de acessibilidade do design — LeIA

Base: WCAG 2.2 AA (AAA onde barato), eMAG 3.1 e LBI art. 63. Insumos: as 14 telas e os 6 documentos compartilhados em `docs/design/`, a pesquisa `docs/research/project/accessibility-patterns.md` e a tabela de contraste em `docs/brand/README.md`. Personas de referência: cidadã com baixa escolaridade em Android básico (TalkBack, fonte do sistema a 130 %, uma mão, rede instável) e advogado em desktop com teclado.

Método: para cada tela, conferi contraste de todos os pares texto/fundo nomeados (razões recalculadas), tamanho de alvos, ordem e visibilidade do foco, anúncios de leitor de tela, operação por teclado, tempo limite, ajuda consistente, entrada redundante, autenticação, reflow a 320 px e texto a 200 %, foco não obscurecido pela barra fixa, mensagens de status, idioma, alternativas ao áudio, nível de leitura, carga cognitiva, VLibras/símbolo e comportamento offline.

## Resumo

| Severidade | Quantidade | O que significa |
|---|---|---|
| Crítico | 6 | Bloqueia a cidadã-alvo ou reprova critério A/AA no fluxo principal |
| Importante | 13 | Reprova critério A/AA em ponto secundário ou degrada muito a experiência assistiva |
| Polimento | 22 | Boas práticas, AAA barato, consistência |

O design está acima da média: um tópico por rota com foco no h1, `aria-pressed`, live regions pareadas, `scroll-padding-bottom`, sem tempo limite, ajuda no mesmo lugar, transcrição editável e texto visível para todo áudio. Os problemas críticos são de especificação faltante (anel de foco, alturas fixas) e de comportamento real do Android (autoplay contra o TalkBack, `SpeechRecognition` que para sozinho, voz pt-BR ausente).

## Contraste recalculado (WCAG 2.x, luminância relativa)

| Par (frente sobre fundo) | Onde | Razão | Veredito |
|---|---|---|---|
| `#F0F0E8` sobre `#081820` | banner, sidebar, painel esquerdo de A0 | 15,8:1 | AAA |
| `#38A8A8` sobre `#081820` | "Falar com o advogado", "IA" do wordmark, barra do item ativo | 6,3:1 | AA texto; 3:1 não-texto ok |
| branco sobre `#1F7373` | botão primário, chip "em andamento" | 5,6:1 | AA |
| `#1F7373` sobre `#FAF8F4` | botão outline, links, ghost | 5,3:1 | AA (borda 3:1 ok) |
| `#1F7373` sobre `#F0F0E8` | fundo lateral em ≥ 768 px | 4,9:1 | AA |
| branco sobre `#195E5E` | hover do primário | 7,5:1 | AAA |
| branco sobre `#1F7A4D` | chip "entendido", "registrado" | 5,3:1 (o plano diz 5,9) | AA |
| `#1F7A4D` sobre `#FAF8F4` | selo "trecho conferido" | 5,0:1 | AA |
| `#1F7A4D` sobre `#EAF4F4` | check dentro do card | 4,7:1 | AA (no limite) |
| branco sobre `#B26A00` | chips "carimbo pendente", "marcado para o Dr. João", FeedbackCard pendente | **4,2:1** (o plano diz 4,6) | **Reprova** texto 15 px; passa só em texto grande e não-texto |
| `#7A4800` sobre `#FFF4DD` | alternativa para chips âmbar | 7,0:1 | AAA |
| `#7A4800` sobre branco | alternativa no painel | 7,6:1 | AAA |
| branco sobre `#9A5B00` | alternativa de fundo âmbar | 5,4:1 | AA |
| `#1A1D1F` sobre `#FAF8F4` | texto corpo | 16,0:1 | AAA |
| `#1A1D1F` sobre `#EAF4F4` | cards lembrete/apresentação | 14,8:1 | AAA |
| `#1A1D1F` sobre `#FFF4DD` | aviso de C5 | 15,5:1 | AAA |
| `#1A1D1F` sobre `#FFF1B8` | texto dentro do `<mark>` | 14,9:1 | AAA |
| `#4A4F52` sobre `#FAF8F4` | muted 15 px | 7,8:1 | AAA |
| `#4A4F52` sobre branco | muted do advogado | 8,3:1 | AAA |
| `#5C3A00` sobre `#FFF4DD` | OfflineBanner | 9,3:1 | AAA |
| `#FFF1B8` sobre `#FAF8F4` / branco | fundo do `<mark>` contra o fundo do card | **1,07:1 / 1,13:1** | **Reprova** como único sinal do trecho citado (1.4.1, 1.4.11) |
| `#1F7373` sobre `#E3E0D8` | segmento preenchido vs trilha do progresso | 4,2:1 | ok |
| `#E3E0D8` sobre `#FAF8F4` | bordas de card e da barra | 1,2:1 | decorativo; nunca como único limite de componente |
| `#0F2A36` sobre `#081820` | item ativo da sidebar | 1,2:1 | ok só porque há barra teal 6,3:1 e deve haver `aria-current` |
| `#081820` sobre `#FAF8F4` | anel de foco proposto (claro) | 17,0:1 | AAA |
| `#081820` sobre `#1F7373` | anel de foco sobre botão primário | 3,2:1 | AA não-texto |
| `#F0F0E8` sobre `#081820` | anel de foco no banner/sidebar | 15,8:1 | AAA |
| `#B91C1C` sobre `#FAF8F4`; branco sobre `#B91C1C` | vermelho proposto (gravação, erro) | 6,1:1; 6,5:1 | AA |
| `#A8B4B8` sobre `#081820` | muted sobre marinho proposto (OAB na sidebar) | 8,5:1 | AAA |
| `#6E7377` sobre branco | borda do dropzone proposta | 4,8:1 | AA |

Cores citadas no design sem hex definido: vermelho do anel de gravação e do status "erro ao processar", cinza tracejado do dropzone, muted sobre marinho (rodapé da sidebar), trilha vazia do ProgressSteps, cor do anel de foco. Os valores propostos acima cobrem todas.

## Achados por tela

Legenda de severidade: **C** Crítico · **I** Importante · **P** Polimento. Nível = nível WCAG do critério.

### Transversal — todas as telas da cidadã (CH, C0–C6)

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| T-01 | 2.4.7 Foco visível; 1.4.11; 2.4.13 (AAA) | AA | C | Nenhum documento define cor, espessura ou offset do anel de foco. O padrão do shadcn (`ring` a 50 % de opacidade) fica abaixo de 3:1 sobre `#FAF8F4` e some sobre o botão teal. | Token global: `outline: 3px solid #081820; outline-offset: 2px` no claro (17:1 sobre `#FAF8F4`, 3,2:1 sobre `#1F7373`); `outline-color: #F0F0E8` dentro do banner e da sidebar; aplicar via `:focus-visible` em todos os `Button`, links, segmentos, chips e `<pre tabindex=0>`. |
| T-02 | 1.4.4 Redimensionar texto; 1.4.10 Reflow; 1.4.12 Espaçamento; 2.4.11 Foco não obscurecido | AA | C | Banner com altura fixa (76 px), barra inferior fixa (132 px) e `scroll-padding-bottom: 148px` fixo. Com fonte do sistema a 130 % o banner precisa de ~100 px (3 linhas de 15 px × 1,35 × 1,3) e o botão "Falar com o advogado" (48 × 120 px, rótulo em 2 linhas) passa a 3 linhas: texto cortado. A 200 % a barra cresce e o valor fixo de 148 px deixa de cobrir o elemento focado. Não há `scroll-padding-top` para o banner fixo: ao voltar com Shift+Tab, o banner cobre o elemento. | Usar `min-height` (nunca `height`) no banner, no botão de ajuda e na barra; medir as duas alturas com `ResizeObserver` e escrever `--banner-h` e `--bar-h`; `main { scroll-padding-top: var(--banner-h); scroll-padding-bottom: calc(var(--bar-h) + 16px); padding-bottom: idem }`. Testar a 130 % e 200 %. |
| T-03 | 1.4.3 Contraste mínimo | AA | C | `#B26A00` com texto branco = 4,2:1 (o plano afirma 4,6). Afeta chips "carimbo pendente" (C6, CH, A4, A3, P1), "marcado para o Dr. João conversar com você" (C5), `FeedbackCard kind=pending` (C4), selos "juiz: revisar"/"trecho não encontrado" (A2) sempre que renderizados como fundo âmbar com texto branco a 15 px. | Chips âmbar como texto `#7A4800` sobre fundo `#FFF4DD` com borda `#B26A00` (7,0:1), padrão já indicado em A4/A3 para "fundo claro"; se precisar de fundo sólido, `#9A5B00` (5,4:1). Corrigir a tabela do `component-plan.md`. |
| T-04 | 2.4.2 Página com título | A | I | Só P1 define `<title>`. As demais rotas não têm título distinto; TalkBack e o histórico do navegador anunciam a mesma coisa em todos os tópicos. | `generateMetadata` por rota: "Tópico 2 de 7: Quanto você paga · LeIA", "Conferindo 1 de 3 · LeIA", "Seu comprovante · LeIA", "Painel · LeIA". |
| T-05 | 2.2.1 Tempo ajustável; 3.3.1 Identificação de erro | A | I | Erros entregues em toast de 4 s: "O login não terminou…" (C0), "Sem microfone, tudo bem…" (C3/C4). Quem lê devagar ou usa TalkBack perde a mensagem. | Erros e instruções sempre inline e persistentes (`Alert` ou texto sob o controle, `role="status"`); toast só para confirmações não essenciais ("Copiado", "Link copiado"). Toast da cidadã com `offset` igual a `--bar-h` para não cobrir o botão primário. |
| T-06 | 1.4.1 Uso de cor; 1.4.11 Contraste não textual; 1.3.1 | A/AA | I | O `<mark>` `#FFF1B8` é o único sinal de qual parte da cláusula foi citada: 1,07:1 contra `#FAF8F4` e 1,13:1 contra o card branco; invisível em escala de cinza e para baixa visão. `aria-label` em `<mark>` não é válido (sem papel ARIA) e não é lido. | Além do fundo: `text-decoration: underline; text-decoration-thickness: 2px; font-weight: 600` e texto oculto visualmente "início do trecho citado" / "fim do trecho citado" dentro do `<mark>`. Vale para C2, C3, C4 e A2. |
| T-07 | 3.2.4 Identificação consistente; 3.1.5 (AAA) | AA | I | O mesmo estado aparece como "carimbo a caminho" (CH) e "carimbo pendente" (C6, P1). "Pendente" e "validado" são palavras difíceis para a persona. | Na jornada da cidadã usar sempre "carimbo a caminho" e "Conferido pelo Dr. João" (em vez de "Validado"); "pendente" fica só no painel do advogado. |
| T-08 | COGA; 1.4.10 | AA | I | Banner fixo de 3 linhas em todas as telas ocupa, junto com a barra, 28 % de 740 px (mais a 130 %). Em 320 px o botão de 120 px deixa ~168 px para o texto: 4–5 linhas a 130 %. Ruído cognitivo repetido em cada tópico. | A partir de C2, colapsar o banner para 1 linha ("assistente automática · não dá conselho jurídico", 48 px) com o mesmo botão à direita; texto completo só em C0/C1 e na folha "Falar com o advogado". 3.2.6 continua atendido (mesma posição relativa). |
| T-09 | LBI art. 63 § 1º; eMAG | — | I | Na V1 não há `AccessibilitySheet` ("só VLibras"), logo o link "Recursos de acessibilidade" não leva a nada; C0 (primeira tela que a cidadã vê) não tem o símbolo. Não há página "Acessibilidade". | V1: símbolo + link em C0, C1 e CH apontando para `/acessibilidade` (página estática de 1 tela: áudio, VLibras, tamanho do texto pelo sistema, contato). Sheet completa na V2. |
| T-10 | 3.3.8 Autenticação acessível | AA | I | Passa (Google, sem senha, sem CAPTCHA). Porém, se "Continuar sem conta" for removido, cidadãs sem conta Google no aparelho ou em celular compartilhado ficam bloqueadas. | Manter "Continuar sem conta" como alternativa de acessibilidade (flag ligada) e, na V2, OTP por telefone como alternativa. |
| T-11 | 4.1.2 Nome, papel, valor; 2.5.3 Rótulo no nome | A | P | Microfone e player mudam o rótulo visível ("Gravar" → "Parar de gravar"; "Ouvir" → "Pausar") e também alternam `aria-pressed`: o TalkBack lê "Parar de gravar, botão, pressionado". | Escolher um só sinal. Recomendação: rótulo visível muda (padrão APG para play/pause) e `aria-pressed` sai; o estado "Gravando" vai para a live region. |
| T-12 | 2.5.8 Tamanho do alvo (AAA 2.5.5) | AA | P | Links inline sem tamanho definido: "Perguntar outra coisa", "Voltar para meus documentos", "Recursos de acessibilidade", "Ver na rede pública", "Prefiro escrever". | Renderizar como `Button variant=link` com `min-height: 48px` e `padding-block: 12px`. |
| T-13 | 1.1.1 | A | P | "✓ e ⚑ são SVG com `aria-label`" sem `role="img"`: não são anunciados. | `<svg role="img" aria-label="entendido">` ou texto oculto ao lado. |
| T-14 | 2.4.11 | AA | P | Widget VLibras fixo à direita (offset 148 px) pode cobrir o botão "1×" do player e o chevron de "Ver trecho original" em 320 px. Script externo do gov.br falha offline. | Montar o widget só quando ativado em "Recursos de acessibilidade"; carregar o script com `onerror` silencioso; testar sobreposição em 320 px. |
| T-15 | 2.4.1 Bypass; 2.5.2 | A | P | Cidadã não tem link "Pular para o conteúdo" (advogado tem). Landmarks (`<main>`) bastam para o TalkBack, mas o link é barato. `touch-action: manipulation` da pesquisa não está no design. | Primeiro elemento focável: "Pular para o conteúdo"; `touch-action: manipulation` nos botões. |
| T-16 | 3.1.5 (AAA); 1.2.1 | AAA/A | I | TTS por `speechSynthesis` lê literalmente "R$ 10.000", "30%", "OAB/PR 12345", "0:12": para quem prefere ouvir, o número central do tópico pode sair errado. | `ttsText` normalizado antes de falar: "10 mil reais", "30 por cento", "OAB PR 12345"; conferir no teste de amanhã. |
| T-17 | 1.4.8 (AAA) | AAA | P | Alinhamento do texto não definido. | `text-align: left`, nunca justificado; largura ≤ 60 caracteres já está definida. |

### CH · Meus documentos

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| CH-01 | 4.1.3; 1.3.1 | AA | P | `aria-busy="true"` no `<main>` inteiro durante o carregamento faz alguns leitores pular o h1 e o subtítulo. | `aria-busy` só no contêiner da lista; `role="status"` "Carregando seus documentos" fora dele. |
| CH-02 | 2.5.1 | A | P | Pull-to-refresh desabilitado e V1 "sem Atualizar lista": sem forma de atualizar além de recarregar a página. | Manter um botão "Atualizar lista" (ghost 48 px) já na V1. |
| CH-03 | LBI | — | P | Símbolo de acessibilidade só no rodapé do `<main>` (fora da primeira dobra). | Aceitável; ver T-09. |

### C0 · Entrar

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| C0-01 | 3.3.2; 4.1.2 | A | P | "Continuar sem conta tem `aria-describedby` apontando para a nota sobre salvar o comprovante", mas essa nota não existe em C0 (a nota de C0 é "Você não assina nada aqui…"). | Acrescentar sob o botão: "Sem conta, o comprovante fica só neste celular." e apontar o `aria-describedby` para ela. |
| C0-02 | 2.2.1 | A | P | Token com estado "expirado": é um tempo limite. Passa pela exceção de > 20 h desde que a validade seja de dias. | Documentar validade mínima de 7 dias no backend. |
| C0-03 | LBI | — | I | Sem símbolo de acessibilidade na primeira tela. | Ver T-09. |

### C1 · Início

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| C1-01 | 1.2.1; 4.1.3 | A/AA | C | "Começar ouvindo" é o primário e o áudio da V1 depende de `speechSynthesis` com voz pt-BR do sistema. Em Android básico (Go, sem Google TTS ou sem o pacote pt-BR) `getVoices()` volta vazio ou só en-US e o botão falha em silêncio: a cidadã que "prefere ouvir" fica sem nada. | Ao montar C1, checar `speechSynthesis.getVoices()` (com `onvoiceschanged`); sem voz `pt-BR`/`pt`: primário vira "Começar lendo", nota visível "Este celular não tem voz em português. O texto está todo aqui." e botões de ouvir ficam `aria-disabled` com a mesma nota. V2: áudio pré-gerado resolve. |
| C1-02 | 1.3.1; 2.4.6 | A/AA | P | Títulos dos cards "Quem está falando com você" e "Como funciona" não estão marcados como cabeçalhos. | `<h2>` em ambos; passos em `<ol>`. |

### C2 · Tópico n de N

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| C2-01 | 1.4.2 Controle de áudio; 2.2.2; 4.1.3 | A | C | Com `audio_pref = listen`, o áudio começa sozinho ao entrar no tópico, no mesmo instante em que o TalkBack anuncia "Tópico 2 de 7: …": duas vozes ao mesmo tempo. Nada cancela o `speechSynthesis` ao trocar de rota (o tópico 1 continua falando sobre o 2). | `speechSynthesis.cancel()` em todo unmount/troca de rota; quando houver autoplay, mover o foco para "Pausar" (um toque duplo ou Espaço para parar) em vez do h1 e anunciar o título depois de 600 ms; opção "Não tocar o áudio sozinho" em Recursos de acessibilidade (V2). |
| C2-02 | 2.5.8; uma mão | AA | P | 7 segmentos do ProgressSteps em 328 px úteis: ~43 px cada com 4 px de folga (41 px em 320 px). Passa 24 px, mas um toque errado navega para outro tópico. | Segmentos não interativos (só progresso) e rever pela lista de C5; ou 2 linhas quando N > 6 com gap ≥ 8 px. Segmentos futuros permanecem no DOM como texto "Tópico 5, ainda não visto". |
| C2-03 | 2.4.6; 3.1.1 | AA | P | h1 com `aria-label` "Tópico 2 de 7: …" sobrescreve o conteúdo; o VLibras não vê o prefixo. | `<h1><span class="sr-only">Tópico 2 de 7: </span>Quanto você paga</h1>`. |
| C2-04 | COGA | — | P | Sem "Voltar" visível no tópico (só botão do sistema ou segmento). Para baixa escolaridade, "posso voltar?" precisa de resposta visível. | Link "Voltar para a parte anterior" (48 px) no fim do `<main>` quando n > 1; não entra na barra (limite de 3 ações mantido: é navegação, não ação). |
| C2-05 | 1.4.1 | A | I | Ver T-06 (`<mark>`). | — |

### C3 · Dúvida

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| C3-01 | 1.2.1; 3.3.1; 4.1.3 | A/AA | C | V1 usa `SpeechRecognition` do Chrome Android: o reconhecimento termina sozinho na primeira pausa de 1–2 s e tem teto de ~60 s, enquanto o cronômetro "Gravando, 0:12" continua; a cidadã que fala devagar vê a transcrição cortada no meio. Com TalkBack, o anúncio "Gravando, 15 segundos" a cada 5 s sai pelo alto-falante e entra na transcrição. | Reiniciar `recognition.start()` no `onend` enquanto `aria-pressed`/estado = gravando, acumulando só resultados `isFinal`; live region só no início ("Gravando. Toque de novo quando terminar.") e no fim; cronômetro visual + vibração; instrução visível "Fale devagar. Pode fazer pausas." V2 (`MediaRecorder` + `/stt`) elimina o problema. |
| C3-02 | 1.4.10; 2.1.1; uma mão | AA | I | Chips de exemplo com rolagem horizontal (responsive.md diz que empilham a 200 %, screen-05 diz rolagem a 360 px). Rolagem horizontal é ruim com TalkBack (gesto de 2 dedos) e com o polegar. | Chips sempre empilhados ou em `flex-wrap`, 48 px cada; 3 chips = 144 px de altura, aceitável. |
| C3-03 | 3.3.1; 4.1.2 | A | I | "Enviar dúvida desabilitado sem texto": `disabled` some do Tab e não explica. | `aria-disabled="true"` + `aria-describedby` "Escreva ou grave sua dúvida primeiro"; ao tocar, mostrar a frase sob o botão. Mesmo padrão em C4 ("Enviar resposta") e C5 ("Falta ver 2 partes"). |
| C3-04 | 2.1.1; 2.5.7 | A/AA | P | Esc "cancela a gravação sem apagar o que já estava no campo" não tem equivalente por toque; só existe "Parar de gravar". | Botão ghost "Cancelar" (48 px) ao lado do microfone enquanto grava, com o mesmo efeito do Esc. |
| C3-05 | 4.1.3 | AA | P | Resposta em streaming numa região `aria-live` e, ao mesmo tempo, "foco vai ao início da resposta": leitura dupla. | Manter o foco no botão (agora "Conferindo no documento…", `aria-busy`); live region por frase; ao concluir, mover o foco para o h2 oculto "Resposta" do card. |
| C3-06 | 3.1.5 (AAA); 3.3.2 | AAA/A | P | Consentimento cita "registro público" antes de a cidadã conhecer o conceito (aparece só em C6); "Sua voz será transformada em texto" é passiva. Foco inicial do `Dialog` não definido. | "Eu escuto sua voz e escrevo o que você disse. O áudio não fica guardado. Você pode pedir para apagar." Foco inicial no título do diálogo (`tabIndex=-1`). |
| C3-07 | 3.3.2 | A | P | Rótulo do campo "Escreva aqui ou grave sua voz" vira "Confira o que você disse" após gravar: mesmo campo, dois nomes. | Manter um `<label>` fixo "Sua dúvida" e mostrar "Confira o que você disse" como `aria-describedby`/legenda acima. |

### C4 · Conferindo k de K

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| C4-01 | 2.4.6 Cabeçalhos; 1.3.1; COGA | AA/A | I | O h1 é a frase fixa "Para eu ter certeza de que expliquei bem:" (igual em todas as perguntas) e a pergunta real é h2; o lembrete vem antes do h1 no DOM. Ao focar o h1, o TalkBack lê só a frase fixa; a regra "repetir o essencial antes de perguntar" não chega ao leitor de tela; navegação por cabeçalhos mostra 3 páginas com o mesmo h1. | `<h1><span class="sr-only">Conferindo 1 de 3: </span>Se você ganhar a causa, quanto do dinheiro fica com o advogado?</h1>` com `aria-describedby` apontando para o lembrete; a frase de enquadramento vira `<p>` acima. Visual não muda. |
| C4-02 | idem C3-01 | A | C | Mesma falha do `SpeechRecognition` (aqui é o núcleo do produto: a resposta da cidadã). | Ver C3-01. |
| C4-03 | 1.4.3 | AA | C | `FeedbackCard kind=pending` âmbar: ver T-03. | Texto `#7A4800` sobre `#FFF4DD`. |
| C4-04 | 3.1.5 (AAA) | AAA | P | Frase de feedback "Se você receber R$ 10.000, R$ 3.000 ficam com o advogado e R$ 7.000 com você." tem 16 palavras. | Quebrar: "Você recebe R$ 10.000. R$ 3.000 ficam com o advogado. R$ 7.000 ficam com você." |
| C4-05 | 3.3.2 | A | P | Rótulo "Ou escreva aqui" sem substantivo. | "Sua resposta (escreva aqui)". |
| C4-06 | 4.1.3 | AA | P | Estado "sem conexão" muda o primário para "Seguir para a próxima" e mostra "Sua resposta está salva…": deve ir pela `StatusRegion`. | Confirmar que o texto entra no `role="status"` único da tela. |

### C5 · Confirmação

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| C5-01 | 1.4.3 | AA | C | Chip "marcado para o Dr. João conversar com você" âmbar: ver T-03. | Texto `#7A4800` sobre `#FFF4DD`, ícone ⚑. |
| C5-02 | 4.1.2 | A | P | Cada `<li>` é um botão "Rever: …" também no modo leitura (já confirmada), quando rever não faz sentido. | No modo leitura, itens como texto; só "Ver dúvidas" interativo. |
| C5-03 | 3.3.1 | A | I | "Confirmo que entendi" desabilitado com nota "Falta ver 2 partes": ver C3-03. | `aria-disabled` + `aria-describedby`. |
| C5-04 | 3.3.4 | AA | — | Passa: `AlertDialog` com foco em "Ainda não" e texto que distingue confirmar de assinar. | — |

### C6 · Comprovante

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| C6-01 | 1.4.3 | AA | C | Chip "carimbo pendente" âmbar: ver T-03. | Ver T-03 e T-07 ("carimbo a caminho"). |
| C6-02 | 1.3.1; 3.1.5 | A | P | Hash de 64 hex com `aria-label` "lido em grupos": 8 grupos de 8 caracteres falados não servem para nada; datas "12/09/2026 às 15:40" só por extenso no `aria-label` (`aria-label` em `<p>` não é anunciado de forma confiável). | `<code aria-label="Código do registro, 64 caracteres. Use o botão Copiar.">`; datas visíveis por extenso para todos ("12 de setembro de 2026, 15:40") em `<time datetime>`. |
| C6-03 | 2.2.1 | A | — | Passa: polling de 30 s é silencioso e o anúncio só ocorre quando o carimbo chega. | — |
| C6-04 | 1.1.1 | A | — | Passa: QR com `role="img"` e link textual visível de 48 px. | — |
| C6-05 | Metadados | — | — | Passa: PDF sem Producer/Creator/Author/datas, conforme regra do projeto. Conferir no arquivo final. | — |

### A0 · Entrar (advogado)

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| A0-01 | 1.3.5 Identificar propósito | AA | P | Campos sem `autocomplete`. | `autocomplete="name"` no nome; `inputmode="numeric"` na OAB. |
| A0-02 | 1.4.3 | AA | P | Cor do texto muted sobre marinho (rodapé da sidebar, "OAB/PR 12345") não definida; `#4A4F52` sobre marinho daria 2,2:1. | Token `ink.onNavyMuted = #A8B4B8` (8,5:1). |
| A0-03 | 3.3.1 | A | — | Passa: `aria-invalid`, `aria-describedby`, resumo em `role="alert"`, foco no primeiro campo vazio. | — |

### A4 · Painel do advogado

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| A4-01 | 2.1.4 Atalhos de tecla única | A | I | `N` (novo documento) e `/` (buscar) são atalhos de um caractere sem forma de desligar ou remapear. Usuário de ditado ou leitor de tela pode disparar sem querer. | Remover `N` (há botão); manter `/` só se houver toggle "Atalhos de teclado" nas preferências; ou trocar por `Ctrl+K`. `Ctrl+Enter` está isento. |
| A4-02 | 1.4.13; 1.3.1 | AA/A | P | Informação necessária só em tooltip: "2 pendências (tooltip: 1 pergunta para conversar, 1 dúvida fora do documento)". Tooltip do Radix não abre por toque. | Texto visível na célula ("1 conversa · 1 dúvida") ou `Popover`. |
| A4-03 | 1.4.3 | AA | P | Status "erro ao processar (vermelho)" sem hex. | `#B91C1C` (6,5:1 com branco; 6,1:1 como texto). |
| A4-04 | 4.1.2 | A | P | Item ativo da sidebar com fundo 1,2:1 e barra teal; falta `aria-current="page"`. | Adicionar `aria-current`. |

### A1 · Enviar documento

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| A1-01 | 2.2.1; 3.2.5 (AAA) | A | I | "Redirecionamento automático em 3 s com aviso cancelável": 2.2.1 exige aviso com pelo menos 20 s para estender; 3 s não dá tempo a quem usa leitor de tela. | Sem redirecionamento automático: ao concluir, foco no botão "Revisar explicação" e anúncio "Explicação pronta para revisar". |
| A1-02 | 1.4.11 | AA | P | Borda tracejada do dropzone "≥ 3:1" sem hex. | `#6E7377` (4,8:1). |
| A1-03 | 2.5.7 | AA | — | Passa: arrastar tem alternativa "Escolher arquivo". | — |

### A2 · Revisar e aprovar

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| A2-01 | 1.4.1; 1.4.11 | A/AA | I | `<mark>` na cláusula original: ver T-06. É o único sinal do trecho que o advogado deve conferir. | Sublinhado + negrito + texto oculto de início/fim. |
| A2-02 | 1.4.13 | AA | P | Motivo de "juiz: revisar" só em tooltip. | Frase visível sob o selo (`<p class="text-sm">`). |
| A2-03 | 1.4.3 | AA | I | Selos âmbar: ver T-03. | Texto `#7A4800` sobre `#FFF4DD`. |
| A2-04 | 2.4.11 | AA | — | Passa: `scroll-padding-bottom: 96px` para o rodapé fixo; confirmar que o cabeçalho com h1/chip não é sticky. | — |
| A2-05 | 2.1.1 | A | — | Passa: todo atalho tem botão. | — |

### A3 · Validar

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| A3-01 | 1.4.13 | AA | P | "Tooltip acessível por foco e toque": o `Tooltip` do Radix não abre por toque. | `Popover` ou texto visível no `RubricBadge` ("Citou: 30%, só se ganhar"). |
| A3-02 | 1.3.1 | A | P | `<blockquote aria-label="Resposta de Maria, 1ª tentativa">`: melhor legenda visível. | `<figure><blockquote>…</blockquote><figcaption>1ª resposta de Maria</figcaption></figure>`. |
| A3-03 | 4.1.3 | AA | — | Passa: "Registro gerado" com foco no h2 e anúncio; crossfade do chip com `role="status"`. | — |

### P1 · Verificação pública

| ID | Critério | Nível | Sev. | Achado | Correção |
|---|---|---|---|---|---|
| P1-01 | 1.4.3 | AA | C | Chip "carimbo pendente" âmbar: ver T-03. | Ver T-03. |
| P1-02 | 2.1.1; 1.4.10 | A/AA | — | Passa: `<pre tabindex="0">` com rótulo; rolagem só dentro do bloco; comandos com botão Copiar. | — |
| P1-03 | eMAG | — | P | Página pública sem `accesskey` 1/2/3 nem link "Acessibilidade". | Opcional: `accesskey="1"` no `<main>` e link "Acessibilidade" no rodapé. |
| P1-04 | 2.4.2 | A | — | Passa: título "Verificação pública · LeIA". | — |

## Veredito por critério (conjunto de telas)

| Critério | Nível | Resultado | Referência |
|---|---|---|---|
| 1.1.1 Conteúdo não textual | A | Passa com ajuste | T-13 |
| 1.2.1 Alternativa para áudio | A | Passa (texto visível para todo áudio; transcrição editável); risco de voz ausente | C1-01 |
| 1.3.1 Informação e relações | A | Passa com ressalvas | C4-01, T-06, C1-02 |
| 1.3.4 Orientação | AA | Passa | responsive.md |
| 1.3.5 Identificar propósito de entrada | AA | Ressalva | A0-01 |
| 1.4.1 Uso de cor | A | **Reprova** | T-06 |
| 1.4.2 Controle de áudio | A | Passa formalmente (há "Pausar"); conflito com TalkBack | C2-01 |
| 1.4.3 Contraste mínimo | AA | **Reprova** (âmbar 4,2:1); demais pares passam | T-03 |
| 1.4.4 Redimensionar texto | AA | **Reprova** (alturas fixas) | T-02 |
| 1.4.10 Reflow | AA | **Reprova** (chips horizontais; banner a 320 px/130 %) | C3-02, T-08 |
| 1.4.11 Contraste não textual | AA | **Reprova** (anel de foco indefinido; `<mark>`) | T-01, T-06 |
| 1.4.12 Espaçamento de texto | AA | Ressalva | T-02 |
| 1.4.13 Conteúdo em hover/foco | AA | Ressalva (tooltips com informação necessária) | A4-02, A2-02, A3-01 |
| 2.1.1 Teclado | A | Passa | Espaço/Esc/Tab definidos |
| 2.1.2 Sem armadilha | A | Passa | Dialog/Sheet do Radix |
| 2.1.4 Atalhos por caractere | A | **Reprova** (advogado) | A4-01 |
| 2.2.1 Tempo ajustável | A | **Reprova** (toast de erro 4 s; redirecionamento 3 s) | T-05, A1-01 |
| 2.2.2 Pausar, parar, ocultar | A | Passa | anel de gravação é essencial e para ao parar |
| 2.3.1 Três flashes | A | Passa | — |
| 2.3.3 Animação por interação | AAA | Passa | `prefers-reduced-motion` em toda a tabela |
| 2.4.1 Ignorar blocos | A | Passa (landmarks) | T-15 |
| 2.4.2 Página com título | A | **Reprova** | T-04 |
| 2.4.3 Ordem do foco | A | Passa | ordem definida em todas as telas |
| 2.4.4 Finalidade do link | A | Passa | "abre em nova aba" nos externos |
| 2.4.6 Cabeçalhos e rótulos | AA | Ressalva | C4-01 |
| 2.4.7 Foco visível | AA | **Reprova** (anel indefinido) | T-01 |
| 2.4.11 Foco não obscurecido (mínimo) | AA | **Reprova** (padding fixo; sem `scroll-padding-top`; VLibras) | T-02, T-14 |
| 2.4.13 Aparência do foco | AAA | Reprova (mesma causa) | T-01 |
| 2.5.1 Gestos de ponteiro | A | Passa | — |
| 2.5.2 Cancelamento de ponteiro | A | Passa | — |
| 2.5.3 Rótulo no nome | A | Passa | T-11 é ressalva |
| 2.5.5 Tamanho do alvo (melhorado) | AAA | Passa na cidadã; reprova no painel (32 px, aceitável) | — |
| 2.5.7 Movimentos de arrastar | AA | Passa | dropzone com botão; sem deslizar-para-cancelar |
| 2.5.8 Tamanho do alvo (mínimo) | AA | Passa | C2-02 é melhoria |
| 3.1.1 Idioma da página | A | Passa | `lang="pt-BR"` |
| 3.1.5 Nível de leitura | AAA | Passa em geral (frases ≤ 15 palavras; 1 frase com 16; jargão pontual) | C4-04, C3-06, T-07 |
| 3.2.1 / 3.2.2 Em foco / em entrada | A | Passa | — |
| 3.2.3 Navegação consistente | AA | Passa | banner + barra em todas as telas |
| 3.2.4 Identificação consistente | AA | Ressalva | T-07 |
| 3.2.6 Ajuda consistente | A | Passa | "Falar com o advogado" no mesmo lugar em CH, C0–C6 |
| 3.3.1 Identificação de erro | A | **Reprova** (toasts; `disabled` sem explicação) | T-05, C3-03 |
| 3.3.2 Rótulos ou instruções | A | Passa | C3-07, C4-05 são polimento |
| 3.3.3 Sugestão de erro | AA | Passa | mensagens com próximo passo |
| 3.3.4 Prevenção de erro | AA | Passa | AlertDialog em C5, A2, A3 |
| 3.3.7 Entrada redundante | A | Passa | voltar nunca apaga; nome pré-preenchido; nome da cliente pedido uma vez |
| 3.3.8 Autenticação acessível | AA | Passa | T-10 é recomendação |
| 4.1.2 Nome, papel, valor | A | Passa com ressalvas | T-11, A4-04, C5-02 |
| 4.1.3 Mensagens de status | AA | Passa | StatusRegion única; offline; copiado; feedback |
| LBI art. 63 (símbolo em destaque + boas práticas) | — | Ressalva na V1 | T-09, C0-03 |
| eMAG 3.1 (accesskeys, página Acessibilidade) | — | Parcial | P1-03, T-09 |
| PWA offline anunciado | — | Passa | OfflineBanner `role="status"`, fila, textos por tela |

## Roteiro de teste manual — 30 minutos (amanhã)

Preparação antes de começar (não conta no tempo): Android com Chrome; TalkBack instalado (Configurações → Acessibilidade → TalkBack); "Tamanho da fonte" do sistema em 130 % (Configurações → Tela → Tamanho da fonte, ou "Tamanho de exibição e texto"); link de uma sessão de demo com 7 tópicos e 3 perguntas; modo avião acessível pela barra de notificações; um desktop com Chrome para o bloco do advogado. Anotar cada passo como OK / Falha / Observação.

### Bloco 1 — TalkBack + fonte 130 % (0–10 min)

| Min | Passo | Resultado esperado |
|---|---|---|
| 0 | Ligar TalkBack. Abrir o link do advogado (C0). Deslizar para a direita 3 vezes. | Ouve "Aviso da assistente, região", o texto do banner, "Falar com o advogado, botão", depois o h1. Nada cortado no banner a 130 %. |
| 1 | Toque duplo em "Entrar com Google" (ou "Continuar sem conta"). | Anúncio "Pronto. Vamos começar." e h1 "Oi, Maria" lido ao chegar em C1. |
| 2 | Chegar até "Começar ouvindo" e ativar. | C2: anúncio "Tópico 1 de 7: …". Registrar se o áudio automático fala por cima do TalkBack e se há como parar com um toque duplo (foco em "Pausar"). |
| 3 | Explorar por toque a barra inferior e o fim do `<main>`. | "Ver trecho original" e o "1×" do player não ficam atrás da barra nem do VLibras; expandir o trecho anuncia "expandido". |
| 4 | Ativar "Tenho uma dúvida" (C3). Chegar ao microfone e ativar. | Diálogo de consentimento lido por inteiro; "Continuar" pede permissão. |
| 5 | Falar duas frases com pausa de 3 s entre elas. Esperar 20 s em silêncio. | A gravação não para sozinha na pausa; o cronômetro bate com o estado real. Ao parar, o foco vai para "Confira o que você disse" e a transcrição não contém "Gravando, 15 segundos". |
| 7 | Enviar. | "Conferindo no documento…" anunciado; resposta lida frase a frase; sem leitura dupla. |
| 8 | "Voltar ao tópico", avançar até C4. | Ao entrar, ouve "Conferindo 1 de 3", o lembrete e a pergunta sem precisar deslizar (após C4-01). |
| 9 | Escrever uma resposta errada de propósito e enviar. | Feedback "Vamos ver de novo" anunciado; foco no h3; sem palavras proibidas. |
| 10 | Seguir até C5 → "Confirmo que entendi". | AlertDialog abre com foco em "Ainda não"; após confirmar, C6 anuncia "Seu comprovante, …"; "Copiar código" anuncia "Copiado". |

### Bloco 2 — Fonte 130 % / 200 %, uma mão, sem TalkBack (10–18 min)

| Min | Passo | Resultado esperado |
|---|---|---|
| 10 | Desligar TalkBack. Abrir C2 em 360 px com fonte 130 %. | Banner sem corte; "Falar com o advogado" legível; os 2 botões da barra inteiros, rótulos em 1 linha ou 2 sem corte. |
| 11 | Rolar até o fim com o trecho aberto. | Último elemento visível acima da barra; VLibras não cobre nada. |
| 12 | Subir a fonte do sistema para o máximo (≈ 200 %). Ver C2 e C4. | Sem rolagem horizontal; player em 2 linhas; mic 64 px; chips de C3 empilhados. Voltar para 130 %. |
| 14 | Segurar o celular só com a mão direita. Em C2: tocar "Entendi, próximo"; em C3: tocar o microfone e "Enviar dúvida"; tocar "Falar com o advogado". | Tudo alcançável com o polegar sem reposicionar, exceto o botão do banner (registrar quantas vezes precisou da outra mão; não é bloqueio). |
| 16 | Em C2, tocar o segmento 1 do progresso tentando não acertar o 2. | Abre o tópico 1 (registrar erros de toque). |
| 17 | Girar para paisagem em C3. | Barra com só o primário; secundário no fim do `<main>`; banner em 1 linha. |
| 18 | Ligar "Correção de cor → Escala de cinza" do Android e abrir o trecho original. | O trecho citado continua identificável (sublinhado/negrito, T-06). Desligar. |

### Bloco 3 — Offline (18–24 min)

| Min | Passo | Resultado esperado |
|---|---|---|
| 18 | Em C2 tópico 3, ativar modo avião. | OfflineBanner aparece com "A conexão caiu…" (com TalkBack ligado, é anunciado). |
| 19 | "Entendi, próximo" até o tópico 5; tocar "Ouvir explicação". | Tópicos vêm do cache; áudio V1 funciona sem rede. |
| 20 | Ir a C4, escrever uma resposta e enviar. | "Sua resposta está salva. Eu confiro quando a internet voltar."; primário vira "Seguir para a próxima". |
| 22 | Desligar modo avião. | "Conexão de volta. Enviando suas respostas…" por 3 s; a resposta é conferida ou reaparece em C5 como "para ver de novo". |
| 23 | Ativar modo avião de novo e abrir C6 (ou CH → "Ver comprovante"). | Último estado conhecido com chip "atualizado há …"; "Salvar comprovante" funciona com o cache. Desligar modo avião. |

### Bloco 4 — Teclado no desktop (advogado) e verificações rápidas (24–30 min)

| Min | Passo | Resultado esperado |
|---|---|---|
| 24 | A0: Tab desde o início. | 1º foco em "Pular para o conteúdo"; anel de foco visível (3 px marinho) em todos os elementos; no passo 2, foco no primeiro campo vazio; erro anunciado ao enviar vazio. |
| 25 | A4: Tab pela tabela; digitar "n" com o foco na busca. | Cada botão de ação recebe foco visível com `aria-label` completo; "n" não abre A1 (após A4-01). |
| 26 | A2: Tab até o Textarea da última seção; `Ctrl+Enter`. | Textarea não fica atrás do rodapé fixo; atalho marca e avança; `<mark>` legível em escala de cinza. |
| 27 | A3: `Ctrl+Enter` → AlertDialog → validar. | Foco no h2 "Registro gerado"; anúncio; chip muda com `role="status"`. |
| 28 | Lighthouse (Acessibilidade) e axe em C2, C4 e C6. | ≥ 95 e sem violações críticas. |
| 29 | No celular, ouvir o áudio de C2 e de C4 (pergunta). | "R$ 10.000" sai como "dez mil reais", "30%" como "trinta por cento", "OAB/PR 12345" inteligível. |
| 30 | Checar VLibras no tópico 1 e o símbolo/link de acessibilidade em C0, C1 e CH. | Widget traduz o texto do tópico; link abre a página ou a folha de acessibilidade. |

Critério de saída: nenhum item Crítico com Falha; Importantes com Falha entram na lista de amanhã.
