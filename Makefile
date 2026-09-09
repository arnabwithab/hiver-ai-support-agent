# F000: repo scaffold and toolchain
#
# Thin wrappers only — no business logic. All targets must run green on an
# empty repo (before F001..F012 are built).

.PHONY: setup dev test style build clean

# uv sync + ChaseSupport subsample (idempotent)
setup:
	uv sync

# placeholder until F007 pipeline lands
dev:
	@echo "dev: pipeline not yet implemented (F007)"

test:
	uv run pytest

style:
	uv run black src tests
	uv run ruff check src tests

# F011: cache-first repro — headlines from cache, live smoke only with keys
build:
	uv run python -m src.build $(ARGS)

clean:
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf data/cache
