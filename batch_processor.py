#!/usr/bin/env python3
"""
Batch processing helper for bibliographic references.
This script helps manage the processing of references in batches.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


class BatchProcessor:
    def __init__(self, base_dir='/home/user/CEMA-metadata_all'):
        self.base_dir = Path(base_dir)
        self.liste_file = self.base_dir / 'liste-tout.txt'
        self.json_dir = self.base_dir / 'json'
        self.error_log = self.base_dir / 'errors.log'
        self.progress_file = self.base_dir / 'processing_progress.json'

        # Create directories
        self.json_dir.mkdir(exist_ok=True)

        # Load or initialize progress
        self.progress = self.load_progress()

    def load_progress(self):
        """Load processing progress from file."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            'last_processed_line': 0,
            'total_processed': 0,
            'total_errors': 0,
            'started_at': datetime.now().isoformat()
        }

    def save_progress(self):
        """Save processing progress to file."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def get_next_batch(self, batch_size=50):
        """Get the next batch of references to process."""
        references = []
        start_line = self.progress['last_processed_line'] + 1

        with open(self.liste_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                if line_num < start_line:
                    continue
                if len(references) >= batch_size:
                    break

                reference = line.strip()
                if reference:
                    references.append((line_num, reference))

        return references

    def save_result(self, line_num, json_data):
        """Save a processed reference result."""
        output_file = self.json_dir / f"reference_{line_num:04d}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        self.progress['last_processed_line'] = max(
            self.progress['last_processed_line'], line_num
        )
        self.progress['total_processed'] += 1
        self.save_progress()

    def log_error(self, line_num, reference, error_msg):
        """Log an error."""
        with open(self.error_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] Line {line_num}: {error_msg}\n")
            f.write(f"  Reference: {reference}\n\n")

        self.progress['total_errors'] += 1
        self.progress['last_processed_line'] = max(
            self.progress['last_processed_line'], line_num
        )
        self.save_progress()

    def get_total_references(self):
        """Count total references in file."""
        with open(self.liste_file, 'r') as f:
            return sum(1 for line in f if line.strip())

    def show_status(self):
        """Display current processing status."""
        total_refs = self.get_total_references()
        processed = self.progress['total_processed']
        errors = self.progress['total_errors']
        remaining = total_refs - self.progress['last_processed_line']

        print("=" * 70)
        print("PROCESSING STATUS")
        print("=" * 70)
        print(f"Total references:      {total_refs}")
        print(f"Successfully processed: {processed}")
        print(f"Errors:                {errors}")
        print(f"Last processed line:   {self.progress['last_processed_line']}")
        print(f"Remaining:             {remaining}")
        print(f"Progress:              {(self.progress['last_processed_line']/total_refs)*100:.1f}%")
        print("=" * 70)

    def save_batch_input(self, references, output_file='current_batch.txt'):
        """Save current batch to a file for processing."""
        filepath = self.base_dir / output_file
        with open(filepath, 'w', encoding='utf-8') as f:
            for line_num, ref in references:
                f.write(f"{line_num:04d}: {ref}\n")
        return filepath


def main():
    processor = BatchProcessor()

    if len(sys.argv) < 2:
        print("Batch Processor for Bibliographic References")
        print("\nCommands:")
        print("  status              - Show processing status")
        print("  next <size>         - Get next batch of references")
        print("  reset               - Reset progress (start over)")
        print("  save <line> <json>  - Save a processed result")
        sys.exit(0)

    command = sys.argv[1]

    if command == 'status':
        processor.show_status()

    elif command == 'next':
        batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        references = processor.get_next_batch(batch_size)

        if not references:
            print("No more references to process!")
            processor.show_status()
        else:
            print(f"\n{len(references)} references ready to process:")
            print("=" * 80)
            for line_num, ref in references:
                print(f"{line_num:04d}: {ref}")
            print("=" * 80)

            # Save to file
            batch_file = processor.save_batch_input(references)
            print(f"\nBatch saved to: {batch_file}")

    elif command == 'reset':
        processor.progress = {
            'last_processed_line': 0,
            'total_processed': 0,
            'total_errors': 0,
            'started_at': datetime.now().isoformat()
        }
        processor.save_progress()
        print("Progress reset!")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
