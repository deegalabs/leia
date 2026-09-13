import Link from "next/link";
import { AssistantBanner, Page } from "@/components/ui";

export default function NotFound() {
  return (
    <Page>
      <AssistantBanner />
      <h1 className="mb-2 text-[1.5rem]">Não encontramos esta página</h1>
      <p>O endereço pode estar incompleto. Se você recebeu um link, confira com quem enviou.</p>
      <p className="mt-4"><Link href="/" className="font-bold text-teal-deep underline underline-offset-4">Ir para o início</Link></p>
    </Page>
  );
}
