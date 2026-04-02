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
def env_vars(setup_environment) -> dict:
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
def skip_if_no_real_userdata(setup_environment):
    user_data = os.environ.get("MEDICOVER_USERDATA")
    if not user_data:
        pytest.skip("MEDICOVER_USERDATA environment variable is not set, skipping tests that require valid login")


@pytest.fixture(scope="function")
def real_authenticator(skip_if_no_real_userdata, env_vars, db_client):
    from src.medicover.auth import Authenticator
    from src.medicover.stdin_mfa_provider import stdin_mfa_provider
    from src.config import parse_medicover_accounts

    accounts, default_alias = parse_medicover_accounts(os.environ.get("MEDICOVER_USERDATA", ""))
    sess = db_client.get_account_session(default_alias) if default_alias else None

    # If the DB is ephemeral (like in Jenkins), fallback to testing environment variables
    dev_id = sess[0] if sess else os.environ.get("MEDICONY_TEST_DEVICE_ID")
    ref_tok = sess[1] if sess else os.environ.get("MEDICONY_TEST_REFRESH_TOKEN")

    def session_save_cb(d_id, r_tok):
        if default_alias:
            db_client.save_account_session(default_alias, d_id, r_tok)

    authenticator = Authenticator(
        env_vars["user_data"],
        mfa_code_provider=stdin_mfa_provider,
        device_id=dev_id,
        refresh_token=ref_tok,
        session_save_callback=session_save_cb,
    )
    return authenticator


@pytest.fixture(scope="function")
async def api_client(real_authenticator):
    from src.medicover.api_client import MediAPI
    from src.medicover.auth import MfaVerificationError

    api_client = MediAPI(real_authenticator)

    try:
        await api_client.authenticate()
    except MfaVerificationError:
        pytest.skip("MFA required and cannot be provided interactively (e.g. Jenkins/CI). Skipping.")

    return api_client


@pytest.fixture(scope="function")
def db_client():
    from src.database import MedicoverDbClient

    db_client = MedicoverDbClient()
    return db_client
