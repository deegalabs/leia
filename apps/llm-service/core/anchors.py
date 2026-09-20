"""Where a literal quote really is inside the document text.

This is the only source of a position in the service. It lives in its own module because everything that
claims fidelity depends on it: the checked excerpt the citizen reads beside the explanation, the synthesis
that has to point at a memory item, the section that only gets published when something in it was found, and
the quality gate that measures all of that before a task is called ready.

``norm_map`` and ``find_span`` are the whitespace-insensitive stage of ``locate`` and are exported because a
caller that checks many quotes against the same document builds the map once.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Optional

MIN_QUOTE_CHARS = 12
ANCHOR_MIN_SCORE = 0.82


def norm_map(text: str) -> tuple[str, list[int]]:
    """Whitespace-collapsed copy of the text plus a map from each collapsed char to its original offset."""
    out: list[str] = []
    idx: list[int] = []
    prev_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                out.append(" ")
                idx.append(i)
            prev_space = True
        else:
            out.append(ch)
            idx.append(i)
            prev_space = False
    return "".join(out), idx


def find_span(text_norm: str, idx: list[int], quote: str) -> Optional[list[int]]:
    q = " ".join((quote or "").split())
    if len(q) < 3:
        return None
    pos = text_norm.find(q)
    if pos < 0:
        pos = text_norm.lower().find(q.lower())
        if pos < 0:
            return None
    return [idx[pos], idx[pos + len(q) - 1] + 1]


def _approximate(text_norm: str, q: str) -> tuple[float, Optional[tuple[int, int]]]:
    """Best window of the text that resembles the quote, anchored on pieces of the quote itself.

    Bounded on purpose: a handful of seeds, and only where a seed actually occurs. Comparing the quote against
    every offset of a long document would cost more than the whole pipeline."""
    if len(q) < 24:
        return 0.0, None
    best_score, best_span = 0.0, None
    step = max(8, len(q) // 6)
    for off in range(0, len(q) - 12, step):
        seed = q[off:off + 12]
        pos = text_norm.find(seed)
        while pos >= 0:
            ini = max(0, pos - off)
            fim = min(len(text_norm), ini + len(q))
            score = SequenceMatcher(None, text_norm[ini:fim], q, autojunk=False).ratio()
            if score > best_score:
                best_score, best_span = score, (ini, fim)
            pos = text_norm.find(seed, pos + 1)
    return best_score, best_span


def _snap_to_word_edges(text_norm: str, a: int, b: int) -> tuple[int, int]:
    """Empurra as bordas da janela para fora, até o espaço mais próximo, para nunca cortar uma palavra."""
    while a > 0 and not text_norm[a - 1].isspace():
        a -= 1
    while b < len(text_norm) and not text_norm[b - 1].isspace():
        b += 1
    return a, min(b, len(text_norm))


def locate(texto: str, text_norm: str, idx: list[int], quote: str) -> Optional[dict[str, Any]]:
    """Where the quote really is in the document, found here and never taken from the model.

    A language model does not count characters, so the position it writes is a guess dressed as a fact. It can
    look perfectly valid and point at the wrong clause, or at a clause for a quote that was invented outright.
    Believing it turns the "checked excerpt" seal, which is the promise this product is built on, into
    decoration. So the three stages below are the only source of a position: exact, then with whitespace and
    case collapsed, then approximate above a threshold.
    """
    q_raw = (quote or "").strip()
    if len(q_raw) < MIN_QUOTE_CHARS:
        return None

    pos = (texto or "").find(q_raw)
    if pos >= 0:
        return {"pos": [pos, pos + len(q_raw)], "score": 1.0, "metodo": "exato"}

    q = " ".join(q_raw.split())
    span = find_span(text_norm, idx, q)
    if span:
        return {"pos": span, "score": 1.0, "metodo": "normalizado"}

    score, window = _approximate(text_norm, q)
    if window and score >= ANCHOR_MIN_SCORE:
        a, b = window
        b = min(b, len(idx))
        if b > a:
            # A janela do estágio aproximado é achada por semelhança e cai onde cair, inclusive no meio de
            # um número: cortar "17.11.2014" em "17.11.201" mostra à pessoa um trecho que o documento não
            # tem. Como o trecho publicado é a fatia desta posição, a borda precisa cair entre palavras.
            a, b = _snap_to_word_edges(text_norm, a, b)
            return {"pos": [idx[a], idx[b - 1] + 1], "score": round(score, 3), "metodo": "aproximado"}
    return None
