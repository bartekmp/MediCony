from unittest.mock import MagicMock

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


@pytest.fixture(scope="session", autouse=True)
def cleanup_log_dir():
    from pathlib import Path

    log_dir = Path("log")
    log_file_path = log_dir / "medicony.log"
    yield
    # Cleanup after tests
    log_file_path.unlink(missing_ok=True)


@pytest.fixture
def mock_api_client():
    api_client = MagicMock()
    api_client.find_filters.return_value = {"clinics": [{"id": "2024", "value": "Test Clinic"}]}
    return api_client
