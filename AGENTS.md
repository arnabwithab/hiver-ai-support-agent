# AGENTS.md

Status: `docs/problem.md` (brief) and `docs/design.md` (frozen, 20 decisions) exist.
`docs/features.json` is created at build time from `docs/design.md` §5–§11.

## Project Overview

Hiver-style AI support agent for **ChaseSupport** Twitter threads: a local ML intent
classifier (no LLM) routes each customer message through a thread-state machine; Groq
drafts replies grounded in retrieved same-intent brand resolutions; Gemini judges them as
gate + critic; low-confidence/low-quality cases escalate with a written reason. The graded
deliverable is a reproducible pipeline plus proof (golden set, baselines, calibrated
judge, ≤6-page report), not a hosted service.

## How to work here

- TDD: test first, then implementation. `tests/` mirrors `src/`. No function ships without one.
- Everything runs through `make` — never call `pytest`/`python` directly. `make test && make style` before anything is done.
- `uv` for Python, never `pip`. `black` + `ruff`. snake_case everywhere.
- Env vars only via `settings` (`src/utils/config.py`); logging only via `logger` (`src/utils/logger.py`).
- Conventional commits (`feat:`, `fix:`, …). Push to git after every feature.
- `docs/design.md` is frozen — changes need user sign-off. Never touch `/docs` otherwise.
- Keep `docs/features.json` updated (status + test state) after every task.

## Hard guardrails (from the design — violations break the graded claims)

- Exactly two LLM call sites: `draft.py` (Groq) and `judge.py` (Gemini). Never add a third.
- Training code must not be able to import the golden hold-out — entrypoint takes `data/golden/dev/` only.
- All text reaching an LLM prompt or a committed artifact passes PII redaction first.
- Log `(raw prediction → override → final label)` on every routing decision.
- Judge model ≠ drafter model. Flag judge-guided retries in artifacts.

## Key Commands

```bash
make setup   # uv sync + ChaseSupport subsample (idempotent)
make dev     # full pipeline end-to-end on the dev slice
make test    # all tests
make style   # black + ruff
make build   # headline numbers from cache + live smoke subset (<15 min)
make clean   # artifacts, caches, __pycache__
```

Makefile targets are thin wrappers over `python -m src...` / `pytest` — no business logic in Make.

## Directory Structure

```
./
├── src/
│   ├── ingest.py        # thread reconstruction from reply-ID chains + PII redaction
│   ├── intent.py        # embedding + linear head, calibration, confidence gate
│   ├── state.py         # thread-state machine (Cases A–D, veto, inheritance)
│   ├── retrieve.py      # per-intent clustering + same-intent retrieval
│   ├── draft.py         # LLM call site #1 (Groq)
│   ├── judge.py         # LLM call site #2 (Gemini), ≤3 retries
│   ├── orchestrate.py   # the DAG (design §5), nothing else
│   ├── eval/
│   │   ├── metrics.py   # accuracy/F1, case slices, kappa + bootstrap CIs
│   │   └── baselines.py # trivial (majority+canned) + simple (TF-IDF) baselines
│   └── utils/
│       ├── config.py    # settings (single instantiation)
│       └── logger.py    # logger (single import path)
├── tests/               # mirrors src/
├── data/
│   ├── golden/          # dev slice + LOCKED hold-out
│   └── cache/           # LLM artifacts keyed by (provider, model, prompt hash)
├── docs/                # problem.md, design.md (FROZEN), features.json, report.md
├── Makefile  .env.example  .gitignore  README.md  AGENTS.md
```

## Multi-Agent Workflow

### Flow

1. **Plan**: Identify independent features from `features.json`. Features touching the same files are dependent and batched sequentially.
2. **Build**: Spawn up to 3 builder subagents at a time via the Task tool. When one completes, spawn the next pending feature.
3. **E2E** (if applicable): When all builders complete, spawn the playwright-tester to run browser tests.
4. **Review**: Spawn the ponytail-reviewer to audit the combined diff for over-engineering. Ponytail only works on the full picture — review the combined diff, not per-feature. It must be an adversarial agent.
5. **Verify**: Run `make test && make style`.

### Subagents

Subagents are defined in `~/.config/opencode/agents/` and available globally.

| Agent | File | Purpose | Permissions |
|-------|------|---------|-------------|
| builder | `builder.md` | TDD one feature, writes tests then implementation | edit: allow, bash: allow, task: { \*: deny, playwright-tester: allow } |
| ponytail-reviewer | `ponytail-reviewer.md` | Bloat/over-engineering audit on combined diff | edit: deny, bash: allow |

## Project-Specific Notes

- APIs: Groq drafter (`GROQ_API_KEY`) + Gemini judge (`GEMINI_API_KEY` + `GEMINI_BASE_URL`). Keys in `.env`, never committed; `.env.example` carries names only.
- Data: full Twitter dump lives outside the repo (Kaggle `thoughtvector/customer-support-on-twitter`); setup extracts the ChaseSupport subsample. Banking77 via Kaggle mirror `sssonnn/banking77` — the `datasets`-library path is dead, don't use it.
- No git repo yet — `git init` + first commit is a build-time task.
- Gotchas: free-tier LLM throughput is 15–30 RPM (cache-first repro); ~55% of inbound tweets carry reply links; DM-takeover is the brand's dominant resolution and counts as faithful grounding.
