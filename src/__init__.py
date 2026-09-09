"""PII redaction happens before any text reaches an LLM prompt or committed
artifact, and all routing decisions log the (raw → override → final) triple.
See src/utils/config.py for the single settings object and src/utils/logger.py
for the single logger import path.

Env vars are read ONLY via `src.utils.config.settings`. Never import os.getenv
elsewhere in the codebase.
"""
