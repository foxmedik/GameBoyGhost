from __future__ import annotations

import os
import random
import subprocess
import time
from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

USER_AGENT = "gbg-corpus/0.1 (personal research archive; contact: ben)"


class FetchError(RuntimeError):
    def __init__(self, status: int, url: str, detail: str = ""):
        super().__init__(f"HTTP {status} for {url} {detail}".strip())
        self.status = status
        self.url = url


@dataclass
class Fetcher:
    rate_limit_rps: float = 1.0
    timeout: float = 45.0

    def __post_init__(self):
        self._last = 0.0
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            follow_redirects=True,
            timeout=self.timeout,
        )

    def close(self):
        self.client.close()

    def _pace(self):
        gap = 1.0 / max(self.rate_limit_rps, 0.1)
        wait = self._last + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((httpx.TransportError, FetchError)),
        reraise=True,
    )
    def get(self, url: str, **kwargs) -> httpx.Response:
        self._pace()
        resp = self.client.get(url, **kwargs)
        if resp.status_code in (403, 429, 500, 502, 503, 504):
            # Back off and retry a bounded number of times; never rotate identity.
            raise FetchError(resp.status_code, url)
        resp.raise_for_status()
        return resp


def github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = github_token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return headers
