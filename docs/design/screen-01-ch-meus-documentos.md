# CH · Meus documentos — `/c`

## Propósito e posição no fluxo

Painel da cidadã depois do login com Google. Lista os documentos que advogados mandaram para ela, com estado e ação principal. É a porta de entrada quando ela abre o app instalado (PWA) sem link; quem chega por link vai direto a C0/C1 e só vê esta tela ao voltar depois. Objetivos: retomar de onde parou, abrir comprovantes, falar com o advogado.

## Layout (mobile-first, 360×740)

```
[AssistantBanner — sem advogado fixo; "Falar com o advogado" abre lista]
[main]
  h1 "Meus documentos"                                    22 px
  p  "Oi, Maria. Aqui ficam os documentos que advogados mandaram para você."  17 px
  ── Card por documento (raio 22, borda 1 px, padding 16) ──
   StatusChip  ● em andamento                              15 px, ícone + texto
   h2 "Contrato de honorários"                             19 px
   p  "Dr. João Silva · OAB/PR 12345"                       15 px, muted
   p  "Recebido em 12/09/2026"                              15 px, muted
   [Continuar]  (Button default, 48 px, largura total)
  ── Card seguinte… (ordem: em andamento → a começar → entendido → comprovante disponível)
  Link "Recursos de acessibilidade" (símbolo LBI) no rodapé do main
[BottomActionBar — vazia nesta tela; "Falar com o advogado" fica só no banner]
```

Sem barra inferior aqui: a ação principal está em cada card. Menu "Sair" fica em um `DropdownMenu` no avatar, canto superior direito do main (48 px).

## Componentes (shadcn/ui)

`Card`, `Button`, `Skeleton`, `DropdownMenu` (avatar → "Sair da conta"), `Alert`; novos: `AssistantBanner`, `StatusChip`, `EmptyState`, `OfflineBanner`, `AccessibilitySheet`, `VLibrasMount`.

## Copy exata (pt-BR)

- Título: "Meus documentos"
- Subtítulo: "Oi, Maria. Aqui ficam os documentos que advogados mandaram para você."
- Chips: "a começar" · "em andamento" · "entendido" · "comprovante disponível"
- Linha do advogado: "Dr. João Silva · OAB/PR 12345"
- Data: "Recebido em 12/09/2026"
- Ações por estado: a começar → "Começar a explicação"; em andamento → "Continuar"; entendido → "Ver o resumo" (abre C5 em modo leitura) com legenda "O Dr. João ainda vai conferir."; comprovante disponível → "Ver comprovante".
- Menu: "Sair da conta"
- Rodapé: "Recursos de acessibilidade"

## Estados

**Default** — lista de cards como acima; máximo esperado: poucos documentos, sem paginação.

**Vazio** — `EmptyState` com ícone `Inbox`:
"Nenhum documento por enquanto." / "Quando um advogado mandar um documento, ele aparece aqui. Você também pode abrir o link que ele enviar." Sem botão de ação (a cidadã não cria documentos).

**Carregando** — h1 e subtítulo fixos; 2 `Skeleton` de card (altura 168 px). `aria-busy="true"` no `<main>`; leitor de tela ouve "Carregando seus documentos".

**Erro** — `Alert` acima da lista: "Deu um problema do nosso lado, não foi você. Estamos tentando de novo." Botão "Tentar carregar de novo". Se há cache local (service worker), mostra os cards do cache com chip "atualizado há 2 h" e o mesmo alerta em tom informativo.

**Sem conexão** — `OfflineBanner`; cards vêm do cache; ações "Continuar" funcionam (conteúdo já baixado); "Ver comprovante" mostra o último estado conhecido.

## Interações

- Toque no card inteiro ou no botão → navega para `resume_path` da sessão (C1, C2 n, C4 k, C5 ou C6). Transição fade + 12 px, 180 ms.
- Pull-to-refresh nativo do Chrome desabilitado (evita disparo acidental); há botão "Atualizar lista" (ghost, 48 px) acima da lista quando o cache tem mais de 1 h.
- "Falar com o advogado" (banner) → `LawyerContactSheet` com um item por advogado; se lista vazia, texto "Quando um advogado mandar um documento, o contato dele aparece aqui."
- Avatar → `DropdownMenu` → "Sair da conta" → `AlertDialog` "Sair da conta? Seus documentos continuam salvos com o advogado." / "Sair" · "Ficar".
- Chip "comprovante disponível" com anchor pendente mostra "comprovante disponível · carimbo a caminho".

## Acessibilidade

- Foco inicial no h1 ao entrar. Ordem: banner (texto → Falar com o advogado) → avatar → h1 → cards (cada card é um `<article>` com o botão como único foco; o título do card está no `aria-labelledby` do botão: "Continuar, Contrato de honorários, Dr. João Silva") → rodapé.
- Chips com ícone + texto; cores: em andamento `#1F7373`, entendido `#1F7A4D`, comprovante `#1F7A4D`, a começar `#4A4F52`.
- Alvos: botão do card 48 px; avatar 48 px.
- Texto reflui a 200 % sem rolagem horizontal; cards viram lista simples.
- `lang="pt-BR"`, VLibras montado, símbolo de acessibilidade no rodapé.

## Chamadas de API

- Sessão da conta: Auth.js (`GET /api/auth/session`).
- Lista: **não há endpoint de listagem no contrato.** V1: lista de `session_id`/`token` gravada localmente em `POST /sessions/{id}/bind`, e um `GET /sessions/{id}` por item (paralelo, máximo 5). V2: endpoint de listagem por conta (pendência no INDEX).
- Estado por item: `GET /sessions/{id}` → `status`, `resume_path`, `lawyer {name, oab}`, `document_type`, `created_at`, `record?`.

## O que muda na V1 / V2 / Produto

- **V1 (hackathon):** lista local + `GET /sessions/{id}`; sem "Atualizar lista"; sem paginação; "Sair da conta" simples.
- **V2:** endpoint de listagem por conta; notificação (e-mail) quando o comprovante fica pronto, com link para cá; "Atualizar lista".
- **Produto:** múltiplos advogados por cidadã com agrupamento por escritório; arquivamento de documentos antigos; pedido de exclusão de dados (LGPD) a partir desta tela.
