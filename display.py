from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box
from rich.progress_bar import ProgressBar
from rich.rule import Rule
from collections import Counter
from datetime import datetime

console = Console()

# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_number(n: int) -> str:
    """Format large numbers: 12345 → 12.3k"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _stars_bar(stars: int, max_stars: int, width: int = 20) -> Text:
    """Return a Rich Text bar like ████████░░░░ scaled to max_stars."""
    filled = int((stars / max_stars) * width) if max_stars else 0
    t = Text()
    t.append("█" * filled, style="yellow")
    t.append("░" * (width - filled), style="dim")
    return t


def _language_color(lang: str) -> str:
    """Map language names to Rich color strings."""
    colors = {
        "python": "green",
        "javascript": "yellow",
        "typescript": "cyan",
        "rust": "red",
        "go": "bright_cyan",
        "java": "bright_red",
        "c": "bright_white",
        "c++": "magenta",
        "cpp": "magenta",
        "ruby": "red",
        "swift": "orange3",
        "kotlin": "bright_magenta",
        "shell": "bright_green",
        "dockerfile": "blue",
        "html": "bright_red",
        "css": "bright_blue",
        "php": "blue",
        "scala": "red",
        "dart": "cyan",
        "r": "bright_blue",
    }
    return colors.get((lang or "").lower(), "white")


def _days_ago(date_str: str) -> str:
    """Convert ISO date string to '3 days ago' style."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        delta = datetime.now(dt.tzinfo) - dt
        days = delta.days
        if days == 0:
            return "today"
        if days == 1:
            return "yesterday"
        return f"{days}d ago"
    except Exception:
        return date_str[:10]


# ── Views ──────────────────────────────────────────────────────────────────────

def show_trending(repos: list[dict], language: str = "", period: str = "daily") -> None:
    """Render the main trending table."""
    if not repos:
        console.print("[yellow]No repositories found for that filter.[/yellow]")
        return

    lang_label = f"[cyan]{language}[/cyan]" if language else "[dim]all languages[/dim]"
    period_label = {"daily": "today", "weekly": "this week", "monthly": "this month"}.get(period, period)

    console.print()
    console.print(Rule(f"[bold]GITrend[/bold]  ·  Trending {lang_label}  ·  {period_label}"))
    console.print()

    max_stars = max((r.get("stargazers_count", 0) for r in repos), default=1)

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white",
        border_style="bright_black",
        expand=True,
        pad_edge=False
    )

    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Repository", style="bold", min_width=22)
    table.add_column("Language", width=14)
    table.add_column("⭐ Stars", justify="right", width=8)
    table.add_column("🍴 Forks", justify="right", width=7)
    table.add_column("★ Trend", min_width=22)
    table.add_column("Pushed", width=10)

    for i, repo in enumerate(repos, 1):
        name = repo.get("full_name", "?")
        lang = repo.get("language") or "—"
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        pushed = _days_ago(repo.get("pushed_at", ""))
        lang_color = _language_color(lang)
        bar = _stars_bar(stars, max_stars)

        table.add_row(
            str(i),
            f"[link=https://github.com/{name}]{name}[/link]",
            f"[{lang_color}]{lang}[/]",
            f"[yellow]{_fmt_number(stars)}[/yellow]",
            f"[dim]{_fmt_number(forks)}[/dim]",
            bar,
            f"[dim]{pushed}[/dim]"
        )

    console.print(table)

    # Footer tip
    console.print()
    console.print(
        f"[dim]  💡 Try: python main.py --detail <owner/repo>  ·  "
        f"python main.py --stats  ·  python main.py -l rust -p weekly[/dim]"
    )
    console.print()


def show_repo_detail(repo: dict) -> None:
    """Render a detailed panel for a single repo."""
    name = repo.get("full_name", "unknown")
    desc = repo.get("description") or "[dim]No description provided[/dim]"
    lang = repo.get("language") or "—"
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    watchers = repo.get("watchers_count", 0)
    issues = repo.get("open_issues_count", 0)
    license_info = (repo.get("license") or {}).get("name", "—")
    created = repo.get("created_at", "")[:10]
    updated = _days_ago(repo.get("updated_at", ""))
    topics = repo.get("topics", [])
    default_branch = repo.get("default_branch", "main")
    url = repo.get("html_url", "")
    lang_color = _language_color(lang)

    console.print()
    console.print(Rule(f"[bold]📦 {name}[/bold]"))
    console.print()
    console.print(f"  {desc}")
    console.print()

    # Stats row
    stats = Table.grid(padding=(0, 3))
    stats.add_row(
        f"[yellow]⭐ {_fmt_number(stars)}[/yellow] stars",
        f"[cyan]🍴 {_fmt_number(forks)}[/cyan] forks",
        f"[green]👁  {_fmt_number(watchers)}[/green] watchers",
        f"[red]🐛 {issues}[/red] open issues"
    )
    console.print(stats)
    console.print()

    # Metadata
    meta = Table.grid(padding=(0, 2))
    meta.add_column(style="dim", width=16)
    meta.add_column()
    meta.add_row("Language",      f"[{lang_color}]{lang}[/]")
    meta.add_row("License",       license_info)
    meta.add_row("Default branch", default_branch)
    meta.add_row("Created",       created)
    meta.add_row("Last updated",  updated)
    meta.add_row("URL",           f"[link={url}]{url}[/link]")

    if topics:
        topic_str = "  ".join(f"[bright_black on white] {t} [/]" for t in topics[:8])
        meta.add_row("Topics", topic_str)

    console.print(meta)
    console.print()


def show_language_stats(repos: list[dict]) -> None:
    """Show a bar chart of language distribution in today's trending."""
    if not repos:
        console.print("[yellow]No data available.[/yellow]")
        return

    lang_counts = Counter(
        r.get("language") or "Unknown"
        for r in repos
    )
    star_totals: dict[str, int] = {}
    for r in repos:
        lang = r.get("language") or "Unknown"
        star_totals[lang] = star_totals.get(lang, 0) + r.get("stargazers_count", 0)

    total = sum(lang_counts.values())
    top = lang_counts.most_common(10)
    max_count = top[0][1] if top else 1

    console.print()
    console.print(Rule("[bold]📊 Language Breakdown — Today's Trending[/bold]"))
    console.print()

    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold dim",
        border_style="bright_black"
    )
    table.add_column("Language", min_width=16)
    table.add_column("Repos", justify="right", width=6)
    table.add_column("Share", width=30)
    table.add_column("Total Stars", justify="right", width=12)

    for lang, count in top:
        pct = count / total * 100
        bar_len = int((count / max_count) * 25)
        bar = Text()
        bar.append("█" * bar_len, style=_language_color(lang))
        bar.append("░" * (25 - bar_len), style="dim")
        bar.append(f" {pct:.0f}%", style="dim")
        stars = _fmt_number(star_totals.get(lang, 0))

        table.add_row(
            f"[{_language_color(lang)}]{lang}[/]",
            str(count),
            bar,
            f"[yellow]{stars}[/yellow]"
        )

    console.print(table)
    console.print(f"  [dim]Based on {total} trending repositories · {len(lang_counts)} languages total[/dim]")
    console.print()
