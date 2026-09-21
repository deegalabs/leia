import Link from "next/link";
import { BadgeCheck, ChevronDown, FileSearch, MessageCircleQuestion, ScrollText } from "lucide-react";
import { LinkButton } from "@/components/ui";
import { AuthNav } from "@/components/Session";
import { VersionBadge } from "@/components/UpdatePrompt";
import { faq } from "@/lib/landing";

const steps = [
  { Icon: FileSearch, text: "O documento em PDF é lido e etiquetado. Cada informação guarda o trecho exato de onde veio." },
  { Icon: ScrollText, text: "A explicação em linguagem simples nasce só dessas etiquetas, um ponto de cada vez, com o trecho original ao lado." },
  { Icon: MessageCircleQuestion, text: "Você lê ou ouve, tira dúvidas e responde a algumas perguntas para conferir o que entendeu." },
  { Icon: BadgeCheck, text: "No fim, recebe um comprovante com um código público. Sem nome, sem documento, sem respostas." },
];
const trust = [
  "Toda explicação mostra o trecho literal do documento.",
  "O que não está no documento, a assistente recusa e diz que não está.",
  "Cada etapa fica registrada e é reproduzível: mesmo documento, mesma explicação.",
  "O registro público guarda só um código, nunca os seus dados.",
];

export default function Landing() {
  const demoHash = process.env.NEXT_PUBLIC_DEMO_HASH || "demo";
  return (
    <div className="flex-1">
      <section className="dark bg-navy px-4 pb-12 pt-10 text-paper">
        <div className="mx-auto max-w-[680px]">
          <div className="mb-8 flex items-center justify-between gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-horizontal-dark.svg" alt="LeIA" className="h-10" />
            <AuthNav />
          </div>
          <h1 className="mb-3 text-[2rem] leading-tight wide:text-[2.6rem]">Entenda o seu documento jurídico em linguagem simples.</h1>
          <p className="mb-8 max-w-[560px] text-[1.15rem] text-paper/85">Um contrato, uma petição ou uma decisão vira uma explicação em partes, com o trecho original ao lado. Você pergunta, confere se entendeu e recebe um comprovante.</p>
          <div className="grid gap-3 wide:max-w-[420px]">
            <LinkButton href={`/t/${demoHash}`} className="!bg-teal !text-navy hover:!bg-[#4FBDBD]">Ver um exemplo</LinkButton>
            <LinkButton href="/enviar" variant="secondary" className="!border-paper !text-paper hover:!bg-white/10">Enviar meu documento</LinkButton>
            <LinkButton href="/entrar" variant="ghost" className="!text-paper hover:!bg-white/10">Sou advogado: entrar</LinkButton>
          </div>
          <p className="mt-6 text-[0.95rem] text-paper/70">Funciona no celular e no computador. Pode ser instalado como aplicativo. <Link href="/docs" className="font-bold text-paper underline underline-offset-4">Documentação</Link></p>
        </div>
      </section>
      <section className="px-4 py-10">
        <div className="mx-auto max-w-[680px]">
          <h2 className="mb-5 text-[1.5rem]">Como funciona</h2>
          <ol className="grid gap-4 wide:grid-cols-2">
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
          <div className="grid gap-4 wide:grid-cols-3">
            <div className="rounded-card bg-teal-soft p-5"><h3 className="mb-1 text-[1.1rem]">Cidadã</h3><p className="text-[1rem]">Entender o que está escrito antes de decidir, no seu ritmo, sem juridiquês.</p></div>
            <div className="rounded-card bg-teal-soft p-5"><h3 className="mb-1 text-[1.1rem]">Advogado</h3><p className="text-[1rem]">Enviar o documento, acompanhar as respostas da cliente e ter o registro de que o esclarecimento aconteceu.</p></div>
            <div className="rounded-card bg-teal-soft p-5"><h3 className="mb-1 text-[1.1rem]">Acesso à justiça</h3><p className="text-[1rem]">Defensoria, advogados dativos e Espaço OAB Cidadania.</p></div>
          </div>
        </div>
      </section>
      <section className="px-4 pb-10">
        <div className="mx-auto max-w-[680px]">
          <h2 className="mb-5 text-[1.5rem]">Por que confiar</h2>
          <ul className="grid gap-3 wide:grid-cols-2">
            {trust.map((t) => <li key={t} className="flex gap-3 rounded-card border border-line bg-surface p-4"><BadgeCheck size={22} aria-hidden className="mt-0.5 flex-none text-teal-deep" /><span>{t}</span></li>)}
          </ul>
        </div>
      </section>
      <section className="px-4 pb-10" aria-labelledby="faq-titulo">
        <div className="mx-auto max-w-[680px]">
          <h2 id="faq-titulo" className="mb-2 text-[1.5rem]">Perguntas frequentes</h2>
          <p className="mb-5 text-ink-2">Respostas curtas, sem juridiquês. O resto está na <Link href="/docs" className="font-bold text-teal-deep underline underline-offset-4">documentação</Link>.</p>
          <div className="grid gap-2">
            {faq.map(({ q, a }) => (
              <details key={q} name="faq" className="group rounded-card border border-line bg-surface">
                <summary className="flex min-h-[52px] cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 font-bold [&::-webkit-details-marker]:hidden">
                  <span>{q}</span>
                  <ChevronDown size={20} aria-hidden className="flex-none text-teal-deep transition-transform group-open:rotate-180" />
                </summary>
                <p className="px-4 pb-4 text-[1rem]">{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
      <footer className="border-t border-line px-4 py-8 text-[0.95rem] text-ink-2">
        <div className="mx-auto max-w-[680px] space-y-2">
          <p>Feito no Hackathon da Cidadania OAB-PR 2026, equipe Token Economy. Código aberto, licença MIT. <Link href="/docs" className="font-bold text-teal-deep underline underline-offset-4">Documentação</Link>. <VersionBadge /></p>
          <p>A assistente explica o que está escrito. Não dá conselho jurídico e não substitui o advogado. O comprovante não é assinatura de nada: ele registra que você leu a explicação e respondeu às perguntas.</p>
        </div>
      </footer>
    </div>
  );
}
