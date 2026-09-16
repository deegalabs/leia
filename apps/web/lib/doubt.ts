/* O que sai do aparelho da cidadã quando ela encaminha uma dúvida ao advogado.
 *
 * Isto morava dentro do componente e mandava sempre os dez últimos turnos, enquanto a tela de boas-vindas
 * dizia que as respostas dela ficavam só com ela. A decisão saiu para cá por dois motivos: porque é decisão,
 * não desenho de tela, e porque decisão sobre dado de outra pessoa precisa de teste. */

export type Msg = { role: "user" | "bot"; text: string };

/** Quantos turnos vão junto quando ela escolhe mandar a conversa. O serviço corta em 20; aqui é menos. */
export const CONTEXT_TURNS = 10;

export type DoubtPayload = { texto: string; contexto: Msg[] };

/** A dúvida a encaminhar, ou `null` quando ela ainda não perguntou nada.
 *
 * `incluirConversa` é escolha dela e vem desligada: o padrão é o que a tela promete, e não o contrário com
 * um aviso em letra pequena. Sem ela, o advogado recebe a pergunta e mais nada. */
export function doubtPayload(msgs: Msg[], incluirConversa: boolean): DoubtPayload | null {
  const ultimaPergunta = [...msgs].reverse().find((x) => x.role === "user");
  if (!ultimaPergunta) return null;
  if (!incluirConversa) return { texto: ultimaPergunta.text, contexto: [] };
  // A primeira mensagem é a apresentação da assistente, escrita por nós: não é conversa dela.
  return { texto: ultimaPergunta.text, contexto: msgs.slice(1).slice(-CONTEXT_TURNS) };
}
