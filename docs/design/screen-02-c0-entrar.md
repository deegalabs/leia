# C0 · Entrar — `/c/{token}/login`

## Propósito e posição no fluxo

Primeira tela que a cidadã vê ao abrir o link enviado pelo advogado. Mostra quem mandou (nome + OAB) e qual documento é, pede o login com Google em um toque e explica por quê. O token do link continua obrigatório; o login só liga a sessão à conta para retomar depois e receber o comprovante. Saída: C1 (`/c/{token}`). Se a sessão já está ligada a esta conta e ela está logada, esta tela não aparece.

## Layout (mobile-first, 360×740)

```
[AssistantBanner — Dr. João Silva]
[main, centralizado verticalmente quando sobra espaço]
  Wordmark "LeIA" pequena (marinho), 28 px de altura, aria-hidden + texto "LeIA"
  h1 "Um documento para você entender antes de assinar"        22 px
  Card (raio 22, fundo branco)
    p "Enviado por"                                            15 px muted
    p "Dr. João Silva"                                         19 px semibold
    p "OAB/PR 12345"                                           15 px
    Separator
    p "Documento"                                              15 px muted
    p "Contrato de honorários"                                 19 px semibold
  h2 "Por que pedimos para entrar"                             19 px
  ul (3 itens, ícone check aria-hidden)
    "Para você continuar de onde parou, mesmo trocando de celular."
    "Para você receber o comprovante no final."
    "Não pedimos senha. Só usamos o e-mail para reconhecer você."
[BottomActionBar]
  [Entrar com Google]              primário, ícone G, 52 px
  [Continuar sem conta]            secundário (pendente de decisão)
```

## Componentes (shadcn/ui)

`Card`, `Separator`, `Button`, `Alert`, `Skeleton`; novos: `AssistantBanner`, `BottomActionBar`, `OfflineBanner`.

## Copy exata (pt-BR)

- h1: "Um documento para você entender antes de assinar"
- Rótulos: "Enviado por" · "Documento"
- h2: "Por que pedimos para entrar"
- Itens: como no layout.
- Botão primário: "Entrar com Google"
- Botão secundário: "Continuar sem conta"
- Nota sob os botões (15 px, muted): "Você não assina nada aqui. Aqui você só entende o documento."
- Legenda ao voltar do Google: "Pronto. Vamos começar."

## Estados

**Default** — como no layout. Sessão válida, ainda não ligada a conta.

**Vazio (token inválido ou expirado)** — sem card; h1 "Este link não está mais disponível." p "Peça ao seu advogado um novo link. Se preferir, fale com ele agora." Banner mantém "Falar com o advogado" só se o backend devolver o advogado (`410` com `lawyer`); senão o botão abre a folha com o texto genérico.

**Carregando** — Card em `Skeleton` (4 linhas); botões desabilitados com `aria-disabled`; "Carregando o documento" em `role="status"`.

**Erro** — `Alert`: "Deu um problema do nosso lado, não foi você. Estamos tentando de novo." Botão "Tentar de novo". Se o login do Google falhar ou for cancelado: toast "O login não terminou. Você pode tentar de novo ou continuar sem conta."

**Sessão ligada a outra conta** — h1 "Este documento está ligado a outra conta do Google." p "Entre com a mesma conta que usou antes." Botão "Trocar de conta".

## Interações

- "Entrar com Google" → `signIn("google", { callbackUrl: /c/{token} })`. Ao voltar, o app chama `POST /sessions/{id}/bind`, salva o token localmente (lista de CH) e navega para C1 com fade 180 ms. Toast "Pronto. Vamos começar." (3 s).
- "Continuar sem conta" → navega para C1 sem bind; sessão fica só no dispositivo; C6 mostra aviso "Salve o comprovante agora: sem conta, ele fica só neste celular." **Decisão pendente da equipe** (INDEX › Pendências). Se a equipe retirar a opção, a barra fica só com o primário.
- Sem conexão: botão do Google desabilitado com texto "Precisa de internet para entrar."; "Continuar sem conta" segue disponível se a sessão já está em cache.

## Acessibilidade

- Foco inicial no h1. Ordem: banner → h1 → card (texto, não focável) → h2 → lista → botões.
- Botão do Google: `aria-label="Entrar com Google"`, ícone decorativo. Estado de carregamento: "Entrando…" com `aria-busy`.
- "Continuar sem conta" tem `aria-describedby` apontando para a nota sobre salvar o comprovante.
- Alvos: 52/48 px; contraste do card sobre `#FAF8F4` com borda `#E3E0D8` e texto `#1A1D1F`.
- Anúncio ao chegar do Google: `role="status"` "Pronto. Vamos começar."
- 200 %: card e lista refluem; botões continuam empilhados.

## Chamadas de API

- `GET /sessions/{id}` (id resolvido do token pelo backend; a rota pública aceita o token) → `lawyer {name, oab}`, `document_type`, `bound: bool`, `status`.
- Auth.js Google → `POST /sessions/{id}/bind` `{ token }` → `200` (liga) · `409` (ligada a outra conta).

## O que muda na V1 / V2 / Produto

- **V1:** Google via Auth.js; "Continuar sem conta" presente atrás de flag `NEXT_PUBLIC_ALLOW_GUEST` (default ligada até a decisão); sem tela de troca de conta (mostra só o alerta).
- **V2:** decisão final sobre "sem conta"; e-mail de boas-vindas com o link; detecção de conta diferente com "Trocar de conta".
- **Produto:** login por telefone/OTP como alternativa ao Google (muitas cidadãs não têm conta Google ativa no celular); consentimento LGPD com registro de versão.
