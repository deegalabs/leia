import { Journey } from "@/components/Journey";

export const metadata = { title: "Seu documento" };

export default async function TaskPage({ params }: PageProps<"/t/[hash]">) {
  const { hash } = await params;
  return <Journey hash={hash} />;
}
