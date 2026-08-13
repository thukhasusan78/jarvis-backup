"""Shared Gemini client helpers: key rotation, Orbit provider, retry classification."""
from __future__ import annotations

import logging
import time
from typing import Optional

from google import genai

from config import Config

logger = logging.getLogger("GEMINI_CLIENT")


def build_client(use_orbit: bool = False) -> genai.Client:
    if use_orbit and getattr(Config, "ORBIT_API_KEY", None) and Config.ORBIT_API_KEY:
        logger.info("Using ORBIT API client")
        return genai.Client(
            api_key=Config.ORBIT_API_KEY,
            http_options={
                "base_url": Config.ORBIT_BASE_URL,
                "api_version": "v1beta",
                "headers": {
                    "Authorization": f"Bearer {Config.ORBIT_API_KEY}",
                    "X-API-Key": Config.ORBIT_API_KEY,
                },
            },
        )
    api_key = Config.get_next_api_key()
    logger.info(f"Using Standard API Key ending in: ...{api_key[-4:]}")
    return genai.Client(api_key=api_key)


def is_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "quota" in text


def retry_sleep(attempt: int, quota: bool) -> None:
    time.sleep(1 if quota else 2)
