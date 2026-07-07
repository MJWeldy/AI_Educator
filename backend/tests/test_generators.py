"""Property tests: every generator, every difficulty, many seeds —
the canonical answer must pass its own checker, and instances must be
deterministic in (key, seed, difficulty)."""

import pytest

from app.content import checking
from app.content.generators import REGISTRY, make_instance

SEEDS = range(1, 60)


@pytest.mark.parametrize("key", sorted(REGISTRY))
@pytest.mark.parametrize("difficulty", [1, 2, 3])
def test_canonical_passes_checker(key: str, difficulty: int):
    for seed in SEEDS:
        inst = make_instance(key, seed, difficulty)
        assert inst.statement_md.strip(), f"{key} seed={seed} empty statement"
        assert inst.parts, f"{key} seed={seed} has no parts"
        for part in inst.parts:
            p = {
                "answer_type": part.answer_type,
                "canonical": part.canonical,
                "tolerance": part.tolerance,
                "choices": part.choices,
            }
            if part.answer_type == "multiple_choice":
                assert part.choices and len(part.choices) >= 2, f"{key} seed={seed}"
                idx = int(part.canonical)
                assert 0 <= idx < len(part.choices), f"{key} seed={seed}"
                user = part.canonical
            elif part.answer_type == "expression":
                user = part.canonical.replace("*", "")
            else:
                user = part.canonical
            ok, feedback = checking.check_part(p, user)
            assert ok, f"{key} d={difficulty} seed={seed}: canonical {user!r} rejected ({feedback})"


@pytest.mark.parametrize("key", sorted(REGISTRY))
def test_deterministic(key: str):
    for seed in (7, 99, 12345):
        a = make_instance(key, seed, 2)
        b = make_instance(key, seed, 2)
        assert a.to_dict() == b.to_dict()


@pytest.mark.parametrize("key", sorted(REGISTRY))
def test_wrong_answer_fails(key: str):
    """A garbage answer should never be accepted."""
    for seed in (3, 44):
        inst = make_instance(key, seed, 1)
        for part in inst.parts:
            p = {
                "answer_type": part.answer_type,
                "canonical": part.canonical,
                "tolerance": part.tolerance,
                "choices": part.choices,
            }
            ok, _ = checking.check_part(p, "999999883")
            assert not ok, f"{key} seed={seed} accepted garbage"


def test_all_seed_generator_keys_exist(seeded_db):
    from sqlalchemy import select

    from app.models import Topic

    missing = []
    for topic in seeded_db.scalars(select(Topic)):
        for k in topic.generator_keys:
            if k not in REGISTRY:
                missing.append((topic.slug, k))
    assert not missing, f"seed references unimplemented generators: {missing}"
