"""Shared Gemini client helpers: key rotation and retry classification."""
from __future__ import annotations

import logging
import time

from google import genai

from config import Config

logger = logging.getLogger("GEMINI_CLIENT")


def build_client() -> genai.Client:
    api_key = Config.get_next_api_key()
    logger.info(f"Using Standard API Key ending in: ...{api_key[-4:]}")
    return genai.Client(api_key=api_key)


def is_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "quota" in text


def retry_sleep(attempt: int, quota: bool) -> None:
    time.sleep(1 if quota else 2)
