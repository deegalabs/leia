# A4 · Painel do advogado — `/lawyer`

## Propósito e posição no fluxo

Visão de tudo que o advogado enviou: documentos em preparação e sessões dos clientes, com estado, pendências e ação direta. Primeira tela após o login. Entradas: A0, sidebar, retorno de A1/A2/A3. Saídas: A1 (novo documento), A2 (revisar), A3 (validar), copiar link.

## Layout (desktop, 1440×900)

```
┌ Sidebar 240 ┬────────────────────────────────────────────────────────────┐
│ LeIA        │ h1 "Painel"                                [+ Novo documento]│
│ ● Painel    │ p  "Bom dia, Dr. João. 2 itens precisam de você."           │
│   Novo doc. │ Tabs: Todos (6) · Precisam de mim (2) · Aguardando cliente (3) · Registrados (1) │
│             │ Input busca "Buscar por cliente ou documento"  (à direita)   │
│             │ ┌──────────────────────────────────────────────────────────┐│
│             │ │ Cliente │ Documento │ Status │ Pendências │ Atualizado │ Ações ││
│             │ ├──────────────────────────────────────────────────────────┤│
│             │ │ —       │ Contrato de honorários │ ● aguardando revisão │ — │ há 3 min │ [Revisar] ││
│             │ │ Maria   │ Contrato de honorários │ ● link enviado │ — │ há 1 h │ [Copiar link] ││
│             │ │ Carlos  │ Procuração │ ● em andamento │ 1 dúvida │ há 12 min │ [Acompanhar] ││
│             │ │ Ana     │ Acordo │ ● aguardando validação │ 2 pendências │ há 40 min │ [Validar] ││
│             │ │ Pedro   │ Contrato de honorários │ ✓ registrado │ — │ ontem │ [Ver registro] ││
│ Dr. João    │ └──────────────────────────────────────────────────────────┘│
│ OAB/PR 12345│ Paginação 20 por página                                     │
│ [Sair]      │                                                            │
└─────────────┴────────────────────────────────────────────────────────────┘
```

Ordem padrão: "Precisam de mim" primeiro (aguardando revisão, aguardando validação), depois por atualização mais recente.

## Componentes (shadcn/ui)

`Sidebar`, `Table`, `Tabs`, `Input`, `Button`, `Badge`, `DropdownMenu` (ações secundárias), `Tooltip`, `Skeleton`, `Alert`, `Toast`, `ScrollArea`; novos: `StatusChip`, `EmptyState`.

## Copy exata (pt-BR)

- h1: "Painel"
- Saudação: "Bom dia, Dr. João. 2 itens precisam de você." (variantes: "Boa tarde"/"Boa noite"; 0 itens: "Nada pendente por agora.")
- Botão: "Novo documento"
- Abas: "Todos" · "Precisam de mim" · "Aguardando cliente" · "Registrados"
- Busca: "Buscar por cliente ou documento"
- Colunas: "Cliente" · "Documento" · "Status" · "Pendências" · "Atualizado" · "Ações"
- Status: "processando" · "aguardando revisão" · "link enviado" · "em andamento" · "aguardando validação" · "registrado" · "registrado · carimbo pendente"
- Pendências: "—" · "1 dúvida" · "2 pendências" (tooltip: "1 pergunta para conversar, 1 dúvida fora do documento")
- Ações por status: processando → "Ver etapas"; aguardando revisão → "Revisar"; link enviado → "Copiar link" (menu: "Ver explicação", "Gerar novo link"); em andamento → "Acompanhar"; aguardando validação → "Validar"; registrado → "Ver registro"
- Menu de linha (⋯): "Ver explicação" · "Copiar link" · "Gerar novo link" · "Arquivar"
- Toast: "Link copiado. Envie para a cliente pelo canal que preferir."

## Estados

**Default** — tabela com linhas; chip de contagem nas abas.

**Vazio** — `EmptyState` com ícone `FileText`: "Nenhum documento ainda." / "Envie um PDF e a LeIA prepara a explicação para você revisar." Botão "Novo documento". Nas abas filtradas vazias: "Nada aqui por enquanto." sem botão. Busca sem resultado: "Nenhum resultado para 'xyz'." + "Limpar busca".

**Carregando** — cabeçalho e abas fixos; 5 linhas `Skeleton`; `aria-busy` na tabela; "Carregando o painel".

**Erro** — `Alert` acima da tabela: "Não foi possível carregar o painel. Estamos tentando de novo." + "Tentar de novo". Última lista conhecida fica visível com aviso "Dados de há 5 min".

**Linha com erro de processamento** — status "erro ao processar" (vermelho, ícone AlertTriangle) e ação "Ver o que aconteceu" (abre A1 no estado de erro).

## Interações

- "Novo documento" (ou tecla `N`) → A1.
- Linha inteira clicável → ação principal da linha; botão de ação também. Hover fundo `#F4F4F0` 100 ms.
- Abas filtram sem recarregar; contagens atualizam; sublinhado desliza 150 ms.
- Busca (`/` foca) filtra por nome do cliente ou tipo de documento com debounce 250 ms.
- "Copiar link" → clipboard → toast; o link é `https://{host}/c/{token}`.
- Atualização automática a cada 60 s (silenciosa) quando a aba está visível; linhas alteradas ganham fundo `#EAF4F4` por 2 s.
- Menu ⋯ com `DropdownMenu`; "Arquivar" pede `AlertDialog` "Arquivar este documento? Ele some do painel, mas o registro continua válido."

## Acessibilidade

- Foco no h1 ao entrar. Ordem: pular para conteúdo → sidebar → h1 → Novo documento → abas (`role="tablist"`) → busca → tabela → paginação.
- Tabela semântica (`<table>` com `<th scope="col">`); ordenação por coluna "Atualizado" com `aria-sort`.
- Chips com ícone + texto; cor nunca sozinha; contraste ≥ 4,5:1 (`#B26A00` com branco 4,6:1; em fundo claro usa texto `#7A4800`).
- Linha clicável mantém um único elemento focável (o botão de ação) com `aria-label` completo: "Validar, Ana, Acordo".
- Contagem nas abas anunciada ("Precisam de mim, 2").
- Atualização silenciosa não move o foco; mudanças anunciadas em `role="status"` só quando um item entra em "Precisam de mim" ("Nova sessão aguardando validação: Ana").
- Alvos em tabela ≥ 32 px com 8 px de espaço; em toque ≥ 44 px.

## Chamadas de API

- Listagem: **não há endpoint de listagem no contrato.** Proposta: `GET /documents?lawyer=me` e `GET /sessions?lawyer=me` (ou um `GET /lawyer/overview`). Pendência no INDEX. V1: o Next guarda os ids criados por este advogado e chama `GET /sessions/{id}` para cada um.
- Por linha: `GET /sessions/{id}` → `status`, `pendings[]`, `updated_at`, `client_first_name`, `document_type`, `client_token`.
- "Gerar novo link": `POST /sessions` com o mesmo `document_id` (invalida o anterior; pendência de contrato).

## O que muda na V1 / V2 / Produto

- **V1:** lista local dos ids + `GET /sessions/{id}`; sem paginação; sem "Arquivar"; atualização por recarregar a página.
- **V2:** endpoint de listagem com filtros e paginação; atualização automática; arquivar; notificação por e-mail quando uma sessão entra em "aguardando validação".
- **Produto:** múltiplos advogados por escritório; métricas por período (tempo médio até o comprovante, % de "entendeu na 1ª"); exportação CSV.
