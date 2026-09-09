"""F000 smoke: settings + logger import and behave, proving the toolchain works."""


def test_settings_imports_and_exposes_expected_vars():
    from src.utils.config import settings

    for name in ("GROQ_API_KEY", "GROQ_MODEL", "GEMINI_API_KEY", "GEMINI_BASE_URL", "GEMINI_MODEL"):
        assert hasattr(settings, name)


def test_logger_imports_and_emits_a_record():
    from src.utils.logger import logger

    logger.info("smoke")
    assert logger.name == "hiver"
