# Changelog

Versões do produto, da mais recente para a mais antiga. As entregas do hackathon que deu origem ao projeto estão
no fim, com as evidências em `evidence/` e o índice em [docs/DELIVERIES.md](docs/DELIVERIES.md).

## Não lançado

Entra aqui toda mudança que altera o que alguém percebe, no mesmo pull request que a faz. Quando o conjunto
fecha um sentido, vira versão com tag anotada e release no GitHub.

### Removido

- **Os dois fluxos que mandavam o documento para fora foram removidos**, com os clientes, as sete rotas, a
  renderização do resultado, a demonstração no mock e a documentação. Eles existiam por um motivo que deixou
  de valer: o `docs/RESUMO-ESTRUTURADO-E-CHAT.md` registrava que a API externa devolvia **posições reais**
  enquanto o pipeline local devolvia `0:0` em tudo. Depois disso o serviço passou a localizar o trecho ele
  mesmo, em três estágios, ignorando de propósito a posição que o modelo escreve. O que a integração prestava
  passou a ser feito aqui, e melhor: a busca local confere contra o PDF que o serviço guarda, enquanto no
  fluxo externo o trecho era conferido contra o texto que o próprio terceiro devolvia, ou seja, quem escrevia
  a citação escrevia também a referência.
- Nenhuma tela do produto chamava essas rotas. O que elas produziam era uma jornada **sem perguntas, sem
  conferência e sem comprovante**, e a revisão do advogado mostrava explicação vazia, então ele aprovava um
  texto que não podia ler. Some com elas a maior superfície de saída de dado do serviço.
- Documento antigo preparado por esse caminho passa a **falhar dizendo o motivo**, em vez de virar uma tela de
  explicação vazia que a pessoa leria como se fosse o documento dela.
- A memória de sessão tinha três abas, duas delas reservadas a esses fluxos e nunca alimentadas. Sobrou a do
  pipeline local, que é a única que o chat de bastidor consome.
### Produto

- **A tela deixou de prometer o que o produto não cumpre.** A jornada afirmava "Suas respostas ficam só com
  você" e, ao encaminhar uma dúvida, mandava junto os dez últimos turnos da conversa, sem ela saber. Agora a
  apresentação diz o que acontece de verdade: a conversa não fica guardada e some ao fechar a página, e fica
  guardado só o que ela escolher enviar ao advogado, mais quantas vezes ela respondeu as perguntas. E a
  conversa só vai junto se ela marcar, com a tela dizendo, antes de enviar, exatamente o que vai em cada caso.
- O botão de ouvir a apresentação lia um texto mais curto do que o escrito na tela. Quem ouve passou a receber
  o mesmo que quem lê.
- **Sair da página parou de custar a jornada inteira.** A etapa passou a ser guardada junto com as respostas,
  então voltar devolve a pessoa ao ponto onde ela estava, em vez de obrigá-la a reler tudo tocando "Entendi,
  próximo" tantas vezes quantos pontos já tinha lido. Documento reprocessado com menos pontos não manda
  ninguém para uma etapa que não existe mais.
- **Errar uma pergunta parou de apagar as respostas certas.** Quem errava uma de três perdia as duas certas e
  voltava ao ponto 1. Agora o que ela acertou fica, ela responde só o que faltou, a tela diz isso, e o botão
  descreve o que de fato acontece em vez de prometer uma explicação nova que não existia.
- **O áudio deixou de falhar calado.** Num aparelho sem voz em português o botão não fazia nada; agora a tela
  avisa e diz onde instalar. "Pausar" cancelava e recomeçava do zero; agora pausa e continua de onde parou, e
  existe "Parar" à parte. O texto falado perdeu a marcação e o emoji, que a voz lia em voz alta. E dá para
  ouvir uma alternativa sozinha, sem repetir a pergunta e as outras três.
- Quando guardar o documento no nome dela é recusado, a tela mostra o motivo escrito pelo serviço. Antes a
  recusa era engolida e ela só descobria no fim que não sairia comprovante. No painel, a dica sobre o convite
  passou a dizer que sem convite não há comprovante.

### Segurança e privacidade
- **Quem vê o documento deixou de mandar nele.** A autorização de várias rotas perguntava se a pessoa enxerga o
  documento, e a cidadã vinculada enxerga. Com isso ela baixava `questoes.json`, que carrega `correta` e
  `justificativa`, ou seja, o gabarito das perguntas que ela mesma ia responder, o que devolvia o produto ao
  "li e aceito" passivo que ele existe para não ter. Pelo mesmo caminho saíam os artefatos intermediários, e
  `reprocess` e `nova-rodada` obedeciam: a primeira apaga o resumo que lastreia um comprovante já congelado, a
  segunda cria documento na conta de quem enviou. Agora essas rotas respondem só a quem enviou o documento.
- O e-mail do advogado saiu do `meta.json`, que é gravado no workspace e era baixável. O `advogado_id` já está
  no banco, então o endereço estava ali sem necessidade, enquanto o convite tem o cuidado de mascará-lo.
- **O portão de revisão do advogado valia em algumas rotas e não em outras.** `GET /api/t/{hash}` escondia a
  explicação durante a revisão, e `GET /api/pdf/{hash}/destilado` entregava a mesma explicação ao lado. Agora o
  portão vale nas duas, e quem revisa continua vendo. Os eventos de `GET /api/tarefas/{id}/status` deixaram de
  sair crus para quem não é dono.
- **Vincular deixou de ser por ordem de chegada.** Ler e perguntar seguem abertos a quem tem o link, de
  propósito, porque exigir conta para ler é barreira justamente para quem o produto atende. Mas vincular define
  `cidadao_id`, e quem chega depois recebe 409: na prática o primeiro que aparecia trancava os demais, inclusive
  a pessoa para quem o documento foi mandado. Agora vincular exige convite vivo, e quem enviou pode desfazer o
  vínculo em `DELETE /api/tarefas/{id}/cidadao`, que antes não existia, e que recusa quando já há
  conferência registrada, porque a tentativa pertence à tarefa e a próxima conta herdaria o comprovante da
  anterior, que afirma que **outra** pessoa entendeu o documento.
- **O teto de tentativas e o hash do comprovante tinham corrida.** O número da rodada era escolhido numa sessão
  e gravado em outra, sem restrição no banco. Medido: com teto de 3 e 12 envios simultâneos, 7 tentativas
  gravadas, com números repetidos. Duas consequências, e a segunda é a grave: furava-se o teto que existe para
  impedir o gabarito por tentativa e erro, e duas tentativas diferentes saíam com o mesmo `hash_imutavel`, que é
  o identificador público do comprovante, então `/verify/{hash}` podia atestar um registro que não era o dela.
  O número passou a ser decidido pelo banco, por restrição única, com nova tentativa quando dois envios disputam.
- **O texto do documento passou a ser tratado como dado, e não como comando.** A cerca que separa o conteúdo
  do PDF da instrução era montada por interpolação com etiqueta fixa, então bastava o documento conter a
  etiqueta de fechamento para o resto dele sair da cerca e virar instrução na mensagem. Valia para as duas
  cercas, e a segunda importa mais, porque alimenta 9 das 14 etapas e carrega `trecho_verbatim`, que é cópia
  literal do documento por contrato. A etiqueta agora é sorteada a cada execução: o documento não fecha o que
  não consegue adivinhar. E nenhuma das 14 missões dizia ao modelo que aquele conteúdo é material a analisar;
  o aviso passou a morar no papel de sistema, num lugar só, acima da missão, **nomeando a etiqueta que ele
  mesmo sorteou**: sortear sem nomear transforma a cerca numa forma pública, que qualquer documento imita
  escrevendo uma etiqueta do mesmo feitio. E o conteúdo do documento passa por uma limpeza que tira dele
  qualquer etiqueta, de abertura ou de fechamento, porque estrutura é o que o conteúdo não pode escrever.
- No chat da cidadã, o resumo e a memória saíram de dentro do papel de sistema. Eles são derivados do PDF, e a
  memória carrega o trecho literal dele, então texto de origem não confiável ficava logo abaixo da regra "use
  apenas o contexto", com precedência sobre ela. Agora o sistema só tem regra, e o material do documento chega
  como mensagem à parte, dentro da mesma cerca sorteada.
- **Mandar o documento para um serviço externo deixou de ser o padrão.** Duas rotas repassavam o PDF inteiro,
  byte a byte, para dois hosts de terceiros que ninguém autentica, disparáveis por qualquer conta e sem forma
  de desligar. Agora dependem de `EXTERNAL_FLOWS_ENABLED`, que vem desligada, e respondem só ao fornecedor. A
  saída do documento virou um evento visível na jornada, em vez de existir só no log interno.
- Os dois uploads desses fluxos passaram a conferir tamanho e assinatura de PDF de verdade, o que só existia
  nos outros dois caminhos: antes aceitavam qualquer conteúdo e qualquer tamanho e gravavam no volume.
- A bateria de testes parou de falar com terceiro. O endereço padrão apontava para as APIs externas de
  verdade, então rodar os testes mandava um PDF para fora, inclusive na integração contínua.
- O trecho literal deixou de ser conferido pelo modelo e passou a ser localizado pelo serviço. A posição que o
  modelo escrevia era aceita se parecesse válida, então o selo de "trecho conferido" podia apontar para a
  cláusula errada, ou aparecer para um trecho inventado. Agora a busca é do servidor, em três estágios, e o
  item diz qual achou.
- Na jornada, o trecho só aparece depois de ser encontrado no documento, e a frase muda conforme o método:
  cópia exata só é afirmada quando foi exata. Antes a tela dizia "copiado exatamente do seu documento" para
  uma citação escolhida por semelhança de três palavras, sem nunca ter sido procurada no documento.
- De onde vem o trecho de cada tópico deixou de ser adivinhado. A tela escolhia, entre os trechos do documento,
  aquele com mais palavras em comum com a explicação, o que colocava um trecho sobre os fatos embaixo de "quem
  está nesta história". Agora cada seção declara no protocolo qual parte do documento ela explica, e o trecho vem
  do que a própria síntese diz ter usado. Sem fonte declarada, ou sem achar no documento, nenhum trecho aparece.
- Uma etapa do pipeline que prometia JSON e devolvia outra coisa seguia como sucesso: o texto cru virava a saída
  dela, era gravado no arquivo da etapa e entrava no contexto da seguinte. Agora ela falha, e o documento inteiro
  falha com ela, o que é melhor que uma explicação construída sobre lixo. Sete etapas passaram a declarar no
  protocolo quais campos precisam existir, e a saída é conferida contra isso.
- O comprovante passou a dizer **a que documento e a que explicação** ele se refere, com o hash de cada um. Antes
  esses dois campos existiam no registro publicado e saíam sempre vazios, então o comprovante provava que houve
  uma tentativa com N acertos e nada mais, sem amarrar o entendimento ao documento que a pessoa leu.
- O registro passou a ser gravado no momento em que a pessoa o conquistou, e nunca mais reconstruído. Antes ele era
  remontado do banco a cada visita: mudou uma linha, mudou a prova, e o carimbo de tempo passava a corresponder a
  um registro que não existia mais. Comprovantes emitidos antes desta mudança continuam abrindo.

### Por dentro
- A bateria lê também um corpus privado, fora do repositório, por `LEIA_EVAL_CASES`. Documento de verdade não é
  versionado; o que fica escrito é a estrutura de cada tipo de peça, em `docs/DOCUMENT-TYPES.md`.
- Existe uma bateria de avaliação do motor (`apps/llm-service/evals`). Ela mede, sobre casos gravados de tarefas
  reais e sem chave de modelo, se o trecho mostrado está mesmo no documento, se a posição informada é a certa e se
  o gabarito não viaja com a pergunta. Cobertura e precisão de âncora têm piso, que não reprova entrega mas acusa
  piora. A camada de juiz não existe ainda, e a bateria diz isso em voz alta em vez de fingir.
- `pytest -q` passou a encontrar todo arquivo de teste do serviço. Antes os arquivos eram nomeados um a um no
  comando, então um arquivo novo de teste podia existir sem nunca ser executado.

## v1.1.0 · 2026-09-15 · a sessão e o link deixam de ser credenciais soltas

### Segurança e privacidade
- A sessão saiu do armazenamento do navegador e virou cookie inacessível a script. Para isso o navegador
  deixou de falar direto com o serviço: agora ele fala com a aplicação, e a aplicação fala com o serviço.
  Quem estava com sessão aberta no pacote antigo foi deslogado uma vez.
- O link do documento deixou de ser credencial de quem o tivesse. Ele pode vencer, pode ser cancelado e pode
  ser endereçado a uma pessoa. Ler e perguntar seguem sem exigir conta, de propósito; o que exige identidade é
  guardar o comprovante, porque ele afirma que uma pessoa entendeu o documento.

### Infraestrutura
- A configuração de deploy do serviço virou código em `.railway/railway.ts`, antes do corte do formato antigo
  em 2026-12-01. O deploy passou a esperar a verificação contínua e só reconstrói quando o serviço muda.
- O sinal de vida do serviço apontava para uma rota que não existia mais, então a verificação de saúde nunca
  rodava. Agora aponta para `GET /health`, e um teste amarra o caminho declarado à rota servida.
- `main` protegida: pull request obrigatório, uma aprovação, verificação verde, sem reescrita de histórico.

### Por dentro
- O serviço passou a nomear funções, classes e módulos em inglês. Nenhuma rota, campo ou coluna mudou.
- A raiz do repositório usa pnpm, como o resto, em vez de npm.
- Saíram do versionamento arquivos que o build gera: o service worker e o estado de execução do chat de bastidores.

## v1.0.0 · 2026-09-15 · primeira versão pública

Repositório aberto sob licença MIT, em produção em https://leia-snowy.vercel.app.

### Produto
- Jornada do cidadão: explicação em linguagem simples com o trecho original ao lado, um tópico por vez, dúvidas
  respondidas só com o que está no documento, conferência de compreensão com rubrica e ponto a rever quando erra.
- Painel do advogado: envio do documento, revisão do resumo estruturado e aprovação, que é o que libera o link.
- Comprovante com QR e página pública de verificação, conferível por terceiro sem depender do serviço.
- Documentação navegável em `/docs`, gerada a partir do markdown do repositório, com diagramas em tela cheia.
- Aplicação instalável, responsiva do celular ao computador.

### Segurança e privacidade
- O limite por requisição deixou de ser contornável. Ele era calculado a partir do começo de `X-Forwarded-For`,
  que é o pedaço que quem chama escreve, então bastava variar esse valor para nunca encher o balde.
- O registro público deixou de carregar o link do documento do cidadão. Passou a identificá-lo por um hash
  (`documentRef`), sem o `salt` decorativo que não protegia nada.
- O hash da tentativa virou reprodutível a partir do que fica gravado, sem endereço de rede nem navegador.
- Teto de tentativas na conferência, para o registro não sair por tentativa e erro.
- O comprovante em PDF deixou de afirmar o que não prova e de imprimir endereço de rede e navegador.
- A casca HTML antiga do serviço saiu inteira: dez rotas, sete templates, e com elas o gabarito que ficava
  visível no HTML e o PDF acessível sem autenticação.
- Rotas de bastidor restritas ao papel de fornecedor.
- Abrir o link deixou de vincular o documento a quem abriu; o vínculo virou um ato explícito.
- O markdown da documentação deixou de renderizar HTML bruto, fechando a injeção por pull request de documentação.
- Prova de carimbo que não corresponde ao registro é refeita em vez de bloquear o carimbo.

### Infraestrutura
- Integração contínua nos dois lados a cada pull request, com `main` protegida: pull request obrigatório,
  uma aprovação e verificação verde.
- Sinal de vida em `GET /health` no serviço, que é o que autoriza uma versão nova a assumir.

## Hackathon da Cidadania OAB-PR · 12 e 13 de setembro de 2026

Equipe Token Economy, categoria Inovação Aberta e Cidadania. O produto nasceu aqui, com o nome definido durante
o evento: LeIA, de Lei mais IA, antes ConsentChain e Ciente.

- **Entrega 1, Canvas** (`token-economy/v0.1.0`, sáb 12h): canvas transcrito em `docs/CANVAS.md`, mais
  posicionamento, arquitetura, contrato da API, personas, casos de uso, telas, escopo por entrega, roadmap,
  escala e plano de testes.
- **Entregas 2 e 3** (V1 com testes internos, V2 com testes externos): aconteceram no evento e estão no histórico
  do git, sem tag e sem arquivo em `evidence/`. O que foi testado está em `docs/INTERNAL-TESTS.md`.
- **Entrega 4, produto e auditoria**: 20 arquivos em `evidence/04-product/`.
- **Entrega 5, slides**: apresentação e guia de defesa em `evidence/05-slides/`.

O código de cada entrega está no histórico do git entre a tag da Entrega 1 e a `v1.0.0`. As pastas
`evidence/01-canvas/`, `02-internal-tests/` e `03-external-tests/` ficaram vazias.
