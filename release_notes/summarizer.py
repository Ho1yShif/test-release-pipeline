from datetime import datetime, timedelta
from typing import Any, Optional, Tuple
from openai import OpenAI
from prompt import SYSTEM_PROMPT
import os
import logging

client: OpenAI = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize_release(note: str, release_tag: str) -> Tuple[str, str]:
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
        logging.error(f"Error obtaining summary from OpenAI: {e}")
        return note, "Summary not available."


def get_monday_of_week(date_str: str) -> str:
    """
    Get the Monday of the week for a given date string.
    If the date is a Sunday, return the next day's date (Monday).
    Args:
        date_str (str): Date string in ISO format (e.g. '2024-03-21T10:30:00Z')
    Returns:
        str: Date string for Monday of that week in YYYY-MM-DD format
    """
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    if date.weekday() == 6:  # Sunday
        monday = date + timedelta(days=1)
    else:
        monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")
