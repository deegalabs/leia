# Crítica de design — LeIA, 14 telas

Escopo lido: `INDEX.md`, 14 `screen-*.md`, 6 `shared/*.md`, POSITIONING, USE-CASES, SCREENS, LLM-API-CONTRACT, brand/README, pesquisa (content-strategy, ux-patterns, recommendations) e DELIVERIES.

**Veredito: aprovado com condições.** Nielsen 40/50 · Gosto 53/75 (nível 4, "refinado", faixa baixa). Seis correções críticas (≈ 2 h 25 min somadas) antes da V2 de hoje; nenhuma exige tela nova nem muda a arquitetura.

Nota prévia sobre rótulos: o design usa "V1 = 48 h, V2 = semanas seguintes, Produto = produção". As entregas reais são V1 hoje 15h30 (outro protótipo), V2 hoje 17h30 (voz, ancoragem, verificação) e Produto amanhã 10h30. Nesta crítica, "V2 hoje" corresponde ao que o design chama de V1; "Produto amanhã" absorve os itens baratos que o design empurrou para a sua V2. A tabela de correções usa os rótulos reais.

## 1. Alinhamento estratégico

O que está certo e deve ficar:

- A cidadã é a usuária primária de fato, não só no discurso: 8 das 14 telas são dela, todas com um tópico por rota, áudio como botão primário ("Começar ouvindo") e leitura como secundário.
- A supervisão aparece sem dominar: nome + OAB do advogado em C0/C1/CH, "anotei para o Dr. João" nas recusas, "marcado para o Dr. João conversar com você" em C5, "Validado pelo Dr. João" em C6. O advogado é presença, não gargalo visual.
- A IA declara limites em todas as telas (banner) e nunca decide: A2 não aprova seção sem selo de citação; A3 mostra a rubrica em palavras.

Onde a execução desvia da tese:

- **C0 põe o login do Google antes de qualquer valor.** A pesquisa recomenda "link tokenizado sem login, sem senha" (recommendations §2.1; ux-patterns §6) e a meta de sucesso é "comprovante em < 4 min sem instrução" (persona). O plano de verificação D2 é "entregar o celular a um jurado sem explicar nada". Com C0 na frente, o jurado esbarra numa conta Google no celular da demo. O design já prevê "Continuar sem conta" atrás de flag; a correção é inverter o padrão: link abre C1 direto e o Google entra em C6 como "Entrar com Google para guardar o comprovante", no momento em que o valor existe.
- **7 tópicos + 3 perguntas ≈ 5 min** contradiz a meta de 4 min, e C1 diz isso em voz alta ("Leva uns 5 minutos"). A pendência 10 do INDEX reconhece; falta a alavanca em A2 (tempo estimado visível + "Juntar com a anterior") e um PDF de demo com 5 seções.
- **Banner (76 px) + barra (132 px) ocupam 28 % de 360×740** de forma permanente. A regra "3 ações por tela" é boa; o custo em área de leitura, com fonte de 17 px e zoom de 200 %, não foi medido (ver §4).

## 2. Usabilidade — Nielsen, 40/50

| # | Heurística | Nota | Evidência |
|---|---|---|---|
| 1 | Visibilidade do status | 4 | Progresso 1:1 (C2), PipelineStepper com tempo real por etapa (A1), 3 momentos do comprovante (C6). Perde por: barras separadas reiniciam em C4 ("Tópico 7 de 7" → "Conferindo 1 de 3") e polling de 30 s em C6 deixa a jurada olhando para "aguardando" na demo. |
| 2 | Correspondência com o mundo real | 4 | Linguagem da cidadã é exemplar ("carimbo pendente", "Código do registro", exemplo em R$). Perde por: selo "juiz: fiel" em A2 — para advogado, "juiz" é o magistrado; e o OfflineBanner manda "tocar em Continuar", botão que não existe em C2/C4. |
| 3 | Controle e liberdade | 4 | Voltar nunca perde resposta; "Não sei, explica de novo" não consome tentativa; sem tempo limite; "Quero rever uma parte". Perde por: login obrigatório como porta (C0) e AlertDialog em C5 sobre um botão que já diz "Confirmo que entendi". |
| 4 | Consistência e padrões | 3 | A regra 2 do INDEX ("player, microfone e trecho têm o mesmo tamanho e posição em C2, C3 e C4") é violada pelo próprio design: C3 = campo → microfone; C4 = microfone → campo; rótulos "Escreva aqui ou grave sua voz" vs "Ou escreva aqui"; player é card em C2 e botão ghost em C3/C4. Atalho Ctrl+Enter significa "aprovar" em navigation.md e "marcar conferida" em A2. |
| 5 | Prevenção de erros | 5 | Transcrição editável antes de enviar; A2 bloqueia aprovação sem trecho verificado e sem 2 perguntas; validação local do PDF; guarda de palavras proibidas no front com fallback; foco inicial em "Ainda não" no dialog. |
| 6 | Reconhecimento em vez de memória | 4 | Lembrete do essencial antes de cada pergunta (C4); resumo com ✓ em C5; chips de exemplo em C3. Perde por: o selo "trecho conferido" só aparece com o Collapsible aberto — a prova anti-alucinação fica escondida atrás de um toque. |
| 7 | Flexibilidade e eficiência | 4 | Ouvir/ler, voz/texto, 0,8×/1×/1,25×, segmentos tocáveis do progresso, atalhos no painel. Perde por: em C4 a pergunta não toca sozinha mesmo com `audio_pref = listen` (C2 toca). |
| 8 | Estética e minimalismo | 3 | C1 tem 3 parágrafos + 2 cards + nota + link + 2 botões numa tela que a pesquisa pede com "uma frase e um botão" (ux-patterns §7: "sem tutorial, sem tour"). O card "Como funciona" é um tour. C4 empilha lembrete + h1 + h2 + p + botão + microfone + campo. |
| 9 | Recuperação de erros | 4 | Copy de erro excelente e uniforme; nada se perde; retentativa automática. Perde por: nenhum estado para `speechSynthesis` sem voz pt-BR (autoplay silencioso), `SpeechRecognition` ausente (Firefox, iOS) ou offline (Chrome envia áudio à nuvem; a fila offline de C3/C4 não resolve a transcrição). |
| 10 | Ajuda e documentação | 5 | Banner fixo com limites, "Falar com o advogado" na mesma posição (WCAG 3.2.6), "Não sei, explica de novo", "Recursos de acessibilidade", passo a passo com `sha256sum` em P1. |

### Percurso A — Maria abre o link no Android, ouve, responde 2 perguntas por voz, recebe o comprovante

1. **C0** — toque 1: "Entrar com Google" (ou descobrir "Continuar sem conta"). Se a conta do celular não é dela, trava aqui. Risco maior de toda a jornada.
2. **C1** — lê ou ouve a apresentação; "Começar ouvindo". Tela longa; o card "Como funciona" pede rolagem antes dos botões em 360×740 se a fonte estiver em 150 %.
3. **C2 ×7** — áudio toca sozinho (gesto vindo de C1, correto). "Entendi, próximo" ×7. Se o Android não tiver voz pt-BR, o áudio é silêncio e o botão mostra "Pausar": nada avisa.
4. **C3 (opcional)** — grava, confere transcrição, "Enviar dúvida". Ao chegar a resposta, o botão primário continua "Enviar dúvida" desabilitado; o próximo passo natural ("Voltar ao tópico") é o secundário.
5. **C4 ×2–3** — a pergunta não toca sozinha; ela precisa tocar "Ouvir a pergunta" (ghost) e depois o microfone. Consentimento de voz aparece aqui ou em C3 (bom: uma vez só), mas o texto fala em "conferir se você entendeu" mesmo quando é uma dúvida. Feedback em duas partes: correto e humano.
6. **C5** — lista, "Confirmo que entendi", AlertDialog "Confirmar que você entendeu?", "Sim, confirmo". Dois toques para uma ação não destrutiva já explicada pelo card âmbar.
7. **C6** — chega em "aguardando o Dr. João" com "Salvar comprovante" desabilitado. Na demo ao vivo, o advogado valida no outro laptop; com polling de 30 s a jurada espera até meio minuto sem sinal de vida. Depois: `window.print()` no Chrome Android para "salvar" — o diálogo de impressão é a interação mais hostil de toda a jornada para uma leiga.

Contagem: 1 (login) + 1 (começar) + 7 (tópicos) + 3×(ouvir + gravar + parar + enviar + próxima = 5) + 2 (confirmar) = ~26 toques sem nenhuma dúvida. Cortando login, dialog e autoplay da pergunta: ~20.

### Percurso B — Dr. João envia, aprova, valida e recebe a prova

1. **A0** — Google, nome, OAB, UF, prévia "Seu cliente verá:". Limpo.
2. **A1** — tipo + PDF + "Enviar e gerar explicação"; stepper com "Conferindo trechos · 7 de 7 trechos encontrados". É a tela mais forte para D3. Falta expor a "segunda leitura" (juiz de fidelidade, outro fornecedor) e `prompt_version`, que o contrato devolve em toda resposta.
3. **A2** — lado a lado com `<mark>`, selos, dicas de escrita (frases > 15 palavras, palavras a evitar, R$), "Ouvir como a cliente vai ouvir", 2–3 perguntas, dialog do primeiro nome, link. É a tela que mais demonstra D1 e D3. Faltam: índice de legibilidade (recommendations §2.7), `risk_level`/`why_it_matters` do contrato (não aparecem), e o nome "juiz". Sete cliques de "Marcar como conferida" são aceitáveis com Ctrl+Enter.
4. **A4** — "Bom dia, Dr. João. 2 itens precisam de você." + aba "Precisam de mim". Boa priorização.
5. **A3** — rubrica em palavras, resposta literal em `<blockquote>`, dúvidas com recusa nomeada, checkbox "Conversei com Maria", observações privadas, "Validar e gerar registro" → card com hash e transação. O JSON do juiz (`matched/missing`) só existe em tooltip; o plano D1 pede que fique visível.
6. **P1** — hash, JSON canônico, transação, `sha256sum`, "o que prova / não prova". O botão "Conferir aqui no navegador" (`crypto.subtle`) está marcado como futuro; é a demonstração mais forte de D1 e custa ~30 min.

## 3. Conteúdo

Regras cumpridas em quase todo o texto: "você", verbo + resultado, sem caixa alta, sem "errado/nota/reprovado/teste/prova/quiz" nas telas da cidadã, termo técnico entre parênteses depois da explicação, exemplo em R$. Os textos literais da pesquisa (apresentação, recusa, conselho, erro, sem microfone, sem internet) foram usados sem deriva. Nomes e dados são orgânicos ("há 3 min", "340 KB · 6 páginas", Maria/Carlos/Ana/Pedro).

Desvios encontrados (todos com correção na tabela):

- **Palavra proibida por tabela:** P1 "Polygon Amoy (rede de testes)" — a cidadã chega a P1 pelo QR. Trocar por "rede de demonstração".
- **Vazamento de token cru:** o contrato diz que com `refused = true` o campo `answer` vem literalmente como `NAO_ESTA_NO_DOCUMENTO`, e não devolve `refusal_kind`. C3 descreve o texto de recusa, mas não a regra "nunca renderizar `answer` quando `refused`". Sem essa guarda, Maria pode ler `NAO_ESTA_NO_DOCUMENTO` na tela.
- **Frases acima de 15 palavras:** C4 "Se você receber R$ 10.000, R$ 3.000 ficam com o advogado e R$ 7.000 com você." (16); P1 rodapé "O que este registro prova: que este código existia neste horário e foi gerado a partir do JSON acima, que descreve uma sessão de entendimento (…) validada por um advogado." (35).
- **Jargão antes da explicação:** C2 "você não paga esses honorários (chamados de honorários de êxito)" usa "honorários" sem explicar; a própria tabela do glossário tem a forma certa.
- **Voz passiva + finalidade errada no consentimento de voz:** "Sua voz será transformada em texto só para conferir se você entendeu" aparece também em C3, onde é uma dúvida (LGPD pede finalidade específica).
- **Botão só com verbo:** CH "Continuar"; C5 sheet "Fechar"; CH dialog "Sair"/"Ficar".
- **Referência a botão inexistente:** OfflineBanner "é só tocar em Continuar".
- **Contexto trocado:** C4 após a 2ª tentativa: "Podemos seguir para o próximo tópico" quando o próximo é uma pergunta.
- **Ambiguidade para advogado:** "juiz: fiel" / "juiz: revisar".
- **Gramática:** A2 "Para aprovar: 1 seção com trecho não encontrado, escolha ao menos 2 perguntas." mistura estado e imperativo.

## 4. Implementação e consistência

- **C2/C3/C4 não são idênticas onde o design promete.** Ordem microfone/campo invertida; rótulo do campo diferente; player como card (C2) vs botão ghost (C3/C4). Para uma persona que "prefere ouvir", o microfone deve vir antes do campo nas duas telas, e o "Ouvir" deve ter o mesmo lugar sob o texto principal nas três.
- **Especificação impossível com a tecnologia da V2 de hoje:** o player de C2 mostra "0:12 / 0:38" e barra de progresso, mas `speechSynthesis` não expõe duração. Enquanto o áudio for do navegador, o player precisa de um estado "Falando…" indeterminado, sem tempo.
- **Estados:** todas as 14 telas têm default, vazio, carregando, erro e, na cidadã, sem conexão — raro e valioso. Faltam três estados de voz (sem voz TTS, sem STT, STT offline) e o de "transcrição ruim" que a pesquisa prevê (content-strategy §4).
- **Movimento:** tabela completa com coluna reduced-motion, easing ease-out, spring só no check final, nada em loop além de gravação e skeleton. Sem anti-padrões (nenhum linear em transição, nenhuma animação de `top/left`). Boa.
- **Responsivo:** 320 px, paisagem, 200 % e impressão tratados. Lacuna: com zoom de 200 % em 360 px, banner (~150 px) + barra (~260 px) deixam ~270 px de conteúdo; o documento diz "reflui" mas não mede o que sobra. A partir de C2 o banner pode virar uma linha (48 px) com o texto completo ao tocar; abaixo de `100dvh: 600px` a barra fica só com o primário.
- **Anti-padrões (checklist):** sem Inter, sem gradiente, sem cards sem propósito, sem "Oops", sem exclamações; neutros quentes coerentes (#FAF8F4 / #E3E0D8 / #1A1D1F); lucide como único set de ícones — exceto o emoji do título do tópico (💰), que renderiza diferente em cada Android e destoa do resto. Sem sombras em lugar nenhum: opção de contenção defensável, mas player e FeedbackCard ganhariam com uma sombra tingida única.
- **Acessibilidade:** foco no h1 a cada rota, live region única por tela, `aria-pressed` no player e no microfone, alvos 48/52/64 px, Atkinson 17 px, VLibras, símbolo LBI, contraste conferido por token. Um erro semântico: em C4 o h1 (19 px, enquadramento) é menor e menos importante que o h2 (22 px, pergunta); para leitor de tela o título da página vira "Para eu ter certeza de que expliquei bem:".

## 5. Aderência às dimensões da auditoria

| Dimensão | O design já demonstra | O que falta (e custa pouco) |
|---|---|---|
| D1 confiabilidade | `QuoteDisclosure` com `<mark>` e selo "trecho conferido"; recusa com texto fixo + chip; A2 só aprova com "trecho verificado"; A3 rubrica com resposta literal; P1 com `sha256sum` e "o que não prova". | Selo visível com o trecho fechado; guarda contra `NAO_ESTA_NO_DOCUMENTO` cru; `matched/missing` do juiz inline em A3; "Conferir aqui no navegador" em P1; linha de "instruções escondidas no PDF: nenhuma" no stepper (se o backend expõe). |
| D2 usabilidade inclusiva | Um tópico por tela, 3 ações, áudio primeiro, teach-back sem vocabulário de prova, transcrição editável, estados completos, VLibras, reduced-motion, 200 %. | Login fora do caminho crítico; C1 sem tour; C5 sem dialog; C6 com compartilhar em vez de imprimir; autoplay da pergunta em C4; estados de voz indisponível; banner compacto sob zoom. |
| D3 sofisticação técnica | PipelineStepper com etapas reais e contagens; selos duplos (substring + juiz); dicas de escrita ao vivo; rubrica em palavras; JSON canônico + hash + transação + explorador. | `prompt_version` e `model` visíveis em A2/A3; índice de legibilidade; segunda leitura nomeada no stepper; referências da base OAB por seção (o contrato de `explain` não as devolve — lacuna de contrato, não de tela). |

## 6. Gosto — 53/75 (nível 4, refinado)

| Item | Nota | Comentário |
|---|---|---|
| Tipografia | 4 | Atkinson Hyperlegible para a cidadã e IBM Plex para o advogado são escolhas com motivo; escala 15–19 px declarada. Falta tracking em títulos e `tabular-nums` nas tabelas do painel. |
| Cor | 4 | Dois teals com regra clara (claro só no escuro), neutros quentes, semânticos com contraste conferido. |
| Ritmo de espaço | 3 | Paddings e raios definidos (12/22), mas sem escala vertical explícita. |
| Sombra e profundidade | 2 | Nenhuma sombra; tudo por borda de 1 px. |
| Movimento | 4 | Tabela completa, ease-out, spring só onde faz sentido, reduced-motion por linha. |
| Autenticidade do conteúdo | 5 | Copy real, dados orgânicos, textos literais da pesquisa. |
| Individualidade dos componentes | 3 | shadcn com tokens próprios; componentes novos bem definidos; ainda reconhecível como shadcn. |
| Confiança de layout | 3 | Coluna única na cidadã é correta; A0 em split e A2 em três colunas dão variação; nada arriscado. |
| Coerência visual | 4 | Uma linguagem nas três superfícies. |
| Textura | 2 | Plano. |
| Completude de estados | 5 | Quatro estados + offline em todas as telas, mais estados próprios. |
| Responsivo | 4 | Faixas, paisagem, zoom, impressão. |
| Ícones | 3 | lucide consistente; emoji nos tópicos quebra a família. |
| Direção de imagem | 3 | "Nenhuma imagem" é decisão declarada e coerente com a persona. |
| Impressão geral | 4 | Parece produto pensado, não template; a assinatura está no conteúdo, não no visual. |

## 7. Pontos fortes a preservar

1. **As regras de conteúdo viram mecanismo, não só documento:** guarda de palavras proibidas no front com fallback (C4) e dicas de escrita ao vivo para o advogado (A2). Isso é o que um auditor de D1/D2 quer ver.
2. **Teach-back fiel à evidência:** enquadramento com responsabilidade no sistema, lembrete antes da pergunta, feedback em duas partes, mesma pergunta repetida, "Não sei" sem custo, pendência nomeada para o humano.
3. **Comprovante honesto em três momentos** e P1 com passo a passo reproduzível, "o que prova / o que não prova" e JSON de bytes idênticos.
4. **Cobertura de estados e acessibilidade** acima do padrão de hackathon: foco, live regions, alvos, reduced-motion, offline com fila.
5. **Supervisão visível sem tutela:** o advogado aparece por nome em cada ponto em que a IA para.

## 8. Duas direções alternativas (curtas)

**A. "Rádio com legenda."** A sessão vira um único áudio contínuo com capítulos; a tela mostra só a frase em leitura em 22 px (karaokê), um botão de pausa de 80 px e "Tenho uma dúvida". As perguntas são faladas e respondidas por voz no mesmo fluxo; o texto integral fica num "Ler tudo" secundário. Ganha: coerência total com "prefere ouvir" e zero navegação por rotas. Perde: quem lê vira segunda classe; exige TTS com marcas de tempo (fora da V2 de hoje). Vale como norte para o produto, não para amanhã.

**B. "Ficha de cinco pontos com pergunta na hora."** Em vez de 7 tópicos e depois 3 perguntas, a explicação segue os cinco itens do CED art. 48 (objeto, valor, pagamento, extensão, acordo) como uma ficha de uma página; cada item expande, toca o áudio e, ao fechar, faz a pergunta daquele item ali mesmo (teach-back intercalado). C5 vira a própria ficha com ✓. A2 mostra a mesma ficha para o advogado. Ganha: menos rotas, tempo < 4 min quase garantido, pergunta colada à explicação (menor carga de memória). Perde: a evidência "uma coisa por página" e o lembrete de C4 deixam de ser necessários — precisa de teste com usuária.

## 9. Referências cruzadas

- Correções priorizadas: `./prioritized-fixes.md`.
- Telas: `../screen-{NN}-{nome}.md`; regras compartilhadas: `../shared/*.md`.
