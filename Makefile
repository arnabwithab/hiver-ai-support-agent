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
	python -m src.orchestrate

test:
	uv run pytest

style:
	uv run black src tests
	uv run ruff check src tests

# placeholder until F011 cache-first repro
build:
	@echo "build: cache repro + smoke subset (F011)"

clean:
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf data/cache
