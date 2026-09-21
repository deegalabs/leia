"use client";
import Link from "next/link";

/* A última rede: quando o próprio layout raiz falha.
 *
 * Este arquivo substitui o layout inteiro, então ele precisa desenhar `<html>` e `<body>` por conta. E é
 * justamente por isso que ele não importa nada **do produto**: se o que quebrou foi o layout, a fonte ou o
 * CSS global, importar o kit de componentes daqui é pedir para a tela de erro quebrar junto com o erro que
 * ela veio explicar. Texto e estilo ficam escritos aqui dentro, feios e sozinhos, de propósito.
 *
 * O `next/link` logo acima é exceção e não contradiz a regra: ele é do framework que está desenhando esta
 * tela, não do produto. Se ele estivesse quebrado, este componente não teria chegado a renderizar.
 *
 * Os valores de cor são os mesmos de `tokens.css` copiados à mão, pela mesma razão: a folha de estilo pode
 * ser exatamente o que não carregou. Se os tokens mudarem, esta tela fica um pouco fora do tom, e continua
 * legível, que é a única coisa que se pede dela.
 *
 * A mensagem crua da exceção não aparece, igual em `error.tsx`. */

export default function GlobalError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <html lang="pt-BR">
      <body style={{ margin: 0, background: "#FAF8F4", color: "#081820",
                     fontFamily: "system-ui, -apple-system, sans-serif", lineHeight: 1.5 }}>
        <main style={{ maxWidth: 520, margin: "0 auto", padding: "32px 16px" }}>
          <h1 style={{ fontSize: "1.5rem", margin: "0 0 12px" }}>Deu um problema do nosso lado</h1>
          <p style={{ margin: "0 0 12px" }}>
            Não foi você, e nada do que você fez se perdeu. Às vezes isso passa sozinho: tente de novo.
          </p>
          <p style={{ margin: "0 0 24px", fontSize: "0.95rem", color: "#3F4B58" }}>
            {error.digest
              ? `Se precisar falar com a gente, este é o código deste erro: ${error.digest}`
              : "Este erro não gerou código."}
          </p>
          <button type="button" onClick={() => retry()}
                  style={{ display: "block", width: "100%", minHeight: 52, marginBottom: 10, padding: "0 16px",
                           border: 0, borderRadius: 12, background: "#1F7373", color: "#FFFFFF",
                           font: "inherit", fontWeight: 700, fontSize: "1.05rem", cursor: "pointer" }}>
            Tentar de novo
          </button>
          <Link href="/"
             style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 48,
                      borderRadius: 12, border: "2px solid #081820", color: "#081820",
                      fontWeight: 700, fontSize: "1.05rem", textDecoration: "none" }}>
            Ir para o início
          </Link>
        </main>
      </body>
    </html>
  );
}
