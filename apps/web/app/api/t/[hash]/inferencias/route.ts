import fixture from "@/data/fixture-honorarios.json";
import { storeTask } from "@/lib/mock";
import { findSpan, type Inferences } from "@/lib/inferences";

/* Mock: the fixture's clauses become tagged items over the extracted text. */
export async function GET(_req: Request, { params }: RouteContext<"/api/t/[hash]/inferencias">) {
  const { hash } = await params;
  const t = storeTask(hash);
  if (!t) return Response.json({ detail: "não encontrado" }, { status: 404 });
  const texto = fixture.documento_texto.map((c) => c.texto).join("\n\n");
  const itens = fixture.topicos.map((tp, n) => {
    const pos = findSpan(texto, tp.trecho);
    return { ref: `clausulas[${n}]`, campo: `cláusula ${tp.clausula}`, valor: tp.titulo, trecho: tp.trecho, pos, conferido: !!pos, cor: "#E3F1F1" };
  });
  const body: Inferences = {
    tarefa: { hash, titulo: t.titulo },
    texto,
    classes: [{ classe: "clausulas", rotulo: "Cláusulas explicadas", cor: "#E3F1F1", itens }],
    sinteses: fixture.topicos.map((tp, n) => ({ classe: "clausulas", rotulo: tp.titulo, texto: tp.explicacao, lastro: [`clausulas[${n}]`] })),
    total: itens.length, conferidos: itens.filter((i) => i.conferido).length,
  };
  return Response.json(body);
}
