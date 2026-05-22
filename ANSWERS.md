# ANSWERS.md

---

## 1. How to Run

**Requirements:** Python 3.10+, internet connection

```bash
# 1. Clone and enter the project
git clone https://github.com/YOUR_USERNAME/dev-pulse.git
cd dev-pulse

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run it
python main.py                  # Top trending today
python main.py -l python        # Python repos
python main.py --stats          # Language chart
python main.py --detail torvalds/linux  # Repo detail
```

No API key is required for basic usage. If you hit GitHub's rate limit (10 req/min unauthenticated), set a free GitHub token:

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

See README.md for full token setup steps.

---

## 2. Stack Choice

**Why Python + requests + rich:**

- **Python** is the natural choice for a CLI data tool — clean `argparse`, excellent HTTP libraries, fast iteration time.
- **requests** is the standard for HTTP in Python. It handles connection pooling, timeout parameters, and gives clean access to response headers (needed for rate limit info).
- **rich** produces genuinely impressive terminal output (tables, progress bars, colored text, clickable links) with almost no boilerplate. The visual quality makes a real difference for a portfolio project.

**What would have been worse:**

- **Node.js/JavaScript** — fine for web, but Python is faster to write and has a more ergonomic CLI story. `argparse` beats manually parsing `process.argv`.
- **Go** — would produce a fast binary, but Go's terminal formatting ecosystem is less mature than `rich`, and the extra complexity doesn't pay off here.
- **curl + bash** — could do the API calls, but error handling, JSON parsing, and any visual formatting becomes a nightmare. Not maintainable.

---

## 3. One Real Edge Case

**Stale cache fallback when the API is unreachable**

**File:** `github_client.py`, lines 103–110

```python
    except GitHubError as e:
        # Fall back to stale cache if available
        stale = _load_cache().get(cache_key)
        if stale:
            print(f"   ⚠️  API unavailable ({e}). Showing cached results.")
            return stale["data"].get("items", [])
        raise
```

**What it handles:** If GitHub is down, the request times out, or the user has no internet — instead of crashing with an unhelpful traceback, the tool checks if there's a previous response on disk (even if it's expired). If one exists, it uses that data and tells the user.

**Without this handling:** The tool would raise a `GitHubError` and exit immediately with an error message. If a user is demoing the project offline, or GitHub has a brief outage, the tool would simply fail. With the stale fallback, it degrades gracefully — showing potentially slightly old data is vastly better than showing nothing.

---

## 4. AI Usage

**Tool used:** Claude (claude.ai)

### Usage 1 — Initial scaffolding
**Asked:** Generate a Python CLI project structure for a GitHub trending explorer using `argparse`, `requests`, and `rich`. Include retry logic and caching.

**What it gave:** A working skeleton for all three files with basic retry logic using a fixed sleep interval.

**What I changed:** The AI used `time.sleep(2)` as a flat retry delay. I changed this to exponential backoff with the `RETRY_BACKOFF = [1, 2, 4]` list (`github_client.py`, line 16), because flat delays waste time on transient errors that usually resolve in under a second, and a fixed long delay would feel sluggish. Exponential backoff is the correct pattern for production HTTP clients.

### Usage 2 — Sparkline bar rendering
**Asked:** How to render a proportional fill bar using Unicode block characters in Python, scaled to a maximum value.

**What it gave:** A one-liner using `int((val / max_val) * width)` with `█` and `░`. I wrapped this into the `_stars_bar()` function in `display.py` with Rich markup tags so the filled portion renders in yellow and the empty portion in dim grey.

### Usage 3 — Rate limit error messaging
**Asked:** How to read GitHub's `X-RateLimit-Reset` header and convert it to a human-readable time.

**What it gave:** `datetime.fromtimestamp(int(reset_ts)).strftime(...)`. I added a fallback for when the header is missing (the `"?"` default in line 67 of `github_client.py`), since the AI's version would crash with a `TypeError` if GitHub omitted that header.

---

## 5. Honest Gap

**The "trending" simulation is an approximation.**

GitHub doesn't expose a public trending API — the trending page at `github.com/trending` is not backed by a documented API endpoint. This project simulates it by searching for repos sorted by stars that were pushed recently (last 1/7/30 days). This is a reasonable proxy, but it's not identical to GitHub's actual trending algorithm, which factors in recent star velocity, not just total stars.

**What I'd do with another day:**

Scrape `github.com/trending` directly using `requests` + `BeautifulSoup` to get the exact same data GitHub shows on its trending page. The HTML structure is stable enough to parse reliably. I'd cache those results with the same TTL system that's already in place, and fall back to the search API if the scrape fails. This would make the "trending" data genuinely accurate instead of an approximation.
