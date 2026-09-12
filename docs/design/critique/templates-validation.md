# Validação tela por tela dos templates do serviço (12/09, 16h)

Método: leitura integral do HTML, CSS e JavaScript dos seis templates em `temp/` contra as specs de
`docs/design/screen-*.md`, as regras de conteúdo, a auditoria de acessibilidade e as três dimensões do manual.
Não renderizei as páginas; onde o veredito depende de execução, está marcado "conferir rodando".
Legenda: ✓ atende · △ parcial · ✗ não atende. "Onde" = arquivo do kit em `docs/brand/` ou spec que resolve.

## Matriz resumo
| Template | Tela | D1 confiabilidade | D2 usabilidade | D3 sofisticação | Conteúdo | Acessibilidade | Segurança |
|---|---|---|---|---|---|---|---|
| `dashboard.html` | cidadã (C2–C6) | △ chat só do documento, mas sem recusa visível e sem trecho original | ✗ texto 9,6–13 px, escuro, prova com nota de corte | △ hash por tentativa | ✗ 9 textos vetados | ✗ contraste 2,2:1, sem live region, alvos < 48 px | ✗ gabarito no HTML; markdown do modelo injetado sem sanitizar |
| `tarefa_nova.html` | advogado (A2/A3) | ✓ log por etapa, hash, gabarito para o advogado | △ rótulos em caixa alta e jargão | ✓ trilha de auditoria | △ APROVADO/REPROVADO, IP, UTC | △ formulários nativos (bom), `confirm()` nativo | △ IP da cidadã exposto |
| `index.html` | advogado (A4) | ✓ | ✓ estrutura boa; △ status internos | ✓ contadores por status | △ "Tarefa", "Chat investigador" | △ meta refresh a cada 5 s | ✓ |
| `cliente_view.html` | espera | ✓ | △ texto pequeno, escuro | ✓ mostra status | △ "análise do seu caso" | △ spinner sem `prefers-reduced-motion`, sem anúncio | ✓ |
| `tarefa_detalhe.html` | login (A0) | ✓ | ✓ | ✓ | ✓ | △ rótulos 11 px em caixa alta | ✓ autocomplete correto |
| `login.html` | workbench (bastidores) | ✓ mostra prompts, payload, memória | n/a (interno) | ✓ ótimo para o auditor | n/a | n/a | ✗ edita o system prompt e salva protocolo: só advogado logado |

## dashboard.html: página da cidadã
| Critério | Veredito | Evidência no código | Correção (onde) |
|---|---|---|---|
| Gabarito não exposto | ✗ | `data-correta="{{ q.correta }}"` em cada questão e `{{ q.justificativa }}` no DOM (`display:none`); qualquer pessoa vê no código-fonte | servidor devolve só enunciado e alternativas; gabarito fica no `/api/t/{hash}/quiz` (bloqueador para "prova de ciência") |
| Conteúdo do modelo sanitizado | ✗ | `el.innerHTML = marked.parse(raw)` com o resumo vindo do LLM e do PDF | usar `marked` com `DOMPurify.sanitize(...)` ou renderizar em texto; PDF com HTML/script injetado vira XSS na página da cidadã |
| Trecho original por tópico | ✗ | resumo inteiro em um bloco, sem lastro | V2: um tópico por tela com "Ver trecho original" (`screen-04-c2-topico.md`); o workflow já traz `lastro`/`_ui` |
| Perguntas abertas / teach-back | ✗ | 12 questões A–D, corte 10/12, "Você marcou", "Questões para revisar" | `screen-06-c4-conferindo.md`; se a múltipla escolha ficar hoje, tirar corte e vocabulário de prova (`copy-replacements.md`) |
| Recusa visível no chat | △ | respostas via SSE em `textContent` (bom), mas nenhum tratamento de `NAO_ESTA_NO_DOCUMENTO` | mapear a recusa para "Isso não está escrito neste documento. Anotei para o Dr. João responder." + chip |
| Apresentação da assistente e limites | ✗ | "Olá! Sou o assistente deste processo… 👋"; rodapé "análise assistida por IA" | texto fixo de `pt-BR.json › c1.selfIntro` no primeiro balão e no rodapé |
| Advogado supervisiona | ✗ | "Uma nova tentativa será gerada pelo administrador do sistema" | "pelo Dr. João" e pendência nomeada |
| Hash ≠ assinatura | ✗ | "Assinatura digital", "Hash imutável da sua assinatura", "Assinatura registrada", "PDF assinado" | "Seu comprovante", "Código do registro", "Registrado", "Baixar comprovante" |
| Palavras vetadas | ✗ | "acertar pelo menos 10 de 12", "Ainda não foi desta vez", "acertos", "Você marcou", "questões", "❌ Erro" | `copy-replacements.md` |
| Tamanho de texto | ✗ | instruções `.78rem` (12,5 px), meta `.6rem` (9,6 px), status `.72rem`, botões `.82rem` | `leia-theme.css` com `body.leia-citizen` (17 px base) |
| Contraste | ✗ | `--tx3 #424660` sobre `#0b0d14` ≈ 2,2:1 nas instruções e status | tema claro do kit (ink sobre papel 17:1) |
| Alvos de toque | △ | `.q-alt` ≈ 34 px de altura; `.btn` ≈ 40 px; `chat-fab` 54 px ✓ | `min-height: 48px` (kit) |
| Mensagens de status | ✗ | `#quiz-status` muda por `textContent` sem `aria-live`; "Enviando…" | `aria-live="polite"` no status e no balão do chat |
| Diálogo acessível | △ | `role="dialog" aria-modal` ✓, Esc fecha ✓; foco não vai para o modal nem volta ao botão | mover foco ao `h3` do modal e devolver ao fechar |
| Ícones | ✗ | emojis em botões e títulos (📖 ❓ ✍️ 💬 ✓ ↺ ⬇️ 🔐 ❌ ⚠️ 👋) | sprite `leia-icons.svg` |
| Dependências externas | △ | Tailwind CDN e `marked` do cdnjs | ok na V1; para PWA offline, empacotar |
| Idioma e viewport | ✓ | `lang="pt-BR"`, viewport ✓ | |
| Estados | △ | vazio ("questões ainda não foram geradas") ✓; erro ✓ (texto vetado); carregando "Enviando…" ✓; offline ✗ | `common.offline` do `pt-BR.json` |

## tarefa_nova.html: detalhe (A2/A3)
| Critério | Veredito | Evidência | Correção |
|---|---|---|---|
| Trilha de auditoria | ✓ | hash da tarefa, hash por tentativa, log com `ts` e `tipo`, rodadas clonadas | manter; é evidência para D1/D3 |
| Formulários nativos | ✓ | `POST /tarefas/{id}/reprocessar`, `/nova-rodada`; funciona sem JS | manter |
| Vocabulário | ✗ | "APROVADO/REPROVADO", "questões erradas", "✗ Marcou / ✓ Correta" | `copy-replacements.md` |
| Dados pessoais | ✗ | `IP {{ t.ip }}` na tela | não exibir; não armazenar em claro |
| Fuso | △ | UTC em todas as datas | Brasília |
| Rótulos | △ | `ID / Hash / Rodada / PDF / Criada em` em mono caixa alta (CSS) | `leia-theme.css` já normaliza; textos pelo mapa |
| Revisão do advogado | ✗ | não edita o texto simples nem escolhe perguntas; não há "validar" | `screen-12-a2-revisar.md`, `screen-13-a3-validar.md`; V2 |
| Confirmações | △ | `confirm()` nativo em "Gerar nova rodada" | aceitável na V1 |
| Estados | ✓ | sem tentativas, pipeline em execução, falhou, pronta | |

## index.html: painel (A4)
| Critério | Veredito | Evidência | Correção |
|---|---|---|---|
| Estrutura | ✓ | contadores por status, filtros, tabela, estado vazio com ação, primeira ação em destaque | manter |
| Status | △ | `criada/processando/pronta/assinada/falhou` em minúsculas internas | `recebido / preparando / pronto para enviar / entendido / com erro` |
| Atualização | △ | `<meta http-equiv="refresh" content="5">` enquanto processa: perde rolagem e foco, quebra leitor de tela | trocar por `fetch` de status a cada 5 s atualizando só as linhas |
| Marca | ✗ | "Painel de Tarefas", "AI Forensics v44", favicon `beeroot_ico.png`, "Chat investigador" | "Sessões · LeIA", favicon do símbolo, "Bastidores" |
| Responsivo | conferir rodando | tabela de 6 colunas | rolagem horizontal no contêiner da tabela |

## cliente_view.html, tarefa_detalhe.html, login.html
- **Espera**: meta refresh 5 s aceitável; adicionar `role="status"` no texto e desligar o spinner com `prefers-reduced-motion`; texto para "Estamos preparando a explicação do seu documento".
- **Login**: correto e simples; rótulos passam a sentence case com o tema; V2 troca por login social (ADR-0006).
- **Workbench**: expõe edição do system prompt e salvamento de protocolo; restringir ao advogado logado e apresentar ao auditor como "bastidores" (payload ativo, log, memória persistente, protocolo de agentes).

## Bloqueadores em ordem (o que resolver antes de mostrar a página da cidadã a um leigo ou auditor)
1. Gabarito e justificativa fora do HTML da cidadã.
2. Sanitizar o markdown do resumo (`DOMPurify`) ou renderizar como texto.
3. Vocabulário: corte 10/12, "Ainda não foi desta vez", "assinatura", "administrador do sistema".
4. Tema claro com texto de 17 px e contraste (kit `leia-theme.css`, `body.leia-citizen`).
5. Apresentação da assistente com limites e recusa visível no chat.
6. IP fora da tela do advogado.
