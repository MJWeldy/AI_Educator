"""Grade-school data and probability (Khan grades 6–7)."""

import random
from fractions import Fraction

from .base import ProblemInstance, ProblemPart, frac_answer, generator, numeric


@generator("data.mean_median_mode")
def mean_median_mode(rng: random.Random, difficulty: int) -> ProblemInstance:
    n = 5 if difficulty <= 2 else 7
    mean = rng.randint(4, 20 if difficulty == 1 else 60)
    # Deviations that sum to zero keep the mean an integer.
    devs = [rng.randint(-3, 3) for _ in range(n - 1)]
    devs.append(-sum(devs))
    values = [max(1, mean + d) for d in devs]
    # Force an unambiguous mode by repeating one value.
    values[1] = values[0]
    total = sum(values)
    if total % n:  # repair the mean after clamping/mode-forcing
        values[-1] += n - (total % n)
    values.sort()
    shown = rng.sample(values, len(values))
    mode = max(set(values), key=values.count)
    median = values[n // 2]
    return ProblemInstance(
        statement_md="Here are the values: $" + ",\\ ".join(map(str, shown)) + "$",
        parts=[
            numeric("What is the **mean**?", sum(values) // n),
            numeric("What is the **median**?", median),
            numeric("What is the **mode**?", mode),
        ],
        solution_md=(
            f"Sorted: ${', '.join(map(str, values))}$. "
            f"Mean $= {sum(values)} \\div {n} = {sum(values) // n}$; the middle value is ${median}$; "
            f"the most frequent value is ${mode}$."
        ),
    )


@generator("data.probability")
def probability(rng: random.Random, difficulty: int) -> ProblemInstance:
    colors = ["red", "blue", "green", "yellow"]
    k = 2 if difficulty == 1 else 3
    counts = [rng.randint(1, 4 + difficulty * 2) for _ in range(k)]
    names = rng.sample(colors, k)
    total = sum(counts)
    target = rng.randrange(k)
    listing = " and ".join(f"${c}$ {n}" for c, n in zip(counts, names))
    if difficulty == 3 and rng.random() < 0.5:
        p = Fraction(total - counts[target], total)
        question = f"What is the probability of drawing a marble that is **not** {names[target]}?"
        why = f"${total} - {counts[target]} = {total - counts[target]}$ favorable out of ${total}$."
    else:
        p = Fraction(counts[target], total)
        question = f"What is the probability of drawing a **{names[target]}** marble?"
        why = f"${counts[target]}$ favorable out of ${total}$ total."
    return ProblemInstance(
        statement_md=f"A bag holds {listing} marbles. One marble is drawn at random.",
        parts=[
            ProblemPart(
                prompt_md=question + " (as a fraction in lowest terms)",
                answer_type="fraction_lowest",
                canonical=frac_answer(p),
            )
        ],
        solution_md=why + f" Probability $= {frac_answer(p)}$.",
    )
