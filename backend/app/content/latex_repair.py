"""Repair LaTeX mangled by JSON escaping in LLM output.

Models sometimes emit '"\\text{x}"' as "\text{x}" in raw JSON, where \t, \f,
\b, \r decode to control characters — so stored content contains TAB+"ext"
instead of \text and renders as a KaTeX error. Control characters followed by
a letter are unambiguously eaten LaTeX commands; newlines are only repaired
for commands whose remainders can't start English words.
"""

import re

_ALWAYS = {"\x08": "\\b", "\x0c": "\\f"}
_TAB_CR = re.compile(r"[\t\r](?=[a-zA-Z])")
_NEWLINE_CMDS = re.compile(r"\n(?=(?:abla|otin|ewline)\b|eq(?![a-zA-Z]))")

# Text-mode LaTeX that KaTeX doesn't support, with unambiguous math equivalents.
_TEXTSUB = re.compile(r"\\textsubscript\{([^{}]*)\}")
_TEXTSUP = re.compile(r"\\textsuperscript\{([^{}]*)\}")

# \bigl/\bigr (etc.) must precede a delimiter; models often glue them onto
# arbitrary commands. Dropping the size prefix preserves the math.
_DELIMS = r"[(){}\[\]|/.]|\\[{}|]|\\(?:l|r)?(?:vert|Vert)|\\[lr](?:brace|angle|ceil|floor|group|moustache)|\\backslash|\\(?:up|down|updown)arrow|\\(?:Up|Down|Updown)arrow"
_BAD_BIG = re.compile(r"\\[bB]igg?[lrm]?\s*(?!" + _DELIMS + r")(?=\\[a-zA-Z]|$)")


def _fix_display_fences(text: str) -> str:
    """remark-math only treats $$ as a display fence when it sits on its own
    line; models routinely write `$$\\begin{aligned}` or `...\\tag{1}$$` inline.
    Split such lines (skipping table rows, where line breaks would corrupt
    the table)."""
    out = []
    for line in text.split("\n"):
        stripped = line.strip()
        is_table_row = stripped.startswith("|") and stripped.endswith("|")
        if "$$" not in line or is_table_row or stripped == "$$":
            out.append(line)
            continue
        parts = line.split("$$")
        pieces = []
        for i, piece in enumerate(parts):
            if i:
                pieces.append("$$")
            if piece.strip():
                pieces.append(piece)
        out.extend(pieces)
    return "\n".join(out)


def repair(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    for ch, rep in _ALWAYS.items():
        text = text.replace(ch, rep)
    text = _TAB_CR.sub(lambda m: "\\" + ("t" if m.group(0) == "\t" else "r"), text)
    text = _NEWLINE_CMDS.sub(r"\\n", text)
    text = _TEXTSUB.sub(r"_{\\text{\1}}", text)
    text = _TEXTSUP.sub(r"^{\\text{\1}}", text)
    text = _BAD_BIG.sub("", text)
    return _fix_display_fences(text)


def repair_tree(obj):
    """Recursively repair every string in a decoded-JSON structure."""
    if isinstance(obj, str):
        return repair(obj)
    if isinstance(obj, list):
        return [repair_tree(v) for v in obj]
    if isinstance(obj, dict):
        return {k: repair_tree(v) for k, v in obj.items()}
    return obj
