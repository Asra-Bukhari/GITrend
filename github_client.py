"""
github_client.py — GitHub API wrapper
Handles: timeouts, retries, rate limiting, caching, error responses
"""

import requests
import time
import json
import os
from datetime import datetime, timedelta
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────────
CACHE_FILE = ".cache.json"
CACHE_TTL_MINUTES = 15
REQUEST_TIMEOUT = 10       # seconds per request
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds between retries (exponential)

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_REPO_URL = "https://api.github.com/repos/{}"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # optional, raises rate limit


class GitHubError(Exception):
    """Raised for all GitHub API / network failures."""
    pass


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    """Load cache from disk. Returns empty dict on missing/corrupt file."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    """Persist cache to disk silently."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass  # Cache write failures are non-fatal


def _get_cached(key: str) -> Optional[dict]:
    """Return cached value if it exists and hasn't expired."""
    cache = _load_cache()
    entry = cache.get(key)
    if not entry:
        return None
    cached_at = datetime.fromisoformat(entry["cached_at"])
    if datetime.now() - cached_at > timedelta(minutes=CACHE_TTL_MINUTES):
        return None  # Expired
    return entry["data"]


def _set_cached(key: str, data: dict) -> None:
    cache = _load_cache()
    cache[key] = {
        "cached_at": datetime.now().isoformat(),
        "data": data
    }
    _save_cache(cache)


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _build_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _get(url: str, params: dict = None) -> dict:
    """
    GET request with retry + exponential backoff.
    Raises GitHubError on all failure modes.
    """
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                params=params,
                headers=_build_headers(),
                timeout=REQUEST_TIMEOUT
            )

            # Rate limit hit — tell user clearly
            if response.status_code == 403:
                remaining = response.headers.get("X-RateLimit-Remaining", "?")
                reset_ts = response.headers.get("X-RateLimit-Reset")
                if reset_ts:
                    reset_time = datetime.fromtimestamp(int(reset_ts)).strftime("%H:%M:%S")
                    raise GitHubError(
                        f"GitHub rate limit hit. Resets at {reset_time}. "
                        f"Set GITHUB_TOKEN env var to get 5x more requests."
                    )
                raise GitHubError("GitHub API returned 403 Forbidden.")

            # Repo not found
            if response.status_code == 404:
                raise GitHubError("Repository not found. Check the owner/repo name.")

            # Server errors — worth retrying
            if response.status_code >= 500:
                last_error = GitHubError(f"GitHub server error ({response.status_code}). Retrying...")
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF[attempt]
                    print(f"   ⏳ GitHub returned {response.status_code}, retrying in {wait}s...")
                    time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            last_error = GitHubError(
                f"Request timed out after {REQUEST_TIMEOUT}s (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                print(f"   ⏳ Timeout, retrying in {wait}s...")
                time.sleep(wait)

        except requests.exceptions.ConnectionError:
            raise GitHubError("Cannot reach GitHub. Check your internet connection.")

        except requests.exceptions.HTTPError as e:
            raise GitHubError(f"HTTP error: {e}")

        except GitHubError:
            raise  # Don't swallow our own errors

    raise last_error or GitHubError("Request failed after all retries.")


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_trending(language: str = "", period: str = "daily", limit: int = 10) -> list[dict]:
    """
    Fetch trending repositories from GitHub Search API.

    GitHub has no official "trending" endpoint, so we simulate it:
    - daily   → pushed in last 1 day,  sort by stars
    - weekly  → pushed in last 7 days, sort by stars
    - monthly → pushed in last 30 days, sort by stars

    Results are cached for CACHE_TTL_MINUTES to avoid hammering the API.
    Falls back to stale cache if the API is unreachable.
    """
    # Build date cutoff
    period_days = {"daily": 1, "weekly": 7, "monthly": 30}
    days = period_days.get(period, 1)
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Build search query
    query = f"pushed:>{since}"
    if language:
        query += f" language:{language}"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(limit, 25)
    }

    cache_key = f"trending_{language}_{period}_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        cached["_from_cache"] = True
        return cached["items"]

    try:
        data = _get(GITHUB_SEARCH_URL, params=params)
        _set_cached(cache_key, data)
        return data.get("items", [])

    except GitHubError as e:
        # Fall back to stale cache if available
        stale = _load_cache().get(cache_key)
        if stale:
            print(f"   ⚠️  API unavailable ({e}). Showing cached results.")
            return stale["data"].get("items", [])
        raise


def fetch_repo_detail(full_name: str) -> dict:
    """
    Fetch detailed info for a single repo by 'owner/repo' name.
    Cached separately per repo.
    """
    cache_key = f"repo_{full_name.lower()}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = GITHUB_REPO_URL.format(full_name)
    data = _get(url)
    _set_cached(cache_key, data)
    return data
