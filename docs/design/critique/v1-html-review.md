# V1 do serviço (HTML do Carlos): validação e insumos de interface

Fonte: duas capturas de 12/09 às 15h04 e 15h05 (`127.0.0.1:8000/tarefas/4`). Papel deste documento: validar o que
já existe e devolver insumos para a interface; decisões de implementação são do dono do serviço.

## O que a V1 já entrega (e vale como evidência)
- Tarefa com id, hash, rodada ("2 · clonada de #3"), PDF, data de criação, **link da cliente com token** (`/t/{hash}`) e ação "Gerar nova rodada".
- Tentativas da cliente com hash SHA-256 por tentativa, data e origem; questões com alternativa correta marcada.
- **Log de eventos** com tempo por tarefa do workflow (16 tarefas, pipeline completo em 75,8 s; T13 humanização 8,1 s; T14 questões 7,4 s) e evento "cliente abriu".
Isso é trilha de auditoria pronta para a Dimensão 3 e para o relatório de testes internos.

## Insumos para a interface (ordem de impacto na auditoria)
| # | O que aparece hoje | Por que importa | Sugestão |
|---|---|---|---|
| 1 | "REPROVADO", "4/12", "Ver as 8 questões erradas" | palavras de prova são vetadas nas telas da cidadã (pesquisa de conteúdo; D2 "orientada a leigos") | para a cidadã: "Vamos ver de novo" com feedback em duas partes; para o advogado: "compreensão insuficiente: 4 de 12" em `pend`, nunca vermelho |
| 2 | Emojis como ícones (📝, 🛰, 🔁) e títulos em serifa dourada | variam por aparelho, sem cor da marca, leitor de tela inconsistente | Lucide 20 px com texto (`docs/brand/icons.md`): `ScrollText` para o log, `RotateCcw` para nova rodada, `FileText` para o documento |
| 3 | Botões dourados com borda, todos iguais ("Gerar nova rodada", "Gerar nova rodada de questões") | sem hierarquia; rótulo sem resultado | hierarquia de `docs/brand/buttons.md`: um primário teal por tela ("Gerar novo link para a cliente"), o resto secundário |
| 4 | Rótulos em monoespaçada e caixa alta (ID, HASH, RODADA, PDF, CRIADA EM, LINK CLIENTE, AÇÕES) | caixa alta é mais lenta de ler; jargão interno na tela | sentence case em pt-BR: "Documento", "Código do registro", "Tentativa de leitura", "Enviado em", "Link da cliente" |
| 5 | Documento de teste é uma peça processual (agravo, "fase processual") | o produto explica contrato, procuração e acordo; a pergunta "em que fase processual" não existe nesse domínio | testar com o contrato de honorários de `examples/` (30% de êxito) e tópicos do CED art. 48 |
| 6 | 12 questões de múltipla escolha com gabarito | permite chute; contraria o teach-back (ver `LLM-WORKFLOW-REVIEW.md`) | 2 a 3 perguntas abertas com elementos esperados; múltipla escolha só como autoconferência |
| 7 | IP e user-agent da cidadã no log visível | LGPD: minimização; não é necessário para a prova | guardar só hash do IP (ou nada) e não exibir na tela do advogado |
| 8 | Tema escuro em toda a interface | bom para o painel do advogado (marinho da marca); ruim para leitura longa da cidadã com baixa visão | painel escuro (`.dark`), jornada da cidadã em `paper-2` com texto 17 a 19 px |
| 9 | Pipeline de 75,8 s ao criar a tarefa | a cidadã nunca pode esperar isso; o advogado pode, se vir progresso | progresso por etapa em A1 ("Lendo o PDF → Separando cláusulas → …") lendo o próprio log de eventos |
| 10 | Hash da tentativa e do documento visíveis e copiáveis | ótimo para D1/D3 | manter; na V2 virar o `payload_hash` canônico com salt (SPEC-001) e link do registro público |

## Mapeamento das telas dele para as telas-alvo
| Tela do Carlos | Tela-alvo | O que já serve |
|---|---|---|
| `/tarefas` (lista, a confirmar) | A4 painel | lista de tarefas, status por rodada |
| `/tarefas/{id}` | A2 revisar + A3 validar | hash, link, tentativas, log; falta edição do texto simples e seleção de perguntas |
| `/t/{hash}` (cliente) | C1 a C5 | link com token, questões; falta tópico por tela, voz, perguntas abertas, confirmação |
| (não existe) | CH, C6, P1 | painel da cidadã, comprovante com QR, verificação pública |
