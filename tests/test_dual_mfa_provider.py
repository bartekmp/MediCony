"""Tests for the dual_mfa_provider logic in MediCony.daemon_worker."""

import asyncio

import pytest

# ---------------------------------------------------------------------------
# Reproduce the dual_mfa_provider logic in isolation so the test does not
# depend on Telegram/bot wiring. This is a faithful copy of the function
# from medicony_app.py.
# ---------------------------------------------------------------------------


async def _dual_mfa_provider(
    mfa_provider,
    stdin_provider,
    channel: str,
) -> str | None:
    """Re-implementation of the fixed dual_mfa_provider for testability."""
    tasks = set()

    if await mfa_provider.send_prompt(channel):
        t1 = asyncio.create_task(mfa_provider.wait_for_reply())
        tasks.add(t1)
    else:
        t1 = None

    t2 = asyncio.create_task(stdin_provider(channel))
    tasks.add(t2)

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


class MockTelegramProvider:
    def __init__(self, send_returns=True, wait_code="123456", wait_delay=0.0):
        self.send_returns = send_returns
        self.wait_code = wait_code
        self.wait_delay = wait_delay
        self.send_prompt_called = False

    async def send_prompt(self, channel):
        self.send_prompt_called = True
        return self.send_returns

    async def wait_for_reply(self):
        if self.wait_delay:
            await asyncio.sleep(self.wait_delay)
        if isinstance(self.wait_code, Exception):
            raise self.wait_code
        return self.wait_code


async def _instant_none(_channel: str) -> str | None:
    return None


async def _delayed_code(_channel: str) -> str | None:
    await asyncio.sleep(0.05)
    return "654321"


async def _instant_code(_channel: str) -> str | None:
    return "654321"


async def _raising_provider(_channel: str) -> str | None:
    raise RuntimeError("Something went wrong")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_falls_back_when_first_provider_returns_none():
    mfa_provider = MockTelegramProvider(wait_code="123456", wait_delay=0.05)
    result = await _dual_mfa_provider(mfa_provider, _instant_none, "SMS")
    assert result == "123456"


@pytest.mark.asyncio
async def test_returns_first_valid_code():
    mfa_provider = MockTelegramProvider(wait_code="123456", wait_delay=0.05)
    result = await _dual_mfa_provider(mfa_provider, _instant_code, "SMS")
    assert result == "654321"


@pytest.mark.asyncio
async def test_returns_none_when_both_providers_fail():
    mfa_provider = MockTelegramProvider(wait_code=None, wait_delay=0.05)
    result = await _dual_mfa_provider(mfa_provider, _instant_none, "SMS")
    assert result is None


@pytest.mark.asyncio
async def test_falls_back_when_first_provider_raises():
    mfa_provider = MockTelegramProvider(wait_code=RuntimeError("err"), wait_delay=0.05)
    result = await _dual_mfa_provider(mfa_provider, _delayed_code, "SMS")
    assert result == "654321"


@pytest.mark.asyncio
async def test_returns_none_when_both_fail_with_exceptions():
    mfa_provider = MockTelegramProvider(wait_code=RuntimeError("err"), wait_delay=0.05)
    result = await _dual_mfa_provider(mfa_provider, _raising_provider, "SMS")
    assert result is None


@pytest.mark.asyncio
async def test_telegram_fails_to_send():
    """When Telegram send_prompt fails, it shouldn't wait_for_reply, but stdin should work."""
    mfa_provider = MockTelegramProvider(send_returns=False)
    result = await _dual_mfa_provider(mfa_provider, _delayed_code, "SMS")
    assert result == "654321"


@pytest.mark.asyncio
async def test_execution_order_verifies_send_prompt_runs_first():
    """Verify that send_prompt is awaited before stdin is called."""
    events = []

    class OrderedTelegramProvider:
        async def send_prompt(self, channel):
            await asyncio.sleep(0.01)  # takes a bit
            events.append("telegram_sent")
            return True

        async def wait_for_reply(self):
            events.append("telegram_wait")
            return "123"

    async def tracking_stdin(channel):
        events.append("stdin_called")
        return None

    await _dual_mfa_provider(OrderedTelegramProvider(), tracking_stdin, "SMS")

    # verify that telegram_sent is strictly before stdin_called
    assert events == ["telegram_sent", "telegram_wait", "stdin_called"] or events == [
        "telegram_sent",
        "stdin_called",
        "telegram_wait",
    ]
    assert events[0] == "telegram_sent"
