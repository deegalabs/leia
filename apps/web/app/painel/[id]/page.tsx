import { TaskDetailView } from "@/components/TaskDetailView";

export const metadata = { title: "Documento" };

export default async function TaskDetailPage({ params }: PageProps<"/painel/[id]">) {
  const { id } = await params;
  return <TaskDetailView id={id} />;
}
