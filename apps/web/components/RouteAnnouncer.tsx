"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

/* Anuncia a troca de rota para quem navega ouvindo.
 *
 * Numa aplicação de página única o navegador não recarrega, então o leitor de tela não tem o marco que ele
 * usa para dizer onde a pessoa chegou: ela toca um botão, a tela inteira muda e o leitor continua calado.
 * Esta região diz o título da página nova, e é a única coisa que ela faz.
 *
 * `aria-live="polite"` espera a leitura em curso terminar, em vez de interromper. Interromper aqui seria
 * cortar a própria frase que fez a pessoa tocar no botão. */

export function RouteAnnouncer() {
  const pathname = usePathname();
  const [anuncio, setAnuncio] = useState("");

  useEffect(() => {
    /* O título só existe depois que o Next o aplica ao documento, e isso acontece depois deste efeito.
       Um quadro de espera é o suficiente, e é menos frágil que observar o `<title>`. */
    const t = setTimeout(() => setAnuncio(document.title || "Página carregada"), 100);
    return () => clearTimeout(t);
  }, [pathname]);

  return <p aria-live="polite" aria-atomic="true" className="sr-only">{anuncio}</p>;
}
