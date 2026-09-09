<h1 align="center">hiver support agent</h1>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="python 3.11" />
  <img src="https://img.shields.io/badge/version-0.1.0-informational" alt="version 0.1.0" />
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="code style: black" />
  <img src="https://img.shields.io/badge/lint-ruff-red?logo=ruff&logoColor=white" alt="lint: ruff" />
  <img src="https://img.shields.io/badge/tests-121%20passed-green?logo=pytest&logoColor=white" alt="tests: 121 passed" />
  <img src="https://img.shields.io/badge/drafter-Groq-orange" alt="drafter: Groq" />
  <img src="https://img.shields.io/badge/judge-Gemini-blue" alt="judge: Gemini" />
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

Prerequisites: `curl` and a C compiler toolchain (for `uv sync`
dependencies). `uv` itself is bootstrapped by `make setup` when missing.
`kaggle` credentials and LLM API keys are needed only for the tracks
marked below — the core repro is credential-free.

### 15-minute reproduction (credential-free, new PC)

```bash
git clone <repo-url> && cd hiver-ai-support-agent
cp .env.example .env        # no keys needed for this track
make setup                  # installs uv if missing, then uv sync (~3 min first run)
make test                   # 121 tests, ~30 s (pulls the 90 MB encoder once)
make build                  # headline numbers from cache, zero live calls (~1 min)
make dev                    # offline pipeline demo: one golden thread, fake LLMs
```

### Full-number reproduction (needs credentials, +10 min)

```bash
make data                   # Kaggle dumps to data/raw/ (~520 MB, needs kaggle CLI + credentials)
make subsample              # Chase thread extraction + social mining
make train                  # Phase-A training + ceiling 0.887/0.786 (~4 min)
make build ARGS="--live 3"  # + live Groq/Gemini smoke (needs API keys, ~2 min)
```

```bash
make style   # black + ruff
make clean   # caches, __pycache__
```

Raw dumps live under gitignored `data/raw/` and are never committed.
Without `make data`, `make train` runs on synthetic fixtures and prints
that fallback — same code path, smaller numbers.

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
