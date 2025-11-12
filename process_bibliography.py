#!/usr/bin/env python3
"""
Process bibliographic references using Anthropic Claude API.
Reads references from liste.txt, applies extraction prompt from prompt-CC.txt,
and generates JSON files for each reference.
"""

import os
import json
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not installed. Installing...")
    os.system(f"{sys.executable} -m pip install anthropic")
    import anthropic


def read_file(filepath: str) -> str:
    """Read file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def get_references(filepath: str) -> list[tuple[int, str]]:
    """Read references from liste.txt and return list of (line_number, reference) tuples."""
    references = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            # Remove the arrow prefix if present and strip whitespace
            reference = line.strip()
            if reference and '→' in reference:
                reference = reference.split('→', 1)[1].strip()
            if reference:  # Only add non-empty references
                references.append((line_num, reference))
    return references


def process_reference(client: anthropic.Anthropic, prompt_template: str, reference: str, max_retries: int = 3) -> Optional[dict]:
    """
    Process a single reference using Claude API.
    Returns the extracted JSON data or None if processing fails.
    """
    # Combine the prompt template with the actual reference
    full_prompt = f"{prompt_template}\n\n**Reference to process:**\n```\n{reference}\n```"

    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            )

            # Extract the response text
            response_text = message.content[0].text.strip()

            # Try to parse as JSON (remove markdown code blocks if present)
            if response_text.startswith('```'):
                # Remove markdown code blocks
                lines = response_text.split('\n')
                response_text = '\n'.join([l for l in lines if not l.strip().startswith('```')])

            # Parse JSON
            result = json.loads(response_text)
            return result

        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"  Rate limit hit, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                raise
        except json.JSONDecodeError as e:
            print(f"  JSON parsing error: {e}")
            print(f"  Response was: {response_text[:200]}...")
            return None
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  Error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

    return None


def save_json(data: dict, output_path: str):
    """Save JSON data to file with proper formatting."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_error(error_log_path: str, line_number: int, reference: str, error_msg: str):
    """Log an error to the error log file."""
    with open(error_log_path, 'a', encoding='utf-8') as f:
        f.write(f"Line {line_number}: {error_msg}\n")
        f.write(f"  Reference: {reference}\n")
        f.write(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")


def main():
    """Main processing function."""
    # Setup paths
    base_dir = Path('/home/user/CEMA-metadata_all')
    liste_file = base_dir / 'liste-tout.txt'
    prompt_file = base_dir / 'prompt-CC.txt'
    json_dir = base_dir / 'json'
    error_log = base_dir / 'errors.log'

    # Create json directory if it doesn't exist
    json_dir.mkdir(exist_ok=True)

    # Clear error log if it exists
    if error_log.exists():
        error_log.unlink()

    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Please set it with: export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)

    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=api_key)

    # Read prompt template
    print("Reading prompt template...")
    prompt_template = read_file(str(prompt_file))

    # Read references
    print("Reading references...")
    references = get_references(str(liste_file))
    total_refs = len(references)
    print(f"Found {total_refs} references to process.\n")

    # Process each reference
    success_count = 0
    error_count = 0

    for idx, (line_num, reference) in enumerate(references, start=1):
        # Show progress every 10 references
        if idx % 10 == 0 or idx == 1:
            print(f"Processing reference {idx}/{total_refs}...")

        # Create output filename with zero-padded line number
        output_file = json_dir / f"reference_{line_num:04d}.json"

        try:
            # Process the reference
            result = process_reference(client, prompt_template, reference)

            if result is not None:
                # Save to JSON file
                save_json(result, str(output_file))
                success_count += 1
                print(f"  ✓ Line {line_num} -> {output_file.name}")
            else:
                error_msg = "Failed to parse JSON response from API"
                log_error(str(error_log), line_num, reference, error_msg)
                error_count += 1
                print(f"  ✗ Line {line_num}: {error_msg}")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            log_error(str(error_log), line_num, reference, error_msg)
            error_count += 1
            print(f"  ✗ Line {line_num}: {error_msg}")

        # Small delay to avoid rate limiting
        if idx < total_refs:
            time.sleep(0.5)

    # Final summary
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"  Total references: {total_refs}")
    print(f"  Successfully processed: {success_count}")
    print(f"  Errors: {error_count}")
    if error_count > 0:
        print(f"  Error log: {error_log}")
    print(f"  Output directory: {json_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
