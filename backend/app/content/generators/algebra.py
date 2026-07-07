import random

from .base import ProblemInstance, ProblemPart, generator, mc, numeric


def expression(prompt_md: str, canonical: str) -> ProblemPart:
    return ProblemPart(prompt_md=prompt_md, answer_type="expression", canonical=canonical)


@generator("algebra.translate")
def translate(rng: random.Random, difficulty: int) -> ProblemInstance:
    a = rng.randint(2, 9)
    b = rng.randint(1, 12)
    phrases = [
        (f"{a} times a number, increased by {b}", f"${a}x + {b}$", [f"${a}(x + {b})$", f"${a} + {b}x$", f"${a}x - {b}$"]),
        (f"{b} less than {a} times a number", f"${a}x - {b}$", [f"${b} - {a}x$", f"${a}(x - {b})$", f"${a}x + {b}$"]),
        (f"{a} times the sum of a number and {b}", f"${a}(x + {b})$", [f"${a}x + {b}$", f"${a} + x + {b}$", f"${a}x \\cdot {b}$"]),
        (f"the quotient of a number and {a}, decreased by {b}", f"$\\dfrac{{x}}{{{a}}} - {b}$", [f"$\\dfrac{{{a}}}{{x}} - {b}$", f"$\\dfrac{{x - {b}}}{{{a}}}$", f"${a}x - {b}$"]),
    ]
    text, correct, distractors = phrases[rng.randrange(len(phrases))]
    return ProblemInstance(
        statement_md=f'Translate into an algebraic expression: "*{text}*" (let $x$ be the number).',
        parts=[mc(rng, "Which expression matches?", correct, distractors)],
        solution_md=f"Reading piece by piece gives {correct}.",
    )


@generator("algebra.evaluate")
def evaluate(rng: random.Random, difficulty: int) -> ProblemInstance:
    a, b, c = rng.randint(2, 6), rng.randint(1, 9), rng.randint(2, 5)
    x = rng.randint(-4, 6) if difficulty >= 2 else rng.randint(1, 6)
    y = rng.randint(-3, 5) if difficulty >= 3 else rng.randint(1, 4)
    if difficulty == 1:
        expr, val = f"{a}x + {b}", a * x + b
        sub = f"{a}({x}) + {b} = {a*x} + {b} = {val}"
    elif difficulty == 2:
        expr, val = f"{a}x^2 - {b}", a * x * x - b
        sub = f"{a}({x})^2 - {b} = {a}\\cdot{x*x} - {b} = {val}"
    else:
        expr, val = f"{a}x - {c}y + {b}", a * x - c * y + b
        sub = f"{a}({x}) - {c}({y}) + {b} = {a*x} - {c*y} + {b} = {val}"
    given = f"$x = {x}$" + (f" and $y = {y}$" if difficulty == 3 else "")
    return ProblemInstance(
        statement_md=f"Evaluate ${expr}$ when {given}.",
        parts=[numeric("Value:", val)],
        solution_md=f"Substitute: ${sub}$.",
    )


@generator("algebra.combine_like_terms")
def combine_like_terms(rng: random.Random, difficulty: int) -> ProblemInstance:
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    c, d = rng.randint(1, 9), rng.randint(1, 9)
    if difficulty == 1:
        stmt = f"{a}x + {b}x"
        canonical = f"{a+b}*x"
        pretty = f"{a+b}x"
    elif difficulty == 2:
        stmt = f"{a}x + {c} + {b}x - {d}"
        canonical = f"{a+b}*x + {c - d}"
        pretty = f"{a+b}x {'+' if c-d >= 0 else '-'} {abs(c-d)}" if c != d else f"{a+b}x"
        if c == d:
            canonical = f"{a+b}*x"
    else:
        stmt = f"{a}x + {c}y - {b}x + {d}y"
        coeff_x = a - b
        x_term = f"{coeff_x}*x" if coeff_x != 0 else ""
        canonical = (x_term + f" + {c+d}*y") if x_term else f"{c+d}*y"
        pretty = (f"{coeff_x}x + " if coeff_x else "") + f"{c+d}y"
    return ProblemInstance(
        statement_md=f"Simplify by combining like terms: ${stmt}$",
        parts=[expression("Simplified expression:", canonical)],
        solution_md=f"Group the like terms: ${pretty}$.",
    )


@generator("algebra.distribute")
def distribute(rng: random.Random, difficulty: int) -> ProblemInstance:
    a = rng.randint(2, 7) * (1 if difficulty < 3 else rng.choice([1, -1]))
    b, c = rng.randint(1, 9), rng.randint(1, 9)
    op = rng.choice(["+", "-"])
    inner = f"x {op} {c}"
    prod_c = a * c if op == "+" else -a * c
    canonical = f"{a}*x {'+' if prod_c >= 0 else '-'} {abs(prod_c)}" if prod_c != 0 else f"{a}*x"
    if difficulty >= 2:
        inner = f"{b}x {op} {c}"
        coeff = a * b
        canonical = f"{coeff}*x {'+' if prod_c >= 0 else '-'} {abs(prod_c)}"
    a_str = f"({a})" if a < 0 else str(a)
    return ProblemInstance(
        statement_md=f"Expand: ${a_str}({inner})$",
        parts=[expression("Expanded expression:", canonical)],
        solution_md=f"Multiply each term inside by ${a}$: ${canonical.replace('*', '')}$.",
    )


@generator("algebra.one_step")
def one_step(rng: random.Random, difficulty: int) -> ProblemInstance:
    x = rng.randint(-12, 12) if difficulty >= 2 else rng.randint(1, 12)
    kind = rng.choice(["add", "sub", "mul", "div"])
    a = rng.randint(2, 9 + difficulty * 3)
    if kind == "add":
        eq, step = f"x + {a} = {x + a}", f"subtract ${a}$ from both sides"
    elif kind == "sub":
        eq, step = f"x - {a} = {x - a}", f"add ${a}$ to both sides"
    elif kind == "mul":
        a = a if difficulty < 2 else a * rng.choice([1, -1])
        a_str = f"({a})" if a < 0 else str(a)
        eq, step = f"{a_str}x = {a * x}", f"divide both sides by ${a}$"
    else:
        eq, step = f"\\dfrac{{x}}{{{a}}} = {x}", f"multiply both sides by ${a}$"
        x = x * a
    return ProblemInstance(
        statement_md=f"Solve for $x$: ${eq}$",
        parts=[numeric("$x =$", x)],
        solution_md=f"To isolate $x$, {step}: $x = {x}$.",
    )


@generator("algebra.two_step")
def two_step(rng: random.Random, difficulty: int) -> ProblemInstance:
    x = rng.randint(-9, 9) if difficulty >= 2 else rng.randint(1, 9)
    a = rng.randint(2, 6 + difficulty * 2)
    b = rng.randint(1, 15)
    op = rng.choice(["+", "-"])
    rhs = a * x + b if op == "+" else a * x - b
    if difficulty == 3 and rng.random() < 0.5:
        eq = f"{a}(x {op} {b}) = {a * (x + b) if op == '+' else a * (x - b)}"
        rhs_val = a * (x + b) if op == "+" else a * (x - b)
        sol = f"Divide by ${a}$ first: $x {op} {b} = {rhs_val // a}$, then solve: $x = {x}$."
    else:
        eq = f"{a}x {op} {b} = {rhs}"
        sol = (
            f"{'Subtract' if op == '+' else 'Add'} ${b}$: ${a}x = {a*x}$. "
            f"Divide by ${a}$: $x = {x}$."
        )
    return ProblemInstance(
        statement_md=f"Solve for $x$: ${eq}$",
        parts=[numeric("$x =$", x)],
        solution_md=sol,
    )


@generator("algebra.inequality")
def inequality(rng: random.Random, difficulty: int) -> ProblemInstance:
    x = rng.randint(-9, 12)
    a = rng.randint(2, 8)
    symbols = ["<", ">", "\\le", "\\ge"]
    sym = rng.choice(symbols)
    flip = {"<": ">", ">": "<", "\\le": "\\ge", "\\ge": "\\le"}
    if difficulty == 1:
        b = rng.randint(1, 10)
        eq = f"x + {b} {sym} {x + b}"
        ans_sym, sol = sym, f"Subtract ${b}$ from both sides."
    elif difficulty == 2:
        eq = f"{a}x {sym} {a * x}"
        ans_sym, sol = sym, f"Divide both sides by ${a}$ (positive — the inequality keeps its direction)."
    else:
        eq = f"-{a}x {sym} {-a * x}"
        ans_sym = flip[sym]
        sol = f"Divide both sides by $-{a}$ — dividing by a negative **flips** the inequality."
    display = {"<": "<", ">": ">", "\\le": "≤", "\\ge": "≥"}
    return ProblemInstance(
        statement_md=f"Solve for $x$: ${eq}$",
        parts=[
            numeric("Boundary value:", x),
            mc(
                rng,
                "Direction of the solution:",
                f"$x {ans_sym} {x}$",
                [f"$x {s} {x}$" for s in symbols if s != ans_sym],
            ),
        ],
        solution_md=sol + f" Solution: $x {ans_sym} {x}$.",
    )
