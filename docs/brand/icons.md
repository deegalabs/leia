# Ícones

Biblioteca: **Lucide** (`lucide-react`, licença ISC), traço 2 px, 24 px na jornada da cidadã e 20 px no painel do
advogado. Nada de emoji na interface: emoji varia por aparelho, não tem cor da marca e não é lido de forma
consistente pelo leitor de tela. Todo ícone acompanha um texto; ícone sozinho só com `aria-label`; ícone decorativo
recebe `aria-hidden="true"`.

## Ações
| Ação | Ícone Lucide | Onde |
|---|---|---|
| Ouvir explicação / pausar | `Play` / `Pause` | C1, C2, C4 |
| Ouvir de novo | `RotateCcw` | C2 |
| Velocidade | `Gauge` | C2 (0,8× 1× 1,25×) |
| Gravar resposta / parar | `Mic` / `Square` | C3, C4 |
| Escrever | `Keyboard` | C3, C4 |
| Enviar resposta | `Send` | C3, C4 |
| Entendi, próximo | `ArrowRight` | C2 |
| Voltar | `ArrowLeft` | todas |
| Tenho uma dúvida | `MessageCircleQuestion` | C2 |
| Ver trecho original | `Quote` | C2, C3, A2 |
| Não sei, explica de novo | `HelpCircle` | C4 |
| Falar com o advogado | `Phone` | banner fixo |
| Confirmo que entendi | `CircleCheck` | C5 |
| Salvar comprovante | `Download` | C6 |
| Copiar link | `Copy` | A2, A4 |
| Novo documento / enviar PDF | `FilePlus` / `Upload` | A4, A1 |
| Revisar | `PenLine` | A2 |
| Aprovar e gerar link | `Check` + `Link` | A2 |
| Validar e gerar registro | `ClipboardCheck` | A3 |
| Entrar com Google / sair | `LogIn` / `LogOut` | A0, C0 |

## Estados
| Estado | Ícone | Cor |
|---|---|---|
| Entendido | `CircleCheck` | `ok` |
| Pendência para o advogado | `CircleAlert` | `pend` |
| Em andamento | `Clock` | `ink-3` |
| Registrado | `BadgeCheck` | `teal-deep` (claro) / `teal` (escuro) |
| Carimbo pendente | `Hourglass` | `pend` |
| Sem conexão | `WifiOff` | `ink-3` |
| Erro do sistema | `TriangleAlert` | `danger` |

## Objetos
| Objeto | Ícone |
|---|---|
| Documento / contrato | `FileText` |
| Comprovante | `FileCheck` |
| Registro público / carimbo de tempo | `Stamp` |
| QR de verificação | `QrCode` |
| Código (hash) | `Hash` |
| Advogado | `Scale` |
| Cidadã | `User` |
| Assistente automática | `MessageSquareText` (nunca robô ou brilho) |
| Painel | `LayoutDashboard` |
| Sessões | `Users` |
| Registro de eventos | `ScrollText` |

## Tópicos do documento (C2)
| Tópico | Ícone |
|---|---|
| Quem são as partes | `Users` |
| O que você está autorizando / contratando | `FileText` |
| Quanto e quando você paga | `Banknote` |
| Poderes do advogado | `KeyRound` |
| Prazo e validade | `CalendarClock` |
| O que pode dar errado | `TriangleAlert` |
| Como cancelar ou sair | `DoorOpen` |
| Acordo e quitação | `Handshake` |

Símbolo da marca (documento com selo) é a única exceção: SVG próprio, derivado da logo, usado no ícone do aplicativo, no favicon e no cabeçalho.
