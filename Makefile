# F000: repo scaffold and toolchain
#
# Thin wrappers only — no business logic. All targets must run green on an
# empty repo (before F001..F012 are built).

.PHONY: setup dev test style build clean data

# uv sync (idempotent; bootstraps uv itself when missing) + cache the
# sentence encoder now so the first test run doesn't pay the download
setup:
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	@export PATH="$$HOME/.local/bin:$$HOME/.cargo/bin:$$PATH"; uv sync
	@uv run python -c "from src.intent import EMBEDDING_MODEL; from sentence_transformers import SentenceTransformer; SentenceTransformer(EMBEDDING_MODEL)"

# raw Kaggle dumps (skipped when present; needs the kaggle CLI + credentials)
data:
	@command -v kaggle >/dev/null 2>&1 || (echo "install the kaggle CLI and configure ~/.kaggle/credentials.json first"; exit 1)
	@test -f data/raw/banking77/train.csv || kaggle datasets download sssonnn/banking77 -p data/raw/banking77 --unzip
	@test -f data/raw/twcs/twcs/twcs.csv || kaggle datasets download thoughtvector/customer-support-on-twitter -p data/raw/twcs --unzip

# offline pipeline demo: one golden thread, fake LLMs
dev:
	uv run python -m src.orchestrate

test:
	uv run pytest

style:
	uv run black src tests
	uv run ruff check src tests

# Headline eval: baselines + shipped head on the locked holdout, live only with --live
build:
	uv run python -m src.build $(ARGS)

clean:
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf data/cache
