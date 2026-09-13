import { Verify } from "@/components/Verify";

export const metadata = { title: "Verificação pública" };

export default async function VerifyPage({ params }: PageProps<"/verify/[attempt]">) {
  const { attempt } = await params;
  return <Verify attempt={attempt} />;
}
