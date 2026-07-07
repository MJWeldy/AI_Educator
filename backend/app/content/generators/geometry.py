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


@generator("geometry.angles")
def angles(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty == 1:
        total, name = rng.choice([(90, "complementary"), (180, "supplementary")])
        a = rng.randint(10, total - 10)
        return ProblemInstance(
            statement_md=f"Two angles are **{name}** (they add to ${total}°$). One measures ${a}°$.",
            parts=[numeric("The other angle, in degrees:", total - a)],
            solution_md=f"${total}° - {a}° = {total - a}°$.",
        )
    if difficulty == 2:
        a = rng.randint(20, 90)
        b = rng.randint(20, 150 - a)
        return ProblemInstance(
            statement_md=f"A triangle has angles of ${a}°$ and ${b}°$.",
            parts=[numeric("The third angle, in degrees:", 180 - a - b)],
            solution_md=f"Triangle angles sum to $180°$: $180 - {a} - {b} = {180 - a - b}$.",
        )
    a = rng.randint(25, 155)
    return ProblemInstance(
        statement_md=(
            f"Two lines cross. One of the four angles formed measures ${a}°$."
        ),
        parts=[
            numeric("The angle **vertical** (opposite) to it, in degrees:", a),
            numeric("An angle **adjacent** to it on the straight line, in degrees:", 180 - a),
        ],
        solution_md=(
            f"Vertical angles are equal (${a}°$); adjacent angles on a line are "
            f"supplementary ($180 - {a} = {180 - a}°$)."
        ),
    )


@generator("geometry.volume")
def volume(rng: random.Random, difficulty: int) -> ProblemInstance:
    if difficulty == 1:
        l, w, h = rng.randint(2, 6), rng.randint(2, 6), rng.randint(2, 6)
        return ProblemInstance(
            statement_md=f"A box is ${l}$ units long, ${w}$ wide, and ${h}$ tall.",
            parts=[numeric("Volume, in cubic units:", l * w * h)],
            solution_md=f"$V = l \\times w \\times h = {l} \\times {w} \\times {h} = {l*w*h}$.",
        )
    if difficulty == 2:
        e = rng.randint(3, 12)
        return ProblemInstance(
            statement_md=f"A cube has edges of length ${e}$.",
            parts=[numeric("Its volume:", e**3), numeric("Its surface area:", 6 * e * e)],
            solution_md=f"$V = {e}^3 = {e**3}$; surface area $= 6 \\times {e}^2 = {6*e*e}$.",
        )
    l, w = rng.randint(3, 12), rng.randint(2, 9)
    v = l * w * rng.randint(2, 9)
    return ProblemInstance(
        statement_md=(
            f"A rectangular tank with a ${l} \\times {w}$ base holds ${v}$ cubic units of water."
        ),
        parts=[numeric("How deep is the water?", v // (l * w))],
        solution_md=f"depth $= V \\div (l \\times w) = {v} \\div {l*w} = {v // (l*w)}$.",
    )


PYTHAGOREAN_TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41)]


@generator("geometry.pythagorean")
def pythagorean(rng: random.Random, difficulty: int) -> ProblemInstance:
    a, b, c = rng.choice(PYTHAGOREAN_TRIPLES[: 2 + difficulty])
    if difficulty >= 2 and rng.random() < 0.4:
        k = rng.randint(2, 3)
        a, b, c = a * k, b * k, c * k
    if difficulty == 3 and rng.random() < 0.5:
        return ProblemInstance(
            statement_md=(
                f"A right triangle has a hypotenuse of ${c}$ and one leg of ${a}$."
            ),
            parts=[numeric("The other leg:", b)],
            solution_md=f"$b = \\sqrt{{{c}^2 - {a}^2}} = \\sqrt{{{c*c - a*a}}} = {b}$.",
        )
    return ProblemInstance(
        statement_md=f"A right triangle has legs of ${a}$ and ${b}$.",
        parts=[numeric("The hypotenuse:", c)],
        solution_md=(
            f"$c = \\sqrt{{{a}^2 + {b}^2}} = \\sqrt{{{a*a} + {b*b}}} = \\sqrt{{{c*c}}} = {c}$."
        ),
    )
