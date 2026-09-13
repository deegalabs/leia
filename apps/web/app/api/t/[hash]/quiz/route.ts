import { evaluateQuiz, findTask, nextAttemptNumber, recordAttempt } from "@/lib/mock";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/quiz">) {
  const { hash } = await params;
  const f = findTask(hash);
  if (!f) return Response.json({ detail: "não encontrado" }, { status: 404 });
  const body = await req.json().catch(() => ({}));
  const respostas: Record<string, number> = {};
  for (const [k, v] of Object.entries(body?.respostas ?? {})) respostas[String(k)] = Number(v);
  /* LeIA: v3 keeps the attempt on the task so the panels can show it */
  const result = evaluateQuiz(f, respostas, nextAttemptNumber(hash));
  recordAttempt(hash, result);
  return Response.json(result);
}
