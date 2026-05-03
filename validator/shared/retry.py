"""
retry.py — Shared retry utility for the Monoboard validator chain.

Usage:
    from shared.retry import call_with_retry

    result = call_with_retry(lambda: sp_client.get_list_items(list_url))

Design notes:
- Used wherever validators make outbound calls: SharePoint list reads
  (Permission Matrix, Escalation Matrix, Schemas library), Azure Table writes.
- Handles transient 503 / gRPC UNAVAILABLE errors with exponential backoff + jitter.
- Does NOT retry on validation logic failures (schema mismatch, scope violation,
  naming violation) — those are deterministic and retrying won't help.
- Constitution reference: Phase 0 Build Spec §Validator Chain — "no caching beyond
  a 60-second in-memory cache to handle bursts." This utility handles the retry
  layer beneath that cache.
"""

import time
import random
import logging

logger = logging.getLogger(__name__)


def call_with_retry(fn, max_retries: int = 5, context: str = ""):
    """
    Call fn() with exponential backoff on transient 503/UNAVAILABLE errors.

    Args:
        fn:           Zero-argument callable to attempt.
        max_retries:  Maximum number of attempts before raising. Default: 5.
        context:      Optional label for log messages (e.g. 'scope_validator:permission_matrix').

    Returns:
        The return value of fn() on success.

    Raises:
        The original exception if it is not a transient 503/UNAVAILABLE error.
        Exception("Max retries exceeded") if all retries are exhausted.
    """
    label = f"[{context}] " if context else ""

    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "%sTransient error on attempt %d/%d — retrying in %.2fs. Error: %s",
                    label, attempt + 1, max_retries, wait, e
                )
                time.sleep(wait)
            else:
                # Non-transient error — re-raise immediately, do not retry.
                logger.error("%sNon-transient error, not retrying: %s", label, e)
                raise

    raise Exception(f"{label}Max retries exceeded after {max_retries} attempts")
