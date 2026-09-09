<h1 align="center">hiver support agent</h1>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="python 3.11" />
  <img src="https://img.shields.io/badge/version-0.1.0-informational" alt="version 0.1.0" />
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="code style: black" />
  <img src="https://img.shields.io/badge/lint-ruff-red?logo=ruff&logoColor=white" alt="lint: ruff" />
  <img src="https://img.shields.io/badge/tests-123%20passed-green?logo=pytest&logoColor=white" alt="tests: 123 passed" />
  <img src="https://img.shields.io/badge/drafter-Groq-orange" alt="drafter: Groq" />
  <img src="https://img.shields.io/badge/judge-Gemini-blue" alt="judge: Gemini" />
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="license: Apache 2.0" />
</p>

<p align="center">
  Intent-routed AI support agent for ChaseSupport Twitter threads with HITL escalation and LLM-as-a-judge evals.
</p>

## Setup

Prerequisites: `curl`, a C toolchain, `kaggle` CLI with credentials
(you supplied the dataset), and Groq + Gemini API keys (you asked for
an AI agent). `uv` itself is bootstrapped by `make setup` when missing.

```bash
git clone https://github.com/arnabwithab/hiver-ai-support-agent.git
cd hiver-ai-support-agent
cp .env.example .env        # fill in GROQ_API_KEY + GEMINI_API_KEY (table below)
make setup                  # installs uv if missing, then uv sync (~3 min first run)
make data                   # Kaggle dumps to data/raw/ (~520 MB, skipped when present)
make subsample              # Chase thread extraction + social mining
make train                  # Phase-A training + ceiling 0.887/0.786 (~4 min)
make test                   # 123 tests, ~30 s (pulls the 90 MB encoder once)
make build                  # headlines from cache + live smoke (~2 min)
make verify                 # recheck report arithmetic over committed evidence
make dev                    # offline pipeline demo: one golden thread, fake LLMs
```

`make test`, `make build` (without `--live`), and `make verify` also run
with no keys and no data (synthetic fallbacks, clearly labeled) — but the
numbers above assume the full track.

### Envicronment variable setup

```
cp .env.example .env
```

| Variable | Used by |
|---|---|
| `GROQ_API_KEY` | Drafter (`src/draft.py`, Groq endpoint)
| `GEMINI_API_KEY` | Judge (`src/judge.py`, OpenAI-compatible endpoint)

