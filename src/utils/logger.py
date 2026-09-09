"""Single logger import path. Everything logs via `from src.utils.logger import logger`."""

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("hiver")

# Third-party chatter is not ours: keep the channel to our own records.
for _noisy in ("httpx", "sentence_transformers", "urllib3"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
