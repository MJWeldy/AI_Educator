import random

from .base import ProblemInstance, generator, mc, numeric


@generator("integers.compare")
def compare(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 10, 2: 30, 3: 100}[difficulty]
    vals = rng.sample(range(-hi, hi + 1), 4)
    ordered = sorted(vals)
    correct = ", ".join(f"${v}$" for v in ordered)
    wrong1 = ", ".join(f"${v}$" for v in sorted(vals, reverse=True))
    wrong2 = ", ".join(f"${v}$" for v in sorted(vals, key=abs))
    wrong3 = ", ".join(f"${v}$" for v in sorted(vals, key=lambda v: (v < 0, abs(v))))
    return ProblemInstance(
        statement_md=f"Consider the numbers ${vals[0]}$, ${vals[1]}$, ${vals[2]}$, ${vals[3]}$.",
        parts=[
            mc(rng, "Which lists them from **least to greatest**?", correct, [wrong1, wrong2, wrong3])
        ],
        solution_md=f"Further left on the number line = smaller: {correct}.",
    )


@generator("integers.add_sub")
def add_sub(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 12, 2: 30, 3: 99}[difficulty]
    a = rng.randint(-hi, hi)
    b = rng.randint(1, hi)
    if rng.random() < 0.5:
        b = -b
    op = rng.choice(["+", "-"])
    val = a + b if op == "+" else a - b
    b_str = f"({b})" if b < 0 else str(b)
    return ProblemInstance(
        statement_md=f"Compute ${a} {op} {b_str}$.",
        parts=[numeric("Result:", val)],
        solution_md=(
            f"${a} {op} {b_str} = {val}$. "
            + ("Subtracting a negative is adding." if op == "-" and b < 0 else
               "Adding a negative is subtracting." if op == "+" and b < 0 else
               "Move along the number line.")
        ),
    )


@generator("integers.mul_div")
def mul_div(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 9, 2: 12, 3: 25}[difficulty]
    a = rng.randint(2, hi) * rng.choice([1, -1])
    b = rng.randint(2, hi) * rng.choice([1, -1])
    if a > 0 and b > 0:
        a = -a  # keep at least one negative so the topic is exercised
    if rng.random() < 0.5:
        b_str = f"({b})" if b < 0 else str(b)
        a_str = f"({a})" if a < 0 else str(a)
        return ProblemInstance(
            statement_md=f"Compute ${a_str} \\times {b_str}$.",
            parts=[numeric("Product:", a * b)],
            solution_md=f"{'Same signs → positive' if a*b > 0 else 'Different signs → negative'}: ${a*b}$.",
        )
    prod = a * b
    prod_str = f"({prod})" if prod < 0 else str(prod)
    b_str = f"({b})" if b < 0 else str(b)
    return ProblemInstance(
        statement_md=f"Compute ${prod_str} \\div {b_str}$.",
        parts=[numeric("Quotient:", a)],
        solution_md=f"{'Same signs → positive' if a > 0 else 'Different signs → negative'}: ${a}$.",
    )


@generator("integers.absolute_value")
def absolute_value(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 15, 2: 50, 3: 120}[difficulty]
    a = rng.randint(-hi, -1)
    b = rng.randint(1, hi)
    if difficulty == 1:
        return ProblemInstance(
            statement_md=f"Evaluate $\\lvert {a} \\rvert$.",
            parts=[numeric("Value:", abs(a))],
            solution_md=f"Absolute value is distance from zero: $\\lvert {a} \\rvert = {abs(a)}$.",
        )
    val = abs(a) + abs(b) if rng.random() < 0.5 else abs(a) - abs(b)
    op = "+" if val == abs(a) + abs(b) else "-"
    return ProblemInstance(
        statement_md=f"Evaluate $\\lvert {a} \\rvert {op} \\lvert {b} \\rvert$.",
        parts=[numeric("Value:", val)],
        solution_md=f"$\\lvert {a} \\rvert = {abs(a)}$ and $\\lvert {b} \\rvert = {abs(b)}$, so the result is ${val}$.",
    )
