import subprocess
import json
import os
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import sys
import argparse
import pathlib

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# Set your API keys and configuration from environment variables
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
GITHUB_USERNAME: Optional[str] = os.getenv("GITHUB_USERNAME")
DEFAULT_REPO: Optional[str] = os.getenv("DEFAULT_REPO")

if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY not found. Please set it in the .env file.")

client: OpenAI = OpenAI(api_key=OPENAI_API_KEY)


def fetch_release_notes(
    repos: Union[str, List[str], pathlib.Path] = DEFAULT_REPO,
) -> Dict[str, Dict[str, Any]]:
    """
    Fetches release notes from one or multiple GitHub repositories using the GitHub CLI.
    Works with both public and private repositories, provided the authenticated user has access.

    Args:
        repos (Union[str, List[str], pathlib.Path]): A single repository string, list of repository strings,
                                                  or path to a JSON file containing a list of repos
                                                  in format "owner/repo". Defaults to value from DEFAULT_REPO.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary mapping repo names to their latest release info
    """
    # Process the repos input to handle various formats
    if isinstance(repos, pathlib.Path) or (
        isinstance(repos, str) and os.path.exists(repos) and repos.endswith(".json")
    ):
        # It's a file path to a JSON file
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

    for repo in repos:
        try:
            # Verify access
            verify_access = subprocess.run(
                ["gh", "repo", "view", repo],
                capture_output=True,
                text=True,
            )

            if verify_access.returncode != 0:
                print(f"""Error: Cannot access repository {repo}. Please check:
1. You are authenticated with GitHub CLI ('gh auth status')
2. You have access to this repository
3. The repository name is correct""")
                continue

            # Fetch the releases from specified repo with detailed format
            result: subprocess.CompletedProcess = subprocess.run(
                ["gh", "api", f"/repos/{repo}/releases", "--jq", ".[]"],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                print(f"No releases found in {repo}")
                continue

            try:
                # Try to parse as a list of releases
                releases: List[Dict[str, Any]] = [
                    json.loads(release) for release in result.stdout.strip().split("\n")
                ]
            except json.JSONDecodeError:
                # If that fails, try parsing as a single release
                try:
                    releases = [json.loads(result.stdout)]
                except json.JSONDecodeError as e:
                    print(f"Error parsing release data for {repo}: {e}")
                    continue

            # Only store the latest release from each repository
            if releases:
                latest_release = releases[0]
                results[repo] = latest_release

                # Debug: Print what we found
                print(f"""
Found latest release for {repo}:
Tag: {latest_release.get("tag_name")}
Name: {latest_release.get("name")}
Body length: {len(latest_release.get("body", ""))}
Created: {latest_release.get("created_at")}""")

        except subprocess.CalledProcessError as e:
            print(f"Error calling GitHub CLI for {repo}: {e.stderr}")
        except Exception as e:
            print(f"Unexpected error processing {repo}: {e}")

    return results


def summarize_release(note: str, release_tag: str) -> tuple[str, str]:
    """
    Use OpenAI API to summarize the provided release note text.

    Args:
        note (str): The release note text to summarize
        release_tag (str): The tag/version of the release

    Returns:
        tuple[str, str]: Original notes and a summarized version of the release notes
    """
    cleaned_note = note.strip()

    # Check for common non-content cases
    if not cleaned_note:
        return note, "No release notes provided."
    if cleaned_note.startswith("**Full Changelog**:"):
        return (
            note,
            "This release only contains a link to the changelog. Please visit the repository for detailed changes.",
        )

    SYSTEM_PROMPT: str = """You are a release notes organizer. Reorganize the given release notes into a clear, user-friendly format.

Input:
{note}

Instructions:
1. Identify existing sections in the release notes (like "Features", "Bug Fixes", "BREAKING CHANGES")
2. Remove commit hashes in parentheses (e.g., "(d6188e0)")
3. Format entries as bullet points: "- [Feature description]"
4. Use clear, user-friendly language while preserving technical terms
5. Organize into these sections (only include sections that have content):
   - 🚀 Features
   - 🌟 Improvements
   - 🛠️ Bug fixes
   - ⚠️ Breaking changes
   - 📝 Additional changes

6. For each item, convert technical commit messages to user-friendly descriptions:
   - "add line" → "New line functionality has been added"
   - "fix css overflow" → "CSS overflow issue has been fixed"

7. IMPORTANT: Strictly exclude the following from your output:
   - Any mentions of branches (main, master, develop, feature, etc.)
   - Any references to branch integration or merges
   - Any language about "added to branch" or "integrated into branch"
   - Dependency version bumps
   - Test additions
   - Work in progress (WIP) items
   - Commit hashes

8. When processing entries like "add X workflow to main":
   - Keep only the core functionality: "X workflow has been added"
   - REMOVE all branch references like "to main", "from feature", etc.

9. Never add or infer features not explicitly stated in the original notes

Sample input:
```
⚠ BREAKING CHANGES
update authentication requirement
Features
add export functionality (d6188e0)
add release please workflow to main (cb9528c)
Bug Fixes
fix css overflow (413ac2d)
```

Sample output:
```
⚠️ Breaking changes
- Authentication requirements have been updated which may require changes to existing integrations

🚀 Features
- Export functionality has been added for saving your work
- Release please workflow has been added

🛠️ Bug fixes
- CSS overflow issue has been fixed, improving layout stability
```
"""

    try:
        response: Any = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(note=cleaned_note),
                },
            ],
            temperature=0.1,  # Very low temperature to minimize creativity
            max_tokens=500,  # Increased to handle longer notes
        )

        summary: str = response.choices[0].message.content.strip()

        # Fall back to original if the summary is empty or too short
        if not summary or len(summary) < 10:
            return note, f"Original release notes:\n\n{cleaned_note}"

        return note, summary
    except Exception as e:
        print(f"Error obtaining summary from OpenAI: {e}")
        return note, "Summary not available."


def get_monday_of_week(date_str: str) -> str:
    """
    Get the Monday of the week for a given date string.

    Args:
        date_str (str): Date string in ISO format (e.g. '2024-03-21T10:30:00Z')

    Returns:
        str: Date string for Monday of that week in YYYY-MM-DD format
    """
    # Parse the ISO date string
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    # Calculate the Monday of that week (weekday() returns 0 for Monday)
    monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")


def main() -> Optional[tuple[str, str]]:
    """
    Main function that fetches and summarizes the latest release notes from multiple repositories.

    Usage Examples:
    --------------
    1. Single repository:
       python summarize_release_notes.py --repos "owner/repo"

    2. Multiple comma-separated repositories:
       python summarize_release_notes.py --repos "owner1/repo1,owner2/repo2,owner3/repo3"

    3. JSON file containing repository list:
       python summarize_release_notes.py --repos repos.json

       Where repos.json content is like:
       [
         "owner1/repo1",
         "owner2/repo2"
       ]

    4. Using dedicated repos-file parameter:
       python summarize_release_notes.py --repos-file repos.json

    Returns:
        Optional[tuple[str, str]]: A tuple containing the raw notes and formatted summary,
                                  or None if no releases were found
    """
    # Set up argument parser
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

    args = parser.parse_args()

    # Process repos argument if provided
    if args.repos_file and os.path.exists(args.repos_file):
        repos = args.repos_file
    elif args.repos:
        if os.path.exists(args.repos) and args.repos.endswith(".json"):
            # Path to JSON file
            repos = args.repos
        else:
            # Single repo or comma-separated list
            repos = args.repos
    else:
        repos = DEFAULT_REPO

    # Fetch releases from all specified repositories
    repo_releases = fetch_release_notes(repos)

    if not repo_releases:
        print("No releases fetched from any repository.")
        return None

    # Find the most recent release across all repositories
    most_recent_date = None
    combined_notes = ""

    for repo, release in repo_releases.items():
        created_at = release.get("created_at", "")
        if not created_at:
            continue

        release_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")

        if most_recent_date is None or release_date > most_recent_date:
            most_recent_date = release_date

    # Format the combined notes with repo names and content
    for repo, release in repo_releases.items():
        tag_name = release.get("tag_name", "unknown")
        body = release.get("body", "")

        if body.strip():
            combined_notes += f"\n## {repo} ({tag_name})\n\n{body}\n\n"

    if combined_notes:
        print("Summarizing combined release notes...")
        all_notes, summary = summarize_release(combined_notes, "Combined Releases")

        monday_date = (
            get_monday_of_week(most_recent_date.strftime("%Y-%m-%dT%H:%M:%SZ"))
            if most_recent_date
            else datetime.now().strftime("%Y-%m-%d")
        )

        formatted_summary = f"""# 🗓️ Week of {monday_date}\n\n{summary}"""

        print(f"Combined Release Summary:\n{formatted_summary}")

        return all_notes, formatted_summary
    else:
        print("No release notes found in any repository.")
        return None


if __name__ == "__main__":
    try:
        # Call main() which returns notes and formatted_summary
        result = main()

        if result:
            notes, formatted_summary = result

            # Write formatted_summary to formatted_summary.mdx in repo root
            with open("formatted_summary.mdx", "w", encoding="utf-8") as f:
                f.write(formatted_summary)

            # Write notes to raw_notes.mdx in repo root
            with open("raw_notes.mdx", "w", encoding="utf-8") as f:
                f.write(notes)

            print("Release notes written to formatted_summary.mdx and raw_notes.mdx")
    except Exception as e:
        import traceback

        print(f"Error: {str(e)}\n{traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)
