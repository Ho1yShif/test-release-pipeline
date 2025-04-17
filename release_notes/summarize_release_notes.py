import os
import sys
import argparse
import pathlib
from datetime import datetime
from typing import Optional, Tuple
import logging

from github_fetcher import fetch_release_notes
from summarizer import summarize_release, get_monday_of_week
from output import write_summary_and_notes, print_json_output


def main() -> Optional[Tuple[str, str]]:
    """
    Main function that fetches and summarizes the latest release notes from multiple repositories.

    Usage Examples:
    --------------
    1. Single repository:
       python summarize_release_notes.py --repos "owner/repo" --since-date 2024-06-01

    2. Multiple comma-separated repositories:
       python summarize_release_notes.py --repos "owner1/repo1,owner2/repo2,owner3/repo3" --since-date 2024-06-01

    3. JSON file containing repository list:
       python summarize_release_notes.py --repos repos.json --since-date 2024-06-01

       Where repos.json content is like:
       [
         "owner1/repo1",
         "owner2/repo2"
       ]

    4. Using dedicated repos-file parameter:
       python summarize_release_notes.py --repos-file repos.json --since-date 2024-06-01

    5. Using JSON output mode (for GitHub Actions):
       python summarize_release_notes.py --repos-file repos.json --since-date 2024-06-01 --json-output

    Returns:
        Optional[Tuple[str, str]]: A tuple containing the raw notes and formatted summary,
                                  or None if no releases were found
    """
    parser = argparse.ArgumentParser(
        description="Fetch and summarize GitHub release notes from multiple repositories."
    )
    parser.add_argument(
        "--repos",
        type=str,
        help="A single repo, comma-separated list of repos, or path to a JSON file containing repos to fetch",
    )
    parser.add_argument(
        "--repos-file",
        type=pathlib.Path,
        help="Path to a JSON file containing an array of repositories to fetch",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds for API calls",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results as JSON instead of writing to files (for GitHub Actions)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="review_release_notes",
        help="Directory to write output files to when not in JSON mode",
    )
    parser.add_argument(
        "--since-date",
        type=str,
        help="Only include releases created after this date (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    # Configure logging
    if args.json_output:
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.repos_file and os.path.exists(args.repos_file):
        repos = args.repos_file
    elif args.repos:
        if os.path.exists(args.repos) and args.repos.endswith(".json"):
            repos = args.repos
        else:
            repos = args.repos
    else:
        repos = os.getenv("DEFAULT_REPO")

    repo_releases = fetch_release_notes(
        repos, timeout_seconds=args.timeout, since_date=args.since_date
    )

    if not repo_releases:
        if args.json_output:
            print_json_output(
                {"error": "No releases with content fetched from any repository."}
            )
            return None
        else:
            logging.warning("No releases with content fetched from any repository.")
            return None

    most_recent_date = None
    combined_notes = ""
    for repo, release in repo_releases.items():
        created_at = release.get("created_at", "")
        if not created_at:
            continue
        release_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        if most_recent_date is None or release_date > most_recent_date:
            most_recent_date = release_date
    for repo in sorted(repo_releases.keys()):
        release = repo_releases[repo]
        body = release.get("body", "")
        if body.strip():
            combined_notes += f"\n{body}\n\n"
    if combined_notes:
        logging.info(f"Collected release notes from {len(repo_releases)} repositories")
        logging.info("Summarizing combined release notes...")
        all_notes, summary = summarize_release(combined_notes, "Combined Releases")
        monday_date = (
            get_monday_of_week(most_recent_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
            if most_recent_date
            else datetime.now().strftime("%Y-%m-%d")
        )
        formatted_summary = f"# 🗓️ Week of {monday_date}\n\n{summary}"
        logging.info(f"Combined Release Summary:\n{formatted_summary}")
        if args.json_output:
            result = {
                "formatted_summary": formatted_summary,
                "raw_notes": all_notes,
                "monday_date": monday_date,
                "repositories_count": len(repo_releases),
            }
            print_json_output(result)
            return None
        return all_notes, formatted_summary
    else:
        if args.json_output:
            print_json_output({"error": "No release notes found in any repository."})
            return None
        else:
            logging.warning("No release notes found in any repository.")
            return None


if __name__ == "__main__":
    try:
        args, _ = argparse.ArgumentParser().parse_known_args()
        json_output = False
        output_dir = "review_release_notes"
        for i, arg in enumerate(sys.argv):
            if arg == "--json-output":
                json_output = True
            elif arg == "--output-dir" and i + 1 < len(sys.argv):
                output_dir = sys.argv[i + 1]
        if json_output:
            main()
        else:
            result = main()
            if result:
                notes, formatted_summary = result
                write_summary_and_notes(
                    formatted_summary, notes, output_dir, json_output=json_output
                )
    except Exception as e:
        import traceback

        logging.error(f"Error: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)
