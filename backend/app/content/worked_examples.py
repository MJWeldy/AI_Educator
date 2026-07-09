"""Normalize a lesson's ``worked_examples`` into a clean ``list[dict]``.

An LLM occasionally emits the whole ``worked_examples`` array as a single
JSON-encoded *string* rather than a list, and that string is sometimes itself
invalid JSON (unescaped inner quotes, literal newlines). Stored verbatim, such a
value crashes every reader that does ``WorkedExample(**ex)``. This module
coerces whatever was stored back into a list of ``{problem_md, solution_md}``
dicts, salvaging the content when possible and dropping what it cannot parse.
"""

import json


def _repair_json_string(s: str) -> str:
    """Best-effort fix for JSON that has unescaped ``"`` and raw control
    characters inside string values (a common LLM failure mode). A quote is
    treated as a real delimiter only when the next non-space char is structural
    (``,:}]``); otherwise it is escaped."""
    out: list[str] = []
    in_str = False
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\" and in_str:
            out.append(c)
            if i + 1 < n:
                out.append(s[i + 1])
                i += 2
                continue
            i += 1
            continue
        if c == '"':
            if not in_str:
                in_str = True
                out.append(c)
                i += 1
                continue
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j >= n or s[j] in ",:}]":
                in_str = False
                out.append(c)
                i += 1
                continue
            out.append('\\"')
            i += 1
            continue
        if in_str and c in "\n\r\t":
            out.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[c])
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _coerce_to_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        for candidate in (value, _repair_json_string(value)):
            try:
                parsed = json.loads(candidate)
            except (ValueError, TypeError):
                continue
            if isinstance(parsed, list):
                return parsed
    return []


def normalize_worked_examples(value) -> list[dict]:
    """Return only valid ``{problem_md, solution_md}`` examples, salvaging a
    stringified/malformed value where possible."""
    return [
        {"problem_md": str(ex["problem_md"]), "solution_md": str(ex["solution_md"])}
        for ex in _coerce_to_list(value)
        if isinstance(ex, dict) and ex.get("problem_md") and ex.get("solution_md")
    ]
