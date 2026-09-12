# Navegação

## Cidadã (mobile, `/c/...`)

Estrutura fixa em todas as telas C0–C6 e CH, nesta ordem no DOM:

```
┌──────────────────────────────────────────┐
│ AssistantBanner (fixo no topo, marinho)  │ 76 px em 360 px; 64 px a partir de 400 px
├──────────────────────────────────────────┤
│ <main> rolável                           │ padding-bottom = altura da barra + 16 px
│   …conteúdo da tela…                     │ scroll-padding-bottom idem
├──────────────────────────────────────────┤
│ BottomActionBar (fixo embaixo)           │ 1 ou 2 botões empilhados, largura total
└──────────────────────────────────────────┘
```

### AssistantBanner

- Fundo marinho `#081820`, texto off-white `#F0F0E8` 15 px/1.35, três linhas curtas: "assistente automática" / "explica este documento" / "não dá conselho jurídico". A partir de 400 px cabe em duas linhas; a quebra é por `·`.
- À direita, botão "Falar com o advogado": outline, borda e texto teal da marca `#38A8A8` (6,4:1 sobre marinho), 48 × ~120 px, rótulo em duas linhas. Mesma posição em todas as telas (WCAG 3.2.6 Ajuda consistente).
- `role="region" aria-label="Aviso da assistente"`; o texto é lido uma vez por carregamento (não é `aria-live`).
- Ao tocar "Falar com o advogado": abre `Sheet` inferior "Falar com o Dr. João Silva" com OAB/PR 12345, texto "O Dr. João vê todas as suas dúvidas anotadas quando confere sua sessão." e, se houver telefone cadastrado, botão "Ligar para o escritório" (`tel:`). Fecha com "Voltar para a explicação" ou Esc. Canal de contato é pendência (INDEX).
- Se há sessão em CH (sem token na rota), a folha lista os advogados dos documentos; sem documentos, mostra só o texto "Quando um advogado mandar um documento, o contato dele aparece aqui.".

### BottomActionBar

- `position: fixed; bottom: 0; padding: 12px 16px calc(12px + env(safe-area-inset-bottom))`; fundo `#FAF8F4` com borda superior 1 px `#E3E0D8`.
- Botão primário: teal de ação `#1F7373`, texto branco 17 px semibold, altura 52 px, raio 12 px. Botão secundário: outline `#1F7373` sobre claro, 48 px. No máximo 2 botões aqui; o terceiro do limite de 3 ações é sempre "Falar com o advogado" no banner.
- Rótulos sempre verbo + resultado: "Ouvir explicação", "Entendi, próximo", "Tenho uma dúvida", "Confirmo que entendi".
- A barra nunca cobre o elemento focado: `main { scroll-padding-bottom: 148px }` e `padding-bottom` equivalente.

### Voltar

- Botão de sistema (Android) e gesto de borda funcionam como "voltar" do histórico. O estado de cada tela é salvo antes de sair (rascunho de resposta, transcrição, posição do áudio). Voltar nunca perde resposta.
- Não há botão "Voltar" visível nas telas de tópico: a progressão é "Entendi, próximo"; rever é pela lista de C5 ou pelo indicador de progresso (toque em um segmento já visto abre o tópico correspondente).
- C3 volta para o tópico de origem (`?from={n}`); C2 aberto a partir de C5 volta para C5.

### Estado de conexão (OfflineBanner)

- Abaixo do AssistantBanner, faixa amarela `#FFF4DD` texto `#5C3A00` 15 px, `role="status"`: "A conexão caiu. Suas respostas estão salvas. Quando voltar, é só tocar em Continuar." Some ao reconectar com "Conexão de volta. Enviando suas respostas…" por 3 s.

### Rodapé de acessibilidade

- Widget VLibras montado à direita (padrão do plugin), acima da BottomActionBar (offset 148 px). Símbolo de acessibilidade (LBI art. 63) no rodapé do `<main>` de C1 e CH com link "Recursos de acessibilidade" (abre `Sheet` com: tamanho do texto 100/150/200 %, reduzir animações, VLibras).
- `lang="pt-BR"` no `<html>`.

## Advogado (desktop, `/lawyer/...`)

```
┌────────────┬───────────────────────────────────────────┐
│ Sidebar    │ Cabeçalho da página (título, ações)        │
│ 240 px     ├───────────────────────────────────────────┤
│ marinho    │ Conteúdo (tabelas, revisão lado a lado)     │
│            │                                           │
│ [Painel]   │                                           │
│ [Novo doc.]│                                           │
│ …          │                                           │
│ Dr. João   │                                           │
│ OAB/PR …   │                                           │
│ [Sair]     │                                           │
└────────────┴───────────────────────────────────────────┘
```

- Sidebar (`Sidebar` do shadcn): fundo marinho, wordmark "LeIA" (IA em teal da marca), itens "Painel" (`/lawyer`) e "Novo documento" (`/lawyer/new`), item ativo com fundo `#0F2A36` e barra 3 px teal da marca. Rodapé com avatar (Google), nome, "OAB/PR 12345" e "Sair". Colapsa para 64 px (só ícones + tooltip) entre 768 e 1023 px.
- `Breadcrumb` no cabeçalho: Painel › Documento #123 › Revisar. Título h1 20 px.
- Atalhos: `N` novo documento (no painel), `Ctrl+Enter` aprova/valida na tela correspondente, `/` foca a busca. Sempre há equivalente clicável.
- Foco: ao trocar de rota, foco vai ao h1; o link "Pular para o conteúdo" é o primeiro elemento focável.

## Público (`/verify/{id}`)

- Sem sidebar nem banner. Cabeçalho simples com wordmark e "Verificação pública". Rodapé com "O que esta página mostra e o que não mostra".
