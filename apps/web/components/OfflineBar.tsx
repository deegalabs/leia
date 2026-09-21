"use client";
import { useSyncExternalStore } from "react";
import { WifiOff } from "lucide-react";

/* A faixa de quando a conexão cai.
 *
 * Sem ela, a pessoa toca um botão, nada acontece e a tela mostra um erro genérico do nosso lado — que é
 * mentira, porque o problema é a conexão dela. Dizer qual é o problema evita que ela tente de novo várias
 * vezes e conclua que o produto está quebrado.
 *
 * O texto separa o que continua funcionando do que espera: ler a explicação que já chegou funciona offline,
 * porque ela está na tela; enviar respostas e abrir documento novo, não. Essa diferença é o que decide se
 * ela guarda o celular ou continua lendo.
 *
 * `navigator.onLine` mente para cima: ele diz que há rede quando há Wi-Fi sem internet. Mente pouco para
 * baixo, e é esse o caso que importa aqui — quando ele diz que caiu, caiu mesmo. */

/* `useSyncExternalStore` e não `useState` com efeito: o estado da conexão vive fora do React, e esta é a
   ferramenta para assinar um estado externo sem passar por um `setState` durante o efeito, que dispara
   renderização em cascata. Ela também resolve o servidor: lá não existe `navigator`, e o terceiro argumento
   diz o que responder para o HTML do servidor não divergir do primeiro do navegador. */
const assinar = (avisar: () => void) => {
  window.addEventListener("online", avisar);
  window.addEventListener("offline", avisar);
  return () => {
    window.removeEventListener("online", avisar);
    window.removeEventListener("offline", avisar);
  };
};
const noNavegador = () => navigator.onLine;
const noServidor = () => true;   // o servidor sempre tem rede; quem não tem é quem lê

export function OfflineBar() {
  const online = useSyncExternalStore(assinar, noNavegador, noServidor);

  if (online) return null;
  return (
    <div role="status" className="sticky top-0 z-50 flex items-start gap-2.5 bg-pend-soft px-4 py-2.5 text-[0.95rem] text-ink">
      <WifiOff size={20} aria-hidden className="mt-0.5 flex-none text-pend" />
      <p>
        <span className="font-bold">Você está sem internet.</span>{" "}
        Dá para continuar lendo o que já apareceu na tela. Enviar respostas e abrir um documento novo só
        funciona quando a conexão voltar, e esta faixa some sozinha quando isso acontecer.
      </p>
    </div>
  );
}
