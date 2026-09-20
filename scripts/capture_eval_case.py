#!/usr/bin/env python3
"""Record an evaluation case from a real pipeline run.

``evals/README.md`` says cases are recorded rather than generated, and it is right: running the pipeline
inside the battery would measure model, network and code at once, and a gate that needs the network is not a
gate. But nothing in the repository recorded them, so the only case drifted away from the engine it was
supposed to measure: by 17/09/2026 it was a capture of 15/09 failing floors that the engine had already been
taught to meet. A promise to re-record with no tool to re-record with is how a fixture becomes a relic.

What lands in the file is the public output, the same thing the two people see, because that is what the
battery measures. Everything else stays in the workspace.

    GROQ_API_KEY=... python scripts/capture_eval_case.py \
        --pdf examples/contrato-honorarios-exemplo.pdf \
        --name contrato-honorarios \
        --out apps/llm-service/evals/casos/contrato-honorarios.json

The document must be fictional. Real documents live outside the repository, under LEIA_EVAL_CASES.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import tempfile

SERVICE = pathlib.Path(__file__).resolve().parents[1] / "apps" / "llm-service"


def _public_output(client, hash_: str) -> dict:
    """The task as the citizen reads it, plus the inferences the lawyer reviews."""
    task = client.get(f"/api/t/{hash_}").json()
    inferences = client.get(f"/api/t/{hash_}/inferencias").json()
    return {
        "documento": inferences.get("texto") or inferences.get("documento") or "",
        "topicos": task.get("topicos") or [],
        "questoes": task.get("questoes") or [],
        "inferencias": {
            "classes": inferences.get("classes") or [],
            "sinteses": inferences.get("sinteses") or [],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True, help="fictional PDF to run through the pipeline")
    ap.add_argument("--name", required=True, help="case name, as it appears in the battery output")
    ap.add_argument("--out", required=True, help="where to write the case")
    ap.add_argument("--origin", default="tarefa de exemplo, documento fictício de examples/")
    args = ap.parse_args()

    if not os.getenv("GROQ_API_KEY"):
        print("GROQ_API_KEY ausente: a captura roda o motor de verdade e precisa da chave.", file=sys.stderr)
        return 2

    pdf = pathlib.Path(args.pdf).resolve()
    if not pdf.exists():
        print(f"não encontrei {pdf}", file=sys.stderr)
        return 2

    # A database of its own, thrown away at the end: recording a case must never touch anyone's data.
    tmp = tempfile.mkdtemp(prefix="leia-capture-")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/capture.db"
    os.environ["DATA_DIR"] = tmp
    os.environ["OTS_ENABLED"] = "false"
    sys.path.insert(0, str(SERVICE))

    from fastapi.testclient import TestClient
    import main as service

    client = TestClient(service.app)
    signup = client.post("/api/auth/cadastro", json={
        "nome": "Captura", "email": "captura@local", "senha": "captura-123", "papel": "cidadao",
    })
    signup.raise_for_status()
    token = signup.json()["token"]

    created = client.post(
        "/api/tarefas",
        data={"titulo": args.name},
        files={"pdf": (pdf.name, pdf.read_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    created.raise_for_status()
    task = created.json()

    # TestClient runs BackgroundTasks before the response returns, so POST /api/tarefas already ran the
    # pipeline once. Calling it again here would run a second round over the same task and race with itself.
    print(f"o motor rodou em {pdf.name} durante o envio")

    status = client.get(f"/api/t/{task['hash']}").json().get("tarefa", {}).get("status")
    if status != "pronta":
        print(f"a tarefa terminou como {status!r}, não como 'pronta'. Nada foi gravado.", file=sys.stderr)
        print("Se a porta de qualidade reprovou, o caso não deve ser gravado: o motor é que precisa passar.",
              file=sys.stderr)
        return 1

    case = {
        "nome": args.name,
        "origem": args.origin,
        "capturado_em": dt.date.today().isoformat(),
        **_public_output(client, task["hash"]),
    }
    out = pathlib.Path(args.out).resolve()
    out.write_text(json.dumps(case, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"gravado em {out}")
    print(f"  {len(case['topicos'])} tópicos, {len(case['questoes'])} perguntas, "
          f"{len(case['inferencias']['sinteses'])} sínteses, {len(case['documento'])} caracteres de documento")
    print("agora rode: cd apps/llm-service && python -m evals.run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
