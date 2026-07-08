import random
from decimal import Decimal
from fractions import Fraction
from math import gcd

from .base import ProblemInstance, ProblemPart, frac_answer, generator, mc, numeric


@generator("ratio.basic")
def basic(rng: random.Random, difficulty: int) -> ProblemInstance:
    k = rng.randint(2, {1: 4, 2: 8, 3: 12}[difficulty])
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    while gcd(a, b) != 1 or a == b:
        a, b = rng.randint(2, 9), rng.randint(2, 9)
    red, blue = a * k, b * k
    return ProblemInstance(
        statement_md=(
            f"A bag holds ${red}$ red marbles and ${blue}$ blue marbles."
        ),
        parts=[
            mc(
                rng,
                "What is the ratio of red to blue in simplest form?",
                f"${a} : {b}$",
                [f"${b} : {a}$", f"${red} : {blue}$", f"${a} : {a + b}$"],
            ),
        ],
        solution_md=f"Divide both by $\\gcd({red}, {blue}) = {k}$: ${a} : {b}$.",
    )


@generator("ratio.unit_rate")
def unit_rate(rng: random.Random, difficulty: int) -> ProblemInstance:
    qty = rng.choice({1: [2, 4, 5], 2: [3, 6, 8], 3: [7, 12, 16]}[difficulty])
    unit_price = Decimal(rng.randint(50, 599)) / 100
    total = unit_price * qty
    return ProblemInstance(
        statement_md=f"A pack of ${qty}$ notebooks costs \\${total}.",
        parts=[numeric("What is the price per notebook, in dollars?", unit_price)],
        solution_md=f"\\${total} divided by ${qty}$ notebooks is \\${unit_price} per notebook.",
    )


@generator("ratio.proportion")
def proportion(rng: random.Random, difficulty: int) -> ProblemInstance:
    a = rng.randint(2, {1: 9, 2: 12, 3: 15}[difficulty])
    b = rng.randint(2, 12)
    k = rng.randint(2, {1: 5, 2: 9, 3: 15}[difficulty])
    x = a * k
    return ProblemInstance(
        statement_md=f"Solve for $x$: $\\dfrac{{{a}}}{{{b}}} = \\dfrac{{x}}{{{b*k}}}$",
        parts=[numeric("$x =$", x)],
        solution_md=(
            f"Cross-multiply: ${a} \\times {b*k} = {b} \\, x$, so "
            f"$x = \\dfrac{{{a * b * k}}}{{{b}}} = {x}$."
        ),
    )


@generator("percent.meaning")
def percent_meaning(rng: random.Random, difficulty: int) -> ProblemInstance:
    p = rng.choice({1: [10, 20, 25, 50, 75], 2: [5, 15, 40, 60, 85], 3: [4, 12.5, 37.5, 62.5, 95]}[difficulty])
    dec_val = Decimal(str(p)) / 100
    frac = Fraction(str(p)) / 100
    return ProblemInstance(
        statement_md=f"Consider ${p}\\%$.",
        parts=[
            numeric("Write it as a decimal:", dec_val),
            ProblemPart(
                prompt_md="Write it as a fraction in lowest terms:",
                answer_type="fraction_lowest",
                canonical=frac_answer(frac),
            ),
        ],
        solution_md=(
            f"Percent means per hundred: ${p}\\% = {dec_val} = "
            f"\\dfrac{{{frac.numerator}}}{{{frac.denominator}}}$."
        ),
    )


@generator("percent.of_number")
def percent_of_number(rng: random.Random, difficulty: int) -> ProblemInstance:
    p = rng.choice({1: [10, 25, 50], 2: [5, 15, 20, 30, 40], 3: [12, 35, 65, 85]}[difficulty])
    base = rng.randint(2, 40) * {1: 4, 2: 20, 3: 20}[difficulty]
    part = base * p // 100
    if base * p % 100:
        base = (base // 100 + 1) * 100
        part = base * p // 100
    if rng.random() < 0.6 or difficulty == 1:
        return ProblemInstance(
            statement_md=f"What is ${p}\\%$ of ${base}$?",
            parts=[numeric("Value:", part)],
            solution_md=f"${p}\\% = {Decimal(p)/100}$, and ${Decimal(p)/100} \\times {base} = {part}$.",
        )
    return ProblemInstance(
        statement_md=f"${part}$ is ${p}\\%$ of what number?",
        parts=[numeric("The whole:", base)],
        solution_md=f"whole $= {part} \\div {Decimal(p)/100} = {base}$.",
    )


@generator("percent.change")
def percent_change(rng: random.Random, difficulty: int) -> ProblemInstance:
    p = rng.choice({1: [10, 25, 50], 2: [5, 15, 20, 40], 3: [8, 12, 35, 60]}[difficulty])
    old = rng.randint(2, 30) * (100 // gcd(100, p) if p != 12 and p != 8 else 25)
    change = old * p // 100
    increase = rng.random() < 0.5
    new = old + change if increase else old - change
    word = "increased" if increase else "decreased"
    return ProblemInstance(
        statement_md=f"A price {word} from \\${old} to \\${new}.",
        parts=[numeric("What was the percent change, in percent?", p)],
        solution_md=(
            f"$\\text{{change}} = \\lvert {new} - {old} \\rvert = {change}$; "
            f"$\\dfrac{{{change}}}{{{old}}} = {Decimal(change*100)/old if old else 0}\\% = {p}\\%$ of the original."
        ),
    )
