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

## Stack

- **Backend**: FastAPI + SQLite (SQLAlchemy), sympy answer checking, py-fsrs
  spaced repetition, PyMuPDF extraction. Lives in `backend/`.
- **Frontend**: React + Vite + TypeScript, KaTeX math rendering. Lives in `frontend/`.
- **AI**: pluggable — Ollama (default, free, local) and the Anthropic API
  (optional, for high-stakes jobs like textbook ingestion). Configured in Settings.

All state lives in `data/` (gitignored): the SQLite DB, uploaded PDFs, and
extraction artifacts.
