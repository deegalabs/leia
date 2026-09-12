# Substituições de texto nos templates do serviço (12/09/2026)

Mapa de "buscar → trocar" para os seis templates recebidos. Motivo ao lado quando não for óbvio. Vale para a tela da
cidadã (`dashboard.html`), o detalhe (`tarefa_nova.html`), o painel (`index.html`) e a espera (`cliente_view.html`).

## Marca e nomes
| Buscar | Trocar por |
|---|---|
| `Para.AI`, `Para .AI` | `LeIA` |
| `AI Forensics`, `AI Forensics v44`, `Groq v43` | `LeIA · painel` (o workbench pode manter "bastidores" no título) |
| `Seu processo` | `Seu documento` |
| `Análise do seu processo` | `Entenda o que você vai assinar` |
| `Tarefa`, `Painel de Tarefas`, `Nova tarefa`, `Criar a primeira tarefa` | `Documento`, `Sessões`, `Novo documento`, `Enviar o primeiro documento` |
| `Preparando seu documento… / Estamos processando a análise do seu caso.` | `Estamos preparando a explicação do seu documento. Esta página atualiza sozinha.` |

## Tela da cidadã (`dashboard.html`)
| Buscar | Trocar por | Motivo |
|---|---|---|
| `📖 Entenda o que está acontecendo` | `Entenda o que você vai assinar` | não é processo, é documento |
| `❓ Confira se você entendeu` | `Vamos conferir se eu expliquei bem` | responsabilidade no sistema (teach-back) |
| `Responda as N questões abaixo. Elas confirmam que você leu e compreendeu o resumo. Este é o registro que documenta sua ciência do processo. Você precisa acertar pelo menos 10 de 12.` | `Responda com suas palavras. Não tem certo ou errado: as respostas mostram o que ficou claro e o que precisa de outra explicação.` | vocabulário de prova é vetado; nota de corte não aparece para a cidadã |
| `❓ Questões de verificação` | `Conferindo o que você entendeu` | |
| `✓ Enviar respostas` / `↺ Limpar` / `💬 Tirar dúvida antes` | `Enviar minhas respostas` (primário) / `Começar de novo` / `Tenho uma dúvida` | |
| `✍️ Assinatura digital` | `Seu comprovante` | hash não é assinatura (posicionamento) |
| `Hash imutável da assinatura (SHA-256)` | `Código do registro` | |
| `Assinado em {data} UTC` | `Registrado em {data}` (horário de Brasília) | |
| `Rodada N · X/Y acertos` | remover da tela da cidadã | |
| `⬇️ Baixar PDF assinado` | `Salvar comprovante` | |
| `🔐 A assinatura é liberada após o quiz ser aprovado (≥ 10/12).` | `O comprovante fica pronto depois que o Dr. João validar suas respostas.` | supervisão humana |
| `Ainda não foi desta vez` | `Vamos ver de novo` + feedback em duas partes | |
| `Para.AI · análise assistida por inteligência artificial` | `Assistente automática. Explica o que está escrito. Não dá conselho jurídico.` | limites (Rec. CFOAB 001/2024) |
| `Assistente do processo / responde com base neste documento / Olá! Sou o assistente deste processo. Pode me perguntar em linguagem simples — vou responder com base no documento. 👋` | `Sou uma assistente automática do escritório. Explico o que está escrito neste documento. Não sou advogada e não dou conselho jurídico. Quem responde por você é o Dr. João.` | apresentação obrigatória |
| `Digite sua pergunta…` | `Fale ou escreva sua dúvida aqui` | |
| `💡 {justificativa}` | mostrar só depois de responder, como `O que o documento diz:` | não revelar gabarito antes |

## Detalhe e painel do advogado (`tarefa_nova.html`, `index.html`)
| Buscar | Trocar por |
|---|---|
| `ID / Hash / Rodada / PDF / Criada em / Link cliente / Ações` (caixa alta via CSS) | `Documento · Código do registro · Tentativa de leitura · Arquivo · Enviado em · Link da cliente · Ações` (sentence case) |
| `🔄 Reprocessar pipeline` | `Gerar a explicação de novo` |
| `🔁 Gerar nova rodada` / `Gerar nova rodada de questões` | `Gerar novas perguntas` |
| `⬇️ PDF assinado` / `Exportar PDF assinado` | `Baixar comprovante` |
| `📝 Tentativas do cliente` | `Respostas da cliente` |
| `APROVADO` / `REPROVADO` | `entendeu` / `precisa de outra explicação` (chip `ok` / `pend`, nunca vermelho) |
| `X/Y acertos` | `X de Y pontos entendidos` |
| `Ver as N questões erradas` | `Ver o que precisa de outra explicação` |
| `✗ Marcou:` / `✓ Correta:` | `Respondeu:` / `O documento diz:` |
| `IP {ip}` | remover (LGPD: minimização) |
| `⏳ Pipeline em execução` | `Preparando a explicação` |
| `📖 Resumo humanizado` | `Explicação em linguagem simples` |
| `❓ Questões (rodada atual · N)` | `Perguntas de compreensão (N)` |
| `📡 Log de eventos` | `Registro de eventos` |
| status `criada / processando / pronta / assinada / falhou` | `recebido / preparando / pronto para enviar / entendido / com erro` |
| `Abrir →` | `Abrir` |
| `Sair` | `Sair` (mantém) |

## Emojis → ícones (sprite `leia-icons.svg`)
📖 `book-open` · ❓ `help-circle` · 💬 `message-circle-question` · ✍️ `clipboard-check` · 🔐 `stamp` · ⬇️ `download` ·
🔄 `rotate-ccw` · 🔁 `repeat` · 📝 `clipboard-list` · ⏳ `hourglass` · 📡 `scroll-text` · 📄 `file-text` · 📭 `inbox` ·
＋ `plus` · ✓ `check` · ✕ `x` · 💡 `lightbulb` · 👋 (remover).
