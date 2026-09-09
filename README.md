<h1 align="center">hiver support agent</h1>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="python 3.11" />
  <img src="https://img.shields.io/badge/version-0.1.0-informational" alt="version 0.1.0" />
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="code style: black" />
  <img src="https://img.shields.io/badge/lint-ruff-red?logo=ruff&logoColor=white" alt="lint: ruff" />
  <img src="https://img.shields.io/badge/tests-121%20passed-green?logo=pytest&logoColor=white" alt="tests: 121 passed" />
  <img src="https://img.shields.io/badge/repro-%3C15%20min-brightgreen" alt="repro under 15 min" />
  <img src="https://img.shields.io/badge/drafter-Groq-orange" alt="drafter: Groq" />
  <img src="https://img.shields.io/badge/judge-Gemini-blue" alt="judge: Gemini" />
  <img src="https://img.shields.io/badge/embeddings-MiniLM--L6--v2-yellow" alt="embeddings: MiniLM-L6-v2" />
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="license: Apache 2.0" />
</p>

<p align="center">
  Intent-routed AI support agent for ChaseSupport Twitter threads: a local
  embedding + logistic-regression classifier routes each customer message
  through a thread-state machine, Groq drafts replies grounded in retrieved
  same-intent brand resolutions, Gemini judges them as gate + critic, and
  low-confidence cases escalate with a written reason. Proof (golden set,
  baselines, calibrated judge, report) over polish.
</p>

## Setup

Prerequisites: `uv`, `kaggle` credentials (for raw dumps), and API keys (for
live LLM calls only — everything else reproduces offline from cache).

```bash
make setup     # uv sync (idempotent)
make data      # download Kaggle dumps to data/raw/ (skipped when present)
make subsample # Chase thread extraction + cross-brand social mining
make train     # Phase-A training + ceiling (reproduces report §7)
make test      # full suite (118 tests, needs the ST model cached)
make style     # black + ruff
make build     # headline numbers from cache, zero live calls
make build ARGS="--live 3"  # + 3-thread live smoke (needs keys)
make dev       # offline pipeline demo: one golden thread, fake LLMs
make clean     # caches, __pycache__
```

Timings on a 15 GB CPU box: `make test` ~30 s (first run downloads the
90 MB encoder once), `make train` ~4 min, `make build` ~1 min, `make build
--live 3` ~2 min. Raw dumps (~520 MB) live under gitignored `data/raw/`
and are never committed.

## .env setup

Copy `.env.example` to `.env` and fill in keys. Only the `--live` smoke
subset and live drafting/judging need keys; training, eval, and cached
repro run without them (and fail loudly if keys are required but missing).

| Variable | Used by | Default |
|---|---|---|
| `GROQ_API_KEY` | Drafter (`src/draft.py`, Groq endpoint) | _(required for live)_ |
| `GROQ_MODEL` | Drafter model id, recorded in artifacts | `openai/gpt-oss-20b` |
| `GEMINI_API_KEY` | Judge (`src/judge.py`, OpenAI-compatible endpoint) | _(required for live)_ |
| `GEMINI_BASE_URL` | Judge endpoint | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `GEMINI_MODEL` | Judge model id, recorded in artifacts | `gemini-2.5-flash` |

Code reads env only via `settings` (`src/utils/config.py`); logs only via
`logger` (`src/utils/logger.py`). See `docs/report.md` for results and
`docs/design.md` for the frozen architecture spec.
