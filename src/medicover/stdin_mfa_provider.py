"""
Stdin-based MFA code provider for CLI mode.

Prompts the user in the terminal for the 6-digit 2FA code.
"""

import asyncio

import sys
from src.logger import log


def is_interactive() -> bool:
    """
    Check if the current process is running in an interactive terminal.
    Can be overridden by MEDICONY_INTERACTIVE environment variable (true/false).
    """
    import os

    force = os.getenv("MEDICONY_INTERACTIVE")
    if force is not None:
        return force.lower() in ("1", "true", "yes")
    return sys.stdin.isatty()


async def stdin_mfa_provider(channel: str) -> str | None:
    """
    Prompt the user via stdin for the MFA 2FA code.

    Args:
        channel: The MFA channel description (e.g., "Email", "SMS").

    Returns:
        The code string entered by the user, or None if empty/EOF/not interactive.
    """
    if not is_interactive():
        return None

    loop = asyncio.get_running_loop()
    try:
        # Run the blocking input() in a thread executor to avoid blocking the event loop
        code = await loop.run_in_executor(
            None,
            lambda: input(f"\n🔐 Enter the 6-digit MFA code sent to you via {channel}:\n\t"),
        )
        code = code.strip()
        if not code:
            return None
        return code
    except (EOFError, KeyboardInterrupt):
        print()  # newline after ^C
        log.info("MFA code input cancelled by user")
        return None
    except Exception as e:
        log.error(f"Failed to read MFA code from stdin: {e}")
        return None
