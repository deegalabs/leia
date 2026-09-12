# O que reaproveitar dos projetos existentes (varredura de 12/09/2026)

| Projeto local | O que tem | Reaproveitar no LeIA |
|---|---|---|
| `~/development/passexplorer/repos/webapp` | Next.js + Tailwind + shadcn (`components/ui`: button, card, dialog, sheet, skeleton, progress, radio-group, select, input, label, badge, alert, switch, slider, sonner, eyebrow, flow-numerals, persona-pill), `class-variance-authority`, `tailwind-merge`, `lucide-react`, `next-intl`, `@serwist/next` (PWA) | **Base do `apps/web`**: copiar `components/ui`, configuração do Serwist (service worker), estrutura do `next-intl` com `messages/pt-BR.json`; trocar tokens pelos de `docs/brand/tokens.css` e adicionar as variantes de botão de `docs/brand/buttons.md` |
| `~/development/passexplorer/repos/website` | Next.js + Tailwind, landing com `HowItWorks` e `Footer` | Estrutura da landing (`docs/design/screen-15-landing.md`) |
| `~/development/deegalabs/ipe-marketplace/client` | PWA mobile-first (Vite): `pwa-assets.config.ts` com `@vite-pwa/assets-generator` (maskable com padding), `InstallPrompt.tsx`, `UpdatePrompt.tsx`, `Logo.tsx`, `manifest.webmanifest` completo (`display: standalone`, `orientation: portrait`, ícones 64/192/512 + maskable), `qrcode.react` | Gerar os ícones do PWA a partir da logo (padding 0,4 e fundo marinho para o maskable), manifesto, aviso de instalação e de atualização, componente de QR do comprovante |
| `~/development/ipe/IpeXchange` | `tokens.css` separado do `globals.css`, `lucide-react` | Padrão de organizar tokens em arquivo próprio (já feito em `docs/brand/tokens.css`) |
| `deegalabs/tokeneconomy` (GitHub, privado, 03/09) | não está no disco local | conferir se é do time antes de qualquer uso |

Regra do edital (5.5): reaproveitar **infraestrutura genérica** (kit de UI, configuração de PWA, i18n) é boilerplate; o
produto (telas, prompts, serviço, registro) nasce no evento com commits datados.
