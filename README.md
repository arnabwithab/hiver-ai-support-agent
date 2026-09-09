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

```bash
git clone https://github.com/arnabwithab/hiver-ai-support-agent.git
cd hiver-ai-support-agent
make setup                  # sets up dev environment
make test                   # 123 tests + pulls encoder
make build                  # headline numbers from cache, zero live calls (~1 min)
make verify                 # recheck report arithmetic over committed evidence, keyless (replays verdicts, does not re-judge)
make dev                    # offline pipeline demo: one golden thread, fake LLMs
```

### Full-number reproduction (needs credentials, +10 min)

```bash
make data                   # Kaggle dumps to data/raw/ (~520 MB, needs kaggle CLI + credentials)
make subsample              # Chase thread extraction + social mining
make train                  # Phase-A training + ceiling 0.887/0.786 (~4 min)
```

### Envicronment variable setup

```
cp .env.example .env
```

| Variable | Used by |
|---|---|
| `GROQ_API_KEY` | Drafter (`src/draft.py`, Groq endpoint)
| `GEMINI_API_KEY` | Judge (`src/judge.py`, OpenAI-compatible endpoint)

