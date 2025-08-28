import os

import pytest


def pytest_configure():
    from pathlib import Path

    # Create a temporary directory
    log_dir = Path("log")
    log_dir.mkdir(parents=True, exist_ok=True)
    # Create a fake log file in the temporary directory
    log_file_path = log_dir / "medicony.log"
    with open(log_file_path, "w") as f:
        f.write("")


@pytest.fixture(autouse=True)
async def slow_down_tests():
    # This imitates a user interactions and slows down the tests to avoid hitting rate limits
    from asyncio import sleep
    from random import randint

    yield
    await sleep(randint(5, 10))


@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    # Load environment variables from .env file
    from dotenv import load_dotenv

    load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def env_vars() -> dict:
    vars = {}
    if user_data := os.environ.get("MEDICOVER_USERDATA"):
        # Use the same validation as the main config parser
        from src.config import parse_medicover_accounts
        try:
            accounts, default_alias = parse_medicover_accounts(user_data)
            if accounts:
                # For feature tests, get the default account credentials in the old format
                username, password = accounts[default_alias]
                vars["user_data"] = f"{username}:{password}"
        except ValueError as e:
            raise ValueError(f"MEDICOVER_USERDATA environment variable is not in the correct format: {e}")

    return vars


@pytest.fixture(scope="function")
def skip_if_no_real_userdata():
    user_data = os.environ.get("MEDICOVER_USERDATA")
    if not user_data:
        pytest.skip("MEDICOVER_USERDATA environment variable is not set, skipping tests that require valid login")


@pytest.fixture(scope="function")
async def api_client(skip_if_no_real_userdata, env_vars):
    from src.medicover.api_client import MediAPI
    from src.medicover.auth import Authenticator

    authenticator = Authenticator(env_vars["user_data"])
    api_client = MediAPI(authenticator)
    await api_client.authenticate()

    return api_client


@pytest.fixture(scope="function")
def db_client():
    from src.database import MedicoverDbClient

    db_client = MedicoverDbClient()
    return db_client
