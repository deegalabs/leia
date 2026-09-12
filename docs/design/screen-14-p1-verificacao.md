# P1 · Verificação pública — `/verify/{id}`

## Propósito e posição no fluxo

Página pública, sem login, aberta pelo QR do comprovante ou pelo link. Mostra o hash, o JSON canônico, a transação na rede pública e o horário do bloco, e ensina a conferir com `sha256sum`. Não mostra nome, documento, respostas ou dúvidas. Usuários: auditor da OAB, juiz, a própria cidadã meses depois, o advogado.

## Layout (responsivo, coluna única max 720 px)

```
Cabeçalho: wordmark "LeIA" · "Verificação pública"
h1 "Registro de entendimento"                                          22 px
StatusChip ✓ "registrado em 12/09/2026 às 16:42 (horário de Brasília)"  | ◔ "carimbo pendente"
Card "O que esta página mostra"
  p "Esta página mostra um código e onde ele foi gravado. Ela não mostra nome, documento nem respostas."
Card "Código do registro (SHA-256)"
  HashDisplay mono, grupos de 8, [Copiar código]
Card "Transação pública"
  p "Rede: Polygon Amoy (rede de testes)"           ← rótulo vem do backend
  p "Transação: 0x8f3a…c21e"  [Copiar] [Abrir no explorador ↗]
  p "Horário do bloco: 12/09/2026 16:42:07 (UTC-3)"
Card "JSON canônico" (Collapsible, fechado)
  [▸ Ver JSON canônico]  ·  [Baixar registro.json]  ·  [Copiar JSON]
  <pre> com o JSON exatamente como foi hasheado (bytes idênticos)
Card "Como conferir por conta própria"
  ol
   1 "Baixe o arquivo registro.json (botão acima). Não abra e salve de novo: isso pode mudar os bytes."
   2 "No terminal, rode:"  <code>sha256sum registro.json</code> [Copiar]
   3 "Compare o resultado com o código do registro acima. Precisa ser igual, caractere por caractere."
   4 "Abra a transação no explorador e confira que o mesmo código está gravado no campo de dados (input data)."
  p muted "No Windows: certutil -hashfile registro.json SHA256. No macOS: shasum -a 256 registro.json."
Rodapé: "O que este registro prova" + "O que não prova" (dois parágrafos) · link "Sobre a LeIA"
```

## Componentes (shadcn/ui)

`Card`, `Badge`, `Button`, `Collapsible`, `Alert`, `Skeleton`, `Toast`; novos: `HashDisplay`, `StatusChip`.

## Copy exata (pt-BR)

- h1: "Registro de entendimento"
- Chips: "registrado em {data} às {hora} (horário de Brasília)" · "carimbo pendente" · "registro não encontrado"
- Card 1: "O que esta página mostra" + "Esta página mostra um código e onde ele foi gravado. Ela não mostra nome, documento nem respostas."
- Card 2: "Código do registro (SHA-256)" · "Copiar código" / "Copiado"
- Card 3: "Transação pública" · "Rede: {nome}" · "Transação:" · "Abrir no explorador" · "Horário do bloco:"
- Card 4: "JSON canônico" · "Ver JSON canônico" / "Fechar JSON canônico" · "Baixar registro.json" · "Copiar JSON" · nota "Este é o texto exato que gerou o código. Qualquer espaço a mais muda o resultado."
- Card 5: "Como conferir por conta própria" + passos do layout.
- Rodapé: "O que este registro prova: que este código existia neste horário e foi gerado a partir do JSON acima, que descreve uma sessão de entendimento (número de tópicos, perguntas e resultados) validada por um advogado." / "O que não prova: não é a assinatura do contrato, não mostra o conteúdo do documento e não substitui a conversa com o advogado."
- Provisório: "O código já existe. A gravação na rede pública ainda está sendo confirmada; volte em alguns minutos."

## Estados

**Default (final)** — chip registrado, hash, transação, JSON, passos.

**Vazio (id inexistente ou sessão não finalizada)** — h1 "Registro não encontrado"; p "Confira o link ou o QR do comprovante. Se o registro foi feito há poucos minutos, tente de novo em instantes." Sem cards de hash/transação. HTTP 404.

**Carregando** — h1 fixo; `Skeleton` nos cards de hash e transação; "Carregando o registro".

**Erro** — `Alert`: "Não foi possível carregar o registro. Tente de novo em instantes." + "Tentar de novo".

**Provisório (carimbo pendente)** — chip "carimbo pendente"; hash e JSON presentes; card de transação com o texto provisório; passos 1–3 disponíveis, passo 4 marcado "disponível quando a gravação confirmar". Recarrega a cada 60 s.

## Interações

- "Copiar código"/"Copiar JSON"/"Copiar" (transação e comando) → clipboard; rótulo "Copiado" 1,5 s; `role="status"`.
- "Baixar registro.json" → download do JSON canônico com os mesmos bytes usados no hash (`Content-Type: application/json`, sem reformatar, sem BOM, sem quebra final adicional). O arquivo não leva metadados além do conteúdo.
- "Abrir no explorador" → `explorer_url` em nova aba, `rel="noopener noreferrer"`.
- "Ver JSON canônico" → `Collapsible` 200 ms; `<pre>` com rolagem horizontal interna.
- Sem login, sem cookies, sem analytics de terceiros. `<meta name="robots" content="noindex">`.

## Acessibilidade

- Foco no h1; título da aba "Verificação pública · LeIA".
- Ordem: cabeçalho → h1 → chip → cards na ordem visual; cada botão de copiar tem `aria-describedby` do bloco que copia.
- Hash e transação em `<code>` com `overflow-wrap: anywhere`; leitor de tela lê em grupos de 8.
- `<pre>` do JSON com `tabindex="0"` e `aria-label="JSON canônico"` para rolagem por teclado.
- Passos em `<ol>`; comandos em `<code>` com botão Copiar ao lado (não só seleção).
- Links externos com "abre em nova aba" no `aria-label`.
- Contraste ≥ 4,5:1; chips com ícone + texto; texto 16 px (público), mono 14 px.
- 200 % e 320 px: JSON rola dentro do bloco; nada da página rola horizontalmente.
- VLibras montado (LBI).

## Chamadas de API

- `GET /verify/{id}` → `{ status: "registered" | "pending" | "not_found", payload_hash, canonical_json (string exata), anchor { network, tx_hash, explorer_url, block_time } | null }`.
- Nenhuma outra chamada; nada é enviado pelo cliente.

## O que muda na V1 / V2 / Produto

- **V1:** página estática por render no servidor; JSON em `<pre>`; passos fixos; rede de testes (Polygon Amoy) declarada no rótulo.
- **V2:** botão "Conferir aqui no navegador" (recalcula o SHA-256 do JSON com `crypto.subtle` e compara, mostrando "Confere" / "Não confere"); leitura do `input data` da transação via RPC público para comparar automaticamente.
- **Produto:** rede principal; versão do esquema do JSON documentada em página própria; API pública de verificação para tribunais e OAB.
