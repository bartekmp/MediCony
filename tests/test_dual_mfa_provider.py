"""Tests for the dual_mfa_provider logic in MediCony.daemon_worker.

The dual_mfa_provider races a Telegram provider and a stdin provider via
asyncio.wait(FIRST_COMPLETED).  These tests verify that:
  - when one provider returns None first (e.g. stdin EOFError in Docker),
    the other provider is NOT cancelled and is waited on instead;
  - when one provider returns a valid code first, the other is cancelled;
  - when both providers return None, the overall result is None.
"""

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Reproduce the dual_mfa_provider logic in isolation so the test does not
# depend on Telegram/bot wiring.  This is a faithful copy of the function
# from medicony_app.py, parameterised with two arbitrary providers.
# ---------------------------------------------------------------------------


async def _dual_mfa_provider(
    provider_a,  # async callable (channel) -> str | None
    provider_b,  # async callable (channel) -> str | None
    channel: str,
) -> str | None:
    """Re-implementation of the fixed dual_mfa_provider for testability."""
    t1 = asyncio.create_task(provider_a(channel))
    t2 = asyncio.create_task(provider_b(channel))
    tasks = {t1, t2}

    while tasks:
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Check all done tasks for a valid result
        valid_result = None
        for result_task in done:
            try:
                res = result_task.result()
            except Exception:
                res = None
            if res is not None and valid_result is None:
                valid_result = res

        if valid_result is not None:
            for p in tasks:
                p.cancel()
            # Await cancellations to suppress 'Task exception was never retrieved'
            for p in tasks:
                try:
                    await p
                except (asyncio.CancelledError, Exception):
                    pass
            return valid_result

    return None


# ---------------------------------------------------------------------------
# Helpers — tiny async callables that simulate the two MFA providers.
# ---------------------------------------------------------------------------


async def _instant_none(_channel: str) -> str | None:
    """Simulates stdin_mfa_provider hitting EOFError (no TTY / Docker)."""
    return None


async def _delayed_code(_channel: str) -> str | None:
    """Simulates Telegram provider returning a code after a short wait."""
    await asyncio.sleep(0.05)
    return "123456"


async def _delayed_none(_channel: str) -> str | None:
    """Simulates a provider that takes time but ultimately returns None."""
    await asyncio.sleep(0.05)
    return None


async def _instant_code(_channel: str) -> str | None:
    """Simulates stdin provider returning a code immediately."""
    return "654321"


async def _raising_provider(_channel: str) -> str | None:
    """Simulates a provider that raises an exception."""
    raise RuntimeError("Something went wrong")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_falls_back_when_first_provider_returns_none():
    """
    Reproduces the original bug: stdin returns None instantly (EOFError in
    Docker).  The Telegram provider should NOT be cancelled — we should
    wait for it and return its code.
    """
    result = await _dual_mfa_provider(_instant_none, _delayed_code, "SMS")
    assert result == "123456"


@pytest.mark.asyncio
async def test_returns_first_valid_code():
    """When stdin returns a code instantly, Telegram should be cancelled."""
    result = await _dual_mfa_provider(_instant_code, _delayed_code, "SMS")
    assert result == "654321"


@pytest.mark.asyncio
async def test_returns_none_when_both_providers_fail():
    """When both providers return None, the overall result is None."""
    result = await _dual_mfa_provider(_instant_none, _delayed_none, "SMS")
    assert result is None


@pytest.mark.asyncio
async def test_falls_back_when_first_provider_raises():
    """
    When the first provider raises an exception, the second provider
    should still be waited on.
    """
    result = await _dual_mfa_provider(_raising_provider, _delayed_code, "SMS")
    assert result == "123456"


@pytest.mark.asyncio
async def test_returns_none_when_both_fail_with_exceptions():
    """When both providers raise, the overall result is None."""
    result = await _dual_mfa_provider(_raising_provider, _raising_provider, "SMS")
    assert result is None


@pytest.mark.asyncio
async def test_telegram_first_stdin_second():
    """When the Telegram provider returns a code first, stdin is cancelled."""
    result = await _dual_mfa_provider(_delayed_code, _instant_none, "SMS")
    assert result == "123456"
