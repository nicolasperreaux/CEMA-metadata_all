#!/usr/bin/env python3
"""
Process all bibliographic references from liste-tout.txt.
This script creates batches for Claude to process.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def read_all_references(filepath):
    """Read all references from file."""
    references = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            reference = line.strip()
            if reference:
                references.append({'line_num': line_num, 'text': reference})
    return references


def save_json_result(line_num, json_data, json_dir):
    """Save a single JSON result."""
    output_file = json_dir / f"reference_{line_num:04d}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    return output_file


def save_batch_results(results, json_dir, error_log):
    """Save multiple results at once."""
    success_count = 0
    error_count = 0

    for item in results:
        try:
            line_num = item['line_num']
            json_data = item['data']

            save_json_result(line_num, json_data, json_dir)
            success_count += 1

            if success_count % 10 == 0:
                print(f"Processing reference {success_count}/{len(results)}...")

        except Exception as e:
            error_count += 1
            with open(error_log, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().isoformat()}] Line {item.get('line_num', '?')}: {e}\n")

    return success_count, error_count


def main():
    base_dir = Path('/home/user/CEMA-metadata_all')
    liste_file = base_dir / 'liste-tout.txt'
    json_dir = base_dir / 'json'
    error_log = base_dir / 'errors.log'

    # Create directories
    json_dir.mkdir(exist_ok=True)

    # Clear error log
    if error_log.exists():
        error_log.write_text('')

    print("Reading all references...")
    references = read_all_references(liste_file)
    print(f"Total references to process: {len(references)}\n")

    # Read processed results from stdin (JSON array)
    print("Waiting for processed results on stdin...")
    print("Expected format: JSON array with objects containing 'line_num' and 'data' fields")

    try:
        results = json.load(sys.stdin)

        if not isinstance(results, list):
            results = [results]

        print(f"\nReceived {len(results)} results to save...")
        success, errors = save_batch_results(results, json_dir, error_log)

        print(f"\n{'='*60}")
        print(f"Batch complete!")
        print(f"  Saved: {success}")
        print(f"  Errors: {errors}")
        print(f"{'='*60}")

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
