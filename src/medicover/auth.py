import asyncio
import base64
import hashlib
import random
import re
import string
import time
import uuid
from dataclasses import dataclass
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from src.logger import log


@dataclass
class Userdata:
    username: str
    password: str


class LoginError(requests.RequestException):
    pass


class TokenExchangeError(requests.RequestException):
    pass


def parse_userdata(userdata: str) -> Userdata:
    # Userdata format: "username:password"
    if ":" not in userdata:
        log.error(f"Invalid userdata format: {userdata}")
        raise ValueError(f"Invalid userdata format: {userdata}")
    return Userdata(userdata.split(":")[0], userdata.split(":")[1])


class Authenticator:
    def __init__(self, userdata: str):
        self.userdata = parse_userdata(userdata)
        self.session = None
        # Default headers for the requests, with a randomized real user agent
        self.headers = {
            "User-Agent": UserAgent(platforms="desktop").random,
            "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Authorization": None,
        }
        self.bearerToken = None

    async def slack_get(self, url: str, **kwargs) -> requests.Response:
        """
        Wrapper for session.get() with randomized sleep time to simulate real user behavior.
        """
        if self.session is None:
            raise ValueError("Session is not initialized, call login() first")
        await asyncio.sleep(random.randint(0, 2))
        return self.session.get(url, headers=self.headers, **kwargs)

    def generate_code_challenge(self, uuid_input: str) -> str:
        # Generate a code challenge from the given UUID input using SHA-256 and base64 URL encoding
        sha256 = hashlib.sha256(uuid_input.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(sha256).decode("utf-8").rstrip("=")

    async def retrieve_app_version(self) -> str:
        version_url = "https://online24.medicover.pl/env-config.js"
        response = await self.slack_get(version_url)
        if response.status_code != 200:
            log.error(f"Failed to retrieve app version, status code: {response.status_code}")
            raise requests.RequestException(f"Failed to retrieve app version, status code: {response.status_code}")

        content = response.text
        if "VITE_VERSION" not in content:
            log.error("Version not found in the response content")
            raise ValueError("Version not found in the response content")

        match = re.search(r'VITE_VERSION:\s*"([^"]+)"', content)
        if not match:
            log.error("VITE_VERSION not found in env-config.js")
            raise ValueError("VITE_VERSION not found in env-config.js")
        return match.group(1)

    async def skip_mfa_gate(self, mfa_get_url: str) -> str | None:
        # Skip the MFA gate page telling you to turn MFA on, which appears for some accounts for unknown reasons, even if MFA is not enabled on the account.
        # This allows to proceed with the login and avoid getting stuck on that page.
        # Returns the redirection URL after skipping the MFA gate, which should lead to the authorization code exchange step.
        # If the MFA gate was not present, returns None.
        # Note: This method should be called after a successful login and before fetching the authorization code.
        if self.session is None:
            raise ValueError("Session is not initialized, call login() first")

        login_url = "https://login-online24.medicover.pl"
        mfa_selection_page = await self.slack_get(f"{login_url}{mfa_get_url}", allow_redirects=False)
        if 'formaction="/Account/MfaGate?handler=SkipMfaGate"' not in mfa_selection_page.text:
            log.info("MFA gate not detected on the page, proceeding without skipping")
            return None

        soup = BeautifulSoup(mfa_selection_page.text, "html.parser")
        csrf_input = soup.find("input", {"name": "__RequestVerificationToken"})
        return_url_input = soup.find("input", {"name": "Input.ReturnUrl"})
        skip_button = soup.find(attrs={"formaction": "/Account/MfaGate?handler=SkipMfaGate"})

        if not csrf_input or not return_url_input:
            log.log_to_file("ERROR", f"Invalid MFA page response: {mfa_selection_page.text}")
            raise ValueError("Failed to extract MFA form fields required for skipping MFA gate")

        csrf_token = csrf_input.get("value")
        return_url = return_url_input.get("value")
        if not csrf_token or not return_url:
            log.log_to_file("ERROR", f"Invalid MFA page response: {mfa_selection_page.text}")
            raise ValueError("MFA skip form fields were empty")

        skip_action_url = str(skip_button.get("formaction")) if skip_button and skip_button.get("formaction") else "/Account/MfaGate?handler=SkipMfaGate"
        skip_endpoint = urljoin(login_url, skip_action_url)
        mfa_skip_data = {
            "Input.ReturnUrl": return_url,
            "__RequestVerificationToken": csrf_token,
        }
        mfa_skip_headers = {
            **self.headers,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": login_url,
            "Referer": f"{login_url}{mfa_get_url}",
        }
        response = self.session.post(
            skip_endpoint,
            data=mfa_skip_data,
            headers=mfa_skip_headers,
            allow_redirects=False,
        )
        if response.status_code != 302:
            log.error(f"Failed to skip MFA gate, status code: {response.status_code}")
            raise requests.RequestException(f"Failed to skip MFA gate, status code: {response.status_code}")

        return response.headers.get("Location")

    async def login(self):
        self.session = requests.Session()
        # Generate random state, device_id, code_verifier and code_challenge for the login request
        state = "".join(random.choices(string.ascii_lowercase + string.digits, k=32))
        device_id = str(uuid.uuid4())
        code_verifier = "".join(uuid.uuid4().hex for _ in range(3))
        code_challenge = self.generate_code_challenge(code_verifier)

        app_version = await self.retrieve_app_version()

        login_url = "https://login-online24.medicover.pl"
        oidc_redirect = "https://online24.medicover.pl/signin-oidc"
        # Current authorization parameters for the login request
        auth_params = (
            f"?client_id=web&redirect_uri={oidc_redirect}&response_type=code"
            f"&scope=openid+offline_access+profile&state={state}&code_challenge={code_challenge}"
            f"&code_challenge_method=S256&response_mode=query&ui_locales=pl&app_version={app_version}"
            f"&previous_app_version={app_version}&device_id={device_id}&device_name=Chrome"
        )

        # Initialize login by redirecting to authorization page
        response = await self.slack_get(
            f"{login_url}/connect/authorize{auth_params}",
            allow_redirects=False,
        )

        # Retrieve the redirection target from the response
        redirection_url = response.headers.get("Location")
        if not redirection_url or response.status_code != 302:
            log.log_to_file("ERROR", f"Invalid response: {response.text}")
            raise requests.URLRequired(
                f"Failed to initialize login, authorization redirect target was empty or the request was unsuccessful, status code: {response.status_code}",
                response=response,
            )

        # Construct the redirection URL to acces the authorization form
        next_url = (
            # Attach the timestamp in ISO format to the redirection URL
            f"{response.headers.get("Location")}%26ts%3D{int(time.time_ns() / 1000000)}"
        )

        # Get the authorization form page
        response = await self.slack_get(next_url, allow_redirects=False)

        # Parse the HTML response to get the verification token
        soup = BeautifulSoup(response.content, "html.parser")
        if (csrf_input := soup.find("input", {"name": "__RequestVerificationToken"})) is not None:
            csrf_token = csrf_input.get("value")  # type: ignore
        else:
            log.log_to_file("ERROR", f"Invalid response: {response.text}")
            raise ValueError("Failed to find the CSRF token in the response, see the log for more details")

        # Submit login form with auth data and get the redirection URL
        login_data = {
            "Input.ReturnUrl": f"/connect/authorize/callback{auth_params}",
            "Input.LoginType": "FullLogin",
            "Input.Username": self.userdata.username,
            "Input.Password": self.userdata.password,
            "Input.Button": "login",
            "Input.IsSimpleAccessRegulationAccepted": "true",
            "__RequestVerificationToken": csrf_token,
        }
        response = self.session.post(next_url, data=login_data, headers=self.headers, allow_redirects=False)
        # Check if the login failed due to invalid credentials
        if "INVALID_CREDENTIALS" in response.text or response.status_code != 302:
            log.error("Invalid login credentials provided")
            raise LoginError("Invalid login credentials provided")

        # Check if the login was successful and get the redirection URL
        next_url = response.headers.get("Location")
        if not next_url:
            log.error("'Location' header was empty after submitting the login form")
            raise requests.URLRequired("'Location' header was empty after submitting the login form")

        if "MfaGate" in next_url:
            log.info("MFA gate detected, attempting to skip it")
            next_url = await self.skip_mfa_gate(next_url)
            if not next_url:
                log.error("MFA gate was detected but no redirection URL was provided after skipping it")
                raise ValueError("MFA gate was detected but no redirection URL was provided after skipping it")

        # Fetch authorization code by parsing query string from the next redirection URL
        response = await self.slack_get(f"{login_url}{next_url}", allow_redirects=False)
        next_url = response.headers.get("Location")
        query = urlparse(next_url).query

        # Ensure query is a str for parse_qs
        if not isinstance(query, str):
            query = str(query)
        code_dict = parse_qs(query, keep_blank_values=True, strict_parsing=False)

        # parse_qs returns dict[str, list[str]]
        code = code_dict.get("code")
        if not code:
            log.error(f"No 'code' found in query: {query}")
            raise ValueError("No 'code' found in authorization redirect URL")
        code = code[0]

        # Exchange the auth code for bearer tokens
        token_data = {
            "grant_type": "authorization_code",
            "redirect_uri": oidc_redirect,
            "code": code,
            "code_verifier": code_verifier,
            "client_id": "web",
        }
        response = self.session.post(f"{login_url}/connect/token", data=token_data, headers=self.headers)
        if response.status_code != 200:
            log.error(f"Failed to exchange authorization code for tokens: {response.text}")
            raise TokenExchangeError(
                f"Failed to exchange authorization code for tokens, status code: {response.status_code}",
                response=response,
            )
        # Save the token and add it to the headers
        self.bearerToken = response.json()["access_token"]
        self.headers["Authorization"] = f"Bearer {self.bearerToken}"
        return self.session
