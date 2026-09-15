# LeIA — brief da marca

> Fase: brief | Marca: LeIA | Gerado: 2026-09-15 | Modo: evoluir marca existente

---

## O que é

LeIA, de Lei mais IA. Plataforma que pega o documento jurídico que a pessoa recebeu e explica em português
simples, sempre mostrando o trecho original ao lado, tira dúvidas apenas com o que está escrito ali, confere
se ela entendeu e emite um comprovante verificável desse entendimento. O advogado revisa e libera antes de o
link chegar ao cidadão.

Mantenedora: Deega Labs. Nasceu no Hackathon da Cidadania OAB-PR, 12 e 13 de setembro de 2026. Em produção em
https://leia-snowy.vercel.app, código aberto sob licença MIT.

**Frase que resume:** hoje fica registrado que a pessoa recebeu o documento, não fica registrado que ela entendeu.

---

## Personas

| Persona | Quem é | Contexto de uso | O que a marca precisa transmitir |
|---|---|---|---|
| **Cidadã** (principal) | recebeu contrato, procuração, petição ou decisão; muitas vezes baixa escolaridade; celular básico; prefere ouvir a ler; medo de golpe e de decidir errado | leitura linear, um ponto por vez, foco único, em pé, com pressa ou ansiedade | acolhimento sem infantilizar, clareza, ausência de ameaça, "isso é para mim" |
| **Advogado** (supervisão) | pequeno escritório, dativo, Defensoria, núcleo de prática; pouco tempo; dever de informar | trabalho em computador, várias tarefas, lista e detalhe lado a lado, revisão e liberação | seriedade profissional, densidade de informação, controle, responsabilidade |
| **Verificador** | auditor da Ordem, juiz, a própria cidadã meses depois | abre um link ou lê um QR, quer conferir sem depender do sistema | sobriedade institucional, prova, neutralidade |

A tensão central da identidade: a mesma marca precisa acolher alguém assustado no celular e transmitir
autoridade profissional num painel de trabalho. Hoje isso é resolvido com duas superfícies, clara para a
cidadã e navy para as áreas de marca, comprovante e trilho do profissional.

---

## Cenário competitivo

- **Commodity gratuita:** explicar documento em linguagem simples já é entregue de graça pelos grandes modelos
  com upload de PDF, explicação guiada e quiz, e por um grande portal jurídico brasileiro voltado ao cidadão.
- **Commodity paga:** hash, carimbo de tempo e trilha de auditoria são vendidos por várias plataformas
  brasileiras de assinatura eletrônica.
- **Adjacente em saúde:** existe produto de consentimento com identidade, assinatura e trilha, sem verificação
  de compreensão.
- **Patente adjacente:** há família de patente concedida sobre validação de identidade e integridade com
  detecção de coação por câmera, que não cobre aferição de compreensão.

**O que sobra de diferenciado:** o artefato probatório de compreensão, com trecho literal conferido por
operação computacional e liberação por advogado. A marca precisa comunicar prova, não resumo.

---

## Essência da marca

- **Promessa:** você entende antes de decidir, e fica registrado que entendeu.
- **Postura:** assistente que explica o que está escrito, nunca conselheira. Não diz o que fazer.
- **Limite declarado, que é parte da identidade:** não presta consultoria, não interpreta o caso concreto,
  não substitui o advogado. Vedação da Ordem, e aparece na interface como texto fixo.
- **Tom:** português simples, frases curtas, sem juridiquês, sem travessão. Existe tabela de substituição de
  termos em `docs/brand/copy-replacements.md`.

---

## Sistema visual aplicado hoje

- **Cor:** navy #081820 e #0F2431; paper #F0F0E8 e #FAF8F4; surface #FFFFFF; ink #081820 e #3F4B58; line
  #E3DED6; teal #38A8A8, teal-deep #1F7373, teal-soft #E3F1F1; mais estados de ok, pendente e perigo.
  Total de 51 variáveis em `apps/web/app/tokens.css`, com razões de contraste medidas em `docs/brand/README.md`.
- **Tipografia:** Archivo para display (600, 700, 800), Atkinson Hyperlegible para corpo, escolhida por
  legibilidade para baixa escolaridade, IBM Plex Mono para dados, códigos e rótulos.
- **Logo:** marca gráfica e duas versões horizontais, clara e escura, mais ícones de aplicativo instalável.
- **Componentes:** 19 componentes em `apps/web/components`, com primitivas em `ui.tsx`.

---

## Restrições que não são preferência

1. **Acessibilidade é requisito.** A fonte de corpo foi escolhida por isso. Alvos de toque grandes, contraste
   medido, foco visível, movimento reduzido respeitado, e o texto pode ser ouvido.
2. **Celular básico é o piso**, não o caso excepcional. Nada pode depender de aparelho potente.
3. **Sem posicionamento de consultoria jurídica.** O advogado aparece como supervisão humana.
4. **Código aberto**, com licença permissiva, e compromisso de não impor barreira ao uso pela advocacia.

---

## Direção de projeto já decidida

Duas cascas separadas, uma para a cidadã e outra para o advogado, mais telas públicas sem casca. Um único
ponto de virada em 1024 px. Sistema de largura declarado uma vez em tokens. Painel com cartões no celular e
tabela no computador. Documento e revisão em mestre mais trilho grudado.

**Lacuna conhecida:** o layout raiz é vazio, há 44 usos de breakpoint espalhados e cinco larguras diferentes
em oito arquivos. O sistema existe na camada de marca e não existe na camada de layout.

---

## Related

- [STATE.md](./STATE.md)
- [config.json](./config.json)
