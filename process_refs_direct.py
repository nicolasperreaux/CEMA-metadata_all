#!/usr/bin/env python3
"""
Process bibliographic references by reading references and outputting them
for Claude to process directly in the conversation.
"""

import json
import sys
from pathlib import Path


def read_references(filepath: str, start_line: int = 1, count: int = None):
    """Read references from file, optionally limiting range."""
    references = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            if line_num < start_line:
                continue
            if count and len(references) >= count:
                break

            reference = line.strip()
            if reference:
                references.append((line_num, reference))

    return references


def save_json(data: dict, output_path: str):
    """Save JSON data to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_error(error_log_path: str, line_number: int, error_msg: str):
    """Log an error."""
    with open(error_log_path, 'a', encoding='utf-8') as f:
        f.write(f"Line {line_number}: {error_msg}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 process_refs_direct.py <start_line> [count]")
        print("Example: python3 process_refs_direct.py 1 50")
        sys.exit(1)

    base_dir = Path('/home/user/CEMA-metadata_all')
    liste_file = base_dir / 'liste-tout.txt'

    start_line = int(sys.argv[1])
    count = int(sys.argv[2]) if len(sys.argv) > 2 else None

    references = read_references(str(liste_file), start_line, count)

    print(f"References from line {start_line}:")
    print("=" * 80)
    for line_num, ref in references:
        print(f"{line_num:04d}: {ref}")
    print("=" * 80)
    print(f"Total: {len(references)} references")


if __name__ == "__main__":
    main()
