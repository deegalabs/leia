import { answer, findTask, publicGate, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/chat">) {
  const up = await viaService(req);
  if (up) return up;
  const { hash } = await params;
  const gate = publicGate(hash, userFromRequest(req)); /* LeIA: 409 while the lawyer reviews */
  if (gate) return gate;
  const f = findTask(hash);
  if (!f) return Response.json({ detail: "não encontrado" }, { status: 404 });
  const body = await req.json().catch(() => ({}));
  const text = answer(f, String(body?.mensagem ?? ""));
  const enc = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      for (let i = 0; i < text.length; i += 12) {
        controller.enqueue(enc.encode(`data: ${JSON.stringify({ t: text.slice(i, i + 12) })}\n\n`));
        await new Promise((r) => setTimeout(r, 20));
      }
      controller.close();
    },
  });
  return new Response(stream, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" } });
}
