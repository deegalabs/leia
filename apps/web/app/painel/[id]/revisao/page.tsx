import { ReviewView } from "@/components/ReviewView";

export const metadata = { title: "Revisão antes de liberar" };

export default async function ReviewPage({ params }: PageProps<"/painel/[id]/revisao">) {
  const { id } = await params;
  return <ReviewView id={id} />;
}
