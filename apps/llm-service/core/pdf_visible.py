"""Keeps only the text a person can actually see on the page.

``page.extract_text()`` hands over everything the content stream draws, including what the PDF hides on
purpose: text in render mode 3, text painted in the colour of the background and text parked outside the
CropBox. That text reaches the model as document content, so a crafted file can dictate the explanation the
citizen reads. Here the content stream is walked operator by operator, the text-showing operators that paint
nothing visible are dropped, and pypdf extracts what is left.

Scope: the operators of the page content stream. Text drawn inside a Form XObject (``Do``) is not inspected,
and neither is transparency set through ``gs``.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Optional

from pypdf.generic import ContentStream, NameObject

# Render modes 3 and 7 paint no glyph at all: 3 is the plain invisible mode, 7 only adds to the clip path.
INVISIBLE_MODES = frozenset({3, 7})
STROKE_ONLY_MODES = frozenset({1, 5})
TEXT_SHOWING_OPS = frozenset({b"Tj", b"TJ", b"'", b'"'})
FILL_PAINT_OPS = frozenset({b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"})
PATH_END_OPS = FILL_PAINT_OPS | frozenset({b"S", b"s", b"n"})
DEVICE_SPACES = frozenset({"/DeviceGray", "/DeviceRGB", "/DeviceCMYK", "/G", "/RGB", "/CMYK"})

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
WHITE = (1.0, 1.0, 1.0)
BLACK = (0.0, 0.0, 0.0)
# #FEFEFE on white is as hidden as #FFFFFF, so the comparison has room instead of asking for equality.
COLOR_TOLERANCE = 0.05
# The origin of a run sitting a couple of points past the edge is still readable; a hidden run is far away.
OUTSIDE_TOLERANCE_PT = 2.0
# A rectangle has to cover almost the whole page before it counts as the background behind the text.
BACKGROUND_COVERAGE = 0.95


@dataclass(frozen=True)
class VisibleText:
    """Text the page really shows, plus how much was dropped on the way."""

    text: str
    hidden_chars: int
    hidden_runs: int


@dataclass(frozen=True)
class _GraphicsState:
    ctm: tuple[float, ...] = IDENTITY
    fill: Optional[tuple[float, float, float]] = BLACK
    stroke: Optional[tuple[float, float, float]] = BLACK
    fill_space: Optional[str] = None
    stroke_space: Optional[str] = None
    render_mode: int = 0
    leading: float = 0.0


def visible_text(page: Any) -> VisibleText:
    """Extract the page text without what the page hides.

    The page object is rewritten in memory when something is dropped, never on disk: pypdf then extracts from
    the pruned stream and keeps its own font and layout handling, which reimplementing here would lose.
    """
    owner = getattr(page, "pdf", None)
    content = ContentStream(page.get("/Contents"), owner)
    crop = _crop_bounds(page)

    state = _GraphicsState()
    stack: list[_GraphicsState] = []
    background = WHITE
    pending_rects: list[tuple[float, float, float, float]] = []
    text_matrix = IDENTITY
    line_matrix = IDENTITY
    kept: list[tuple[list[Any], bytes]] = []
    hidden_chars = 0
    hidden_runs = 0

    for operands, operator in content.operations:
        if operator == b"q":
            stack.append(state)
        elif operator == b"Q":
            state = stack.pop() if stack else _GraphicsState()
        elif operator == b"cm":
            state = replace(state, ctm=_multiply(_matrix(operands), state.ctm))
        elif operator == b"BT":
            text_matrix = line_matrix = IDENTITY
        elif operator == b"Tm":
            text_matrix = line_matrix = _matrix(operands)
        elif operator in (b"Td", b"TD"):
            tx, ty = _number(operands, 0), _number(operands, 1)
            if operator == b"TD":
                state = replace(state, leading=-ty)
            line_matrix = _multiply((1.0, 0.0, 0.0, 1.0, tx, ty), line_matrix)
            text_matrix = line_matrix
        elif operator == b"TL":
            state = replace(state, leading=_number(operands, 0))
        elif operator == b"T*":
            line_matrix = _multiply((1.0, 0.0, 0.0, 1.0, 0.0, -state.leading), line_matrix)
            text_matrix = line_matrix
        elif operator == b"Tr":
            state = replace(state, render_mode=int(_number(operands, 0)))
        elif operator in (b"g", b"rg", b"k", b"cs", b"sc", b"scn"):
            state = _with_fill(state, operator, operands)
        elif operator in (b"G", b"RG", b"K", b"CS", b"SC", b"SCN"):
            state = _with_stroke(state, operator, operands)
        elif operator == b"re":
            pending_rects.append(_device_rect(operands, state.ctm))
        elif operator in PATH_END_OPS:
            if operator in FILL_PAINT_OPS and state.fill is not None:
                if any(_covers(rect, crop) for rect in pending_rects):
                    background = state.fill
            pending_rects = []

        if operator in (b"'", b'"'):
            line_matrix = _multiply((1.0, 0.0, 0.0, 1.0, 0.0, -state.leading), line_matrix)
            text_matrix = line_matrix

        if operator in TEXT_SHOWING_OPS and not _is_visible(state, text_matrix, crop, background):
            hidden_runs += 1
            hidden_chars += _shown_length(operator, operands)
            continue

        kept.append((operands, operator))

    if not hidden_runs:
        return VisibleText(page.extract_text() or "", 0, 0)

    pruned = ContentStream(None, owner)
    pruned.operations = kept
    page[NameObject("/Contents")] = pruned
    return VisibleText(page.extract_text() or "", hidden_chars, hidden_runs)


def _is_visible(state: _GraphicsState, text_matrix: tuple[float, ...],
                crop: tuple[float, float, float, float], background: tuple[float, float, float]) -> bool:
    if state.render_mode in INVISIBLE_MODES:
        return False
    x, y = _origin(text_matrix, state.ctm)
    if not (crop[0] - OUTSIDE_TOLERANCE_PT <= x <= crop[2] + OUTSIDE_TOLERANCE_PT
            and crop[1] - OUTSIDE_TOLERANCE_PT <= y <= crop[3] + OUTSIDE_TOLERANCE_PT):
        return False
    ink = state.stroke if state.render_mode in STROKE_ONLY_MODES else state.fill
    # An unresolved colour space says nothing about visibility, and dropping on a guess erases real clauses.
    if ink is not None and _same_color(ink, background):
        return False
    return True


def _crop_bounds(page: Any) -> tuple[float, float, float, float]:
    box = page.cropbox
    left, right = sorted((float(box.left), float(box.right)))
    bottom, top = sorted((float(box.bottom), float(box.top)))
    return left, bottom, right, top


def _matrix(operands: list[Any]) -> tuple[float, ...]:
    return tuple(_number(operands, i, 1.0 if i in (0, 3) else 0.0) for i in range(6))


def _number(operands: list[Any], index: int, default: float = 0.0) -> float:
    try:
        return float(operands[index])
    except (IndexError, TypeError, ValueError):
        return default


def _multiply(m: tuple[float, ...], n: tuple[float, ...]) -> tuple[float, ...]:
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2,
            c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)


def _origin(text_matrix: tuple[float, ...], ctm: tuple[float, ...]) -> tuple[float, float]:
    combined = _multiply(text_matrix, ctm)
    return combined[4], combined[5]


def _device_rect(operands: list[Any], ctm: tuple[float, ...]) -> tuple[float, float, float, float]:
    x, y = _number(operands, 0), _number(operands, 1)
    w, h = _number(operands, 2), _number(operands, 3)
    corners = [_origin((1.0, 0.0, 0.0, 1.0, x + dx, y + dy), ctm) for dx, dy in ((0, 0), (w, 0), (0, h), (w, h))]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    return min(xs), min(ys), max(xs), max(ys)


def _covers(rect: tuple[float, float, float, float], crop: tuple[float, float, float, float]) -> bool:
    area = (crop[2] - crop[0]) * (crop[3] - crop[1])
    if area <= 0:
        return False
    overlap_x = max(0.0, min(rect[2], crop[2]) - max(rect[0], crop[0]))
    overlap_y = max(0.0, min(rect[3], crop[3]) - max(rect[1], crop[1]))
    return (overlap_x * overlap_y) / area >= BACKGROUND_COVERAGE


def _same_color(a: tuple[float, float, float], b: tuple[float, float, float]) -> bool:
    return all(abs(x - y) <= COLOR_TOLERANCE for x, y in zip(a, b))


def _with_fill(state: _GraphicsState, operator: bytes, operands: list[Any]) -> _GraphicsState:
    if operator == b"cs":
        return replace(state, fill_space=_space_name(operands))
    return replace(state, fill=_color(operator, operands, state.fill_space))


def _with_stroke(state: _GraphicsState, operator: bytes, operands: list[Any]) -> _GraphicsState:
    if operator == b"CS":
        return replace(state, stroke_space=_space_name(operands))
    return replace(state, stroke=_color(operator.lower(), operands, state.stroke_space))


def _space_name(operands: list[Any]) -> Optional[str]:
    return str(operands[0]) if operands else None


def _color(operator: bytes, operands: list[Any],
           space: Optional[str]) -> Optional[tuple[float, float, float]]:
    if operator == b"g":
        return _gray(_number(operands, 0))
    if operator == b"rg":
        return (_number(operands, 0), _number(operands, 1), _number(operands, 2))
    if operator == b"k":
        return _cmyk(operands)
    # sc/scn: a named pattern or a colour space this module cannot resolve leaves the colour unknown.
    if space is not None and space not in DEVICE_SPACES:
        return None
    numbers = [o for o in operands if isinstance(o, (int, float)) and not isinstance(o, bool)]
    if len(numbers) != len(operands):
        return None
    if len(numbers) == 1:
        return _gray(float(numbers[0]))
    if len(numbers) == 3:
        return (float(numbers[0]), float(numbers[1]), float(numbers[2]))
    if len(numbers) == 4:
        return _cmyk(operands)
    return None


def _gray(value: float) -> tuple[float, float, float]:
    return (value, value, value)


def _cmyk(operands: list[Any]) -> tuple[float, float, float]:
    c, m, y, k = (_number(operands, i) for i in range(4))
    return ((1.0 - c) * (1.0 - k), (1.0 - m) * (1.0 - k), (1.0 - y) * (1.0 - k))


def _shown_length(operator: bytes, operands: list[Any]) -> int:
    if operator == b"TJ":
        items = operands[0] if operands else []
        return sum(len(item) for item in items if isinstance(item, (str, bytes)))
    index = 2 if operator == b'"' else 0
    if len(operands) > index and isinstance(operands[index], (str, bytes)):
        return len(operands[index])
    return 0
