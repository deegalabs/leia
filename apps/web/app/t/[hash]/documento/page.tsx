import { DocumentView } from "@/components/DocumentView";

export const metadata = { title: "Documento e marcações" };

export default async function DocumentPage({ params }: PageProps<"/t/[hash]/documento">) {
  const { hash } = await params;
  return <DocumentView hash={hash} />;
}
