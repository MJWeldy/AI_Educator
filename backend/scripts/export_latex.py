"""Collect every LaTeX fragment the app can display into a JSON file, so
frontend/scripts/check-katex.mjs can compile each one with the real KaTeX.

Sources: seed YAML lessons/examples, every problem generator (all difficulties,
many seeds), and — when the real database exists — all stored lessons and
problems (i.e. AI-generated and ingested-book content).

Usage: ../.venv/bin/python scripts/export_latex.py [out.json] (from backend/)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MATH_DISPLAY = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
# Inline math: delimiters are unescaped $; \$ inside stays part of the content.
MATH_INLINE = re.compile(r"(?<!\\)\$((?:\\.|[^$\\])+?)\$")
PAREN_BLOCK = re.compile(r"(?<!\\)\\\[([\s\S]*?)(?<!\\)\\\]")
PAREN_INLINE = re.compile(r"(?<!\\)\\\(([\s\S]*?)(?<!\\)\\\)")


def normalize(md: str) -> str:
    """Same delimiter normalization the frontend Markdown component applies."""
    strip = lambda body: re.sub(r"\\+\s*$", "", body)  # noqa: E731
    md = PAREN_BLOCK.sub(lambda m: f"$${strip(m.group(1))}$$", md)
    return PAREN_INLINE.sub(lambda m: f"${strip(m.group(1))}$", md)


def fragments(md: str, source: str, out: list, display_hint: bool = False) -> None:
    if not md:
        return
    md = normalize(str(md))
    rest = MATH_DISPLAY.sub(
        lambda m: out.append({"source": source, "math": m.group(1), "display": True}) or " ",
        md,
    )
    for m in MATH_INLINE.finditer(rest):
        out.append({"source": source, "math": m.group(1), "display": False})


def collect_generators(out: list, seeds: int = 40) -> None:
    from app.content.generators import REGISTRY, make_instance

    for key in sorted(REGISTRY):
        for difficulty in (1, 2, 3):
            for seed in range(1, seeds + 1):
                inst = make_instance(key, seed, difficulty)
                src = f"generator:{key} d{difficulty} s{seed}"
                fragments(inst.statement_md, src, out)
                fragments(inst.solution_md, src, out)
                for p in inst.parts:
                    fragments(p.prompt_md, src, out)
                    for choice in p.choices or []:
                        fragments(choice, src, out)


def collect_seed(out: list) -> None:
    import yaml

    from app.config import SEED_DIR

    for path in sorted(SEED_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        for unit in doc.get("units", []):
            for t in unit.get("topics", []):
                src = f"seed:{t['slug']}"
                fragments(t.get("lesson", ""), src, out)
                fragments(t.get("description", ""), src, out)
                for ex in t.get("worked_examples", []):
                    fragments(ex.get("problem", ""), src, out)
                    fragments(ex.get("solution", ""), src, out)


def collect_db(out: list) -> None:
    from sqlalchemy import select

    from app.config import DATA_DIR
    from app.db import SessionLocal
    from app.models import Lesson, Problem

    if not (DATA_DIR / "educator.db").exists():
        return
    with SessionLocal() as db:
        for lesson in db.scalars(select(Lesson)):
            src = f"db:lesson:{lesson.id}"
            fragments(lesson.content_md, src, out)
            for ex in lesson.worked_examples or []:
                fragments(ex.get("problem_md", ""), src, out)
                fragments(ex.get("solution_md", ""), src, out)
        for problem in db.scalars(select(Problem)):
            src = f"db:problem:{problem.id}"
            fragments(problem.statement_md, src, out)
            fragments(problem.solution_md, src, out)
            for part in problem.parts or []:
                fragments(part.get("prompt_md", ""), src, out)
                for choice in part.get("choices") or []:
                    fragments(choice, src, out)


def main() -> None:
    out: list = []
    collect_seed(out)
    collect_generators(out)
    collect_db(out)
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/educator-latex.json")
    dest.write_text(json.dumps(out))
    print(f"collected {len(out)} math fragments -> {dest}")


if __name__ == "__main__":
    main()
