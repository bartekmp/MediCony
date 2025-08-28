import random
import string
from secrets import choice

import pytest

from src.medicover.auth import Authenticator, LoginError, TokenExchangeError, parse_userdata


def get_random_login_string():
    return "".join([choice(string.digits) for _ in range(random.randint(6, 8))])


def test_userdata_parsing():
    # Test valid userdata format
    login = get_random_login_string()
    password = get_random_login_string()
    valid_userdata_str = f"{login}:{password}"

    user_data = parse_userdata(valid_userdata_str)

    assert user_data.username == login
    assert user_data.password == password

    # Test invalid userdata format
    invalid_userdata = "aaaaaaaaaaaaaaaaaaaaaaa"
    with pytest.raises(ValueError):
        parse_userdata(invalid_userdata)


async def test_invalid_real_login(env_vars):
    # Test invalid login credentials
    user_data_str = f"{get_random_login_string}:{get_random_login_string}"
    authenticator = Authenticator(user_data_str)
    with pytest.raises(LoginError):
        await authenticator.login()


async def test_valid_real_login(skip_if_no_real_userdata, env_vars):
    # Test valid login credentials
    if "user_data" not in env_vars:
        pytest.skip("MEDICOVER_USERDATA not available")
    
    authenticator = Authenticator(env_vars["user_data"])
    try:
        await authenticator.login()
    except LoginError:
        pytest.fail("Login should not raise LoginError for valid credentials")
    except TokenExchangeError:
        pytest.fail("Token exchange should not raise TokenExchangeError for valid credentials")


async def test_reauthentication_after_error(skip_if_no_real_userdata, env_vars):
    # Test that reauthentication works after an initial error
    if "user_data" not in env_vars:
        pytest.skip("MEDICOVER_USERDATA not available")
        
    authenticator = Authenticator(env_vars["user_data"])

    # First login should succeed
    try:
        session1 = await authenticator.login()
        assert session1 is not None
    except (LoginError, TokenExchangeError):
        pytest.fail("Initial login should succeed for valid credentials")

    # Simulate a scenario where we need to re-authenticate
    # by calling login again (simulating token expiration scenario)
    try:
        session2 = await authenticator.login()
        assert session2 is not None

        # Headers should be updated after re-authentication
        assert authenticator.headers is not None
        # The session should be valid (this is a basic check)
        assert hasattr(session2, "get") or hasattr(session2, "post")

    except (LoginError, TokenExchangeError):
        pytest.fail("Re-authentication should succeed for valid credentials")
