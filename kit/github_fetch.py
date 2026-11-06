"""The kit's only network code: GitHub REST API and codeload, read-only (P4-T8, ADR-021).

Used by `kit source add|update|check --online`. Standard library urllib only (R-08). Requests go
to api.github.com and codeload.github.com and nowhere else. GITHUB_TOKEN, when given, is sent to
api.github.com only and never printed. Nothing downloaded is executed here or anywhere.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional
from urllib.parse import unquote

from .model import TargetError

MAX_BYTES = 20 * 1024 * 1024
_SHA = re.compile(r"^[0-9a-f]{40}$")
__all__ = ["GitHub", "NetworkError", "DownloadTooLarge", "MAX_BYTES", "unquote"]


class NetworkError(Exception):
    """GitHub could not be reached or refused (rate limit): exit 2."""


class DownloadTooLarge(Exception):
    """The download is over its limit (the add is blocked, exit 1)."""


class GitHub:
    API = "https://api.github.com"
    CODELOAD = "https://codeload.github.com"

    def __init__(self, token: Optional[str] = None, timeout: float = 30.0):
        self._token = token
        self._timeout = timeout

    def _get(self, url: str, accept: str, limit: int = 5 * 1024 * 1024) -> bytes:
        headers = {"Accept": accept, "User-Agent": "skill-kit-source"}
        if self._token and url.startswith(self.API):
            headers["Authorization"] = f"Bearer {self._token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                data = response.read(limit + 1)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LookupError(url) from None
            if exc.code in (403, 429):
                raise NetworkError(
                    f"GitHub refused the request (HTTP {exc.code}, rate limit?); "
                    "set GITHUB_TOKEN or try later"
                ) from None
            raise NetworkError(f"GitHub answered HTTP {exc.code}") from None
        except (urllib.error.URLError, OSError) as exc:
            raise NetworkError(f"GitHub is not reachable: {getattr(exc, 'reason', exc)}") from None
        if len(data) > limit:
            raise DownloadTooLarge(f"download is larger than {limit // (1024 * 1024)} MiB")
        return data

    def repo(self, owner: str, repo: str) -> dict:
        try:
            data = json.loads(self._get(f"{self.API}/repos/{owner}/{repo}", "application/json"))
        except LookupError:
            raise TargetError(f"GitHub repository {owner}/{repo} not found") from None
        lic = data.get("license") or {}
        return {
            "full_name": data.get("full_name", f"{owner}/{repo}"),
            "default_branch": data.get("default_branch") or "main",
            "archived": bool(data.get("archived")),
            "spdx": lic.get("spdx_id"),
        }

    def commit(self, owner: str, repo: str, ref: str) -> str:
        quoted = urllib.parse.quote(ref, safe="")
        try:
            sha = self._get(
                f"{self.API}/repos/{owner}/{repo}/commits/{quoted}", "application/vnd.github.sha"
            )
        except LookupError:
            raise TargetError(f"ref '{ref}' not found in {owner}/{repo}") from None
        text = sha.decode("ascii", "replace").strip()
        if not _SHA.match(text):
            raise NetworkError("GitHub did not return a commit SHA")
        return text

    def commit_exists(self, owner: str, repo: str, sha: str) -> bool:
        try:
            return self.commit(owner, repo, sha) == sha
        except TargetError:
            return False

    def tree(self, owner: str, repo: str, sha: str) -> list:
        """Every entry of the commit's tree: [{path, mode, type, sha, size}] (sparse add)."""
        try:
            data = json.loads(
                self._get(
                    f"{self.API}/repos/{owner}/{repo}/git/trees/{sha}?recursive=1",
                    "application/json",
                    MAX_BYTES,
                )
            )
        except LookupError:
            raise TargetError(f"no tree for {owner}/{repo}@{sha[:12]}") from None
        if data.get("truncated"):
            raise DownloadTooLarge("the repository file list is too long for GitHub to return")
        return list(data.get("tree") or [])

    def blob(self, owner: str, repo: str, sha: str, limit: int) -> bytes:
        if not _SHA.match(sha):
            raise NetworkError("GitHub returned a bad blob id")
        try:
            return self._get(
                f"{self.API}/repos/{owner}/{repo}/git/blobs/{sha}",
                "application/vnd.github.raw",
                limit,
            )
        except LookupError:
            raise TargetError(f"blob {sha[:12]} not found in {owner}/{repo}") from None

    def tarball(self, owner: str, repo: str, sha: str) -> bytes:
        try:
            return self._get(
                f"{self.CODELOAD}/{owner}/{repo}/tar.gz/{sha}", "application/x-gzip", MAX_BYTES
            )
        except LookupError:
            raise TargetError(f"no archive for {owner}/{repo}@{sha[:12]}") from None
