import random
from decimal import Decimal
from fractions import Fraction

from .base import ProblemInstance, generator, mc, numeric

DEC_PLACES = ["tenths", "hundredths", "thousandths"]


def dec(value: Decimal) -> str:
    """Trim trailing zeros but keep at least one decimal digit if fractional."""
    s = format(value.normalize(), "f")
    return s


@generator("decimals.place_value")
def place_value(rng: random.Random, difficulty: int) -> ProblemInstance:
    places = min(3, difficulty + 1)
    digits = [rng.randint(1, 9) for _ in range(places)]
    whole = rng.randint(1, 99)
    s = f"{whole}." + "".join(map(str, digits))
    pos = rng.randrange(places)
    digit = digits[pos]
    value = Fraction(digit, 10 ** (pos + 1))
    return ProblemInstance(
        statement_md=f"Consider the number ${s}$.",
        parts=[
            mc(
                rng,
                f"Which place does the digit ${digit}$ after the decimal point occupy?",
                DEC_PLACES[pos],
                [DEC_PLACES[i] for i in range(3) if i != pos],
            ),
            numeric(
                f"What is the value of that digit, as a decimal?",
                Decimal(digit) / (10 ** (pos + 1)),
            ),
        ],
        solution_md=(
            f"The digit ${digit}$ is in the **{DEC_PLACES[pos]}** place: its value is "
            f"${digit} \\times 10^{{-{pos+1}}} = {Decimal(digit) / (10 ** (pos + 1))}$."
        ),
    )


@generator("decimals.compare_round")
def compare_round(rng: random.Random, difficulty: int) -> ProblemInstance:
    places = min(3, difficulty + 1)
    a = Decimal(rng.randint(100, 9999)) / (10**places)
    delta = Decimal(rng.randint(1, 9)) / (10**places)
    b = a + delta if rng.random() < 0.5 else a - delta
    bigger = max(a, b)
    round_to = rng.randint(0, places - 1)
    rounded = a.quantize(Decimal(1).scaleb(-round_to))
    place_name = "whole number" if round_to == 0 else DEC_PLACES[round_to - 1].rstrip("s")
    return ProblemInstance(
        statement_md=f"Consider the decimals ${a}$ and ${b}$.",
        parts=[
            mc(rng, "Which is greater?", f"${bigger}$", [f"${min(a,b)}$", "they are equal"]),
            numeric(f"Round ${a}$ to the nearest **{place_name}**.", rounded),
        ],
        solution_md=(
            f"Compare digit by digit from the left: ${bigger}$ is greater. "
            f"Rounding ${a}$ to the nearest {place_name} gives ${rounded}$."
        ),
    )


@generator("decimals.add_sub")
def add_sub(rng: random.Random, difficulty: int) -> ProblemInstance:
    scale = {1: 1, 2: 2, 3: 2}[difficulty]
    hi = {1: 99, 2: 999, 3: 9999}[difficulty]
    a = Decimal(rng.randint(10, hi)) / (10**scale)
    b = Decimal(rng.randint(10, hi)) / (10 ** rng.randint(1, scale))
    if rng.random() < 0.5:
        return ProblemInstance(
            statement_md=f"Compute ${a} + {b}$.",
            parts=[numeric("Sum:", a + b)],
            solution_md=f"Line up the decimal points: ${a} + {b} = {a + b}$.",
        )
    x, y = max(a, b), min(a, b)
    return ProblemInstance(
        statement_md=f"Compute ${x} - {y}$.",
        parts=[numeric("Difference:", x - y)],
        solution_md=f"Line up the decimal points: ${x} - {y} = {x - y}$.",
    )


@generator("decimals.multiply")
def multiply(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty == 1:
        a = Decimal(rng.randint(2, 99)) / 10
        b = rng.randint(2, 9)
        val = a * b
        stmt = f"Compute ${a} \\times {b}$."
    else:
        a = Decimal(rng.randint(11, 99)) / 10
        b = Decimal(rng.randint(11, 99)) / (10 ** (difficulty - 1))
        val = a * b
        stmt = f"Compute ${a} \\times {b}$."
    return ProblemInstance(
        statement_md=stmt,
        parts=[numeric("Product:", val)],
        solution_md=(
            "Multiply as whole numbers, then place the decimal point with as many decimal "
            f"digits as the two factors combined: ${val}$."
        ),
    )


@generator("decimals.divide")
def divide(rng: random.Random, difficulty: int) -> ProblemInstance:
    q = Decimal(rng.randint(11, 99)) / 10
    d = rng.randint(2, 9) if difficulty == 1 else Decimal(rng.randint(2, 39)) / 10
    n = q * d
    return ProblemInstance(
        statement_md=f"Compute ${n} \\div {d}$.",
        parts=[numeric("Quotient:", q)],
        solution_md=(
            f"Shift the decimal in both numbers until the divisor is whole, then long-divide: ${q}$. "
            f"Check: ${d} \\times {q} = {n}$."
        ),
    )


@generator("decimals.from_fraction")
def from_fraction(rng: random.Random, difficulty: int) -> ProblemInstance:
    nice = {
        1: [(1, 2), (1, 4), (3, 4), (1, 5), (2, 5), (3, 5), (4, 5), (1, 10), (7, 10)],
        2: [(1, 8), (3, 8), (5, 8), (7, 8), (1, 20), (3, 20), (9, 20), (1, 25), (12, 25)],
        3: [(1, 8), (5, 16), (7, 16), (11, 40), (3, 40), (13, 25), (17, 20), (9, 8)],
    }[difficulty]
    n, d = rng.choice(nice)
    val = Decimal(n) / Decimal(d)
    return ProblemInstance(
        statement_md=f"Write $\\dfrac{{{n}}}{{{d}}}$ as a decimal.",
        parts=[numeric("Decimal value:", val)],
        solution_md=f"Divide: ${n} \\div {d} = {val}$.",
    )
