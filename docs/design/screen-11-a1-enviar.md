# A1 · Enviar documento — `/lawyer/new`

## Propósito e posição no fluxo

O advogado escolhe o tipo, envia o PDF (com texto selecionável) e acompanha o processamento por etapa real. Ao terminar, segue para A2 revisar. Entrada: A4 "Novo documento" ou sidebar. Saída: A2 (`/lawyer/documents/{id}`). Decisão desta versão: quem envia o documento é o advogado (pendência registrada no INDEX).

## Layout (desktop, 1440×900)

```
┌ Sidebar ┬──────────────────────────────────────────────────────────┐
│         │ Breadcrumb: Painel › Novo documento                        │
│         │ h1 "Enviar documento"                                       │
│         │ p  "A LeIA lê o PDF, separa as cláusulas e escreve a explicação para você revisar." │
│         │ ┌─ Card (max 720 px) ─────────────────────────────────────┐│
│         │ │ Label "Tipo de documento"                                ││
│         │ │ RadioGroup em cards horizontais (3):                      ││
│         │ │  ( ) Contrato de honorários  ( ) Procuração  ( ) Acordo   ││
│         │ │ Label "Arquivo PDF"                                       ││
│         │ │ Dropzone tracejada 160 px: ícone Upload                   ││
│         │ │  "Arraste o PDF aqui ou"  [Escolher arquivo]              ││
│         │ │  p muted "Só PDF com texto selecionável. Até 10 MB."      ││
│         │ │ (após escolher) linha: nome.pdf · 340 KB · 6 páginas [Trocar arquivo] ││
│         │ │ [Enviar e gerar explicação]  48 px, à direita             ││
│         │ └───────────────────────────────────────────────────────────┘│
│         │ ── após enviar: PipelineStepper substitui o Card ──          │
│         │ h2 "Preparando a explicação"                                 │
│         │ ✓ Lendo o PDF                       4 s                      │
│         │ ✓ Separando cláusulas               6 s · 9 cláusulas         │
│         │ ◌ Escrevendo em linguagem simples   12 s… (spinner)          │
│         │ ○ Conferindo trechos                                          │
│         │ ○ Gerando áudio                                               │
│         │ p muted "Você pode sair; o processamento continua e aparece no painel." │
│         │ (ao concluir) [Revisar explicação]  primário                  │
└─────────┴──────────────────────────────────────────────────────────┘
```

## Componentes (shadcn/ui)

`Breadcrumb`, `Card`, `RadioGroup`, `Label`, `Button`, `Progress`, `Alert`, `Toast`, `Skeleton`; novos: `PipelineStepper`, dropzone (com `react-dropzone`).

## Copy exata (pt-BR)

- h1: "Enviar documento"
- p: "A LeIA lê o PDF, separa as cláusulas e escreve a explicação para você revisar."
- Tipo: "Tipo de documento" · "Contrato de honorários" · "Procuração" · "Acordo"
- Arquivo: "Arquivo PDF" · "Arraste o PDF aqui ou" · "Escolher arquivo" · "Só PDF com texto selecionável. Até 10 MB." · "Trocar arquivo"
- Botão: "Enviar e gerar explicação" (carregando: "Enviando…")
- Etapas: "Lendo o PDF" → "Separando cláusulas" → "Escrevendo em linguagem simples" → "Conferindo trechos" → "Gerando áudio"
- Detalhes por etapa: "9 cláusulas" · "7 tópicos" · "7 de 7 trechos encontrados" · "7 áudios"
- Rodapé: "Você pode sair; o processamento continua e aparece no painel."
- Conclusão: h2 "Explicação pronta para revisar" + "Revisar explicação"
- Erros de validação: "Escolha o tipo de documento." · "Escolha um arquivo PDF." · "Este arquivo passa de 10 MB." · "Este PDF é só imagem, sem texto selecionável. Exporte de novo com texto ou use OCR antes."
- Erro de etapa: "Deu um problema em 'Separando cláusulas'. Você pode tentar de novo a partir daqui." Botão "Tentar esta etapa de novo".

## Estados

**Default** — formulário vazio; botão desabilitado até tipo + arquivo válidos.

**Vazio (dropzone)** — texto de arraste e botão "Escolher arquivo"; ao arrastar sobre a área, borda teal e texto "Solte para enviar".

**Carregando** — upload com `Progress` (% real via `XMLHttpRequest`/`fetch` com stream) na linha do arquivo; depois `PipelineStepper` com etapa ativa (spinner + cronômetro) e etapas concluídas com check e tempo. `aria-busy` no stepper; anúncio a cada mudança de etapa.

**Erro** — validação inline por campo; erro de etapa em `Alert` dentro da etapa com botão de retentativa; erro de rede: "A conexão caiu. O processamento continua no servidor; recarregue para ver o andamento."

**Concluído** — todas as etapas com check; h2 "Explicação pronta para revisar"; botão "Revisar explicação"; redirecionamento automático em 3 s com aviso cancelável ("Abrindo a revisão… Ficar aqui").

## Interações

- Escolha do tipo em cards de rádio (clique na área toda, 64 px de altura).
- Dropzone: arrastar/soltar ou clique; valida extensão, tamanho e presença de camada de texto (leitura local com `pdfjs` da 1ª página; se sem texto, erro antes de enviar).
- "Enviar e gerar explicação" → sequência: `POST /documents` (etapas 1–2) → `POST /documents/{id}/explain` (etapas 3–4) → `POST /documents/{id}/questions` (perguntas sugeridas, sem etapa visível) → `POST /tts` por seção (etapa 5, V2). Cada etapa marca concluída quando a chamada correspondente retorna; o cronômetro por etapa é real.
- Sair da tela não cancela; A4 mostra "processando" e "Ver etapas" volta para cá com o estado atual.
- Esc não cancela o processamento; há botão "Cancelar envio" só durante o upload.

## Acessibilidade

- Foco no h1; após enviar, foco no h2 "Preparando a explicação".
- Ordem: breadcrumb → h1 → p → tipo (rádios com setas) → dropzone (botão "Escolher arquivo" é o alvo focável; a área inteira aceita drop mas não é focável) → linha do arquivo → botão enviar.
- Stepper: `<ol>` com `aria-current="step"` na etapa ativa; cada `<li>` com texto de estado ("concluída", "em andamento", "aguardando", "com problema"); tempos em texto.
- Anúncios em `role="status"`: "Etapa 3 de 5: Escrevendo em linguagem simples" ao mudar.
- Erros com `role="alert"` e foco no primeiro campo inválido.
- Dropzone com contraste de borda ≥ 3:1; ícone decorativo.
- Sem tempo limite; redirecionamento automático cancelável (WCAG 2.2.1).

## Chamadas de API

- `POST /documents` (multipart: `pdf`, `document_type`) → `{ id, clauses[] }`.
- `POST /documents/{id}/explain` → `{ sections[] { quote, quote_verified, lastro, … } }`.
- `POST /documents/{id}/questions` → `{ questions[] { text, expected_elements[] } }` (só advogado).
- V2: `POST /tts { text, section_id }` por seção → `audio_url`.
- Andamento após sair: `GET /documents/{id}` não está no contrato; V1 mantém a sequência viva na aba; pendência no INDEX.

## O que muda na V1 / V2 / Produto

- **V1:** 4 etapas visíveis (sem "Gerando áudio"; o áudio é `speechSynthesis` no cliente); processamento só enquanto a aba está aberta; sem detecção de PDF-imagem além do erro do backend.
- **V2:** etapa "Gerando áudio" com `POST /tts`; job assíncrono com `GET /documents/{id}` para retomar o andamento; verificação local de camada de texto.
- **Produto:** OCR integrado para PDF-imagem; modelos de documento do escritório (reaproveitar explicações aprovadas); envio direto do PJe/Drive.
