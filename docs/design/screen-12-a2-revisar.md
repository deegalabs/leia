# A2 · Revisar e aprovar — `/lawyer/documents/{id}`

## Propósito e posição no fluxo

O advogado confere, seção por seção, o texto simples ao lado da cláusula original com a citação destacada, edita o que quiser, escolhe 2–3 perguntas e aprova. Só depois da aprovação a cidadã vê algo. Entrada: A1 concluído ou A4 "Revisar". Saída: link gerado (status "link enviado") e volta a A4. Também abre em modo leitura ("Ver explicação") após aprovada.

## Layout (desktop, 1440×900)

```
┌ Sidebar ┬───────────────────────────────────────────────────────────────────────┐
│         │ Breadcrumb: Painel › Contrato de honorários · #123                       │
│         │ h1 "Revisar explicação"   chip "aguardando revisão"   [Salvo há 10 s]     │
│         │ ┌ Lista de seções 260 px ┐ ┌ ClauseSideBySide ─────────────────────────┐ │
│         │ │ 1 ✓ O que o advogado… │ │ Cabeçalho da seção: Input "Título"  ícone   │ │
│         │ │ 2 ● Quanto você paga  │ │  [💰] "Quanto você paga"                     │ │
│         │ │ 3 ✓ Como e quando…    │ │ ┌ Cláusula original ┐ ┌ Texto simples ─────┐│ │
│         │ │ 4 ⚠ Até onde vai…     │ │ │ "Cláusula 4ª. A   │ │ Textarea 17 px:     ││ │
│         │ │ 5 ✓ Se houver acordo  │ │ │ título de honorá- │ │ "O advogado só      ││ │
│         │ │ 6 ✓ Os riscos…        │ │ │ rios contratuais, │ │ recebe se você      ││ │
│         │ │ 7 ✓ Como cancelar     │ │ │ o CONTRATANTE     │ │ ganhar a causa…"    ││ │
│         │ │                       │ │ │ pagará … <mark>30%│ │                     ││ │
│         │ │ [+ Adicionar seção]   │ │ │ (trinta por cento)│ │ Input "Frase        ││ │
│         │ └───────────────────────┘ │ │ … êxito</mark>"    │ │ essencial (≤ 15     ││ │
│         │                           │ │ Badge ✓ trecho    │ │ palavras)"          ││ │
│         │                           │ │ verificado        │ │ Dicas: "1 frase com ││ │
│         │                           │ │ Badge ✓ juiz: fiel│ │ mais de 15 palavras"││ │
│         │                           │ └───────────────────┘ └─────────────────────┘│ │
│         │                           │ [Ouvir como a cliente vai ouvir] [Marcar como conferida] │
│         │                           └────────────────────────────────────────────┘ │
│         │ ┌ QuestionPicker ────────────────────────────────────────────────────┐   │
│         │ │ h2 "Perguntas para conferir o entendimento"  "Escolha 2 ou 3"       │   │
│         │ │ [x] Se você ganhar a causa, quanto fica com o advogado?              │   │
│         │ │     espera: 30% · só se ganhar · exemplo em R$                        │   │
│         │ │ [x] Se você perder, precisa pagar honorários?   espera: não · êxito   │   │
│         │ │ [ ] Se quiser trocar de advogado, o que acontece?  espera: …           │   │
│         │ │ [ ] … (até 6 sugeridas)   [+ Escrever minha pergunta]                 │   │
│         │ └────────────────────────────────────────────────────────────────────┘   │
│         │ Rodapé fixo: "7 de 7 seções conferidas · 2 perguntas"  [Aprovar e gerar link] │
└─────────┴───────────────────────────────────────────────────────────────────────┘
```

## Componentes (shadcn/ui)

`Breadcrumb`, `Badge`, `Input`, `Textarea`, `Checkbox`, `Button`, `Dialog`, `Tabs` (≤ 1279 px), `Collapsible`, `Tooltip`, `Alert`, `Toast`, `Skeleton`, `ScrollArea`; novos: `ClauseSideBySide`, `QuestionPicker`, `StatusChip`, `AudioPlayer`.

## Copy exata (pt-BR)

- h1: "Revisar explicação"; autosave: "Salvo há 10 s" / "Salvando…" / "Não salvo — tentando de novo"
- Lista: "Seções" · "Adicionar seção"
- Painéis: "Cláusula original" · "Texto simples (o que a cliente vai ler e ouvir)" · "Título" · "Frase essencial (≤ 15 palavras)"
- Selos: ✓ "trecho verificado" (verde) · ⚠ "trecho não encontrado no PDF" (âmbar) · ✓ "juiz: fiel" (verde) · ⚠ "juiz: revisar" (âmbar, tooltip com o motivo em 1 frase)
- Dicas de escrita (contador abaixo do Textarea): "1 frase com mais de 15 palavras" · "Contém palavra a evitar: 'errado'" · "Sem exemplo em R$" · "Pronto para a cliente"
- Botões: "Ouvir como a cliente vai ouvir" · "Marcar como conferida" / "Conferida" · "Aprovar e gerar link" · "Escrever minha pergunta"
- Perguntas: h2 "Perguntas para conferir o entendimento" · "Escolha 2 ou 3" · "espera:" + elementos
- Rodapé: "7 de 7 seções conferidas · 2 perguntas"
- Bloqueio: "Para aprovar: 1 seção com trecho não encontrado, escolha ao menos 2 perguntas."
- `Dialog` "Gerar link para a cliente": Input "Primeiro nome da cliente" (placeholder "Maria"), p "Só o primeiro nome. Ele aparece na saudação e no painel; não vai para o registro público." Botão "Gerar link". Resultado: link em `Input` somente leitura + "Copiar link" / "Copiado" + "Envie pelo canal que preferir (WhatsApp, e-mail, SMS)." + "Voltar ao painel".

## Estados

**Default** — seções carregadas; a 1ª sem conferir fica selecionada.

**Vazio (nenhuma seção)** — não deve ocorrer; defesa: `Alert` "A LeIA não conseguiu separar seções deste PDF." + "Adicionar seção" (manual) e "Enviar outro PDF".

**Carregando** — lista e painéis em `Skeleton`; "Carregando a explicação".

**Erro** — `Alert` topo: "Não foi possível carregar. Estamos tentando de novo." Erro de autosave: chip "Não salvo — tentando de novo" + retentativa exponencial; ao sair com pendência, `AlertDialog` "Há alterações não salvas."

**Modo leitura (aprovada)** — campos desabilitados, chip "link enviado", botão "Copiar link" no lugar de aprovar; "Gerar novo link" no menu.

## Interações

- Selecionar seção na lista → painéis trocam (fade 120 ms); rascunho salvo a cada 2 s de inatividade (`PUT` local no Next; pendência de endpoint).
- Editar "Texto simples" → dicas recalculam ao vivo (frases > 15 palavras, palavras a evitar, presença de "R$"). Nada bloqueia além do trecho não verificado.
- "Marcar como conferida" → ✓ na lista; `Ctrl+Enter` marca e vai para a próxima.
- Trecho não encontrado → botão "Selecionar trecho no PDF" abre o texto da cláusula em `Dialog` para o advogado selecionar; ao salvar, `quote_verified = true` pelo backend (re-verificação) e selo aparece com fade 150 ms.
- "Ouvir como a cliente vai ouvir" → `AudioPlayer` (V1 `speechSynthesis`; V2 `POST /tts` do texto atual).
- `QuestionPicker`: mínimo 2, máximo 3; ao marcar a 4ª, checkbox desabilitada com tooltip "Máximo 3". "Escrever minha pergunta" adiciona Input + "elementos esperados".
- "Aprovar e gerar link" (ou `Ctrl+Shift+Enter`) → `Dialog` nome → `POST /sessions` → link + copiar; status muda para "link enviado".

## Acessibilidade

- Foco no h1; ao trocar de seção, foco no Input "Título".
- Ordem: breadcrumb → h1 → lista de seções (`<nav aria-label="Seções">`, botões com estado "conferida"/"a conferir"/"com problema") → título → cláusula original (`<blockquote>`, `<mark>` com `aria-label="trecho citado"`) → selos (texto) → Textarea → frase essencial → dicas (`aria-live="polite"`, resumidas) → botões → perguntas → rodapé.
- Painéis lado a lado com `aria-labelledby` nos cabeçalhos; ≤ 1023 px empilham.
- Selos com ícone + texto; tooltip acessível por foco.
- Dicas de escrita não são erros: `role="status"`, sem `aria-invalid`.
- Rodapé fixo não cobre o Textarea focado (`scroll-padding-bottom: 96px`).
- Atalhos documentados em tooltip; todos têm botão equivalente.

## Chamadas de API

- Carregar: resultado de `POST /documents/{id}/explain` e `POST /documents/{id}/questions` (guardado pelo Next após A1); não há `GET /documents/{id}` no contrato (pendência).
- Salvar edições e aprovação: **sem endpoint no contrato** — proposta `PUT /documents/{id}/sections` e `POST /documents/{id}/approve { sections[], question_ids[] }`. Pendência no INDEX.
- Re-verificar trecho: reuso de `POST /documents/{id}/explain` com `section_id` (pendência).
- Gerar link: `POST /sessions { document_id, client_first_name }` → `{ session_id, client_token }`; link `https://{host}/c/{client_token}`.

## O que muda na V1 / V2 / Produto

- **V1:** edições salvas no Next (banco próprio) e enviadas inteiras no `POST /sessions`; sem "Adicionar seção"; sem seleção manual de trecho (seção sem selo não pode ser aprovada: o advogado edita a citação manualmente e o backend re-verifica).
- **V2:** endpoints de seções/aprovação; seleção de trecho no PDF; re-geração de áudio por seção após edição.
- **Produto:** histórico de versões da explicação; modelos por tipo de documento com seções pré-aprovadas; revisão em dupla (assistente edita, titular aprova).
