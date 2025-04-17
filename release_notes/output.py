import os
import json
import sys
import logging


def write_summary_and_notes(
    formatted_summary: str, notes: str, output_dir: str, json_output: bool = False
) -> None:
    """
    Write the formatted summary and raw notes to files in the specified output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    summary_path = os.path.join(output_dir, "formatted_summary.mdx")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(formatted_summary)
    notes_path = os.path.join(output_dir, "raw_notes.mdx")
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(notes)
    if not json_output:
        logging.info(
            f"Release notes written to: {summary_path}, {notes_path} for your review"
        )


def print_json_output(result: dict) -> None:
    """
    Print the result as a JSON string (for GitHub Actions or other automation).
    """
    print(json.dumps(result, indent=2))
