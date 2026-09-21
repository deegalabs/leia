/* A mensagem que ela manda para si mesma para voltar ao documento depois.
 *
 * O link é a credencial: quem o tem abre o documento, e quem o perde não tem senha nem e-mail para pedir
 * de volta, porque a conta nasceu sem os dois. Guardar o endereço é, então, a única forma de voltar — e o
 * lugar onde a persona deste produto guarda coisas é a conversa dela consigo mesma no WhatsApp, não os
 * favoritos de um navegador que ela talvez nem saiba que existem.
 *
 * A mensagem leva só o endereço. O título de um documento jurídico costuma ser o pior pedaço dele para
 * aparecer na conversa de alguém, e o endereço sozinho já reabre o documento, que é o serviço inteiro que
 * esta mensagem presta. O parâmetro `titulo` existe para quem chama não precisar lembrar disso: ele é
 * aceito e deliberadamente ignorado. */

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- o título é aceito e ignorado de propósito
export function resumeMessage(url: string, _titulo?: string): string {
  return `Guardei meu documento no LeIA. Para abrir de novo: ${url}`;
}

/* Sem número de destino: `wa.me` sem número abre a lista de conversas e ela escolhe para quem mandar,
   que na maioria das vezes é ela mesma. Pôr um número aqui seria escolher por ela. */
export function whatsappLink(mensagem: string): string {
  return `https://wa.me/?text=${encodeURIComponent(mensagem)}`;
}
