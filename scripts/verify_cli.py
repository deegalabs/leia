#!/usr/bin/env python3
"""Recompute the LeIA registry hash from a canonical JSON file and compare with an expected value.

Usage: scripts/verify_cli.py payload.json <expected_sha256> [proof.ots]
Exit code 0 when the hash matches (and, if given, the .ots proof verifies via the `ots` CLI when available).
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    path, expected = pathlib.Path(sys.argv[1]), sys.argv[2].lower()
    raw = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(raw)
        canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except json.JSONDecodeError:
        print("arquivo não é JSON válido")
        return 1
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    print(f"sha256 calculado: {digest}")
    print(f"sha256 esperado:  {expected}")
    if digest != expected:
        print("NÃO CONFERE: o conteúdo mudou ou o JSON não está canônico")
        return 1
    print("CONFERE: o registro não mudou")
    if len(sys.argv) > 3:
        proof = pathlib.Path(sys.argv[3])
        if shutil.which("ots"):
            canonical_path = path.with_suffix(".canonical.json")
            canonical_path.write_text(canonical, encoding="utf-8")
            result = subprocess.run(["ots", "verify", "-f", str(canonical_path), str(proof)], capture_output=True, text=True)
            print(result.stdout or result.stderr)
            return result.returncode
        print("cliente `ots` não instalado: pip install opentimestamps-client")
    return 0


if __name__ == "__main__":
    sys.exit(main())
