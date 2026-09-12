# C6 · Comprovante — `/c/{token}/receipt`

## Propósito e posição no fluxo

Fim do fluxo da cidadã. Mostra data/hora, código (hash), QR e explica em linguagem simples o que o registro prova e o que não prova. Três momentos: aguardando o advogado validar (sem hash), provisório (hash pronto, carimbo público pendente) e final (transação confirmada). Entrada: C5 ou CH ("Ver comprovante"). Saídas: salvar, falar com o advogado, voltar para CH.

## Layout (mobile-first, 360×740)

```
[AssistantBanner — Dr. João Silva]
[main]
  h1 "Seu comprovante"                                              22 px
  StatusChip  ✓ "registrado"  |  ◔ "carimbo pendente"  |  ○ "aguardando o Dr. João"
  ReceiptCard (raio 22, fundo branco, borda 1 px)
    p  "Contrato de honorários · Dr. João Silva · OAB/PR 12345"      15 px
    p  "Você confirmou em 12/09/2026 às 15:40"                        17 px
    p  "Validado pelo Dr. João em 12/09/2026 às 16:20"                17 px
    QrCode 200 px centralizado, legenda "Aponte a câmera para conferir"
    p  "Código do registro"                                          15 px muted
    HashDisplay  mono 15 px, 8 grupos de 8 caracteres, [Copiar código]
    p  "Carimbo público em 12/09/2026 às 16:42"  + link "Ver na rede pública"   (final)
  Card explicação (fundo #EAF4F4)
    h2 "O que este comprovante prova"                                19 px
    p  "Este código prova que você respondeu estas perguntas neste dia. Ele não contém seu documento nem suas respostas. Não é a assinatura do contrato."
    [▶ Ouvir explicação]
  Link "Voltar para meus documentos"
[BottomActionBar]
  [Salvar comprovante]           primário 52 px
  (secundário vazio; "Falar com o advogado" fica no banner)
```

## Componentes (shadcn/ui)

`Card`, `Button`, `Badge`, `Skeleton`, `Alert`, `Toast`; novos: `ReceiptCard`, `HashDisplay`, `QrCode`, `StatusChip`, `AudioPlayer`, `AssistantBanner`, `BottomActionBar`.

## Copy exata (pt-BR)

- h1: "Seu comprovante"
- Chips: "registrado" · "carimbo pendente" · "aguardando o Dr. João"
- Linhas: "Você confirmou em {data} às {hora}" · "Validado pelo Dr. João em {data} às {hora}" · "Carimbo público em {data} às {hora}"
- QR: "Aponte a câmera para conferir"
- Hash: "Código do registro" · "Copiar código" / "Copiado"
- Provisório: "O carimbo público está sendo gravado. Pode levar alguns minutos. Seu código já vale." 
- Aguardando: "Você confirmou. Agora o Dr. João confere suas respostas. O comprovante aparece aqui quando ele terminar."
- Explicação (literal): "Este código prova que você respondeu estas perguntas neste dia. Ele não contém seu documento nem suas respostas. Não é a assinatura do contrato."
- Botões: "Salvar comprovante" · "Ver na rede pública" · "Voltar para meus documentos"
- Sem conta (se "Continuar sem conta" existir): `Alert` "Salve o comprovante agora: sem conta, ele fica só neste celular."

## Estados

**Default (final)** — chip "registrado", QR, hash, carimbo com data e link; "Salvar comprovante" ativo.

**Vazio (aguardando o Dr. João)** — `status = confirmed`, sem `record`: chip "aguardando o Dr. João", card sem QR/hash, texto de aguardando, ícone Clock; "Salvar comprovante" desabilitado com nota "Disponível quando o Dr. João validar." Recarrega sozinho a cada 30 s enquanto a tela está aberta.

**Carregando** — h1 fixo; `Skeleton` no lugar do QR (200 px) e do hash; "Carregando seu comprovante".

**Erro** — `Alert`: "Deu um problema do nosso lado, não foi você. Estamos tentando de novo." Se há comprovante em cache, mostra a última versão com chip "atualizado há 2 h".

**Provisório (carimbo pendente)** — `record` com `anchor = null`: chip "carimbo pendente", hash e QR presentes, texto provisório; "Salvar comprovante" ativo (o PDF marca "carimbo pendente"). Recarrega a cada 30 s; ao chegar `anchor`, chip faz crossfade e anúncio "Registro concluído. O comprovante está completo."

## Interações

- "Salvar comprovante" → V1: `window.print()` com folha de impressão (só o ReceiptCard + explicação); a cidadã escolhe "Salvar como PDF". V2: `Web Share API` com PDF gerado no servidor. O arquivo não pode ter metadados (Producer, Creator, Author, datas): limpar no gerador e conferir antes de entregar.
- "Copiar código" → clipboard; rótulo vira "Copiado" por 1,5 s; `role="status"` "Copiado".
- "Ver na rede pública" → abre `explorer_url` em nova aba (`rel="noopener"`), aviso `aria-label="abre em nova aba"`.
- QR aponta para `https://{host}/verify/{id}` (P1). Sem dado pessoal na URL.
- "Ouvir explicação" → player compacto lê o texto do card.
- Chip muda de estado sem recarregar a página (polling em `GET /sessions/{id}`).

## Acessibilidade

- Foco no h1; anúncio inclui o chip ("Seu comprovante, registrado").
- Ordem: banner → h1 → chip → card (linhas → QR → hash → copiar → link rede) → explicação (texto → ouvir) → voltar → barra.
- QR: `role="img" aria-label="QR para a página de verificação pública"`; o link textual "Abrir página de verificação" (visível, 48 px) fica logo abaixo para quem não usa câmera.
- Hash em `<code>` com `aria-label` lido em grupos; o botão Copiar tem `aria-describedby` do hash.
- Chips com ícone + texto (✓, ◔, ○).
- Datas por extenso no `aria-label` ("12 de setembro de 2026 às 15h40").
- 200 %: QR reduz até 160 px; hash quebra por grupo; nada corta.
- Impressão acessível: PDF com texto real (não imagem), ordem lógica.

## Chamadas de API

- `GET /sessions/{id}` → `status`, `confirmed_at`, `validated_at`, `record { payload_hash, anchor { tx_hash, explorer_url, block_time } | null, verify_id }`.
- Polling a cada 30 s enquanto `status = confirmed` ou `anchor = null` (para ao fechar a aba).
- V2: `GET /verify/{id}` também serve como fonte do QR sem sessão.

## O que muda na V1 / V2 / Produto

- **V1:** impressão do navegador; polling 30 s; QR gerado no cliente; sem e-mail.
- **V2:** PDF no servidor sem metadados + compartilhar; e-mail com o link do comprovante ao concluir; push quando o carimbo confirma.
- **Produto:** carteira de comprovantes em CH com busca; segunda via por QR no escritório; exportação para o processo (PJe) pelo advogado.
