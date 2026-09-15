/* The OpenTimestamps proof, so a third party can check the receipt without this app or the service.
   The mock has no real stamp, so there is nothing to download without a service behind it. */
import { viaService } from "@/lib/server/service";

export async function GET(req: Request, { params }: RouteContext<"/api/verify/[attempt]/proof">) {
  const { attempt } = await params;
  const up = await viaService(req, `/verify/${encodeURIComponent(attempt)}/proof.ots`);
  if (up) {
    if (!up.headers.has("content-disposition")) {
      up.headers.set("content-disposition", `attachment; filename="${attempt.slice(0, 12)}.ots"`);
    }
    return up;
  }
  return Response.json({ detail: "carimbo indisponível na demonstração" }, { status: 404 });
}
