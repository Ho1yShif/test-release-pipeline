import subprocess
import json
import os
import pathlib
from typing import List, Dict, Optional, Any, Union
import sys

DEFAULT_REPO = os.getenv("DEFAULT_REPO")


def fetch_release_notes(
    repos: Union[str, List[str], pathlib.Path],
    timeout_seconds: int = 120,
    since_date: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Fetches release notes from one or multiple GitHub repositories using the GitHub CLI.
    Works with both public and private repositories, provided the authenticated user has access.

    Args:
        repos (Union[str, List[str], pathlib.Path]): A single repository string, list of repository strings,
                                                  or path to a JSON file containing a list of repos
                                                  in format "owner/repo". Defaults to value from DEFAULT_REPO.
        timeout_seconds (int): Timeout in seconds for API calls. Defaults to 120 seconds.
        since_date (Optional[str]): Only include releases created after this date (YYYY-MM-DD).

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary mapping repo names to their latest release info

    Example usage:
        fetch_release_notes(repos="Ho1yShif/test-release-pipeline", since_date="2024-06-01")
    """

    # Check GitHub CLI is installed
    try:
        subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            check=True,
            timeout=timeout_seconds,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        print(
            "Error: GitHub CLI (gh) is not installed or not in PATH. Please install it: https://cli.github.com/"
        )
        sys.exit(1)

    # Process the repos input to handle various formats
    if isinstance(repos, pathlib.Path) or (
        isinstance(repos, str) and os.path.exists(repos) and repos.endswith(".json")
    ):
        try:
            with open(repos, "r") as f:
                repos = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading repos from JSON file: {e}")
            repos = [DEFAULT_REPO]  # Fall back to default
    elif isinstance(repos, str):
        # Single repo string or comma-separated list
        repos = [repo.strip() for repo in repos.split(",")]

    results = {}
    no_releases_count = 0
    total_repos = len(repos)

    # Check GitHub authentication status
    try:
        auth_check = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if auth_check.returncode != 0:
            print(
                "Warning: GitHub CLI authentication issue. You may not be able to access private repositories."
            )
            print(auth_check.stderr)
    except subprocess.SubprocessError as e:
        print(f"Warning: Unable to verify GitHub authentication: {e}")

    for repo in repos:
        try:
            # Verify access
            verify_access = subprocess.run(
                ["gh", "repo", "view", repo],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )

            if verify_access.returncode != 0:
                print(f"""Error: Cannot access repository {repo}. Please check:
1. You are authenticated with GitHub CLI ('gh auth status')
2. You have access to this repository
3. The repository name is correct""")
                continue

            # Fetch all releases, not just the latest
            result = subprocess.run(
                ["gh", "api", f"/repos/{repo}/releases"],
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout_seconds,
            )
            releases = json.loads(result.stdout)
            for release in releases:
                if since_date:
                    release_date = release.get("created_at", "")
                    if release_date and release_date <= since_date:
                        continue
                results[repo] = release

        except subprocess.TimeoutExpired:
            print(
                f"Timeout error: GitHub CLI for {repo} exceeded {timeout_seconds} seconds timeout"
            )
        except subprocess.CalledProcessError as e:
            print(f"Error calling GitHub CLI for {repo}: {e.stderr}")
        except Exception as e:
            print(f"Unexpected error processing {repo}: {e}")

    if no_releases_count > 0:
        print(
            f"\nSkipped {no_releases_count} out of {total_repos} repositories due to no available releases"
        )

    return results
