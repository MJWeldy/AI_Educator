"""Grades K–2: counting, early addition/subtraction, tens and ones, time,
money, and shapes. Aligned with Khan Academy's Early math course."""

import random

from .base import ProblemInstance, generator, mc, numeric


@generator("earlymath.count_sequence")
def count_sequence(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 20, 2: 100, 3: 1000}[difficulty]
    n = rng.randint(2, hi - 1)
    if rng.random() < 0.5:
        return ProblemInstance(
            statement_md=f"What number comes **right after** ${n}$ when counting?",
            parts=[numeric("Next number:", n + 1)],
            solution_md=f"Counting up by one: ${n}, {n + 1}$.",
        )
    return ProblemInstance(
        statement_md=f"What number comes **right before** ${n}$ when counting?",
        parts=[numeric("Number before:", n - 1)],
        solution_md=f"Counting back by one: ${n - 1}, {n}$.",
    )


@generator("earlymath.compare_numbers")
def compare_numbers(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 20, 2: 100, 3: 1000}[difficulty]
    a, b = rng.sample(range(1, hi + 1), 2)
    bigger, smaller = max(a, b), min(a, b)
    return ProblemInstance(
        statement_md=f"Look at the numbers ${a}$ and ${b}$.",
        parts=[
            mc(rng, "Which number is **greater**?", str(bigger), [str(smaller)]),
            numeric("How much greater is it?", bigger - smaller),
        ],
        solution_md=f"${bigger} > {smaller}$, and ${bigger} - {smaller} = {bigger - smaller}$.",
    )


@generator("earlymath.skip_count")
def skip_count(rng: random.Random, difficulty: int) -> ProblemInstance:
    step = rng.choice({1: [2, 5, 10], 2: [2, 3, 5, 10], 3: [4, 25, 50, 100]}[difficulty])
    start = rng.randint(0, 5) * step
    seq = [start + i * step for i in range(5)]
    hidden = rng.randint(2, 4)
    shown = [str(v) if i != hidden else r"\_\_" for i, v in enumerate(seq)]
    return ProblemInstance(
        statement_md="Fill in the missing number: $" + ",\\ ".join(shown) + "$",
        parts=[numeric("Missing number:", seq[hidden])],
        solution_md=f"The pattern counts by ${step}$s, so the missing number is ${seq[hidden]}$.",
    )


@generator("earlymath.add_within_20")
def add_within_20(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 10, 2: 20, 3: 20}[difficulty]
    a = rng.randint(1, hi - 1)
    b = rng.randint(1, hi - a)
    if difficulty == 3:  # missing addend
        return ProblemInstance(
            statement_md=f"Find the missing number: ${a} + \\_\\_ = {a + b}$",
            parts=[numeric("Missing number:", b)],
            solution_md=f"${a + b} - {a} = {b}$, and check: ${a} + {b} = {a + b}$.",
        )
    return ProblemInstance(
        statement_md=f"Add: ${a} + {b}$",
        parts=[numeric("Sum:", a + b)],
        solution_md=f"${a} + {b} = {a + b}$.",
    )


@generator("earlymath.sub_within_20")
def sub_within_20(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 10, 2: 20, 3: 20}[difficulty]
    a = rng.randint(2, hi)
    b = rng.randint(1, a - 1)
    if difficulty == 3:
        return ProblemInstance(
            statement_md=f"Find the missing number: ${a} - \\_\\_ = {a - b}$",
            parts=[numeric("Missing number:", b)],
            solution_md=f"${a} - {a - b} = {b}$.",
        )
    return ProblemInstance(
        statement_md=f"Subtract: ${a} - {b}$",
        parts=[numeric("Difference:", a - b)],
        solution_md=f"${a} - {b} = {a - b}$.",
    )


@generator("earlymath.word_problems")
def word_problems(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 10, 2: 20, 3: 50}[difficulty]
    a = rng.randint(3, hi)
    b = rng.randint(1, min(a - 1, hi // 2))
    name = rng.choice(["Maya", "Leo", "Ava", "Sam", "Nia", "Kai"])
    thing = rng.choice(["marbles", "stickers", "apples", "blocks", "crayons"])
    if rng.random() < 0.5:
        return ProblemInstance(
            statement_md=f"{name} has ${a}$ {thing} and gets ${b}$ more.",
            parts=[numeric(f"How many {thing} does {name} have now?", a + b)],
            solution_md=f"Getting more means adding: ${a} + {b} = {a + b}$.",
        )
    return ProblemInstance(
        statement_md=f"{name} has ${a}$ {thing} and gives ${b}$ away.",
        parts=[numeric(f"How many {thing} are left?", a - b)],
        solution_md=f"Giving away means subtracting: ${a} - {b} = {a - b}$.",
    )


@generator("earlymath.tens_ones")
def tens_ones(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty <= 2:
        n = rng.randint(11, 99)
        return ProblemInstance(
            statement_md=f"Think about the number ${n}$.",
            parts=[
                numeric("How many **tens** does it have?", n // 10),
                numeric("How many **ones** are left over?", n % 10),
            ],
            solution_md=f"${n} = {n // 10}$ tens $+ {n % 10}$ ones.",
        )
    tens = rng.randint(2, 9)
    ones = rng.randint(0, 9)
    hundreds = rng.randint(1, 9)
    n = hundreds * 100 + tens * 10 + ones
    return ProblemInstance(
        statement_md=f"What number is ${hundreds}$ hundreds, ${tens}$ tens, and ${ones}$ ones?",
        parts=[numeric("The number:", n)],
        solution_md=f"${hundreds}00 + {tens}0 + {ones} = {n}$.",
    )


@generator("earlymath.telling_time")
def telling_time(rng: random.Random, difficulty: int) -> ProblemInstance:
    hour = rng.randint(1, 11)
    if difficulty == 1:
        minute = rng.choice([0, 30])
        phrase = "o'clock" if minute == 0 else "thirty"
        return ProblemInstance(
            statement_md=f'A clock shows **{hour} {phrase}**. Write the time as it appears on a digital clock.',
            parts=[
                numeric("Hour:", hour),
                numeric("Minutes:", minute),
            ],
            solution_md=f"{hour} {phrase} is ${hour}:{minute:02d}$.",
        )
    minute = rng.choice([5, 10, 15, 20, 25, 35, 40, 45, 50, 55])
    until = 60 - minute
    return ProblemInstance(
        statement_md=f"A digital clock reads **{hour}:{minute:02d}**.",
        parts=[numeric(f"How many minutes until {hour + 1}:00?", until)],
        solution_md=f"$60 - {minute} = {until}$ minutes.",
    )


@generator("earlymath.money")
def money(rng: random.Random, difficulty: int) -> ProblemInstance:
    max_coins = {1: 4, 2: 7, 3: 10}[difficulty]
    quarters = rng.randint(0, min(3, max_coins))
    dimes = rng.randint(0, min(4, max_coins - quarters))
    nickels = rng.randint(0, min(3, max_coins - quarters - dimes))
    pennies = rng.randint(1, 4)
    total = quarters * 25 + dimes * 10 + nickels * 5 + pennies
    parts_text = []
    for count, coin in [(quarters, "quarter"), (dimes, "dime"), (nickels, "nickel"), (pennies, "penny")]:
        if count:
            plural = "pennies" if coin == "penny" and count > 1 else coin + ("s" if count > 1 else "")
            parts_text.append(f"${count}$ {plural}")
    return ProblemInstance(
        statement_md="You have " + ", ".join(parts_text) + ".",
        parts=[numeric("How many **cents** is that in total?", total)],
        solution_md=(
            f"${quarters} \\times 25 + {dimes} \\times 10 + {nickels} \\times 5 + {pennies}"
            f" = {total}$ cents."
        ),
    )


SHAPES = [
    ("triangle", 3, 3),
    ("square", 4, 4),
    ("rectangle", 4, 4),
    ("pentagon", 5, 5),
    ("hexagon", 6, 6),
    ("octagon", 8, 8),
]


@generator("earlymath.shapes")
def shapes(rng: random.Random, difficulty: int) -> ProblemInstance:
    pool = SHAPES[: 3 + difficulty]
    name, sides, corners = rng.choice(pool)
    return ProblemInstance(
        statement_md=f"Think about a **{name}**.",
        parts=[
            numeric("How many sides does it have?", sides),
            numeric("How many corners (vertices)?", corners),
        ],
        solution_md=f"A {name} has ${sides}$ sides and ${corners}$ corners.",
    )
