import argparse
import sys
from display import show_trending, show_repo_detail, show_language_stats
from github_client import fetch_trending, fetch_repo_detail, GitHubError

VALID_LANGUAGES = [
    "python", "javascript", "typescript", "java", "c", "cpp", "c++",
    "go", "rust", "ruby", "swift", "kotlin", "php", "shell", "html",
    "css", "dart", "scala", "r", "lua", "haskell", "elixir", "clojure",
    "julia", "vim script", "dockerfile", "makefile"
]

VALID_PERIODS = ["daily", "weekly", "monthly"]


def suggest_language(name: str) -> list[str]:
    """Return close matches for a mistyped language."""
    name = name.lower()
    return [lang for lang in VALID_LANGUAGES if name in lang or lang in name]


def main():
    parser = argparse.ArgumentParser(
        prog="gitrend",
        description="GITrend — Explore GitHub Trending Repos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Top trending today (all languages)
  python main.py -l python                # Python trending repos
  python main.py -l javascript -p weekly  # JS trending this week
  python main.py -l rust -p monthly -n 5  # Top 5 Rust repos this month
  python main.py --stats                  # Language breakdown of trending
  python main.py --detail torvalds/linux  # Details for a specific repo
        """
    )

    parser.add_argument(
        "-l", "--language",
        type=str,
        default="",
        help="Filter by programming language (e.g. python, javascript, rust)"
    )
    parser.add_argument(
        "-p", "--period",
        type=str,
        default="daily",
        choices=VALID_PERIODS,
        help="Time period: daily, weekly, or monthly (default: daily)"
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="Number of repos to show (default: 10, max: 25)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show language breakdown chart for today's trending"
    )
    parser.add_argument(
        "--detail",
        type=str,
        metavar="OWNER/REPO",
        help="Show detailed info for a specific repo (e.g. --detail torvalds/linux)"
    )

    args = parser.parse_args()

    # --- Validate: limit ---
    if args.limit < 1 or args.limit > 25:
        print("❌ --limit must be between 1 and 25.")
        sys.exit(1)

    # --- Validate: language input ---
    if args.language:
        lang_input = args.language.strip().lower()
        if lang_input not in VALID_LANGUAGES:
            suggestions = suggest_language(lang_input)
            print(f"❌ Unknown language: '{args.language}'")
            if suggestions:
                print(f"   Did you mean: {', '.join(suggestions)}?")
            else:
                print(f"   Supported languages include: {', '.join(VALID_LANGUAGES[:10])}, ...")
            sys.exit(1)
        args.language = lang_input

    # --- Mode: detail view ---
    if args.detail:
        if "/" not in args.detail:
            print("❌ Invalid format. Use --detail owner/repo  (e.g. --detail torvalds/linux)")
            sys.exit(1)
        try:
            repo = fetch_repo_detail(args.detail)
            show_repo_detail(repo)
        except GitHubError as e:
            print(f"❌ {e}")
            sys.exit(1)
        return

    # --- Mode: language stats ---
    if args.stats:
        try:
            repos = fetch_trending(language="", period="daily", limit=25)
            show_language_stats(repos)
        except GitHubError as e:
            print(f"❌ {e}")
            sys.exit(1)
        return

    # --- Default mode: show trending ---
    try:
        repos = fetch_trending(
            language=args.language,
            period=args.period,
            limit=args.limit
        )
        show_trending(repos, language=args.language, period=args.period)
    except GitHubError as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
