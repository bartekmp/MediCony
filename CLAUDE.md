# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MediCony** is a Python automation tool that monitors [Medicover](https://medicover.pl) (Polish healthcare provider) for appointment availability and pharmacy medicine availability via PharmaRadar. It can automatically book appointments and notify users via Telegram.

## Commands

### Testing
```bash
pytest                          # Run all tests
pytest tests/test_foo.py        # Run a single test file
pytest tests/test_foo.py::test_bar  # Run a single test
pytest -x                       # Stop on first failure
```

Tests require `MEDICONY_INTERACTIVE=true` (set automatically by `pytest-env`). Test paths are configured in `pyproject.toml` (`testpaths = ["tests"]`). The `feature_tests/` directory is excluded from regular runs.

### Linting
```bash
ruff check .                    # Lint with ruff (primary)
ruff format .                   # Format with ruff
flake8 .                        # Alternative linter
isort .                         # Sort imports
```

Ruff line-length: 120. Flake8 max-line-length: 132. Flake8 ignores: E203, E402, E501, E731, W503.

### Build & Run
```bash
pip install -e ".[dev]"         # Install with dev dependencies
python medicony.py <command>    # Run CLI directly
docker build --rm -t medicony . # Build Docker image
./scripts/build_image.sh        # Build script shorthand
```

### Versioning & Release
Versions follow [Conventional Commits](https://www.conventionalcommits.org/). Semantic release is triggered on pushes to `main`. Allowed commit types: `feat`/`feature` (minor), `fix`/`bugfix`/`improvement`/`enhancement`/`update` (patch).

## Architecture

### Entry Points
- `medicony.py` — CLI entry point; parses args, sets up async loop, handles signals
- `src/app/medicony_app.py` — Top-level orchestrator; wires together `MedicoverApp` and `MedicineApp`

### Source Layout (`src/`)
```
app/            # Application orchestrators (medicony_app, medicover_app, medicine_app)
bot/            # Telegram integration
  commands/     # Individual aiogram command handlers
  interactive_bot.py  # TelegramBot class (aiogram dispatcher)
  telegram.py   # Notification sender
  mfa_provider.py     # MFA code retrieval (stdin or Telegram)
medicover/      # Medicover API integration
  api_client.py       # HTTP API client
  auth.py             # Authentication & session handling
  appointment.py      # Appointment model
  watch.py            # Watch/search configuration model
  services/           # Business logic (WatchService for continuous monitoring)
database/       # Data layer (SQLAlchemy + PostgreSQL)
  base_db.py          # Base CRUD operations
  medicover_client.py # Medicover DB operations
  pharma_client.py    # Medicine DB operations
  medicover_db.py     # Query logic
config.py       # Centralized config (reads from env via python-dotenv)
models.py       # SQLAlchemy ORM models
parse_args.py   # argparse CLI definitions
logger.py       # Logging setup
http_client.py  # Shared HTTP utilities
```

### Data Flow
1. CLI args parsed in `medicony.py` → dispatched to `MediCony` (in `medicony_app.py`)
2. `MedicoverApp` handles Medicover login (`auth.py` with optional MFA via `mfa_provider.py`), then calls `MediAPI` client
3. Searches/watches stored in PostgreSQL via SQLAlchemy models (`MedicoverWatchModel`, `MedicineModel`, etc.)
4. Continuous monitoring runs via `WatchService` with APScheduler
5. Notifications sent to Telegram via aiogram; interactive Telegram bot also accepts commands

### Key Design Decisions
- **Session persistence**: Medicover auth tokens are encrypted and stored in the DB (`MedicoverAccountSessionModel`) to avoid re-login on every run
- **MFA handling**: MFA codes can come from stdin (interactive) or from a Telegram message (`mfa_provider.py`); controlled by `MEDICONY_INTERACTIVE` env var
- **Medicine search**: Delegated entirely to the external `pharmaradar` package (installed from GitHub)
- **Async throughout**: All app logic is async (asyncio); Telegram bot uses aiogram v3

### Environment Configuration
Copy `.env.example` to `.env`. Key variables: Medicover credentials, PostgreSQL connection, Telegram bot token and chat ID, log level.
