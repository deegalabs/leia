"""What kind of document this is, decided before anything is extracted from it.

The workflow asks the same fourteen questions of every document, and five of those questions carry a closed
vocabulary borrowed from a court filing. Measured on 20/09/2026 over the two recorded cases: in the fee
contract the ``campo`` of T1 came back as ``autor`` for the CONTRATANTE, because the enum the model received
has no word for a party to a contract. ``campo`` is what the app prints in bold over the marked text, so the
person reads "autor: CONTRATANTE" in a document that has no autor.

So the type is read first and it chooses the vocabulary. Three properties hold it together:

* **It is a claim about the document, so it carries a quote of the document.** Same rule as every other
  claim in the product: the position comes from ``anchors.locate`` and the excerpt is the slice at that
  position, never the model's transcript.
* **It can never fail the run.** Before this step existed the document was explained; a new step able to kill
  the task would be a regression for whoever only wants to understand their own paper. An unreadable or
  invented type becomes ``indefinido``, which is exactly today's vocabulary.
* **A human outranks it.** The lawyer corrects the type, the correction is written beside the document and
  survives ``reprocessar``, and the next run skips the classification and obeys. A wrong classification the
  person can see and fix is cheap; a silent one is the failure this product exists not to have.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.anchors import locate, norm_map

INDEFINIDO = "indefinido"
ARQUIVO_PUBLICO = "tipo_documento.json"
"""What the two screens read: the type this run worked with, written every run. Derived, so ``reprocessar``
throws it away with the rest."""
ARQUIVO_REVISADO = "tipo_documento_revisado.json"
"""The lawyer's answer, which is the opposite: it is an input, not a result. Named so it cannot be taken for
``T0_TIPO_DOCUMENTO.json`` nor for the file above, because ``reprocessar`` wipes every ``T*.json`` and every
derived artifact to redo the run, and this one is precisely what has to outlive that."""

_TIPOS: Optional[dict[str, dict[str, Any]]] = None


def _protocolo() -> dict[str, Any]:
    # Imported inside the function, as ``section_sources`` does: the protocol belongs to the pipeline, and
    # the pipeline asks this module for the vocabulary, so the import cannot go the other way at load time.
    from core.pipeline_pdf import PROTOCOLO_PDF

    return json.loads(Path(PROTOCOLO_PDF).read_text(encoding="utf-8"))


def tipos(protocolo: Optional[dict[str, Any]] = None) -> dict[str, dict[str, Any]]:
    """The closed set, as the protocol declares it. Read once and kept, like the section map."""
    global _TIPOS
    if protocolo is not None:
        return {k: v for k, v in (protocolo.get("tipos_de_documento") or {}).items()}
    if _TIPOS is None:
        try:
            _TIPOS = {k: v for k, v in (_protocolo().get("tipos_de_documento") or {}).items()}
        except Exception:
            _TIPOS = {}
    return _TIPOS


def normalize(tipo: Any, protocolo: Optional[dict[str, Any]] = None) -> str:
    """The type, or ``indefinido`` when it is not one of the declared ones.

    The model writes this field in free text and what leaves here picks the vocabulary of five extraction
    steps, so a word nobody declared must not reach them under the appearance of a decision."""
    nome = str(tipo or "").strip().lower()
    return nome if nome in tipos(protocolo) else INDEFINIDO


def label(tipo: str, protocolo: Optional[dict[str, Any]] = None) -> str:
    """What the two people read on screen, in plain pt-BR."""
    return str((tipos(protocolo).get(normalize(tipo, protocolo)) or {}).get("rotulo") or "Tipo não identificado")


def expected_classes(tipo: str, protocolo: Optional[dict[str, Any]] = None) -> list[str]:
    """Which classes of memory a document of this kind is supposed to sustain.

    A fee contract has no pedidos and cites no law, and today those two empty classes look exactly like a
    step that failed. This list is what tells them apart, and it only ever feeds a report: the quality gate
    keeps judging what reaches the screen, never what the protocol asked for."""
    return [str(c) for c in ((tipos(protocolo).get(normalize(tipo, protocolo)) or {}).get("classes_esperadas") or [])]


def missing_classes(tipo: str, presentes: list[str], protocolo: Optional[dict[str, Any]] = None) -> list[str]:
    """What this kind of document promises and this run did not produce."""
    tem = {str(c) for c in presentes or []}
    return [c for c in expected_classes(tipo, protocolo) if c not in tem]


def read(parsed: Any, texto: str, text_norm: str, idx: list[int],
         protocolo: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """The classification as it will be shown and used: type, label, and the quote that sustains it.

    ``conferido`` says whether the quote was found in the document. It does not gate the type: the kind of a
    document is a judgement about the whole of it, and refusing the judgement because one sentence was
    paraphrased would trade a useful answer for a missing one. It gives the lawyer something to check in one
    glance, which is the whole point of showing it."""
    bruto = parsed if isinstance(parsed, dict) else {}
    tipo = normalize(bruto.get("tipo"), protocolo)
    quote = str(bruto.get("trecho_verbatim") or "")
    found = locate(texto or "", text_norm, idx, quote) if quote else None
    return {
        "tipo": tipo,
        "rotulo": label(tipo, protocolo),
        # The slice of the document at that position, never the model's transcript: same rule as every other
        # excerpt the product publishes.
        "trecho": (texto[found["pos"][0]:found["pos"][1]] if found else ""),
        "pos": found["pos"] if found else None,
        "conferido": bool(found),
        "revisado_por_advogado": False,
    }


def from_review(revisado: dict[str, Any]) -> dict[str, Any]:
    """The same shape, when the answer came from a person instead of from the model.

    There is no quote here on purpose: a person deciding what kind of document this is does not owe the
    document a sentence, and inventing one would be the product doing exactly what it forbids the model."""
    tipo = normalize((revisado or {}).get("tipo"))
    return {"tipo": tipo, "rotulo": label(tipo), "trecho": "", "pos": None,
            "conferido": False, "revisado_por_advogado": True}


def current(hash_: str) -> Optional[dict[str, Any]]:
    """The type this document was worked with, as the screens show it, or ``None`` before the first run."""
    try:
        doc = json.loads((_folder(hash_) / ARQUIVO_PUBLICO).read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) and doc.get("tipo") else None


def read_text(parsed: Any, texto: str, protocolo: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """``read`` for a caller that has only the document text at hand."""
    text_norm, idx = norm_map(texto or "")
    return read(parsed, texto or "", text_norm, idx, protocolo)


def catalog(protocolo: Optional[dict[str, Any]] = None) -> list[dict[str, str]]:
    """The choices a reviewer may pick from, in the order the protocol declares them."""
    return [{"tipo": k, "rotulo": str(v.get("rotulo") or k)} for k, v in tipos(protocolo).items()]


def public(hash_: str) -> Optional[dict[str, Any]]:
    """What the two screens show about the species of this document.

    Once a person has answered, their answer is what is shown, and ``aplicado`` says whether the explanation
    on screen was actually produced with it. The pair matters: a correction that shows up instantly while the
    text next to it still came from the old vocabulary would be the screen claiming a repair that has not
    happened."""
    atual = current(hash_)
    revisado = saved(hash_)
    if revisado:
        aplicado = bool(atual and atual.get("revisado_por_advogado") and atual.get("tipo") == revisado["tipo"])
        return {**from_review(revisado), "aplicado": aplicado}
    return {**atual, "aplicado": True} if atual else None


def vocabulary(task: dict[str, Any], tipo: str, protocolo: Optional[dict[str, Any]] = None) -> str:
    """The block of the mission that changes with the kind of document, or "" when the step has none.

    A step declares ``vocabulario_por_tipo`` with one entry per type plus ``_padrao``, and marks with
    ``{{VOCABULARIO}}`` where it goes. ``_padrao`` is word for word what every document received before this
    existed, so a type nobody recognized keeps behaving exactly as today."""
    por_tipo = task.get("vocabulario_por_tipo")
    if not isinstance(por_tipo, dict):
        return ""
    return str(por_tipo.get(normalize(tipo, protocolo)) or por_tipo.get("_padrao") or "")


# ── a correção do advogado, que manda na próxima rodada ──────────────────────

def _folder(hash_: str) -> Path:
    from core.workspace import folder

    return folder(hash_)


def _path(hash_: str) -> Path:
    return _folder(hash_) / ARQUIVO_REVISADO


def saved(hash_: str) -> Optional[dict[str, Any]]:
    """The reviewed type of this document, or ``None`` when nobody corrected it."""
    try:
        doc = json.loads(_path(hash_).read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) and doc.get("tipo") else None


def save_correction(hash_: str, tipo: str, por: Optional[int] = None) -> dict[str, Any]:
    """Writes the correction beside the document. Raises ``ValueError`` for a type nobody declared."""
    nome = str(tipo or "").strip().lower()
    if nome not in tipos():
        raise ValueError(f"tipo desconhecido: {tipo!r}")
    doc = {"tipo": nome, "rotulo": label(nome), "revisado_por": por,
           "revisado_em": datetime.now(timezone.utc).isoformat()}
    _path(hash_).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
