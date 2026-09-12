# C1 · Início — `/c/{token}`

## Propósito e posição no fluxo

Boas-vindas à sessão. Diz o nome da cidadã, quantas partes tem a explicação, quanto tempo leva, quem é a assistente e o que ela não faz. Oferece a escolha ouvir/ler. Entrada: C0. Saída: C2 tópico 1. Se a sessão já começou, esta rota redireciona para `resume_path` (a cidadã não vê C1 de novo, salvo pelo indicador de progresso).

## Layout (mobile-first, 360×740)

```
[AssistantBanner — Dr. João Silva]
[main]
  h1 "Oi, Maria."                                                   22 px
  p  "O Dr. João Silva mandou o seu contrato de honorários."        17 px
  p  "Vou explicar em 7 partes, uma de cada vez."                    17 px
  p  "Leva uns 5 minutos. Você pode parar e voltar quando quiser."   17 px
  Card "Quem está falando com você" (raio 22, fundo #EAF4F4)
    ícone Bot aria-hidden
    p "Sou uma assistente automática do escritório. Explico o que está escrito neste documento. Não sou advogada e não dou conselho jurídico. Quem responde por você é o Dr. João."
    [▶ Ouvir esta apresentação]  (ghost, 48 px)
  Card "Como funciona" (3 passos numerados, 15 px)
    1 "Eu explico cada parte e mostro o trecho original."
    2 "Você pode perguntar. Eu respondo só com o que está no documento."
    3 "No fim, você conta com suas palavras o que entendeu. O Dr. João confere."
  p (15 px, muted) "Você não assina nada aqui."
  Link "Recursos de acessibilidade" (símbolo LBI)
[BottomActionBar]
  [▶ Começar ouvindo]         primário 52 px
  [Prefiro ler]               secundário 48 px
```

## Componentes (shadcn/ui)

`Card`, `Button`, `Skeleton`, `Alert`; novos: `AssistantBanner`, `BottomActionBar`, `AudioPlayer` (modo compacto), `AccessibilitySheet`, `VLibrasMount`, `OfflineBanner`.

## Copy exata (pt-BR)

- h1: "Oi, Maria."
- Parágrafos: "O Dr. João Silva mandou o seu contrato de honorários." · "Vou explicar em 7 partes, uma de cada vez." · "Leva uns 5 minutos. Você pode parar e voltar quando quiser."
- Título do card: "Quem está falando com você"
- Apresentação (texto e áudio, literal): "Sou uma assistente automática do escritório. Explico o que está escrito neste documento. Não sou advogada e não dou conselho jurídico. Quem responde por você é o Dr. João."
- Botão do card: "Ouvir esta apresentação" / "Pausar"
- Card "Como funciona": passos como no layout.
- Nota: "Você não assina nada aqui."
- Botões: "Começar ouvindo" · "Prefiro ler"

Estimativa: `soma(duração dos áudios) + 45 s × K perguntas`, arredondada para o minuto ("uns 5 minutos"). Com N ≤ 3 partes, a frase vira "Leva uns 2 minutos."

## Estados

**Default** — sessão carregada, `status = created`.

**Vazio (documento ainda não aprovado)** — só acontece se o link foi aberto antes da aprovação (não deve ocorrer; defesa): h1 "Oi, Maria." p "O Dr. João ainda está preparando a explicação. Volte daqui a pouco ou fale com ele." Barra inferior sem botões.

**Carregando** — h1 fixo "Oi." (sem nome) e `Skeleton` nos parágrafos e cards; botões desabilitados; `role="status"` "Carregando sua explicação".

**Erro** — `Alert`: "Deu um problema do nosso lado, não foi você. Estamos tentando de novo." Retentativa automática em 3 s (máximo 3), depois botão "Tentar de novo".

**Sem conexão** — se o conteúdo está em cache: tela normal com `OfflineBanner`; senão: estado de erro com texto "Sem internet agora. Abra de novo quando a conexão voltar."

## Interações

- "Começar ouvindo" → grava `audio_pref = listen`, navega para C2 tópico 1 e inicia o áudio automaticamente ao carregar (permitido porque partiu de um gesto do usuário na mesma navegação SPA). Transição 180 ms.
- "Prefiro ler" → `audio_pref = read`, C2 abre sem tocar áudio; o player continua disponível.
- "Ouvir esta apresentação" → `AudioPlayer` compacto toca o texto do card; botão vira "Pausar" com `aria-pressed="true"`.
- Toque em "Recursos de acessibilidade" → `AccessibilitySheet` (tamanho do texto 100/150/200 %, reduzir animações, abrir VLibras). Preferências salvas no dispositivo.
- Ao entrar nesta tela o service worker pré-carrega `GET /sessions/{id}` completo (tópicos, citações, perguntas) e, na V2, os áudios.

## Acessibilidade

- Foco inicial no h1; anúncio natural "Oi, Maria."
- Ordem: banner → h1 → parágrafos → card apresentação (texto → botão ouvir) → card como funciona → nota → link acessibilidade → botões da barra.
- Player: `aria-pressed`, rótulos "Ouvir esta apresentação"/"Pausar".
- A apresentação da assistente é sempre texto visível, não só áudio (WCAG 1.2).
- Alvos 52/48 px; contraste do card `#EAF4F4` com texto `#1A1D1F` 13:1.
- 200 %: cards refluem; passos numerados mantêm o número à esquerda.
- Sem tempo limite; sem autoplay sem gesto.

## Chamadas de API

- `GET /sessions/{id}` → `citizen_first_name`, `lawyer`, `document_type`, `sections[]` (para N e duração), `questions[]` (K), `status`, `resume_path`.
- V1 áudio: `speechSynthesis` local. V2: `POST /tts` só se `audio_url` faltar (o normal é o áudio já vir gerado na aprovação).

## O que muda na V1 / V2 / Produto

- **V1:** áudio por `speechSynthesis` (voz pt-BR do sistema); estimativa fixa por número de partes (≈ 40 s por parte); sem AccessibilitySheet (só VLibras).
- **V2:** áudio pré-gerado (`audio_url`) e pré-carregado aqui; estimativa pela duração real; AccessibilitySheet completo.
- **Produto:** escolha de voz; vídeo curto em Libras da apresentação; primeira execução com dica de instalação do PWA ("Adicionar à tela inicial").
