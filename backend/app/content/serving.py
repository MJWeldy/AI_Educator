"""One place that serves problems and resolves submissions, whether the
problem is procedural (generator_key + seed) or stored (Problem row from an
ingested textbook)."""

import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Problem, Topic
from .generators import REGISTRY, make_instance


@dataclass
class Served:
    problem_id: int | None
    generator_key: str | None
    seed: int | None
    difficulty: int
    statement_md: str
    parts_public: list[dict]

    def ref(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "generator_key": self.generator_key,
            "seed": self.seed,
            "difficulty": self.difficulty,
        }


def _public_parts(parts: list[dict]) -> list[dict]:
    return [
        {
            "prompt_md": p.get("prompt_md", ""),
            "answer_type": p.get("answer_type", "numeric"),
            "choices": p.get("choices"),
        }
        for p in parts
    ]


def pick_problem(
    db: Session,
    topic: Topic,
    difficulty: int,
    rng: random.Random | None = None,
    verified_only: bool = False,
) -> Served | None:
    rng = rng or random.Random()
    keys = [k for k in (topic.generator_keys or []) if k in REGISTRY]
    if keys:
        key = rng.choice(keys)
        seed = rng.randrange(1, 2**31)
        inst = make_instance(key, seed, difficulty)
        pub = inst.public_dict()
        return Served(
            problem_id=None,
            generator_key=key,
            seed=seed,
            difficulty=difficulty,
            statement_md=pub["statement_md"],
            parts_public=pub["parts"],
        )

    q = select(Problem).where(Problem.topic_id == topic.id)
    if verified_only:
        q = q.where(Problem.answer_verified.is_(True))
    stored = db.scalars(q).all()
    if not stored:
        return None
    at_difficulty = [p for p in stored if p.difficulty == difficulty]
    problem = rng.choice(at_difficulty or stored)
    return Served(
        problem_id=problem.id,
        generator_key=None,
        seed=None,
        difficulty=problem.difficulty,
        statement_md=problem.statement_md,
        parts_public=_public_parts(problem.parts),
    )


def resolve_submission(
    db: Session,
    *,
    problem_id: int | None = None,
    generator_key: str | None = None,
    seed: int | None = None,
    difficulty: int = 1,
) -> tuple[list[dict], dict, str]:
    """Returns (full parts with canonicals, presented snapshot, solution_md)."""
    if problem_id is not None:
        problem = db.get(Problem, problem_id)
        if problem is None:
            raise KeyError("problem not found")
        presented = {
            "statement_md": problem.statement_md,
            "parts": problem.parts,
            "solution_md": problem.solution_md,
        }
        return list(problem.parts), presented, problem.solution_md

    if not generator_key or generator_key not in REGISTRY or seed is None:
        raise KeyError("unknown generator")
    inst = make_instance(generator_key, seed, difficulty)
    parts = [
        {
            "prompt_md": p.prompt_md,
            "answer_type": p.answer_type,
            "canonical": p.canonical,
            "tolerance": p.tolerance,
            "choices": p.choices,
        }
        for p in inst.parts
    ]
    return parts, inst.to_dict(), inst.solution_md
