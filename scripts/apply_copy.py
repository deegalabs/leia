#!/usr/bin/env python3
"""Apply the LeIA copy replacements to the service templates.

Usage: scripts/apply_copy.py <templates_dir> [--write]
Without --write it only reports how many replacements each file would get. Longer keys are applied first
so that "Para.AI · análise..." wins over "Para.AI".
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs" / "brand" / "copy-replacements.json"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = pathlib.Path(sys.argv[1])
    write = "--write" in sys.argv
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    pairs = sorted(table.items(), key=lambda kv: -len(kv[0]))
    total = 0
    for path in sorted(target.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        count = 0
        for old, new in pairs:
            n = text.count(old)
            if n:
                text = text.replace(old, new)
                count += n
        if count:
            print(f"{path.name}: {count} substituições")
            total += count
            if write:
                path.write_text(text, encoding="utf-8")
    print(f"total: {total} ({'gravado' if write else 'simulação, use --write'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
