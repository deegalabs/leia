# Plano de componentes

Base: Next.js App Router + Tailwind + shadcn/ui. Dois temas por segmento de rota: `citizen` (Atkinson Hyperlegible, escala 15–19 px, raio 12/22) e `lawyer` (IBM Plex Sans 14 px, raio 8/12). IBM Plex Mono para hashes nos dois.

## Tokens (Tailwind `theme.extend`)

```
colors: brand.navy #081820 · brand.offwhite #F0F0E8 · brand.teal #38A8A8 (só sobre escuro)
        action.teal #1F7373 · action.tealHover #195E5E · success #1F7A4D · pending #B26A00
        bg.citizen #FAF8F4 · bg.lawyer #FFFFFF · ink #1A1D1F · ink.muted #4A4F52 · line #E3E0D8
        highlight #FFF1B8 (citação) · reading #EAF4F4 (frase em leitura) · warn.bg #FFF4DD
radius: button 12px · card 22px (cidadã) / 12px (advogado)
font: citizen "Atkinson Hyperlegible" · lawyer "IBM Plex Sans" · mono "IBM Plex Mono"
```

Contraste conferido: `#1F7373` com branco 5,6:1; `#38A8A8` sobre `#081820` 6,4:1; `#1F7A4D` com branco 5,9:1; `#B26A00` com branco 4,6:1; `#1A1D1F` sobre `#FAF8F4` 15:1.

## shadcn/ui reutilizados (sem alteração além de tokens)

| Componente | Onde |
|---|---|
| `Button` (variants: default, outline, ghost, destructive) | todas |
| `Card` | CH, C1, C2, C4, C6, A2, A3, P1 |
| `Badge` | A2 selos, A4 status (via StatusChip) |
| `Progress` | A1 (por etapa), player de áudio |
| `Collapsible` | C2 trecho original, P1 JSON canônico |
| `Textarea`, `Input`, `Label`, `Form` | C3, C4, A0, A2, A3 |
| `Select`, `RadioGroup`, `Checkbox` | A0 (UF), A1 (tipo), A2 (perguntas) |
| `Dialog`, `AlertDialog` | consentimento de voz, aprovar, validar |
| `Sheet` | Falar com o advogado, rever uma parte (C5), sidebar mobile |
| `Toast` (Sonner) | copiado, salvo, erros recuperáveis |
| `Skeleton` | estados de carregamento |
| `Table`, `Tabs`, `ScrollArea`, `DropdownMenu`, `Tooltip`, `Breadcrumb`, `Sidebar` | painel do advogado |
| `Alert` | erros de tela, avisos (PDF sem texto) |
| `Separator`, `Avatar` | rodapé da sidebar, cards |

## Componentes novos

| Componente | Props principais | Usado em | Observações |
|---|---|---|---|
| `AssistantBanner` | `lawyer {name, oab, phone?}` | C0–C6, CH | Fixo no topo; contém `LawyerContactSheet`. |
| `BottomActionBar` | `primary {label, onClick, loading?, disabled?}`, `secondary?` | C0–C6, CH | Máximo 2 botões; controla `scroll-padding-bottom`. |
| `OfflineBanner` | — | cidadã | Observa `navigator.onLine` + fila IndexedDB. |
| `ProgressSteps` | `current`, `total`, `label`, `onJump?(n)` | C2, C4 | Segmentos tocáveis (≥ 48 px de altura de toque) para tópicos já vistos; `aria-label="Tópico 2 de 7"`. |
| `TopicCard` | `section`, `audio` | C2 | Ícone + h1 + texto simples + `AudioPlayer` + `QuoteDisclosure`. |
| `AudioPlayer` | `src? \| text`, `rate`, `onEnded` | C1, C2, C3, C4 | V1: `speechSynthesis` (pt-BR); V2: `<audio>` com arquivo. Botões: Ouvir/Pausar (`aria-pressed`), Ouvir de novo, velocidade (0,8×/1×/1,25×). |
| `QuoteDisclosure` | `quote`, `clauseRef`, `verified` | C2, C3, C4 | "Ver trecho original"; `<blockquote>` com `<mark>` no trecho; selo "trecho conferido". |
| `RecordButton` | `state: idle\|recording\|processing`, `onToggle`, `maxSeconds?` | C3, C4 | 64 px, `aria-pressed`, cronômetro em live region, barras de nível, consentimento na 1ª vez. V1: Web Speech `SpeechRecognition`; V2: `MediaRecorder` + `POST /stt`. |
| `TranscriptEditor` | `value`, `onChange`, `onSubmit` | C3, C4 | Textarea rotulada "Confira o que você disse"; recebe foco ao parar de gravar. |
| `StatusChip` | `status`, `audience: citizen\|lawyer` | CH, A4, A3, C6, P1 | Mapeia estado → rótulo/cor (ver information-architecture.md). Ícone + texto; nunca só cor. |
| `RubricBadge` | `score`, `attempt`, `pending` | A3 | Palavras, nunca números. |
| `FeedbackCard` | `kind: right\|again\|pending`, `matched`, `missing`, `reExplanation` | C4 | Duas partes em "again"; `role="status"`. |
| `SummaryList` | `topics[]`, `questions[]`, `doubts[]` | C5 | Lista com ✓ verde e marcador âmbar "para o Dr. João". |
| `ReceiptCard` | `record`, `lawyer`, `provisional` | C6, A3 | Data/hora, `HashDisplay`, `QrCode`, texto do que prova/não prova. |
| `HashDisplay` | `hash`, `copyable` | C6, A3, P1 | Mono, 64 hex em grupos de 8, `overflow-wrap: anywhere`, botão Copiar. |
| `QrCode` | `value`, `size` | C6, P1 | Gera SVG local (`qrcode` npm); `role="img" aria-label="QR para a página de verificação"`. |
| `ClauseSideBySide` | `section`, `onChange`, `badges` | A2 | Original com `<mark>` + Textarea; contador de frases longas (> 15 palavras) e de palavras da lista proibida. |
| `QuestionPicker` | `questions[]`, `selected[]`, `min=2`, `max=3` | A2 | Checkboxes com elementos esperados; validação inline. |
| `PipelineStepper` | `stages[]`, `current`, `elapsed`, `error?` | A1 | Etapas verticais com estado, tempo e mensagem de erro por etapa. |
| `LawyerContactSheet` | `lawyer` | banner | Nome, OAB, telefone (se houver). |
| `AccessibilitySheet` | — | C1, CH | Tamanho do texto, reduzir animações, VLibras. |
| `VLibrasMount` | — | cidadã, P1 | Carrega o widget e reposiciona acima da barra inferior. |
| `EmptyState` | `icon`, `title`, `text`, `action?` | CH, A4, A3 | Só ícone lucide, sem ilustração. |

## Regras de escrita nos componentes

- `Button` recebe sempre rótulo textual; ícones são decorativos (`aria-hidden`).
- `AudioPlayer`, `RecordButton` e `QuoteDisclosure` têm o mesmo tamanho e posição em C2, C3 e C4 (consistência cognitiva).
- Toda live region é única por tela: um `role="status"` compartilhado (`<StatusRegion>`) evita anúncios concorrentes.
- Nenhum componente usa cor como único sinal: chips e selos combinam ícone + texto.
