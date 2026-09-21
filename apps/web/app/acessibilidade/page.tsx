import Link from "next/link";

import { Card, Page } from "@/components/ui";

export const metadata = { title: "Acessibilidade" };

/* A declaração de acessibilidade.
 *
 * Ela vale pelo que admite, não pelo que promete. Uma declaração que só lista conformidade é propaganda; o
 * que serve a quem depende dela é saber exatamente onde o produto ainda falha, para decidir se consegue
 * usá-lo hoje. Por isso a seção "o que ainda não funciona bem" existe e é para crescer, não para esvaziar.
 *
 * Toda afirmação daqui é verificável no repositório. Nada de "nos esforçamos para". */

export default function Acessibilidade() {
  return (
    <Page>
      <h1 className="mb-2 text-[1.75rem]">Acessibilidade</h1>
      <p className="mb-6 text-ink-2">
        Esta página diz o que foi testado, o que funciona e o que ainda não funciona. Ela é atualizada quando
        o produto muda, e não uma vez por ano.
      </p>

      <Card className="mb-4">
        <h2 className="mb-2 text-[1.25rem]">Contra qual norma</h2>
        <p>
          WCAG 2.2, nível AA. É a norma que a legislação brasileira usa como referência para acessibilidade
          na web, e é contra ela que os números abaixo foram medidos.
        </p>
      </Card>

      <Card className="mb-4">
        <h2 className="mb-2 text-[1.25rem]">O que está medido, e por teste automático</h2>
        <ul className="grid list-disc gap-2 pl-5">
          <li>
            <strong>Contraste de cor.</strong> Todo par de cor do produto é medido a partir do arquivo de
            tokens, e nenhum fica abaixo de 4,5:1 para texto nem de 3:1 para a borda do que você opera. Se
            alguém clarear uma cor, o teste reprova antes de chegar ao ar.
          </li>
          <li>
            <strong>Um único ponto de virada de layout.</strong> A tela muda de forma uma vez só, em 1024
            pixels de largura. Abaixo disso é sempre coluna única, que é o que se lê no celular.
          </li>
          <li>
            <strong>Alvo de toque grande.</strong> Os botões de ação e os campos têm de 48 a 56 pixels de
            altura. O menor alvo do produto tem 36, num atalho secundário dentro de texto. A norma pede 24,
            então todos passam com folga.
          </li>
          <li>
            <strong>Fonte escolhida por legibilidade.</strong> O corpo do texto usa Atkinson Hyperlegible,
            desenhada para distinguir letras que se parecem.
          </li>
          <li>
            <strong>Movimento respeitado.</strong> Quem pede menos animação no sistema não recebe animação
            nenhuma.
          </li>
          <li>
            <strong>Erro explicado.</strong> Quando algo falha do nosso lado, a tela diz isso em palavras,
            diz que não foi você e oferece tentar de novo, em vez de página em branco.
          </li>
        </ul>
      </Card>

      <Card tone="pending" className="mb-4">
        <h2 className="mb-2 text-[1.25rem]">O que ainda não funciona bem</h2>
        <ul className="grid list-disc gap-2 pl-5">
          <li>
            <strong>Nenhuma pessoa com deficiência testou este produto ainda.</strong> Tudo acima é medida
            automática e revisão nossa, que pega uma parte do problema e não pega a que mais importa.
          </li>
          <li>
            <strong>Ouvir ainda não cobre tudo.</strong> Dá para ouvir a explicação e as perguntas; a
            resposta do chat ainda não tem botão de ouvir.
          </li>
          <li>
            <strong>Em aparelho sem voz em português</strong>, o botão de ouvir não avisa o motivo com
            clareza suficiente.
          </li>
          <li>
            <strong>Não há alto contraste dedicado.</strong> Quem pede mais contraste no sistema recebe as
            mesmas cores, que cumprem a norma mas não são o ideal para baixa visão.
          </li>
        </ul>
      </Card>

      <Card tone="soft">
        <h2 className="mb-2 text-[1.25rem]">Achou uma barreira? Conte para a gente</h2>
        <p className="mb-2">
          Se alguma parte não funcionou para você, queremos saber qual e em que aparelho. Barreira relatada é
          a única que vira conserto.
        </p>
        <p>
          Se você recebeu este documento de um advogado, fale com ele: ele consegue mandar sua dúvida por
          dentro do produto, na própria página do documento.
        </p>
      </Card>

      <p className="mt-6">
        <Link href="/" className="font-bold text-teal-deep underline underline-offset-4">Ir para o início</Link>
      </p>
    </Page>
  );
}
