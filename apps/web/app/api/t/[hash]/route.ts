import { findTask, publicTask } from "@/lib/mock";

export async function GET(_req: Request, { params }: RouteContext<"/api/t/[hash]">) {
  const { hash } = await params;
  const f = findTask(hash);
  if (!f) return Response.json({ detail: "não encontrado" }, { status: 404 });
  return Response.json(publicTask(f));
}
