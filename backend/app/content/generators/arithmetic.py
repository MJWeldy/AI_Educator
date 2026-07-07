import random

from .base import ProblemInstance, ProblemPart, generator, mc, numeric

PLACE_NAMES = ["ones", "tens", "hundreds", "thousands", "ten-thousands", "hundred-thousands"]


@generator("arithmetic.place_value")
def place_value(rng: random.Random, difficulty: int) -> ProblemInstance:
    digits = {1: 3, 2: 4, 3: 6}[difficulty]
    # Distinct digits, so "the digit d" is unambiguous.
    chosen = rng.sample(range(10), digits)
    if chosen[0] == 0:
        chosen[0], chosen[1] = chosen[1], chosen[0]
    n = int("".join(map(str, chosen)))
    s = str(n)
    pos = rng.randrange(len(s))
    digit = int(s[pos])
    while digit == 0:
        pos = rng.randrange(len(s))
        digit = int(s[pos])
    place_idx = len(s) - 1 - pos
    value = digit * 10**place_idx
    return ProblemInstance(
        statement_md=f"Consider the number ${n:,}$.".replace(",", "{,}"),
        parts=[
            numeric(f"What is the **value** of the digit ${digit}$?", value),
            mc(
                rng,
                f"Which **place** does the digit ${digit}$ occupy?",
                PLACE_NAMES[place_idx],
                [PLACE_NAMES[i] for i in range(len(s)) if i != place_idx],
            ),
        ],
        solution_md=(
            f"The digit ${digit}$ is in the **{PLACE_NAMES[place_idx]}** place, "
            f"so its value is ${digit} \\times {10**place_idx:,} = {value:,}$.".replace(",", "{,}")
        ),
    )


@generator("arithmetic.add_sub")
def add_sub(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 99, 2: 999, 3: 9999}[difficulty]
    a, b = rng.randint(hi // 10, hi), rng.randint(hi // 10, hi)
    if rng.random() < 0.5:
        return ProblemInstance(
            statement_md=f"Compute ${a} + {b}$.",
            parts=[numeric("Sum:", a + b)],
            solution_md=f"${a} + {b} = {a + b}$.",
        )
    a, b = max(a, b), min(a, b)
    return ProblemInstance(
        statement_md=f"Compute ${a} - {b}$.",
        parts=[numeric("Difference:", a - b)],
        solution_md=f"${a} - {b} = {a - b}$.",
    )


@generator("arithmetic.multiply")
def multiply(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty == 1:
        a, b = rng.randint(3, 12), rng.randint(3, 12)
    elif difficulty == 2:
        a, b = rng.randint(13, 99), rng.randint(3, 9)
    else:
        a, b = rng.randint(13, 99), rng.randint(13, 99)
    return ProblemInstance(
        statement_md=f"Compute ${a} \\times {b}$.",
        parts=[numeric("Product:", a * b)],
        solution_md=f"${a} \\times {b} = {a * b}$.",
    )


@generator("arithmetic.divide")
def divide(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty == 1:
        d, q = rng.randint(2, 9), rng.randint(3, 12)
        r = 0
    elif difficulty == 2:
        d, q = rng.randint(3, 9), rng.randint(11, 99)
        r = rng.randint(0, d - 1)
    else:
        d, q = rng.randint(11, 25), rng.randint(11, 99)
        r = rng.randint(0, d - 1)
    n = d * q + r
    if r == 0:
        return ProblemInstance(
            statement_md=f"Compute ${n} \\div {d}$.",
            parts=[numeric("Quotient:", q)],
            solution_md=f"${d} \\times {q} = {n}$, so ${n} \\div {d} = {q}$.",
        )
    return ProblemInstance(
        statement_md=f"Divide ${n} \\div {d}$, giving a quotient and remainder.",
        parts=[numeric("Quotient:", q), numeric("Remainder:", r)],
        solution_md=f"${d} \\times {q} = {d*q}$ and ${n} - {d*q} = {r}$: quotient ${q}$, remainder ${r}$.",
    )


@generator("arithmetic.rounding")
def rounding(rng: random.Random, difficulty: int) -> ProblemInstance:
    digits = {1: 3, 2: 4, 3: 5}[difficulty]
    n = rng.randint(10 ** (digits - 1) + 1, 10**digits - 1)
    place_idx = rng.randint(1, digits - 1)
    unit = 10**place_idx
    rounded = (n + unit // 2) // unit * unit
    return ProblemInstance(
        statement_md=f"Round ${n:,}$ to the nearest **{PLACE_NAMES[place_idx].rstrip('s')}s** place.".replace(",", "{,}"),
        parts=[numeric("Rounded value:", rounded)],
        solution_md=(
            f"Look at the digit to the right of the {PLACE_NAMES[place_idx]} place: "
            f"round up if it's 5 or more. ${n:,} \\to {rounded:,}$.".replace(",", "{,}")
        ),
    )


@generator("arithmetic.order_of_operations")
def order_of_operations(rng: random.Random, difficulty: int) -> ProblemInstance:
    a, b, c = rng.randint(2, 9), rng.randint(2, 9), rng.randint(2, 9)
    d = rng.randint(2, 4)
    if difficulty == 1:
        expr, val = f"{a} + {b} \\times {c}", a + b * c
        steps = f"Multiply first: ${b} \\times {c} = {b*c}$, then ${a} + {b*c} = {a + b*c}$."
    elif difficulty == 2:
        expr, val = f"({a} + {b}) \\times {c} - {d}", (a + b) * c - d
        steps = f"Parentheses: ${a}+{b}={a+b}$. Multiply: ${a+b} \\times {c} = {(a+b)*c}$. Subtract: ${(a+b)*c - d}$."
    else:
        total = a * d * c
        expr, val = f"{total} \\div {d} \\times {c} + {b}", (total // d) * c + b
        steps = (
            f"Division and multiplication left to right: ${total} \\div {d} = {total//d}$, "
            f"${total//d} \\times {c} = {(total//d)*c}$, then $+\\,{b}$ gives ${val}$."
        )
    return ProblemInstance(
        statement_md=f"Evaluate ${expr}$.",
        parts=[numeric("Value:", val)],
        solution_md=steps,
    )


CONVERSIONS = [
    ("m", "cm", 100), ("km", "m", 1000), ("cm", "mm", 10),
    ("kg", "g", 1000), ("L", "mL", 1000),
]


@generator("arithmetic.unit_conversion")
def unit_conversion(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty == 3:
        h, m = rng.randint(1, 5), rng.choice([10, 15, 20, 30, 40, 45, 50])
        return ProblemInstance(
            statement_md=f"A trip takes ${h}$ hours and ${m}$ minutes.",
            parts=[numeric("How many minutes is that in total?", h * 60 + m)],
            solution_md=f"${h} \\times 60 + {m} = {h * 60 + m}$ minutes.",
        )
    big, small, factor = rng.choice(CONVERSIONS)
    if difficulty == 1:
        n = rng.randint(2, 30)
        return ProblemInstance(
            statement_md=f"Convert ${n}$ {big} to {small}.",
            parts=[numeric(f"Value in {small}:", n * factor)],
            solution_md=f"$1$ {big} $= {factor}$ {small}, so ${n} \\times {factor} = {n * factor}$.",
        )
    from decimal import Decimal
    n = Decimal(rng.randint(11, 99)) / 10
    return ProblemInstance(
        statement_md=f"Convert ${n}$ {big} to {small}.",
        parts=[numeric(f"Value in {small}:", int(n * factor))],
        solution_md=f"${n} \\times {factor} = {int(n * factor)}$ {small}.",
    )
