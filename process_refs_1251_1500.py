#!/usr/bin/env python3
"""
Process bibliographic references 1251-1500 from liste-tout.txt
Creates JSON files in json-corrected/ directory with reference_number as first field.
"""

import os
import json
import sys
import time
from pathlib import Path
from collections import OrderedDict

try:
    import anthropic
except ImportError:
    print("Installing anthropic package...")
    os.system(f"{sys.executable} -m pip install anthropic --quiet")
    import anthropic


# Read the extraction prompt
PROMPT_FILE = Path(__file__).parent / 'prompt-CC.txt'
with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
    EXTRACTION_PROMPT = f.read()


def read_references_range(filepath, start_line, end_line):
    """Read references from start_line to end_line (inclusive)."""
    references = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            if start_line <= line_num <= end_line:
                # Extract text after the line number marker
                if '→' in line:
                    reference_text = line.split('→', 1)[1].strip()
                    references.append((line_num, reference_text))
    return references


def get_completed_references(json_dir, start_line, end_line):
    """Get set of already-completed reference numbers in the range."""
    completed = set()
    if not json_dir.exists():
        return completed

    for line_num in range(start_line, end_line + 1):
        json_file = json_dir / f'reference_{line_num:04d}.json'
        if json_file.exists():
            completed.add(line_num)

    return completed


def process_reference(client, reference_text, line_num, max_retries=3):
    """Process a single reference using Claude API."""
    # Include the line number in the prompt
    full_prompt = f"{EXTRACTION_PROMPT}\n\n**Reference to process:**\n```\n{line_num}→{reference_text}\n```\n\nIMPORTANT: Include 'reference_number' as the FIRST field in the 'publication' object with value \"{line_num}\"."

    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                temperature=0,
                messages=[{"role": "user", "content": full_prompt}]
            )

            response_text = message.content[0].text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join([l for l in lines if not l.strip().startswith('```')])

            # Parse JSON
            result = json.loads(response_text)

            # Ensure reference_number is present and is FIRST field
            if 'publication' in result:
                pub = result['publication']

                # Add reference_number if missing
                if 'reference_number' not in pub:
                    pub['reference_number'] = str(line_num)

                # Reorder to put reference_number first
                ordered_pub = OrderedDict()
                ordered_pub['reference_number'] = str(line_num)
                for key, value in pub.items():
                    if key != 'reference_number':
                        ordered_pub[key] = value

                result['publication'] = ordered_pub

            return result, None

        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = min(60, 2 ** (attempt + 2))
                print(f"    Rate limit hit, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                return None, f"Rate limit exceeded after {max_retries} attempts"

        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing error: {str(e)}"
            if attempt < max_retries - 1:
                print(f"    {error_msg}, retrying...")
                time.sleep(2)
            else:
                return None, error_msg

        except anthropic.APIError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                print(f"    API error: {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return None, f"API error: {str(e)}"

        except Exception as e:
            return None, f"Unexpected error: {type(e).__name__}: {str(e)}"

    return None, "Max retries exceeded"


def save_json(data, output_path):
    """Save JSON data to file with reference_number first."""
    # Convert to ensure reference_number is first
    if 'publication' in data:
        ordered_pub = OrderedDict()
        if 'reference_number' in data['publication']:
            ordered_pub['reference_number'] = data['publication']['reference_number']
        for key, value in data['publication'].items():
            if key != 'reference_number':
                ordered_pub[key] = value
        data['publication'] = ordered_pub

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_error(error_log, line_num, reference, error_msg):
    """Log an error."""
    from datetime import datetime
    with open(error_log, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat()}] Line {line_num}: {error_msg}\n")
        f.write(f"  Reference: {reference[:200]}{'...' if len(reference) > 200 else ''}\n\n")


def main():
    # Configuration
    START_LINE = 1251
    END_LINE = 1500
    TOTAL_REFS = END_LINE - START_LINE + 1

    # Setup paths
    base_dir = Path('/home/user/CEMA-metadata_all')
    liste_file = base_dir / 'liste-tout.txt'
    json_dir = base_dir / 'json-corrected'
    error_log = base_dir / f'errors_refs_{START_LINE}_{END_LINE}.log'

    # Create directories
    json_dir.mkdir(exist_ok=True)

    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("=" * 70)
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("=" * 70)
        print("\nTo set your API key, run:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\nThen run this script again:")
        print(f"  python3 {sys.argv[0]}")
        print("=" * 70)
        sys.exit(1)

    # Initialize client
    client = anthropic.Anthropic(api_key=api_key)

    # Read references in range
    print("=" * 70)
    print(f"PROCESSING REFERENCES {START_LINE}-{END_LINE}")
    print("=" * 70)
    print(f"\nReading references from liste-tout.txt...")
    references = read_references_range(liste_file, START_LINE, END_LINE)

    if len(references) != TOTAL_REFS:
        print(f"WARNING: Expected {TOTAL_REFS} references, found {len(references)}")

    # Check for already-completed references
    completed = get_completed_references(json_dir, START_LINE, END_LINE)
    remaining_refs = [(num, ref) for num, ref in references if num not in completed]

    print(f"Total references:      {len(references)}")
    print(f"Already processed:     {len(completed)}")
    print(f"Remaining to process:  {len(remaining_refs)}")
    print("=" * 70)

    if not remaining_refs:
        print("\n✓ All references in this range already processed!")
        return

    # Ask for confirmation
    response = input(f"\nProcess {len(remaining_refs)} references? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Process references
    print(f"\nStarting processing...\n")
    success_count = 0
    error_count = 0
    start_time = time.time()

    for idx, (line_num, reference) in enumerate(remaining_refs, start=1):
        # Show progress
        if idx % 10 == 0 or idx == 1:
            elapsed = time.time() - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            eta_seconds = (len(remaining_refs) - idx) / rate if rate > 0 else 0
            eta_mins = eta_seconds / 60

            print(f"Processing reference {idx}/{len(remaining_refs)} (line {line_num})...")
            print(f"  Progress: {(idx/len(remaining_refs)*100):.1f}% | "
                  f"Rate: {rate:.1f} ref/s | ETA: {eta_mins:.1f} min")

        # Create output filename
        output_file = json_dir / f"reference_{line_num:04d}.json"

        # Process the reference
        result, error = process_reference(client, reference, line_num)

        if result is not None:
            save_json(result, output_file)
            success_count += 1
            if idx % 10 != 0:
                print(f"  ✓ Line {line_num}")
        else:
            log_error(error_log, line_num, reference, error)
            error_count += 1
            print(f"  ✗ Line {line_num}: {error}")

        # Rate limiting: small delay between requests
        time.sleep(0.5)

    # Final summary
    elapsed_total = time.time() - start_time
    print(f"\n{'=' * 70}")
    print("PROCESSING COMPLETE!")
    print("=" * 70)
    print(f"References processed:    {success_count}")
    print(f"Errors:                  {error_count}")
    print(f"Total time:              {elapsed_total/60:.1f} minutes")
    print(f"Average rate:            {len(remaining_refs)/elapsed_total:.2f} ref/second")
    if error_count > 0:
        print(f"\nError log:               {error_log}")
    print(f"Output directory:        {json_dir}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        print("Progress has been saved. Run the script again to resume.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
