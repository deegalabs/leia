"use client";
import Link from "next/link";
import { MessageCircle } from "lucide-react";

import { clientLinkUrl } from "@/lib/api";
import { m } from "@/lib/i18n";
import { resumeMessage, whatsappLink } from "@/lib/resume";
import { AssistantBanner, Card, CopyButton, Page } from "./ui";

/* Como voltar a este documento depois.
 *
 * A conta dela nasceu sem e-mail e sem senha, o que é o ponto inteiro da entrada sem digitação. A conta do
 * que isso custa vem aqui: não há "esqueci minha senha", porque não há senha, e não há endereço para onde
 * mandar um link novo. O endereço que ela já tem é a única forma de voltar, e guardá-lo é coisa que ela
 * precisa fazer agora, enquanto está com o aparelho na mão.
 *
 * O lugar onde esta persona guarda coisas é a conversa dela consigo mesma no WhatsApp. Não são os favoritos
 * do navegador, que ela talvez nem saiba que existem e que somem quando ela troca de aparelho, e não é o
 * histórico, que alguém limpa. Por isso a tela oferece duas coisas só: copiar e mandar. */
export function ResumeView({ hash }: { hash: string }) {
  const url = clientLinkUrl(hash);
  const mensagem = resumeMessage(url);

  return (
    <Page>
      <AssistantBanner />
      <h1 className="mb-2 text-[1.5rem]">{m.resume.title}</h1>
      <p className="mb-4">{m.resume.intro}</p>

      <Card>
        <h2 className="mb-2 text-[1.15rem]">{m.resume.messageTitle}</h2>
        {/* O endereço aparece inteiro, e não escondido atrás de um botão: quem vai conferir se copiou a
            coisa certa precisa ver o que copiou. `break-all` porque endereço não tem espaço para quebrar
            e sem isso ele estoura a tela de um celular estreito. */}
        <p className="mb-3 break-all rounded-card bg-muted px-3 py-2 text-[0.95rem]">{mensagem}</p>
        <div className="grid gap-2">
          <a href={whatsappLink(mensagem)} target="_blank" rel="noopener noreferrer"
             className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-button bg-teal-deep px-4 font-bold text-white">
            <MessageCircle size={20} aria-hidden /> {m.resume.sendWhatsapp}
          </a>
          <CopyButton text={mensagem} label={m.resume.copy} />
        </div>
        <p className="mt-3 text-[0.9rem] text-ink-2">{m.resume.opensWhatsapp}</p>
        <p className="mt-2 text-[0.9rem] text-ink-2">{m.resume.onlyAddress}</p>
      </Card>

      <p className="mt-4">
        <Link href={`/t/${hash}`} className="font-bold text-teal-deep underline underline-offset-4">
          {m.resume.back}
        </Link>
      </p>
    </Page>
  );
}
