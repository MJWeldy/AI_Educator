"""Answer checking.

Numeric and fraction answers are checked exactly (via Fraction), multiple
choice by index, and free-form expressions via sympy equivalence — run in a
worker process with a hard timeout, since sympy can occasionally hang.
Expression input is sanitized to a strict token whitelist before it ever
reaches sympy's parser (which uses eval under the hood).
"""

import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from fractions import Fraction

EXPR_TIMEOUT_S = 2.0
ALLOWED_NAMES = {"x", "y", "a", "b", "n", "t", "pi", "sqrt"}
_TOKEN_RE = re.compile(r"[A-Za-z_]+")
_SAFE_RE = re.compile(r"^[0-9A-Za-z_+\-*/^().\s]+$")

WARMUP_TIMEOUT_S = 30.0

_pool: ProcessPoolExecutor | None = None
_warmup = None


def _import_sympy() -> None:
    import sympy  # noqa: F401


def _get_pool() -> ProcessPoolExecutor:
    global _pool, _warmup
    if _pool is None:
        # "spawn", never fork: a forked worker inherits the server's listening
        # socket and can steal (then never read) incoming HTTP connections,
        # freezing those requests forever.
        _pool = ProcessPoolExecutor(
            max_workers=1, mp_context=multiprocessing.get_context("spawn")
        )
        # Pre-import sympy in the worker so real checks don't spend their
        # EXPR_TIMEOUT_S budget on interpreter + sympy startup.
        _warmup = _pool.submit(_import_sympy)
    return _pool


def warm_pool() -> None:
    """Start the worker ahead of time (called once at app startup)."""
    _get_pool()


def _submit(fn, *args):
    """Submit to a warmed-up worker, so task timeouts measure only the task."""
    pool = _get_pool()
    if _warmup is not None and not _warmup.done():
        _warmup.result(timeout=WARMUP_TIMEOUT_S)
    return pool.submit(fn, *args)


def _kill_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


def sanitize_expression(s: str) -> str | None:
    """Return a cleaned expression, or None if it contains anything unsafe."""
    s = s.strip()
    if not s or len(s) > 200 or not _SAFE_RE.match(s):
        return None
    for name in _TOKEN_RE.findall(s):
        if name not in ALLOWED_NAMES:
            return None
    return s


def _expr_check(user: str, canonical: str) -> tuple[bool, str | None]:
    """Runs inside the worker process."""
    import sympy
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )

    transformations = standard_transformations + (
        implicit_multiplication_application,
        convert_xor,
    )
    local = {name: sympy.Symbol(name) for name in ("x", "y", "a", "b", "n", "t")}
    local["pi"] = sympy.pi
    local["sqrt"] = sympy.sqrt

    try:
        user_expr = parse_expr(user, transformations=transformations, local_dict=local)
        canon_expr = parse_expr(canonical, transformations=transformations, local_dict=local)
    except Exception:
        return False, "could not interpret that expression"

    if sympy.simplify(user_expr - canon_expr) != 0:
        return False, None

    # Enforce fully simplified form: parsing without evaluation exposes
    # uncombined terms (3x + 4x has more operations than 7x).
    try:
        user_raw = parse_expr(
            user, transformations=transformations, local_dict=local, evaluate=False
        )
        canon_raw = parse_expr(
            canonical, transformations=transformations, local_dict=local, evaluate=False
        )
        if sympy.count_ops(user_raw) > sympy.count_ops(canon_raw) + 1:
            return False, "equivalent, but not fully simplified — combine your terms"
    except Exception:
        pass
    return True, None


def _expr_latex(expr: str) -> str | None:
    import sympy
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )

    transformations = standard_transformations + (
        implicit_multiplication_application,
        convert_xor,
    )
    local = {name: sympy.Symbol(name) for name in ("x", "y", "a", "b", "n", "t")}
    local["pi"] = sympy.pi
    local["sqrt"] = sympy.sqrt
    try:
        parsed = parse_expr(expr, transformations=transformations, local_dict=local, evaluate=False)
        return sympy.latex(parsed)
    except Exception:
        return None


def check_expression(user: str, canonical: str) -> tuple[bool, str | None]:
    clean = sanitize_expression(user)
    if clean is None:
        return False, "only numbers, x/y variables, + - * / ^ and sqrt() are allowed"
    try:
        fut = _submit(_expr_check, clean, canonical)
        return fut.result(timeout=EXPR_TIMEOUT_S)
    except FutureTimeout:
        _kill_pool()
        return False, "that expression took too long to interpret"
    except Exception:
        _kill_pool()
        return False, "could not interpret that expression"


def preview_latex(expr: str) -> str | None:
    clean = sanitize_expression(expr)
    if clean is None:
        return None
    try:
        fut = _submit(_expr_latex, clean)
        return fut.result(timeout=EXPR_TIMEOUT_S)
    except Exception:
        _kill_pool()
        return None


def parse_number(s: str) -> Fraction | None:
    """Parse '7', '-2.5', '3/4', '1 3/4' into an exact Fraction."""
    s = s.strip().replace(",", "")
    mixed = re.match(r"^(-?\d+)\s+(\d+)\s*/\s*(\d+)$", s)
    if mixed:
        whole, n, d = int(mixed.group(1)), int(mixed.group(2)), int(mixed.group(3))
        if d == 0:
            return None
        sign = -1 if whole < 0 else 1
        return Fraction(whole) + sign * Fraction(n, d)
    frac = re.match(r"^(-?\d+)\s*/\s*(-?\d+)$", s)
    if frac:
        n, d = int(frac.group(1)), int(frac.group(2))
        if d == 0:
            return None
        return Fraction(n, d)
    try:
        return Fraction(s)  # handles ints and decimal strings exactly
    except (ValueError, ZeroDivisionError):
        return None


def check_part(part: dict, user_answer: str) -> tuple[bool, str | None]:
    """Returns (correct, feedback). Feedback explains *input* problems, not math."""
    answer_type = part["answer_type"]
    canonical = str(part["canonical"])
    user_answer = (user_answer or "").strip()
    if not user_answer:
        return False, "no answer given"

    if answer_type == "multiple_choice":
        return user_answer == canonical, None

    if answer_type == "exact_string":
        return user_answer.casefold() == canonical.casefold(), None

    if answer_type == "numeric":
        value = parse_number(user_answer)
        if value is None:
            return False, "enter a number (decimals and fractions like 3/4 are fine)"
        target = parse_number(canonical)
        tolerance = part.get("tolerance")
        if tolerance:
            return abs(float(value) - float(target)) <= tolerance, None
        return value == target, None

    if answer_type == "fraction_lowest":
        value = parse_number(user_answer)
        if value is None:
            return False, "enter a fraction like 3/4 (or a whole number)"
        target = parse_number(canonical)
        if value != target:
            return False, None
        # Fraction() reduces automatically, so re-read the raw numerator/denominator.
        frac = re.match(r"^(-?\d+)\s*/\s*(-?\d+)$", user_answer.strip())
        if frac:
            n, d = int(frac.group(1)), int(frac.group(2))
            if Fraction(n, d) == value and (abs(n) != abs(value.numerator) or abs(d) != value.denominator):
                return False, "right value — now reduce it to lowest terms"
        return True, None

    if answer_type == "expression":
        return check_expression(user_answer, canonical)

    return False, f"unknown answer type {answer_type!r}"


def check_instance(parts: list[dict], answers: list[str]) -> tuple[bool, list[dict]]:
    results = []
    for i, part in enumerate(parts):
        user = answers[i] if i < len(answers) else ""
        ok, feedback = check_part(part, user)
        results.append({"correct": ok, "feedback": feedback})
    return all(r["correct"] for r in results), results
