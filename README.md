# Release Notes Summarizer

A tool to fetch and summarize GitHub release notes from one or multiple repositories, generating well-organized, user-friendly summaries using AI.

## Features

- Fetch release notes from multiple GitHub repositories
- Combine releases into a unified summary
- Organize content by feature type (new features, improvements, bug fixes, etc.)
- Convert technical commit messages to user-friendly descriptions
- Support for multiple input formats (single repo, comma-separated list, JSON file)
- Generate formatted output files (MDX format)

## Prerequisites

- Python 3.7+
- GitHub CLI installed and authenticated
- OpenAI API key

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the dependencies:
   ```
   uv pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   cp .env.example .env
   ```
   
4. Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. Ensure you're authenticated with GitHub CLI:
   ```
   gh auth login
   ```

## Usage

The script provides several ways to specify which repositories to fetch release notes from:

### Single Repository

```bash
python summarize_release_notes.py --repos "owner/repo"
```

### Multiple Repositories (Comma-separated)

```bash
python summarize_release_notes.py --repos "owner1/repo1,owner2/repo2,owner3/repo3"
```

### JSON File with Repository List

Create a JSON file (e.g., `repos.json`) with the following content:
```json
[
  "owner1/repo1",
  "owner2/repo2"
]
```

Then run:
```bash
python summarize_release_notes.py --repos repos.json
```

Or use the dedicated parameter:
```bash
python summarize_release_notes.py --repos-file repos.json
```

## Output Files

The script generates two output files in the current directory:

- `formatted_summary.mdx` - Contains the AI-generated summary of all releases
- `notes.mdx` - Contains the original release notes

## Customization

You can modify the default repository in your `.env` file by adding:
```
DEFAULT_REPO=owner/repository
```

## Example Output

```md
# 🗓️ Week of 2023-05-01

🚀 Features
- Export functionality has been added for saving your work
- New dashboard widgets are now available

🌟 Improvements
- Database performance has been optimized for faster queries
- User interface has been updated with a more modern design

🛠️ Bug fixes
- Login error has been resolved when using special characters
- CSS overflow issue has been fixed improving layout stability
```
