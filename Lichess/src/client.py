"""Polite Lichess API client.

Etiquette (PLAN §2): strictly sequential requests, one at a time; honor
Retry-After; back off aggressively on 429 (Lichess guidance ~ a full minute);
use the bulk endpoint wherever possible.
"""
from __future__ import annotations

import json
import time
from typing import Iterable

import requests

from . import config


class LichessClient:
    """Thin wrapper around requests with built-in politeness.

    - Enforces a minimum interval between requests (all requests are sequential).
    - On 429: sleeps Retry-After (default 60s per Lichess guidance), then retries.
    - On transient 5xx: exponential backoff.
    """

    def __init__(self, request_interval_s: float = config.REQUEST_INTERVAL_S,
                 token: str | None = None) -> None:
        self.min_interval = request_interval_s
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)

    def _request(self, method: str, url: str, max_retries: int = 5, **kwargs) -> requests.Response:
        for attempt in range(max_retries):
            self._throttle()
            resp = self.session.request(method, url, timeout=60, **kwargs)
            self._last_request = time.monotonic()
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", config.BACKOFF_429_DEFAULT_S))
                print(f"429 rate-limited; sleeping {retry_after:.0f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_after)
                continue
            if resp.status_code >= 500:
                wait = max(2 ** attempt, 5)
                print(f"{resp.status_code} server error; sleeping {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError(f"Failed after {max_retries} attempts: {method} {url}")

    def get_json(self, path: str, **params) -> dict | list:
        resp = self._request("GET", config.API_BASE + path, params=params)
        return resp.json()

    def get_ndjson(self, path: str, **params) -> list[dict]:
        resp = self._request("GET", config.API_BASE + path, params=params)
        return [json.loads(line) for line in resp.text.strip().split("\n") if line]

    # -- domain helpers ------------------------------------------------------

    def bulk_users(self, usernames: Iterable[str], progress_every: int = 10) -> list[dict]:
        """Fetch profiles in batches of 300 via POST /api/users.

        Confirmed bulk fields: createdAt, seenAt, perfs, playTime, title, profile;
        patron appears on supporter accounts (asserted in P2 before use).
        """
        usernames = list(usernames)
        out: list[dict] = []
        bulk = LichessClient(request_interval_s=config.BULK_REQUEST_INTERVAL_S)
        if "Authorization" in self.session.headers:
            bulk.session.headers["Authorization"] = self.session.headers["Authorization"]
        n_chunks = (len(usernames) + config.BULK_MAX_IDS - 1) // config.BULK_MAX_IDS
        for i in range(0, len(usernames), config.BULK_MAX_IDS):
            chunk = usernames[i:i + config.BULK_MAX_IDS]
            resp = bulk._request(
                "POST", config.BULK_USERS_URL,
                data=",".join(chunk),
                headers={"Content-Type": "text/plain"},
            )
            out.extend(resp.json())
            done = i // config.BULK_MAX_IDS + 1
            if done % progress_every == 0 or done == n_chunks:
                print(f"bulk profiles: {done}/{n_chunks} batches ({len(out):,} users)")
        return out

    def top_players(self, perf: str = "classical", nb: int = 200) -> list[dict]:
        return self.get_json(f"/api/player/top/{nb}/{perf}").get("users", [])
