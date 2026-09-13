import { Receipt } from "@/components/Receipt";

export const metadata = { title: "Seu comprovante" };

export default async function ReceiptPage({ params }: PageProps<"/comprovante/[attempt]">) {
  const { attempt } = await params;
  return <Receipt attempt={attempt} />;
}
