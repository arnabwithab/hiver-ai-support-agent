# F000: repo scaffold and toolchain
#
# Thin wrappers only — no business logic. All targets must run green on an
# empty repo (before F001..F012 are built).

.PHONY: setup dev test style build clean data subsample train verify

# uv sync (idempotent; bootstraps uv itself when missing)
setup:
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	@export PATH="$$HOME/.local/bin:$$HOME/.cargo/bin:$$PATH"; uv sync

# raw Kaggle dumps (skipped when present; needs the kaggle CLI + credentials)
data:
	@command -v kaggle >/dev/null 2>&1 || (echo "install the kaggle CLI and configure ~/.kaggle/credentials.json first"; exit 1)
	@test -f data/raw/banking77/train.csv || kaggle datasets download sssonnn/banking77 -p data/raw/banking77 --unzip
	@test -f data/raw/twcs/twcs/twcs.csv || kaggle datasets download thoughtvector/customer-support-on-twitter -p data/raw/twcs --unzip

# Chase thread extraction + cross-brand social mining (needs: data)
subsample:
	uv run python -m src.subsample

# Phase-A training + ceiling (needs: data, subsample for social rows)
train:
	uv run python -m src.intent

# offline pipeline demo: one golden thread, fake LLM clients, no keys
dev:
	uv run python -m src.orchestrate

test:
	uv run pytest

style:
	uv run black src tests
	uv run ruff check src tests

# F011: cache-first repro — headlines from cache, live smoke only with keys
build:
	uv run python -m src.build $(ARGS)

# keyless check: recompute every report number from the committed evidence
verify:
	uv run python -m src.eval.verify

clean:
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf data/cache
