import { createTask, listTasks, userFromRequest } from "@/lib/mock";

export async function GET(req: Request) {
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  return Response.json(listTasks(u));
}

/* multipart: titulo + pdf. The mock does not read the PDF; every task reuses the fixture content. */
export async function POST(req: Request) {
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  const form = await req.formData().catch(() => null);
  if (!form) return Response.json({ detail: "envie titulo e pdf" }, { status: 422 });
  const pdf = form.get("pdf");
  if (!(pdf instanceof File) || pdf.size === 0) return Response.json({ detail: "pdf obrigatório" }, { status: 422 });
  const titulo = String(form.get("titulo") ?? "").trim() || pdf.name.replace(/\.pdf$/i, "");
  return Response.json(createTask(u, titulo));
}
