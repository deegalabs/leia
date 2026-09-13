import { evaluateQuiz, findTask } from "@/lib/mock";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/quiz">) {
  const { hash } = await params;
  const f = findTask(hash);
  if (!f) return Response.json({ detail: "não encontrado" }, { status: 404 });
  const body = await req.json().catch(() => ({}));
  const respostas: Record<string, number> = {};
  for (const [k, v] of Object.entries(body?.respostas ?? {})) respostas[String(k)] = Number(v);
  return Response.json(evaluateQuiz(f, respostas));
}
