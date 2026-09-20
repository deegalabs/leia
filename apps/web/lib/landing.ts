/* Copy for the landing page. It lives apart from the page so the promises it makes about the engine can be
   checked by a test: the landing is read before anyone sees the product work, so a promise here that the
   pipeline does not keep is the one lie a visitor cannot catch. */
export type FaqEntry = { q: string; a: string };

/* Short answers in plain language. Same content as the objections and questions in the pitch guide. */
export const faq: FaqEntry[] = [
  { q: "A assistente dá conselho jurídico?", a: "Não. Ela explica o que está escrito no seu documento, sempre mostrando o trecho original ao lado. Ela não diz o que você deve fazer. Quem aconselha é o advogado, e é ele quem revisa e libera a explicação quando o link vem dele." },
  { q: "Como sei que ela não inventa?", a: "Cada informação da explicação carrega o trecho exato do documento de onde veio, e você vê os dois lado a lado. Se você perguntar algo que não está no documento, ela responde que isso não está escrito ali." },
  { q: "O comprovante é uma assinatura eletrônica?", a: "Não. Assinatura registra que alguém assinou ou clicou. O comprovante registra que você leu a explicação e respondeu às perguntas de conferência. Se o documento precisa de assinatura, ela continua sendo feita como sempre, e o comprovante vai junto." },
  { q: "O que é o código do comprovante?", a: "As suas respostas viram um texto fixo, e desse texto sai uma impressão digital, que é o código. Ele recebe um carimbo de tempo público. Qualquer pessoa confere, na página de verificação, que o comprovante existia naquele dia e não foi alterado, sem precisar confiar na gente." },
  { q: "Meus dados vão para algum lugar público?", a: "Não. No registro público vai só o código. Nome, documento e respostas ficam na plataforma." },
  { q: "E se eu não entender de jeito nenhum?", a: "Você não fica reprovada. A assistente explica de outro jeito quantas vezes for preciso. Se ainda assim não ficar claro, você pode enviar a dúvida para o advogado responder no painel dele. O comprovante só é gerado depois que você mostrou que entendeu." },
  { q: "Serve para qualquer documento?", a: "Serve para qualquer PDF com texto: contrato, procuração, petição, decisão, intimação. O caminho é o mesmo para todos: a assistente separa partes, datas e valores, fatos, fundamentos e pedidos, explica cada ponto em linguagem simples e faz as perguntas de conferência sobre essa explicação. O exemplo pronto e os nossos testes usam um contrato de honorários." },
  { q: "Preciso de um advogado para usar?", a: "Não. Você pode enviar o seu documento e tirar dúvidas por conta própria. Quando o link vem de um advogado, ele revisa a explicação antes de você receber e passa a receber as suas dúvidas." },
  { q: "Precisa instalar alguma coisa?", a: "Não. Funciona no navegador do celular e do computador. Se quiser, dá para instalar como aplicativo pelo menu do navegador, e o app avisa quando tem versão nova." },
  { q: "O comprovante vale como prova?", a: "Ele é íntegro e datado, e qualquer pessoa confere sem depender da gente. O peso de cada prova quem dá é o juiz. O que o LeIA entrega é um registro que hoje não existe: o de que a explicação foi lida e conferida." },
  { q: "Quanto custa?", a: "Hoje é uma demonstração aberta e gratuita, feita no hackathon. O custo por documento é de centavos de processamento, e o carimbo de tempo público não custa nada. Os números estão na documentação." },
];
