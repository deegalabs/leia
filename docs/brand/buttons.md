# Botões

Rótulo = verbo + resultado ("Ouvir explicação", "Entendi, próximo", "Confirmo que entendi"). Nunca "OK", "Enviar",
"Cancelar" sozinhos. Sentence case, nunca caixa alta. No máximo 2 botões na barra inferior da cidadã e 3 ações por tela.

## Hierarquia
| Nível | Fundo claro (cidadã) | Fundo escuro (marca, painel) | Uso |
|---|---|---|---|
| Primário | fundo `teal-deep` `#1F7373`, texto branco (5,6:1) | fundo `teal` `#38A8A8`, texto `navy` (6,0:1) | a única ação principal da tela |
| Secundário | borda 2 px `ink`, texto `ink`, fundo transparente | borda 2 px `paper`, texto `paper` | alternativa ("Tenho uma dúvida", "Prefiro ler") |
| Discreto | borda 1 px `line`, texto `ink-3`, peso 400 | idem em tons escuros | escape ("Continuar sem conta", "Quero rever uma parte") |
| Perigo | fundo `danger`, só no painel do advogado | | excluir, revogar link; nunca na jornada da cidadã |
| Link | texto `teal-deep` sublinhado | texto `teal` | "Ver trecho original", "Copiar link" |

## Tamanhos
| Contexto | Altura | Fonte | Raio | Ícone |
|---|---|---|---|---|
| Cidadã, primário | 52 px | 17 px, peso 700 | 12 px | 20 px à esquerda, opcional |
| Cidadã, secundário e discreto | 48 px | 16 px | 12 px | idem |
| Microfone | 64 × 64 px, circular | | | `Mic` 28 px |
| Advogado | 40 px | 14 px, peso 600 | 8 px | 16 px |

## Estados
| Estado | Aparência | Acessibilidade |
|---|---|---|
| Repouso | como na hierarquia | `<button type="button">` com texto real |
| Hover (desktop) | fundo 6% mais escuro | |
| Pressionado | escala 0,98, 150 ms, `transform` só | respeita `prefers-reduced-motion` |
| Foco | anel 3 px `teal-deep` (claro) ou `teal` (escuro), deslocado 2 px | `:focus-visible`; nunca remover |
| Carregando | spinner de 20 px à esquerda e texto do que está acontecendo ("Registrando...") | `aria-busy="true"`; botão não muda de tamanho |
| Desabilitado | opacidade 0,5 e motivo visível abaixo ("responda às 2 perguntas para confirmar") | `aria-disabled="true"` em vez de `disabled`, para continuar focável e explicável |
| Gravando (microfone) | fundo `danger`? Não: fundo `teal-deep` com anel pulsante, cronômetro ao lado | `aria-pressed="true"`, região viva "Gravando, 12 segundos" |

## Exemplo (shadcn `Button` com CVA)
```tsx
<Button size="citizen" variant="primary"><ArrowRight aria-hidden /> Entendi, próximo</Button>
<Button size="citizen" variant="secondary"><MessageCircleQuestion aria-hidden /> Tenho uma dúvida</Button>
```
Variantes a adicionar ao `button.tsx` do shadcn: `variant: primary | secondary | quiet | danger | link`; `size: citizen | citizen-sm | lawyer | icon-mic`.
