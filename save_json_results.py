#!/usr/bin/env python3
"""
Helper script to save JSON results from processed references.
Reads JSON objects from stdin and saves them to numbered files.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def save_results(json_data_list, start_line_num):
    """Save a list of JSON results to files."""
    base_dir = Path('/home/user/CEMA-metadata_all')
    json_dir = base_dir / 'json'
    error_log = base_dir / 'errors.log'

    json_dir.mkdir(exist_ok=True)

    success_count = 0
    error_count = 0

    for idx, item in enumerate(json_data_list):
        line_num = item.get('line_number', start_line_num + idx)

        # Extract the JSON data (remove line_number metadata)
        json_data = item.get('data', item)
        if 'line_number' in json_data:
            del json_data['line_number']

        try:
            output_file = json_dir / f"reference_{line_num:04d}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            print(f"✓ Saved: {output_file.name}")
            success_count += 1

        except Exception as e:
            error_msg = f"[{datetime.now().isoformat()}] Line {line_num}: Error saving - {e}\n"
            with open(error_log, 'a', encoding='utf-8') as f:
                f.write(error_msg)
            print(f"✗ Error on line {line_num}: {e}")
            error_count += 1

    print(f"\nResults: {success_count} saved, {error_count} errors")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # Read from stdin
        data = json.load(sys.stdin)

    if isinstance(data, list):
        save_results(data, 1)
    else:
        save_results([data], 1)
