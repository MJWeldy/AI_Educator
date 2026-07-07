"""Procedural problem generators.

A generator is a pure function (rng, difficulty 1..3) -> ProblemInstance.
Instances are fully determined by (key, seed, difficulty), so attempts only
need to store those three plus a snapshot; regenerating is free.
"""

import random
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from fractions import Fraction


@dataclass
class ProblemPart:
    prompt_md: str
    answer_type: str  # numeric | expression | multiple_choice | exact_string
    canonical: str  # sympy-parseable answer, or the index of the correct choice
    tolerance: float | None = None
    choices: list[str] | None = None


@dataclass
class ProblemInstance:
    statement_md: str
    parts: list[ProblemPart]
    solution_md: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def public_dict(self) -> dict:
        """What the frontend may see before answering."""
        return {
            "statement_md": self.statement_md,
            "parts": [
                {
                    "prompt_md": p.prompt_md,
                    "answer_type": p.answer_type,
                    "choices": p.choices,
                }
                for p in self.parts
            ],
        }


Generator = Callable[[random.Random, int], ProblemInstance]

REGISTRY: dict[str, Generator] = {}


def generator(key: str) -> Callable[[Generator], Generator]:
    def wrap(fn: Generator) -> Generator:
        if key in REGISTRY:
            raise ValueError(f"duplicate generator key {key!r}")
        REGISTRY[key] = fn
        return fn

    return wrap


def make_instance(key: str, seed: int, difficulty: int) -> ProblemInstance:
    fn = REGISTRY.get(key)
    if fn is None:
        raise KeyError(f"unknown generator {key!r}")
    rng = random.Random((hash(key) & 0xFFFFFFFF) ^ (seed * 2654435761 % 2**32))
    return fn(rng, max(1, min(3, difficulty)))


# ── shared helpers ──────────────────────────────────────────────────────


def frac_md(f: Fraction, display: bool = False) -> str:
    """LaTeX for a fraction (or plain integer)."""
    if f.denominator == 1:
        return str(f.numerator)
    tex = f"\\dfrac{{{abs(f.numerator)}}}{{{f.denominator}}}"
    if f < 0:
        tex = "-" + tex
    return tex


def frac_answer(f: Fraction) -> str:
    """Canonical sympy-parseable form of a fraction."""
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def rand_fraction(
    rng: random.Random,
    max_den: int = 12,
    proper: bool = True,
    nonzero: bool = True,
) -> Fraction:
    while True:
        d = rng.randint(2, max_den)
        n = rng.randint(0 if not nonzero else 1, d - 1 if proper else 2 * d)
        f = Fraction(n, d)
        if nonzero and f == 0:
            continue
        return f


def mc(
    rng: random.Random,
    prompt_md: str,
    correct: str,
    distractors: list[str],
) -> ProblemPart:
    """Multiple-choice part; canonical is the index of the correct choice.
    Deduplicates distractors that collide with the answer."""
    seen = {correct}
    clean: list[str] = []
    for d in distractors:
        if d not in seen:
            clean.append(d)
            seen.add(d)
    choices = [correct] + clean[:3]
    rng.shuffle(choices)
    return ProblemPart(
        prompt_md=prompt_md,
        answer_type="multiple_choice",
        canonical=str(choices.index(correct)),
        choices=choices,
    )


def numeric(prompt_md: str, answer: object, tolerance: float | None = None) -> ProblemPart:
    return ProblemPart(
        prompt_md=prompt_md,
        answer_type="numeric",
        canonical=str(answer),
        tolerance=tolerance,
    )
