# Personas e implicações de design

Três personas, três superfícies. A cidadã é a usuária primária; o advogado supervisiona; o verificador confere. O produto nunca substitui o advogado.

## 1. Cidadã (primária) — "Maria"

| Campo | Conteúdo |
|---|---|
| Contexto | Vai assinar procuração, contrato de honorários ou acordo. Baixa escolaridade. Android básico (tela 360×740, Chrome), rede instável. Prefere ouvir a ler. |
| Hoje | Pesquisa no Google ou cola o documento e dados pessoais no ChatGPT. Tem medo de golpe e de "assinar errado". |
| Precisa | Entender antes de assinar, num lugar seguro. Perguntar, recusar, falar com o advogado. |
| Sucesso | Chega ao comprovante em menos de 4 minutos sem instruções e explica com as próprias palavras o que vai assinar. |
| Superfície | PWA mobile-first, rotas `/c/...`. |

Implicações de design:

- Uma tarefa por tela; um tópico por tela; layout idêntico entre tópicos (C2) e entre perguntas (C4).
- Áudio é primeiro: "▶ Começar ouvindo" é o botão primário; "Prefiro ler" é o secundário. Todo texto tem versão em áudio.
- Texto 17 px (mínimo 15, máximo 19), Atkinson Hyperlegible, linha ≤ 60 caracteres, frases ≤ 15 palavras, um R$ de exemplo por número.
- Alvos ≥ 48 px; microfone ≥ 64 px; sem tempo limite; "voltar" nunca apaga resposta.
- Segurança percebida: banner fixo "assistente automática · explica este documento · não dá conselho jurídico" e nome + OAB do advogado sempre visíveis no início.
- Nada de "nota", "teste", "prova", "errado". Feedback é "Vamos ver de novo" e "quase lá".
- Offline: conteúdo da sessão fica no service worker; respostas entram numa fila e sobem quando a conexão volta.

## 2. Advogado (supervisão) — "Dr. João Silva, OAB/PR 12345"

| Campo | Conteúdo |
|---|---|
| Contexto | Escritório pequeno, dativo ou Defensoria. Pouco tempo. Dever de informar com clareza (CED art. 9º e 48). |
| Precisa | Aprovar a explicação antes de a cidadã ver; enxergar dúvidas e respostas; validar; receber a prova. |
| Sucesso | Pendências claras; registro gerado; nada dito pela IA sem a citação literal da cláusula. |
| Superfície | Painel desktop, rotas `/lawyer/...`. |

Implicações de design:

- Fluxo em 3 telas curtas: enviar (A1) → revisar e aprovar (A2) → validar (A3). O painel (A4) mostra o que exige ação primeiro.
- Revisão lado a lado: cláusula original com citação destacada à esquerda, texto simples editável à direita. Selos "trecho verificado" e "juiz: fiel" por seção; sem selo verde, não aprova.
- Rubrica em palavras, nunca números: "entendeu e citou a consequência", "entendeu o essencial", "entendeu na 2ª tentativa", "pendente: conversar com a cliente".
- Tudo que a IA recusou ("não está no seu documento") vira pendência nomeada para o advogado responder.
- Tratamento por nome ("Dr. João"); IBM Plex Sans; tabelas densas; atalhos de teclado nas ações principais.

## 3. Verificador — auditor da OAB, juiz, ou a própria cidadã meses depois

| Campo | Conteúdo |
|---|---|
| Contexto | Recebeu o comprovante (QR ou link). Quer saber se o registro é íntegro e o que ele prova. |
| Precisa | Recalcular o hash a partir do JSON canônico e encontrar a transação pública. |
| Sucesso | `sha256sum` bate com o código exibido e com o dado gravado na transação. Nenhum dado pessoal exposto. |
| Superfície | Página pública `/verify/{id}`, responsiva. |

Implicações de design:

- Página sem login, sem nome, sem documento, sem respostas. Só hash, JSON canônico, transação, horário do bloco.
- Passo a passo de conferência com comandos copiáveis (IBM Plex Mono).
- Estado explícito para "carimbo pendente" (hash existe, transação ainda não).

## Tese que orienta todas as telas

"O cidadão entende antes de assinar; o advogado supervisiona; o registro prova."
