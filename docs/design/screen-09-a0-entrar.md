# A0 · Entrar (advogado) — `/lawyer/login`

## Propósito e posição no fluxo

Login obrigatório com Google para o painel. No primeiro acesso, pede nome e OAB/UF antes de liberar qualquer tela. Entrada: link direto, `/` sem sessão, ou redirecionamento de qualquer `/lawyer/*`. Saída: A4 (ou a rota que o advogado tentou abrir, via `callbackUrl`).

## Layout (desktop, referência 1440×900)

```
┌──────────────────────────────┬────────────────────────────────────────┐
│ Painel esquerdo (marinho)    │ Painel direito (branco), coluna 400 px │
│ 40 % da largura              │ centralizada vertical                   │
│                              │                                        │
│  Wordmark "LeIA"             │  h1 "Entrar no painel"         20 px    │
│  (IA em teal da marca)       │  p  "Use a conta Google do escritório  │
│                              │      ou a sua."                        │
│  p off-white 18 px:          │  [G  Entrar com Google]  48 px, largura│
│  "O cidadão entende antes de │                              total     │
│   assinar. Você supervisiona.│  p muted 13 px: "Só pedimos e-mail e   │
│   O registro prova."         │   nome. Nenhum documento fica no       │
│                              │   Google."                             │
│  ul 15 px:                   │                                        │
│  · Explicação em linguagem   │  ── Passo 2 (primeiro acesso) ──       │
│    simples, sempre com o     │  h2 "Complete seu cadastro"            │
│    trecho da cláusula        │  Input "Nome completo" (pré-preenchido)│
│  · Você aprova antes de o    │  Input "Número da OAB" (só dígitos)    │
│    cliente ver               │  Select "UF" (27 opções)               │
│  · Registro público sem      │  [Salvar e entrar no painel]  48 px    │
│    dados pessoais            │                                        │
└──────────────────────────────┴────────────────────────────────────────┘
```

Abaixo de 768 px: painel esquerdo vira faixa de 120 px no topo com a wordmark; formulário ocupa a largura.

## Componentes (shadcn/ui)

`Button`, `Form`, `Input`, `Label`, `Select`, `Alert`, `Skeleton`, `Toast`.

## Copy exata (pt-BR)

- Painel esquerdo: "O cidadão entende antes de assinar. Você supervisiona. O registro prova." + os 3 itens do layout.
- h1: "Entrar no painel"
- p: "Use a conta Google do escritório ou a sua."
- Botão: "Entrar com Google" (carregando: "Entrando…")
- Nota: "Só pedimos e-mail e nome. Nenhum documento fica no Google."
- Passo 2: h2 "Complete seu cadastro"; p "Isso aparece para o seu cliente como 'Dr. João Silva, OAB/PR 12345'."
- Campos: "Nome completo" · "Número da OAB" (placeholder "12345") · "UF" (placeholder "Escolha")
- Botão: "Salvar e entrar no painel"
- Erros de campo: "Digite seu nome como aparece na OAB." · "Digite só os números da OAB." · "Escolha a UF da sua inscrição."
- Prévia ao vivo abaixo dos campos: "Seu cliente verá: Dr. João Silva · OAB/PR 12345"

## Estados

**Default** — passo 1 (botão do Google). Se já logado com cadastro completo, redireciona para A4 sem mostrar a tela.

**Vazio (primeiro acesso)** — após o Google, passo 2 aparece no lugar do botão (mesma coluna), nome pré-preenchido pelo perfil Google, OAB e UF vazios; foco no campo "Número da OAB".

**Carregando** — botão "Entrando…" com spinner e `aria-busy`; ao voltar do Google, `Skeleton` de 3 linhas enquanto `GET /me` responde.

**Erro** — `Alert` acima do botão: "Não foi possível entrar. Tente de novo ou use outra conta." Erro ao salvar cadastro: "Não conseguimos salvar. Seus dados continuam no formulário." Botão "Salvar de novo".

**Conta sem permissão** (lista de e-mails, se existir no hackathon) — `Alert`: "Esta conta ainda não tem acesso. Fale com a equipe LeIA." (pendência: haverá allowlist?)

## Interações

- "Entrar com Google" → `signIn("google", { callbackUrl })`. Retorno com cadastro completo → A4 (fade 120 ms). Incompleto → passo 2.
- Passo 2: validação ao sair do campo (`onBlur`) e ao enviar; OAB aceita 3–7 dígitos; prévia "Seu cliente verá:" atualiza a cada tecla.
- "Salvar e entrar no painel" → salva perfil (Auth.js + tabela `lawyer`) → A4 com toast "Cadastro completo. Bem-vindo, Dr. João."
- Enter envia o formulário; Esc não faz nada (não há modal).

## Acessibilidade

- Foco inicial no h1; no passo 2, foco no primeiro campo vazio.
- Ordem: pular para o conteúdo → h1 → p → botão Google → nota; passo 2: h2 → nome → OAB → UF → prévia (`aria-live="polite"`) → botão.
- Campos com `Label` visível, `aria-invalid` e `aria-describedby` na mensagem de erro; erro anunciado ao enviar via `role="alert"` resumido ("2 campos precisam de atenção").
- `Select` de UF navegável por teclado, com busca por letra.
- Painel esquerdo é decorativo para leitor de tela? Não: o texto da tese é conteúdo; a wordmark tem `alt="LeIA"`.
- Contraste: texto off-white sobre marinho 16:1; botão Google outline com borda `#1A1D1F`.
- Alvos 48 px; sem tempo limite.

## Chamadas de API

- Auth.js Google (`/api/auth/*`).
- Perfil do advogado: fora do contrato FastAPI — proposta: `GET /me` e `PUT /me { name, oab_number, oab_uf }` no Next (route handler) ou no FastAPI. Pendência no INDEX.

## O que muda na V1 / V2 / Produto

- **V1:** Google + formulário de 3 campos salvo no banco do Next; sem validação da OAB; sem allowlist (ou allowlist por variável de ambiente).
- **V2:** telefone do escritório (opcional) para "Falar com o advogado"; verificação do número na CNA (Cadastro Nacional dos Advogados) quando houver API.
- **Produto:** escritórios com vários advogados (convite por e-mail), papéis (titular, assistente), login institucional para Defensoria.
