# Educator

A local, single-user (or single-household) adaptive math learning app in the
style of [Math Academy](https://www.mathacademy.com/): a prerequisite knowledge
graph, mastery-based progression, spaced repetition (FSRS), XP and daily goals —
plus the ability to upload a textbook PDF and have the app turn it into a course.

Everything runs on your machine. No accounts, no subscription, no telemetry.

## Quickstart

**Requirements**: Python 3.12+, Node.js 18+, a POSIX shell (macOS or Linux;
on Windows use WSL). No GPU or AI service is required — see
[AI features](#ai-features-optional) below.

```bash
git clone https://github.com/MJWeldy/AI_Educator.git
cd AI_Educator
./setup.sh    # one time: creates .venv, installs deps, builds the frontend
./run.sh      # start the app
```

Then open **http://localhost:8700**. First launch creates the database, runs
migrations, and seeds the full curriculum automatically. Take the placement
diagnostic so the daily queue starts at your level.

Day-to-day scripts:

```bash
./run.sh      # production mode: everything on :8700
./dev.sh      # development: backend :8700 with reload, frontend :5180 with HMR
./check.sh    # verification gate: pytest + tsc + vite build
```

## What's inside

- **14 built-in courses, ~360 topics** in one prerequisite graph: Early Math
  (Grades K–2) and arithmetic → pre-algebra (Grades 3–8, aligned with Khan
  Academy's grade courses) → algebra → precalc/calculus → Methods of Proof,
  Linear Algebra, Multivariable Calculus, Discrete Math, Abstract Algebra,
  Probability & Statistics, Differential Equations, Mathematics for ML (through
  the math of attention), and Mathematical Methods for the Physical Sciences I/II.
  The advanced pathway mirrors the [OSSU math curriculum](https://github.com/ossu/math),
  with its recommended materials (MIT OCW, Strang's 18.06SC, Book of Proof,
  d2l.ai, …) linked at the matching topics. See `docs/course-map.html` for a
  visual of the whole graph.
- **Learn loop**: lessons with worked examples, then scaffolded practice through
  3 difficulty tiers. ~60 procedural problem generators with exact
  sympy-checked answers cover Early Math and all of Foundations I; advanced
  topics get AI-written lessons and AI-generated (statically verified) problem
  sets on demand, cached forever once generated.
- **Retention**: FSRS spaced repetition per topic, a daily queue (due reviews →
  quizzes → new frontier lessons), XP, daily goals, and streaks.
- **Placement diagnostic**: ~25 adaptive questions find your knowledge frontier
  so you skip what you already know.
- **Profiles**: multiple learners on one install (kids and adults), each with
  their own progress, reviews, and streaks. Content is shared; progress isn't.
- **Upload a textbook**: PDF → extract → segment → LLM-derived topic graph
  welded into the curriculum → lessons + problems (with answer verification) →
  your review → published course, taught by the same engine.

## AI features (optional)

The grade-school curriculum (Early Math + Foundations I) is **fully usable with
no AI at all** — problems, checking, reviews, diagnostics, and XP all run on
built-in generators. AI powers: hints, "explain my mistake", lesson text for
advanced topics, on-demand problem sets for advanced topics, and PDF textbook
ingestion. Two interchangeable providers, configured in **Settings**:

- **Ollama** (free, local, private): install [Ollama](https://ollama.com), pull
  a model (e.g. `ollama pull gpt-oss:20b` with a big GPU, or a smaller model on
  modest hardware), and the app finds it at `localhost:11434` automatically.
- **Claude API** (paid, stronger): paste an Anthropic API key in Settings.
  Recommended for textbook ingestion, where quality matters most; hints and
  lessons cost fractions of a cent. The "Use Claude for ingestion" toggle
  routes only the high-stakes jobs to the API.

Anything the AI generates is stored in the database — it is never regenerated
or re-billed.

## Stack

- **Backend**: FastAPI + SQLite (SQLAlchemy 2.0, Alembic migrations), sympy
  answer checking, py-fsrs spaced repetition, PyMuPDF extraction. Lives in `backend/`.
- **Frontend**: React + Vite + TypeScript, KaTeX math rendering. Lives in `frontend/`.

All state lives in `data/` (gitignored): the SQLite DB, uploaded PDFs, and
extraction artifacts. **Back up `data/educator.db` to preserve learning history**
(the app also keeps rotating snapshots in `data/backups/` automatically).

## Durability & development notes

- **Schema migrations**: managed by Alembic; on startup the app backs up the DB
  (when a migration is pending) and upgrades in place — learning history
  survives schema changes. After editing `backend/app/models.py`, run
  `cd backend && ../.venv/bin/alembic revision --autogenerate -m "what changed"`
  and review the file; `tests/test_maintenance.py` fails if models and
  migrations drift.
- **Backups**: `data/backups/` keeps the 14 most recent snapshots (startup,
  6-hour throttle, always before a migration).
- **Pinned dependencies**: `backend/requirements.lock` +
  `frontend/package-lock.json` reproduce the exact environment.
- **Curriculum as data**: one YAML per course in `backend/app/content/seed/`,
  synced idempotently at startup — edit topics, prerequisites, lessons, and
  resource links there. Regenerate the visual map with
  `backend/scripts/export_course_map.py`.
- **Tests**: `./check.sh` runs ~390 backend tests (including property tests
  over every problem generator) plus the TypeScript/build gate.
