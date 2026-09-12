# A3 · Validar — `/lawyer/sessions/{id}`

## Propósito e posição no fluxo

O advogado vê o que a cliente respondeu (em palavras, não números), as dúvidas com as respostas ou recusas da assistente, as pendências que exigem conversa, escreve observações e valida. A validação gera o JSON canônico → hash → registro público e o comprovante. Entrada: A4 "Validar" (status "aguardando validação") ou "Acompanhar"/"Ver registro" (modo leitura). Saída: painel de registro (hash, transação, link do comprovante).

## Layout (desktop, 1440×900)

```
┌ Sidebar ┬──────────────────────────────────────────────────────────────────────┐
│         │ Breadcrumb: Painel › Maria · Contrato de honorários                     │
│         │ h1 "Validar sessão de Maria"   chip "aguardando validação"               │
│         │ ┌ Resumo 320 px ───────────┐ ┌ Conteúdo ───────────────────────────────┐│
│         │ │ Card "Percurso"          │ │ h2 "Respostas de Maria"                  ││
│         │ │ 7 de 7 partes vistas     │ │ Card por pergunta:                       ││
│         │ │ Tempo total 6 min        │ │  p "Se você ganhar a causa, quanto…?"    ││
│         │ │ Confirmou 12/09 15:40    │ │  RubricBadge ✓ "entendeu e citou a       ││
│         │ │ Card "Pendências (2)"    │ │   consequência"                          ││
│         │ │ ⚑ Pergunta 3: conversar  │ │  blockquote 1ª resposta: "Ele fica com   ││
│         │ │ ⚑ Dúvida fora do doc.    │ │   30% se eu ganhar, tipo 3 mil de 10 mil"││
│         │ │ Card "Dúvidas (2)"       │ │  (se houve 2ª) "Vamos ver de novo" +     ││
│         │ │ 1 respondida · 1 recusada│ │   2ª resposta + RubricBadge              ││
│         │ └──────────────────────────┘ │ h2 "Dúvidas"                             ││
│         │                              │ Card: pergunta · resposta · citação      ││
│         │                              │ Card: pergunta · ⚠ "recusada: fora do    ││
│         │                              │   documento" · "Anotado para você"       ││
│         │                              │ h2 "Pendências para conversar"           ││
│         │                              │ lista com checkbox "Conversei com Maria" ││
│         │                              │ h2 "Suas observações"                    ││
│         │                              │ Textarea "Fica só no seu painel; não     ││
│         │                              │   entra no registro público."            ││
│         │                              └──────────────────────────────────────────┘│
│         │ Rodapé fixo: [Validar e gerar registro]  primário  · "Ctrl+Enter"         │
│         │ ── após validar: Card "Registro gerado" ──                                 │
│         │ HashDisplay mono + Copiar · Transação: link · "Bloco em 12/09/2026 16:42" │
│         │ [Copiar link do comprovante] [Abrir verificação pública]                   │
└─────────┴──────────────────────────────────────────────────────────────────────┘
```

## Componentes (shadcn/ui)

`Breadcrumb`, `Card`, `Badge`, `Checkbox`, `Textarea`, `Button`, `AlertDialog`, `Tooltip`, `Alert`, `Toast`, `Skeleton`; novos: `RubricBadge`, `StatusChip`, `HashDisplay`, `ReceiptCard` (variante advogado), `QuoteDisclosure`.

## Copy exata (pt-BR)

- h1: "Validar sessão de Maria" (modo leitura: "Sessão de Maria")
- Resumo: "Percurso" · "7 de 7 partes vistas" · "Tempo total 6 min" · "Confirmou em 12/09/2026 às 15:40" · "Pendências (2)" · "Dúvidas (2)" · "1 respondida · 1 recusada"
- Rubrica (palavras, nunca números): "entendeu e citou a consequência" · "entendeu o essencial" · "entendeu na 2ª tentativa" · "pendente: conversar com a cliente" · "pediu nova explicação"
- Detalhe da rubrica (tooltip): "Citou: 30%, só se ganhar, exemplo em R$" · "Faltou: consequência se perder"
- Dúvidas: "respondida com citação" · "recusada: fora do documento" · "recusada: pedido de conselho" · "Anotado para você"
- Pendências: h2 "Pendências para conversar" · checkbox "Conversei com Maria sobre isto" · texto "Marcar não é obrigatório para validar; fica no seu histórico."
- Observações: "Suas observações" · "Fica só no seu painel; não entra no registro público."
- Botão: "Validar e gerar registro" (carregando: "Gerando registro…")
- `AlertDialog`: "Validar esta sessão?" p "Isso gera o código do registro e o comprovante para Maria. Nome, documento e respostas não vão para o registro público." Botões "Validar" · "Voltar"
- Resultado: h2 "Registro gerado" · "Código do registro" · "Transação" · "Bloco em {data} às {hora}" · "Carimbo pendente: a transação está sendo gravada. Você pode fechar; o painel atualiza." · "Copiar link do comprovante" · "Abrir verificação pública"
- Toasts: "Registro gerado. Maria já pode ver o comprovante." · "Link copiado."

## Estados

**Default (aguardando validação)** — tudo preenchido, botão ativo.

**Vazio (em andamento)** — sessão ainda não confirmada: h1 "Sessão de Maria", chip "em andamento", respostas parciais com "ainda não respondeu", botão desabilitado com nota "Disponível quando Maria confirmar." Atualiza a cada 60 s.

**Carregando** — resumo e cards em `Skeleton`; "Carregando a sessão".

**Erro** — `Alert`: "Não foi possível carregar. Estamos tentando de novo." Erro ao validar: "Não foi possível gerar o registro. Nada foi perdido; tente de novo." Erro só na âncora (hash ok, `anchor = null` por falha): estado provisório com "Carimbo pendente" e retentativa automática.

**Registrado (modo leitura)** — chip "registrado" ou "registrado · carimbo pendente"; Card "Registro gerado" no topo; observações em leitura.

## Interações

- Cards de resposta expandem a citação da cláusula usada na rubrica (`QuoteDisclosure`).
- Checkbox de pendência salva imediatamente (toast discreto "Salvo").
- Textarea com autosave 2 s.
- "Validar e gerar registro" (ou `Ctrl+Enter`) → `AlertDialog` → `POST /sessions/{id}/validate { notes, pendings_handled[] }` → `POST /sessions/{id}/finalize` → Card "Registro gerado" com fade 150 ms; foco no h2; anúncio "Registro gerado".
- Se `anchor = null`: polling `GET /sessions/{id}` a cada 30 s; ao chegar, chip crossfade + anúncio "Carimbo público concluído".
- "Copiar link do comprovante" → `https://{host}/c/{token}/receipt`; "Abrir verificação pública" → `/verify/{verify_id}` em nova aba.

## Acessibilidade

- Foco no h1. Ordem: breadcrumb → h1 → chip → resumo (cards com listas) → respostas (cada card `<article>` com h3 = pergunta) → dúvidas → pendências (checkboxes) → observações → rodapé → (após) card de registro.
- `RubricBadge`: ícone + texto; tooltip acessível por foco e toque (`aria-describedby`).
- Citações da cliente em `<blockquote>` com `aria-label="Resposta de Maria, 1ª tentativa"`.
- Rodapé fixo com `scroll-padding-bottom`.
- Hash em `<code>` com Copiar; link da transação com "abre em nova aba".
- Contraste: âmbar em fundo claro usa texto `#7A4800`.

## Chamadas de API

- `GET /sessions/{id}` → `client_first_name`, `sections[]`, `questions[]` com `answers[] { attempt, text, score, matched[], missing[], feedback_for_client }`, `chats[]`, `pendings[]`, `timeline`, `status`, `record?`.
- `POST /sessions/{id}/validate { notes, pendings_handled[] }` → `{ status: "validated" }`.
- `POST /sessions/{id}/finalize` → `{ payload_hash, anchor { tx_hash, explorer_url, block_time } | null, verify_id }`.
- Polling `GET /sessions/{id}` enquanto `anchor = null`.

## O que muda na V1 / V2 / Produto

- **V1:** validate + finalize em sequência num clique; observações e checkboxes guardados no Next; polling manual (botão "Atualizar").
- **V2:** polling automático; observações enviadas no `validate`; e-mail para a cliente ao registrar; retentativa de âncora no backend.
- **Produto:** assinatura do advogado no registro (chave própria); exportação do dossiê (respostas + dúvidas + hash) para o processo; painel de pendências entre sessões.
