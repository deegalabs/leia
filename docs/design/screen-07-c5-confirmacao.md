# C5 · Confirmação — `/c/{token}/confirm`

## Propósito e posição no fluxo

Resumo antes de confirmar: lista "o que você entendeu" com ✓, pontos marcados para o advogado e dúvidas anotadas. A cidadã confirma que entendeu a explicação (não é a assinatura do contrato) ou volta para rever uma parte. Entrada: última pergunta de C4. Saída: C6 (após `confirm`) ou C2 n (rever). Também abre em modo leitura a partir de CH ("Ver o resumo") depois de confirmada.

## Layout (mobile-first, 360×740)

```
[AssistantBanner — Dr. João Silva]
[main]
  h1 "O que você entendeu"                                          22 px
  p  "Confira a lista. Se quiser, volte e reveja uma parte."         17 px
  SummaryList (Card raio 22)
    h2 "As 7 partes"                                                 19 px
    li ✓ "O que o advogado vai fazer"  — "Entrar com a ação e acompanhar até o fim."
    li ✓ "Quanto você paga"            — "30% do que você receber, só se ganhar."
    li ✓ "Como e quando você paga"     — …
    li ✓ … (uma linha por tópico: título + essential)
    h2 "O que você explicou com suas palavras"                       19 px
    li ✓ "Quanto fica com o advogado se ganhar"
    li ✓ "Se perder, você paga honorários?"  chip "entendeu na 2ª vez" (só ícone + texto neutro: "vimos de novo")
    li ⚑ "O que acontece se cancelar"  chip âmbar "marcado para o Dr. João conversar com você"
    h2 "Suas dúvidas"                                                19 px
    li "2 dúvidas anotadas para o Dr. João"  [Ver dúvidas] (Collapsible)
  Card aviso (fundo #FFF4DD, ícone Info)
    "Confirmar aqui não é assinar o contrato. Você só confirma que entendeu a explicação. A assinatura é outro passo, com o Dr. João."
[BottomActionBar]
  [Confirmo que entendi]         primário 52 px
  [Quero rever uma parte]        secundário 48 px
```

## Componentes (shadcn/ui)

`Card`, `Button`, `Collapsible`, `Sheet` (escolher parte para rever), `AlertDialog` (confirmação final), `Skeleton`, `Alert`; novos: `SummaryList`, `StatusChip`, `AssistantBanner`, `BottomActionBar`.

## Copy exata (pt-BR)

- h1: "O que você entendeu"
- p: "Confira a lista. Se quiser, volte e reveja uma parte."
- Seções: "As 7 partes" · "O que você explicou com suas palavras" · "Suas dúvidas"
- Chips: "vimos de novo" (neutro) · "marcado para o Dr. João conversar com você" (âmbar) · "para ver de novo" (quando a conferência ficou adiada por falta de internet)
- Dúvidas: "2 dúvidas anotadas para o Dr. João" / "Nenhuma dúvida anotada" · "Ver dúvidas" / "Fechar dúvidas"
- Aviso: "Confirmar aqui não é assinar o contrato. Você só confirma que entendeu a explicação. A assinatura é outro passo, com o Dr. João."
- Botões: "Confirmo que entendi" · "Quero rever uma parte"
- `AlertDialog` ao confirmar: título "Confirmar que você entendeu?" texto "O Dr. João vai conferir suas respostas e depois o comprovante fica pronto. Isso não é a assinatura do contrato." Botões "Sim, confirmo" · "Ainda não"
- `Sheet` rever: título "Qual parte você quer rever?" lista dos 7 tópicos (48 px cada) + "Fechar"
- Modo leitura (já confirmada): aviso vira "Você confirmou em 12/09/2026 às 15:40. O Dr. João está conferindo." e a barra mostra só "Voltar para meus documentos".

## Estados

**Default** — todos os tópicos vistos e perguntas respondidas (com ou sem pendências).

**Vazio (partes ainda não vistas)** — se a cidadã pulou pelo indicador de progresso: itens não vistos aparecem sem ✓ com chip "ainda não vimos" e botão inline "Ver agora"; "Confirmo que entendi" fica desabilitado com nota "Falta ver 2 partes." Perguntas adiadas ("para ver de novo") também bloqueiam, com "Responder agora".

**Carregando** — h1 fixo; lista em `Skeleton` (7 + 3 linhas); botões desabilitados; "Carregando seu resumo".

**Erro (ao confirmar)** — `Alert`: "Deu um problema do nosso lado, não foi você. Estamos tentando de novo." Botão "Confirmar de novo". Nada se perde.

**Sem conexão** — lista vem do cache; "Confirmo que entendi" entra na fila: tela mostra "Sua confirmação está salva. Enviamos quando a internet voltar." e segue para C6 em estado "aguardando".

## Interações

- "Confirmo que entendi" → `AlertDialog` → "Sim, confirmo" → `POST /sessions/{id}/confirm` → círculo com check 250 ms → navega para C6.
- "Quero rever uma parte" → `Sheet` com a lista; toque em um tópico → C2 n com primário "Voltar para o resumo"; ao voltar, a lista mantém tudo.
- "Ver dúvidas" → `Collapsible` com cada dúvida: pergunta, resposta ou recusa, chip.
- Toque em item de tópico (linha inteira, 48 px) → mesmo comportamento que a Sheet (rever).
- Pendências não impedem confirmar: a cidadã confirma o que entendeu; o que ficou marcado vai para o advogado.

## Acessibilidade

- Foco no h1. Ordem: banner → h1 → p → lista (cada `<li>` é um botão "Rever: Quanto você paga, entendido") → dúvidas → aviso → barra.
- ✓ e ⚑ são SVG com `aria-label` ("entendido", "marcado para o advogado"); chips têm texto.
- Lista em `<ul>` com `aria-label` por seção; contagem anunciada no h2 ("As 7 partes").
- `AlertDialog` com foco inicial em "Ainda não" (ação segura), Esc fecha.
- Aviso em `role="note"`; não é live region.
- 200 %: linhas de tópico quebram em 2; chips passam para a linha de baixo.

## Chamadas de API

- `GET /sessions/{id}` → `sections[]`, `questions[]` com `answers[]`, `chats[]`, `pendings[]`, `status`, `confirmed_at`.
- `POST /sessions/{id}/confirm` `{ confirmed: true, client_time }` → `{ status: "confirmed", confirmed_at }`.

## O que muda na V1 / V2 / Produto

- **V1:** lista estática do cache; "Ver dúvidas" simples; modo leitura mínimo.
- **V2:** perguntas adiadas (offline) reaparecem aqui; texto do aviso lido em áudio automaticamente se `audio_pref = listen`.
- **Produto:** exportar o resumo em PDF junto do comprovante; histórico de confirmações quando o documento muda de versão (nova rodada só das partes alteradas).
