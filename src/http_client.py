import asyncio
import random

import requests
import tenacity
from requests import Session

from src.logger import log
from src.medicover.auth import Authenticator


class HTTPClient:
    def __init__(self, authenticator: Authenticator):
        self.authenticator = authenticator
        self.session: Session = Session.__new__(Session)
        self.headers = None

    @tenacity.retry(
        wait=tenacity.wait_fixed(30),
        stop=tenacity.stop_after_attempt(7),
    )
    async def auth(self):
        self.session = await self.authenticator.login()
        self.headers = self.authenticator.headers

    async def re_auth(self):
        await self.auth()

    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type((requests.exceptions.ConnectionError, RuntimeError)),
        reraise=True,
    )
    async def get(self, url, params):
        await asyncio.sleep(random.randint(0, 2))
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.session.get(url, headers=self.headers, params=params))
        if response.status_code == 401:
            log.warning("Response 401. Re-authenticating")
            await self.re_auth()
            raise RuntimeError("Re-authenticated after 401, retrying request")
        response.raise_for_status()
        return response

    async def post(self, url: str, payload: dict) -> dict:
        await asyncio.sleep(random.randint(0, 2))
        response = self.session.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            log.warning("Response 401. Re-authenticating")
            await self.re_auth()
            return await self.post(url, payload)
        else:
            log.error(f"Error {response.status_code}: {response.text}")
            return {}

    async def delete(self, url: str) -> dict:
        await asyncio.sleep(random.randint(0, 2))
        response = self.session.delete(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            log.warning("Response 401. Re-authenticating")
            await self.re_auth()
            return await self.delete(url)
        else:
            log.error(f"Error {response.status_code}: {response.text}")
            return {}
