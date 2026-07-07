# Educator

A local, single-user adaptive math learning app in the style of
[Math Academy](https://www.mathacademy.com/): a prerequisite knowledge graph,
mastery-based progression, spaced repetition (FSRS), XP and daily goals — plus
the ability to upload a textbook PDF and have the app turn it into a course.

## Running

```bash
./dev.sh    # development: backend on :8700 with reload, frontend on :5180
./run.sh    # production: builds the frontend, serves everything on :8700
./check.sh  # verification gate: pytest + tsc + vite build
```

## What's inside

- **13 built-in courses, ~340 topics**: arithmetic → pre-algebra → algebra →
  precalc/calculus → Methods of Proof, Linear Algebra, Multivariable Calculus,
  Discrete Math, Abstract Algebra, Probability & Statistics, Differential
  Equations, Math for ML, and Mathematical Methods for the Physical Sciences I/II,
  all in one prerequisite graph.
- **Learn loop**: lessons with worked examples, then scaffolded practice through
  3 difficulty tiers. ~46 procedural problem generators with exact sympy-checked
  answers cover the foundations; advanced topics get AI-written lessons and
  AI-generated (statically verified) problem sets on demand.
- **Retention**: FSRS spaced repetition per topic, a daily queue (due reviews →
  quizzes → new frontier lessons), XP, daily goals, and streaks.
- **Placement diagnostic**: ~25 adaptive questions find your knowledge frontier
  so you skip what you already know.
- **Upload a textbook**: PDF → extract → segment → LLM-derived topic graph welded
  into the curriculum → lessons + problems (with answer verification) → your
  review → published course, taught by the same engine.
- **AI hints & explanations** during practice, streamed from your local Ollama
  (or Claude if configured).

## Stack

- **Backend**: FastAPI + SQLite (SQLAlchemy), sympy answer checking, py-fsrs
  spaced repetition, PyMuPDF extraction. Lives in `backend/`.
- **Frontend**: React + Vite + TypeScript, KaTeX math rendering. Lives in `frontend/`.
- **AI**: pluggable — Ollama (default, free, local) and the Anthropic API
  (optional, for high-stakes jobs like textbook ingestion). Configured in Settings.

All state lives in `data/` (gitignored): the SQLite DB, uploaded PDFs, and
extraction artifacts.

## Durability

- **Schema migrations**: the database schema is managed by Alembic. On startup the
  app backs up the DB (if a migration is pending), then upgrades to head — your
  learning history survives schema changes. After editing `app/models.py`, run
  `cd backend && ../.venv/bin/alembic revision --autogenerate -m "what changed"`
  and review the generated file; `tests/test_maintenance.py` fails if models and
  migrations ever drift apart.
- **Backups**: `data/backups/` keeps the 14 most recent snapshots (taken at
  startup, throttled to every 6 hours; always taken before a migration).
- **Pinned dependencies**: reproduce the exact environment with
  `pip install -r backend/requirements.lock`.
- **Curriculum map**: `docs/course-map.html` is a standalone visual of every
  course and prerequisite; regenerate with
  `backend/scripts/export_course_map.py` after curriculum changes.
