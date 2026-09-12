# Templates do serviço (recebidos em 12/09, 15h35): validação e como aplicar a marca

Seis arquivos Jinja em `temp/` (fora do repositório até o Carlos fazer o push). Os nomes não batem com o conteúdo:

| Arquivo | O que é de fato | Tela-alvo do design | Uso |
|---|---|---|---|
| `index.html` | Painel de tarefas do advogado: contadores por status (criada, processando, pronta, assinada, falhou), filtros, tabela (id, título, hash, status, data), "Nova tarefa", "Chat", "Sair" | A4 painel | manter; só marca, copy e ícones |
| `tarefa_nova.html` | Detalhe da tarefa: id, hash, rodada, PDF, link da cliente, ações; tentativas com aprovado/reprovado e questões erradas; status do pipeline; resumo humanizado; questões; log de eventos | A2 revisar + A3 validar | manter; esconder IP; renomear; falta editar o texto simples e escolher perguntas |
| `dashboard.html` | Página da cidadã (`/t/{hash}`): resumo humanizado, 12 questões A–D com nota de corte 10/12, "assinatura digital" com hash e PDF assinado, chat lateral com o assistente | C2 a C6 | maior mudança: tema claro, texto grande, sem nota de corte, "comprovante" no lugar de "assinatura", chat com apresentação e recusa |
| `cliente_view.html` | Espera com atualização automática a cada 5 s enquanto o pipeline roda | estado "carregando" de C1 | manter; texto e cor |
| `tarefa_detalhe.html` | Formulário de login (e-mail e senha) "AI Forensics · Gestão de Tarefas" | A0 | manter na V1; login social é V2 |
| `login.html` | Workbench "AI Forensics · Groq v43": chat, payload ativo, log de execução, memória persistente, contexto e anexos, protocolo de agentes | não é tela do produto | **usar na auditoria** como "bastidores": mostra o sistema de prompts, o payload e a memória persistente ao auditor (Dimensão 3) |

Validação elemento por elemento, com vereditos e bloqueadores: [templates-validation.md](templates-validation.md).

## O que já está bom
- Estrutura das páginas cobre A4, A2/A3, C2–C6 e o estado de espera; link da cliente por token; hash por tentativa; log
  com tempo por etapa; chat restrito ao documento; auto-refresh na espera. Tudo em Jinja simples, fácil de retematizar.
- Tokens de cor centralizados em `:root` em todas as páginas: a marca entra com um arquivo CSS, sem mexer em markup.

## O que aplicar (arquivos prontos em `docs/brand/`)
1. **Tema**: linkar `leia-theme.css` depois do `<style>` de cada template; na página da cidadã, `<body class="leia-citizen">`.
   Resultado: marinho e teal no painel; papel claro, texto de 17 px e botões de 48 px na página da cidadã; foco visível;
   sem serifa dourada. Um botão por página recebe `class="primary"`.
2. **Ícones**: copiar `leia-icons.svg` para `static/` e trocar os emojis pelo `<use>` correspondente (mapa em
   `copy-replacements.md`).
3. **Textos**: aplicar a tabela de `copy-replacements.md`. Os três que mais pesam na auditoria: sumir com
   "APROVADO/REPROVADO", "≥ 10/12" e "questões erradas" da tela da cidadã; "Assinatura digital" vira "Seu comprovante";
   a apresentação da assistente com limites.
4. **Dados**: não exibir IP da cidadã; horário em Brasília, não UTC.
5. **Estrutura da página da cidadã** (V2): o resumo inteiro numa página vira um tópico por tela com "ver trecho original"
   (o `_ui`/lastro do workflow já traz as posições) e as questões de múltipla escolha viram 2 a 3 perguntas abertas.
   Se não der tempo hoje, o tema e o texto já entregam a maior parte da Dimensão 2.

## Perguntas para o Carlos
1. Qual o mecanismo do "PDF assinado" (`/t/{hash}/pdf-assinado`)? É o PDF original com carimbo do hash? Precisamos
   garantir que ele não carrega metadados de ferramenta e que o texto diz "comprovante", não "assinatura".
2. O workbench (`login.html`) pode ficar acessível só ao advogado logado, como "bastidores" para a auditoria?
3. As rotas `/t/{hash}` e `/api/t/{hash}/chat` aceitam o `X-Api-Key` do contrato ou são públicas por token?
