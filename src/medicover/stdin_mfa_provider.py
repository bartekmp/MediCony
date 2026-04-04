"""
Stdin-based MFA code provider for CLI mode.

Prompts the user in the terminal for the 6-digit 2FA code.
"""

import asyncio

from src.logger import log


async def stdin_mfa_provider(channel: str) -> str | None:
    """
    Prompt the user via stdin for the MFA 2FA code.

    Args:
        channel: The MFA channel description (e.g., "Email", "SMS").

    Returns:
        The code string entered by the user, or None if empty/EOF.
    """
    loop = asyncio.get_running_loop()
    try:
        # Run the blocking input() in a thread executor to avoid blocking the event loop
        code = await loop.run_in_executor(
            None,
            lambda: input(
                f"\n🔐 Enter the 6-digit MFA code sent to you via {channel}:\n\t"
            ),
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
