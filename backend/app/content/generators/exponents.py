import random
from decimal import Decimal

from .base import ProblemInstance, generator, mc, numeric


@generator("exponents.evaluate")
def evaluate(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty == 1:
        b, e = rng.randint(2, 5), rng.randint(2, 3)
    elif difficulty == 2:
        b, e = rng.randint(2, 6), rng.randint(2, 4)
    else:
        b, e = rng.choice([2, 3, 10]), rng.randint(3, 6)
    return ProblemInstance(
        statement_md=f"Evaluate ${b}^{{{e}}}$.",
        parts=[numeric("Value:", b**e)],
        solution_md=f"${b}^{{{e}}}$ means {e} factors of {b}: ${' \\times '.join([str(b)] * e)} = {b**e}$.",
    )


@generator("exponents.rules")
def rules(rng: random.Random, difficulty: int) -> ProblemInstance:
    b = rng.choice(["x", "y", "2", "3", "a"])
    m, n = rng.randint(2, 5 + difficulty * 2), rng.randint(2, 5 + difficulty * 2)
    if rng.random() < 0.5:
        stmt = f"Simplify ${b}^{{{m}}} \\cdot {b}^{{{n}}} = {b}^{{?}}$"
        ans, rule = m + n, f"add exponents: ${m} + {n} = {m+n}$"
    else:
        m = max(m, n + 1)
        stmt = f"Simplify $\\dfrac{{{b}^{{{m}}}}}{{{b}^{{{n}}}}} = {b}^{{?}}$"
        ans, rule = m - n, f"subtract exponents: ${m} - {n} = {m-n}$"
    return ProblemInstance(
        statement_md=stmt,
        parts=[numeric("Missing exponent:", ans)],
        solution_md=f"Common base, so {rule}.",
    )


@generator("roots.square_root")
def square_root(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty <= 2:
        r = rng.randint(2 if difficulty == 1 else 8, 12 if difficulty == 1 else 20)
        return ProblemInstance(
            statement_md=f"Evaluate $\\sqrt{{{r*r}}}$.",
            parts=[numeric("Value:", r)],
            solution_md=f"${r}^2 = {r*r}$, so $\\sqrt{{{r*r}}} = {r}$.",
        )
    r = rng.randint(4, 15)
    n = rng.randint(r * r + 1, (r + 1) * (r + 1) - 1)
    return ProblemInstance(
        statement_md=f"$\\sqrt{{{n}}}$ is not a whole number. Between which two consecutive whole numbers does it lie?",
        parts=[numeric("Lower:", r), numeric("Upper:", r + 1)],
        solution_md=f"${r}^2 = {r*r} < {n} < {(r+1)*(r+1)} = {r+1}^2$, so ${r} < \\sqrt{{{n}}} < {r+1}$.",
    )


@generator("scinot.convert")
def scinot(rng: random.Random, difficulty: int) -> ProblemInstance:
    coeff = Decimal(rng.randint(11, 99)) / 10
    exp = rng.randint(2, 4 + difficulty)
    if difficulty == 3 and rng.random() < 0.5:
        exp = -rng.randint(2, 5)
    value = coeff * Decimal(10) ** exp
    return ProblemInstance(
        statement_md=f"Write ${format(value, 'f')}$ in scientific notation $a \\times 10^{{n}}$.",
        parts=[numeric("Coefficient $a$ (with $1 \\le a < 10$):", coeff), numeric("Exponent $n$:", exp)],
        solution_md=f"${format(value, 'f')} = {coeff} \\times 10^{{{exp}}}$.",
    )
