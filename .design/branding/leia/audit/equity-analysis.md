# Lastro de equidade

> Fase: audit | Marca: LeIA | Gerado: 2026-09-15

---

## O ponto de partida honesto

A marca LeIA tem três dias. A logo chegou em 12/09/2026 (`docs/brand/README.md:3`), o produto foi construído em 12 e 13/09, e a única exposição pública conhecida é o hackathon da OAB-PR e a URL `leia-snowy.vercel.app`, que está com `robots: { index: false }` em `apps/web/app/layout.tsx:13`, ou seja, fora de busca.

Não existe reconhecimento de mercado. Não há medição de lembrança, preferência, NPS ou menção espontânea, e nenhuma pode ser inventada. Tudo que está abaixo é **equidade de decisão**, não de mercado: escolhas cujo custo de refazer é alto porque o raciocínio por trás delas é sólido e está documentado.

A pergunta útil nesta fase não é "o que o público já reconhece", é "o que foi decidido com fundamento e o que foi só o primeiro caminho que coube nas 48 horas".

## Equidade de decisão, vale preservar

| Ativo | Por que tem lastro |
|---|---|
| **Nome LeIA** | Faz três trabalhos com quatro letras: é o imperativo "leia", nomeia a IA e assina o produto. Funciona falado, que é como a cidadã vai ouvir de um advogado. Quem decide muda o nome perde tudo isso de uma vez |
| **Atkinson Hyperlegible no corpo** | Única escolha do sistema que é uma resposta direta a uma restrição real de persona, não uma preferência estética. Trocá-la é rebaixar a acessibilidade de forma deliberada |
| **Regra teal claro no escuro, teal escuro no claro** | Resolve, em uma frase, o problema de contraste que a logo criou. Está medida, aplicada e é o que dá coerência entre marca e interface |
| **Superfície de papel, não branco puro** | `#FAF8F4` contra o azul e o branco puro dos oito concorrentes mapeados. É o traço cromático que mais separa o LeIA do mercado |
| **Voz de erro e de reprovação** | "Deu um problema do nosso lado, não foi você" e "Vamos ver de novo" são a marca falando. Ninguém no mercado mapeado fala assim com quem assina |
| **Limite declarado como elemento fixo** | O `AssistantBanner` é a única coisa que aparece em toda tela da cidadã. Virou a assinatura visual do produto sem ter sido projetado para isso |
| **Símbolo documento com selo** | A leitura é imediata e não usa nenhum clichê jurídico. O selo é a única representação gráfica do diferencial declarado |
| **Tabela de contraste medida** | A disciplina de medir e registrar, mesmo com três números errados, é rara em marca de hackathon e é o que permite esta auditoria existir |

## Inércia, não equidade

| Item | Por que é só o que ficou pronto primeiro |
|---|---|
| **Navy `#081820` como cor de marca** | Veio do fundo de um JPG. Coincide com a cor do Docusign, o concorrente mais próximo. Não foi escolhido contra alternativas nem testado com a persona |
| **Base de 17 px** | Número herdado de `leia-theme.css:53`, escrito para os templates FastAPI. A pesquisa pede 18 px (`accessibility-patterns.md:76`). Ninguém decidiu 17; ele sobreviveu |
| **Larguras 560 / 680 / 760 px** | Três valores que apareceram em `ui.tsx:125` e viraram o sistema por omissão. Não correspondem ao limite de 60 caracteres por linha que a pesquisa pede |
| **Archivo no display** | Fonte de wordmark que virou fonte de títulos porque estava no SVG. Escolha defensável, decisão nunca tomada |
| **`--font-lawyer` IBM Plex Sans** | Token escrito, fonte nunca carregada. É a marca de uma intenção abandonada, não um ativo |
| **Bloco `.dark`** | 12 variáveis mantidas por uma classe em uma linha. Custa manutenção e não entrega a superfície profissional que justificaria sua existência |
| **`leia-theme.css` e `leia-icons.svg`** | Feitos para rebrandar 6 templates; aplicados em 3 dos 10 servidos. São obra parada, não patrimônio |
| **Escala de 15 tamanhos arbitrários** | Nenhum deles foi decidido; cada um resolveu uma tela |
| **Paleta dourada dos templates legados** | Herança do produto anterior. Zero lastro, custo alto de coexistência |
| **Quiz de múltipla escolha** | Sobreviveu porque cabia no tempo. Contradiz a voz documentada e o diferencial declarado, que é reflexão aberta |

## Casos limítrofes

**Tagline "Leia antes de assinar."** Está em `messages/pt-BR.json:4` e na descrição meta, e não aparece em nenhuma tela. É boa, curta, imperativa e rima com o nome. Não é equidade porque ninguém a viu; é um ativo pronto e não usado. Preservar e passar a usar, não descartar.

**Wordmark "Le" claro + "IA" teal.** A ideia de destacar onde a IA entra é forte e honesta. O risco é que "IA" em destaque puxe a marca para o território de ferramenta de IA, justamente o que o posicionamento tenta evitar ("a marca precisa comunicar prova, não resumo"). Preservar a construção, revisar o peso do destaque na fase de identidade.

**O comprovante.** É o artefato que teria mais chance de virar equidade real, porque é o que a pessoa leva embora e mostra. Hoje não tem forma de marca nenhuma. Não há equidade a preservar; há um espaço vazio a ocupar.

## O que a auditoria não pode afirmar

- Que o navy transmite confiança para a persona cidadã. Não foi testado.
- Que o teal é lido como verificação. Não foi testado, e o teal hoje acumula três papéis.
- Qualquer número de reconhecimento, preferência ou recall. Não existem.
- Que a logo recebida foi aprovada contra alternativas. Não há registro de alternativas.

---

## Related

- [brand-inventory.md](./brand-inventory.md)
- [coherence-assessment.md](./coherence-assessment.md)
- [market-fit.md](./market-fit.md)
- [evolution-map.md](./evolution-map.md)
