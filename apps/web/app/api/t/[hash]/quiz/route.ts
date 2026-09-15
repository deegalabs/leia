import { evaluateQuiz, findTask, nextAttemptNumber, publicGate, recordAttempt, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/quiz">) {
  const up = await viaService(req);
  if (up) return up;
  const { hash } = await params;
  const gate = publicGate(hash, userFromRequest(req)); /* LeIA: 409 while the lawyer reviews */
  if (gate) return gate;
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
