/* A voz do aparelho lendo a explicação.
 *
 * A persona principal prefere ouvir a ler, e o produto tratava áudio como enfeite: o texto ia cru para a voz,
 * com `**`, `- ` e o emoji do título, então ela ouvia asterisco e nome de emoji; e num aparelho sem pacote de
 * voz em português o botão falhava calado. As duas coisas se resolvem antes de a voz começar, aqui. */

/** O texto como ele deve ser ouvido: sem marcação, sem emoji, em frases. */
export function spokenText(md: string): string {
  return (md || "")
    // link em markdown: vale o texto, não o endereço
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*_`]+/g, "")
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*>\s?/gm, "")
    // emoji e símbolos de bloco: a voz lê o nome deles ("documento", "seta para a direita")
    .replace(/[\p{Extended_Pictographic}\p{Emoji_Presentation}️⃣]/gu, "")
    // linha em branco vira pausa de frase; linha simples vira espaço
    .split(/\n{2,}/)
    .map((p) => p.replace(/\s*\n\s*/g, " ").trim())
    .filter(Boolean)
    .join(". ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([.,;:!?])/g, "$1")
    .trim();
}

/** Uma voz em português, ou `null` quando o aparelho não tem nenhuma.
 *
 * `null` não é detalhe: é a diferença entre avisar a pessoa e deixá-la tocando um botão que não faz nada. */
export function ptBrVoice(voices: readonly SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const pt = voices.filter((v) => /^pt\b/i.test(v.lang || ""));
  return pt.find((v) => /^pt[-_]br$/i.test(v.lang)) ?? pt[0] ?? null;
}
