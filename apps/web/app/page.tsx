import { BadgeCheck, FileText, Mic } from "lucide-react";
import { LinkButton } from "@/components/ui";
import { panelUrl } from "@/lib/api";

const steps = [
  { Icon: FileText, text: "O documento entra e a explicação é preparada em linguagem simples." },
  { Icon: Mic, text: "Você ouve ou lê, pergunta e responde algumas perguntas." },
  { Icon: BadgeCheck, text: "Você recebe um comprovante de que entendeu, com código público." },
];
const trust = [
  "Cada explicação mostra o trecho original do documento.",
  "O que não está no documento, a assistente recusa.",
  "Um advogado supervisiona; a assistente não dá conselho jurídico.",
  "O registro público guarda só um código, nunca seus dados.",
];

export default function Landing() {
  const panel = panelUrl();
  const demoHash = process.env.NEXT_PUBLIC_DEMO_HASH || "demo";
  return (
    <main className="flex-1">
      <section className="dark bg-navy px-4 pb-12 pt-10 text-paper">
        <div className="mx-auto max-w-[680px]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-horizontal-dark.svg" alt="LeIA" className="mb-8 h-10" />
          <h1 className="mb-3 text-[2rem] leading-tight md:text-[2.6rem]">Leia antes de assinar.</h1>
          <p className="mb-8 max-w-[520px] text-[1.15rem] text-paper/85">Você entende cada parte do seu documento, em linguagem simples e por voz. Depois fica registrado que você entendeu.</p>
          <div className="grid gap-3 sm:max-w-[420px]">
            <LinkButton href={`/t/${demoHash}`} className="!bg-teal !text-navy hover:!bg-[#4FBDBD]">Ver um exemplo</LinkButton>
            {panel && <LinkButton href={panel} external variant="secondary" className="!border-paper !text-paper hover:!bg-white/10">Sou advogado: começar</LinkButton>}
          </div>
        </div>
      </section>
      <section className="px-4 py-10">
        <div className="mx-auto max-w-[680px]">
          <h2 className="mb-5 text-[1.5rem]">Como funciona</h2>
          <ol className="grid gap-4 md:grid-cols-3">
            {steps.map(({ Icon, text }, i) => (
              <li key={i} className="rounded-card border border-line bg-surface p-5">
                <Icon size={28} aria-hidden className="mb-3 text-teal-deep" />
                <p><span className="font-bold">{i + 1}.</span> {text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>
      <section className="px-4 pb-10">
        <div className="mx-auto max-w-[680px]">
          <h2 className="mb-5 text-[1.5rem]">Para quem</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-card bg-teal-soft p-5"><h3 className="mb-1 text-[1.1rem]">Cidadã</h3><p className="text-[1rem]">Entender antes de assinar, em ambiente seguro, no seu ritmo.</p></div>
            <div className="rounded-card bg-teal-soft p-5"><h3 className="mb-1 text-[1.1rem]">Advogado</h3><p className="text-[1rem]">Supervisionar a explicação e ter a prova de que o esclarecimento aconteceu.</p></div>
            <div className="rounded-card bg-teal-soft p-5"><h3 className="mb-1 text-[1.1rem]">Acesso à justiça</h3><p className="text-[1rem]">Defensoria, advogados dativos e Espaço OAB Cidadania.</p></div>
          </div>
        </div>
      </section>
      <section className="px-4 pb-10">
        <div className="mx-auto max-w-[680px]">
          <h2 className="mb-5 text-[1.5rem]">Por que confiar</h2>
          <ul className="grid gap-3 md:grid-cols-2">
            {trust.map((t) => <li key={t} className="flex gap-3 rounded-card border border-line bg-surface p-4"><BadgeCheck size={22} aria-hidden className="mt-0.5 flex-none text-teal-deep" /><span>{t}</span></li>)}
          </ul>
        </div>
      </section>
      <footer className="border-t border-line px-4 py-8 text-[0.95rem] text-ink-2">
        <div className="mx-auto max-w-[680px] space-y-2">
          <p>Feito no Hackathon da Cidadania OAB-PR 2026, equipe Token Economy. Código aberto, licença MIT.</p>
          <p>A assistente explica o que está escrito. Não dá conselho jurídico e não substitui o advogado. Registro público com carimbo de tempo.</p>
        </div>
      </footer>
    </main>
  );
}
