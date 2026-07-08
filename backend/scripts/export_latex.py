"""Export every displayable markdown document to JSON so
frontend/scripts/check-katex.mjs can validate it with the app's real
markdown+KaTeX pipeline.

Sources: seed YAML lessons/examples/descriptions, every problem generator
(all difficulties, many seeds), and — when the real database exists — all
stored lessons and problems (AI-generated and ingested-book content).

Usage: ../.venv/bin/python scripts/export_latex.py [out.json] (from backend/)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def add(out: list, source: str, md) -> None:
    if md and isinstance(md, str) and md.strip():
        out.append({"source": source, "md": md})


def collect_generators(out: list, seeds: int = 40) -> None:
    from app.content.generators import REGISTRY, make_instance

    for key in sorted(REGISTRY):
        for difficulty in (1, 2, 3):
            for seed in range(1, seeds + 1):
                inst = make_instance(key, seed, difficulty)
                src = f"generator:{key} d{difficulty} s{seed}"
                add(out, src, inst.statement_md)
                add(out, src, inst.solution_md)
                for p in inst.parts:
                    add(out, src, p.prompt_md)
                    for choice in p.choices or []:
                        add(out, src, choice)


def collect_seed(out: list) -> None:
    import yaml

    from app.config import SEED_DIR

    for path in sorted(SEED_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        for unit in doc.get("units", []):
            for t in unit.get("topics", []):
                src = f"seed:{t['slug']}"
                add(out, src, t.get("lesson", ""))
                add(out, src, t.get("description", ""))
                for ex in t.get("worked_examples", []):
                    add(out, src, ex.get("problem", ""))
                    add(out, src, ex.get("solution", ""))


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
            add(out, src, lesson.content_md)
            for ex in lesson.worked_examples or []:
                add(out, src, ex.get("problem_md", ""))
                add(out, src, ex.get("solution_md", ""))
        for problem in db.scalars(select(Problem)):
            src = f"db:problem:{problem.id}"
            add(out, src, problem.statement_md)
            add(out, src, problem.solution_md)
            for part in problem.parts or []:
                add(out, src, part.get("prompt_md", ""))
                for choice in part.get("choices") or []:
                    add(out, src, choice)


def main() -> None:
    out: list = []
    collect_seed(out)
    collect_generators(out)
    collect_db(out)
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/educator-latex.json")
    dest.write_text(json.dumps(out))
    print(f"collected {len(out)} markdown documents -> {dest}")


if __name__ == "__main__":
    main()
