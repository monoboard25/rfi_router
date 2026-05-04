"""Shared helpers used by RFI/CO/Daily/CEO agents."""

import logging
import os
from typing import Any

import requests

VALIDATOR_API_URL = os.getenv("VALIDATOR_API_URL")
AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AOAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AOAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def call_validator(agent: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not VALIDATOR_API_URL:
        raise RuntimeError("VALIDATOR_API_URL not configured")
    body = {"agent": agent, "action": action, **payload}
    resp = requests.post(VALIDATOR_API_URL, json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()


def llm_complete(prompt: str, system: str = "") -> str:
    if not (AOAI_ENDPOINT and AOAI_KEY and AOAI_DEPLOYMENT):
        logging.warning("AOAI not configured, returning prompt echo")
        return prompt
    url = f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/chat/completions?api-version=2024-06-01"
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    resp = requests.post(
        url,
        headers={"api-key": AOAI_KEY, "Content-Type": "application/json"},
        json={"messages": msgs, "temperature": 0.2},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
