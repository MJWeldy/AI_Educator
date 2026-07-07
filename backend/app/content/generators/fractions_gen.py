import random
from fractions import Fraction
from math import gcd

from .base import ProblemInstance, ProblemPart, frac_answer, frac_md, generator, mc, numeric


def frac_part(prompt_md: str, f: Fraction) -> ProblemPart:
    """Answer must be the fraction in lowest terms (integers allowed)."""
    return ProblemPart(prompt_md=prompt_md, answer_type="fraction_lowest", canonical=frac_answer(f))


@generator("fractions.meaning")
def meaning(rng: random.Random, difficulty: int) -> ProblemInstance:
    d = rng.choice([5, 7, 8, 9, 11, 12])
    n = rng.randint(1, d - 1)
    while gcd(n, d) != 1:
        n = rng.randint(1, d - 1)
    ctx = rng.choice(
        [
            ("a pizza cut into {d} equal slices; you eat {n}", "What fraction of the pizza did you eat?"),
            ("a class of {d} students, {n} of whom walk to school", "What fraction of the class walks?"),
            ("a ribbon cut into {d} equal pieces; {n} are used", "What fraction of the ribbon is used?"),
        ]
    )
    return ProblemInstance(
        statement_md="Consider " + ctx[0].format(d=d, n=n) + ".",
        parts=[frac_part(ctx[1] + " (as a fraction in lowest terms)", Fraction(n, d))],
        solution_md=f"${n}$ parts out of ${d}$ equal parts: ${frac_md(Fraction(n, d))}$.",
    )


@generator("fractions.equivalent")
def equivalent(rng: random.Random, difficulty: int) -> ProblemInstance:
    d = rng.choice([3, 4, 5, 6, 7, 8])
    n = rng.randint(1, d - 1)
    while gcd(n, d) != 1:
        n = rng.randint(1, d - 1)
    k = rng.randint(2, {1: 4, 2: 7, 3: 12}[difficulty])
    return ProblemInstance(
        statement_md=f"Fill in the missing numerator: $\\dfrac{{{n}}}{{{d}}} = \\dfrac{{?}}{{{d*k}}}$",
        parts=[numeric("Missing numerator:", n * k)],
        solution_md=(
            f"The denominator was multiplied by ${k}$ (${d} \\to {d*k}$), so multiply the "
            f"numerator by ${k}$ as well: ${n} \\times {k} = {n*k}$."
        ),
    )


@generator("fractions.simplify")
def simplify(rng: random.Random, difficulty: int) -> ProblemInstance:
    d = rng.choice([3, 4, 5, 6, 7, 8, 9, 10])
    n = rng.randint(1, d - 1)
    while gcd(n, d) != 1:
        n = rng.randint(1, d - 1)
    k = rng.randint(2, {1: 4, 2: 8, 3: 15}[difficulty])
    f = Fraction(n, d)
    return ProblemInstance(
        statement_md=f"Write $\\dfrac{{{n*k}}}{{{d*k}}}$ in lowest terms.",
        parts=[frac_part("Simplified fraction:", f)],
        solution_md=f"$\\gcd({n*k}, {d*k}) = {k}$; divide both by ${k}$: ${frac_md(f)}$.",
    )


@generator("fractions.compare")
def compare(rng: random.Random, difficulty: int) -> ProblemInstance:
    max_d = {1: 8, 2: 12, 3: 20}[difficulty]
    while True:
        a = Fraction(rng.randint(1, max_d - 1), rng.randint(2, max_d))
        b = Fraction(rng.randint(1, max_d - 1), rng.randint(2, max_d))
        if a != b and a < 1 and b < 1 and a.denominator != b.denominator:
            break
    bigger = a if a > b else b
    other = b if a > b else a
    return ProblemInstance(
        statement_md=f"Compare ${frac_md(a)}$ and ${frac_md(b)}$.",
        parts=[
            mc(rng, "Which is greater?", f"${frac_md(bigger)}$", [f"${frac_md(other)}$", "they are equal"])
        ],
        solution_md=(
            f"Use a common denominator ${a.denominator * b.denominator}$: "
            f"${frac_md(a)} = \\dfrac{{{a.numerator * b.denominator}}}{{{a.denominator * b.denominator}}}$ and "
            f"${frac_md(b)} = \\dfrac{{{b.numerator * a.denominator}}}{{{a.denominator * b.denominator}}}$, "
            f"so ${frac_md(bigger)}$ is greater."
        ),
    )


def _add_sub_instance(a: Fraction, b: Fraction, op: str) -> tuple[str, Fraction]:
    val = a + b if op == "+" else a - b
    return f"Compute ${frac_md(a)} {op} {frac_md(b)}$. Give your answer in lowest terms.", val


@generator("fractions.add_sub_like")
def add_sub_like(rng: random.Random, difficulty: int) -> ProblemInstance:
    d = rng.choice({1: [4, 5, 6, 8], 2: [7, 9, 10, 12], 3: [11, 13, 15, 16]}[difficulty])
    n1 = rng.randint(1, d - 1)
    n2 = rng.randint(1, d - 1)
    a, b = Fraction(n1, d), Fraction(n2, d)
    op = "+" if rng.random() < 0.5 or n1 <= n2 else "-"
    if op == "-" and n1 < n2:
        n1, n2 = n2, n1
        a, b = Fraction(n1, d), Fraction(n2, d)
    stmt = f"Compute $\\dfrac{{{n1}}}{{{d}}} {op} \\dfrac{{{n2}}}{{{d}}}$. Give your answer in lowest terms."
    val = a + b if op == "+" else a - b
    return ProblemInstance(
        statement_md=stmt,
        parts=[frac_part("Result:", val)],
        solution_md=(
            f"Same denominator — {'add' if op == '+' else 'subtract'} the numerators: "
            f"$\\dfrac{{{n1} {op} {n2}}}{{{d}}} = {frac_md(val)}$."
        ),
    )


@generator("fractions.add_sub_unlike")
def add_sub_unlike(rng: random.Random, difficulty: int) -> ProblemInstance:
    max_d = {1: 6, 2: 10, 3: 15}[difficulty]
    while True:
        d1, d2 = rng.randint(2, max_d), rng.randint(2, max_d)
        if d1 != d2:
            break
    a = Fraction(rng.randint(1, d1 - 1), d1)
    b = Fraction(rng.randint(1, d2 - 1), d2)
    op = "+" if rng.random() < 0.5 else "-"
    if op == "-" and a < b:
        a, b = b, a
    stmt, val = _add_sub_instance(a, b, op)
    lcd = a.denominator * b.denominator // gcd(a.denominator, b.denominator)
    return ProblemInstance(
        statement_md=stmt,
        parts=[frac_part("Result:", val)],
        solution_md=(
            f"The LCD of ${a.denominator}$ and ${b.denominator}$ is ${lcd}$: "
            f"$\\dfrac{{{a.numerator * (lcd // a.denominator)}}}{{{lcd}}} {op} "
            f"\\dfrac{{{b.numerator * (lcd // b.denominator)}}}{{{lcd}}} = {frac_md(val)}$."
        ),
    )


@generator("fractions.multiply")
def multiply(rng: random.Random, difficulty: int) -> ProblemInstance:
    max_d = {1: 6, 2: 10, 3: 15}[difficulty]
    a = Fraction(rng.randint(1, max_d - 1), rng.randint(2, max_d))
    b = Fraction(rng.randint(1, max_d - 1), rng.randint(2, max_d))
    val = a * b
    return ProblemInstance(
        statement_md=f"Compute ${frac_md(a)} \\times {frac_md(b)}$. Give your answer in lowest terms.",
        parts=[frac_part("Product:", val)],
        solution_md=(
            f"Multiply numerators and denominators (cancelling where possible): ${frac_md(val)}$."
        ),
    )


@generator("fractions.divide")
def divide(rng: random.Random, difficulty: int) -> ProblemInstance:
    max_d = {1: 6, 2: 10, 3: 15}[difficulty]
    a = Fraction(rng.randint(1, max_d - 1), rng.randint(2, max_d))
    b = Fraction(rng.randint(1, max_d - 1), rng.randint(2, max_d))
    val = a / b
    return ProblemInstance(
        statement_md=f"Compute ${frac_md(a)} \\div {frac_md(b)}$. Give your answer in lowest terms.",
        parts=[frac_part("Quotient:", val)],
        solution_md=(
            f"Multiply by the reciprocal: ${frac_md(a)} \\times "
            f"\\dfrac{{{b.denominator}}}{{{b.numerator}}} = {frac_md(val)}$."
        ),
    )


@generator("fractions.mixed_convert")
def mixed_convert(rng: random.Random, difficulty: int) -> ProblemInstance:
    d = rng.choice([3, 4, 5, 6, 8])
    whole = rng.randint(1, {1: 3, 2: 6, 3: 12}[difficulty])
    n = rng.randint(1, d - 1)
    if rng.random() < 0.5:
        return ProblemInstance(
            statement_md=f"Write ${whole}\\tfrac{{{n}}}{{{d}}}$ as an improper fraction.",
            parts=[
                numeric("Numerator:", whole * d + n),
                numeric("Denominator:", d),
            ],
            solution_md=f"${whole} \\times {d} + {n} = {whole*d + n}$, so $\\dfrac{{{whole*d+n}}}{{{d}}}$.",
        )
    return ProblemInstance(
        statement_md=f"Write $\\dfrac{{{whole*d + n}}}{{{d}}}$ as a mixed number.",
        parts=[numeric("Whole part:", whole), numeric("Numerator of the fractional part:", n)],
        solution_md=f"${whole*d+n} \\div {d} = {whole}$ remainder ${n}$: ${whole}\\tfrac{{{n}}}{{{d}}}$.",
    )


@generator("fractions.mixed_ops")
def mixed_ops(rng: random.Random, difficulty: int) -> ProblemInstance:
    d1, d2 = rng.choice([(2, 4), (3, 6), (4, 8), (2, 3), (3, 4), (4, 6)])
    a = Fraction(rng.randint(1, 3) * d1 + rng.randint(1, d1 - 1), d1)
    b = Fraction(rng.randint(1, 2) * d2 + rng.randint(1, d2 - 1), d2)
    op = rng.choice(["+", "-", "\\times"] if difficulty >= 2 else ["+", "-"])
    if op == "-" and a < b:
        a, b = b, a
    val = {"+": a + b, "-": a - b, "\\times": a * b}[op]

    def mixed_md(f: Fraction) -> str:
        w, r = divmod(f.numerator, f.denominator)
        return f"{w}\\tfrac{{{r}}}{{{f.denominator}}}" if r else str(w)

    return ProblemInstance(
        statement_md=(
            f"Compute ${mixed_md(a)} {op} {mixed_md(b)}$. "
            "Give your answer as an improper fraction in lowest terms."
        ),
        parts=[frac_part("Result:", val)],
        solution_md=(
            f"As improper fractions: ${frac_md(a)} {op} {frac_md(b)} = {frac_md(val)}$."
        ),
    )
