import random

from .base import ProblemInstance, generator, mc, numeric


@generator("geometry.perimeter_area")
def perimeter_area(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty <= 2 or rng.random() < 0.5:
        w = rng.randint(2, 9 + difficulty * 4)
        h = rng.randint(2, 9 + difficulty * 4)
        return ProblemInstance(
            statement_md=f"A rectangle is ${w}$ units wide and ${h}$ units tall.",
            parts=[
                numeric("Perimeter:", 2 * (w + h)),
                numeric("Area:", w * h),
            ],
            solution_md=(
                f"Perimeter $= 2({w} + {h}) = {2*(w+h)}$; area $= {w} \\times {h} = {w*h}$."
            ),
        )
    b = rng.randint(4, 20)
    h = rng.choice([x for x in range(3, 15) if (b * x) % 2 == 0])
    return ProblemInstance(
        statement_md=f"A triangle has base ${b}$ and height ${h}$.",
        parts=[numeric("Area:", b * h // 2)],
        solution_md=f"Area $= \\tfrac{{1}}{{2}} \\times {b} \\times {h} = {b*h//2}$.",
    )


@generator("geometry.coordinate_plane")
def coordinate_plane(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 5, 2: 8, 3: 12}[difficulty]
    x = rng.choice([v for v in range(-hi, hi + 1) if v != 0])
    y = rng.choice([v for v in range(-hi, hi + 1) if v != 0])
    quadrant = {(True, True): "I", (False, True): "II", (False, False): "III", (True, False): "IV"}[
        (x > 0, y > 0)
    ]
    if difficulty == 1:
        return ProblemInstance(
            statement_md=f"Consider the point $({x}, {y})$.",
            parts=[mc(rng, "Which quadrant is it in?", f"Quadrant {quadrant}",
                      [f"Quadrant {q}" for q in ["I", "II", "III", "IV"] if q != quadrant])],
            solution_md=f"$x$ is {'positive' if x > 0 else 'negative'} and $y$ is {'positive' if y > 0 else 'negative'}: Quadrant {quadrant}.",
        )
    dx, dy = rng.randint(1, 6), rng.randint(1, 6)
    return ProblemInstance(
        statement_md=(
            f"Start at $({x}, {y})$ and move ${dx}$ units right and ${dy}$ units down. "
            "Where do you land?"
        ),
        parts=[numeric("New $x$-coordinate:", x + dx), numeric("New $y$-coordinate:", y - dy)],
        solution_md=f"Right adds to $x$, down subtracts from $y$: $({x + dx}, {y - dy})$.",
    )
