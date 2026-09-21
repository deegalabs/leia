import { ResumeView } from "@/components/ResumeView";

export const metadata = { title: "Voltar a este documento depois" };

export default async function ResumePage({ params }: PageProps<"/t/[hash]/resume">) {
  const { hash } = await params;
  return <ResumeView hash={hash} />;
}
