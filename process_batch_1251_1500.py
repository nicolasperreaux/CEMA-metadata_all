#!/usr/bin/env python3
"""
Process bibliographic references 1251-1500 from liste-tout.txt
Creates JSON files in json-corrected/ directory with reference_number as first field.
This version processes references locally without external API calls.
"""

import json
import re
from pathlib import Path
from collections import OrderedDict


def parse_reference(line_num, reference_text):
    """
    Parse a bibliographic reference and extract metadata.
    Returns a dictionary in the required JSON schema format.
    """

    # Initialize the result structure with reference_number FIRST
    result = {
        "publication": OrderedDict([
            ("reference_number", str(line_num)),
            ("publication_type", "monograph"),  # Default, will be determined
            ("title", None),
            ("auteurs", []),
            ("place_of_publication", None),
            ("publisher", None),
            ("publication_dates", None),
            ("volume", None),
            ("tome", None),
            ("pages", None),
            ("series", None),
            ("journal_title", None),
            ("journal_volume", None),
            ("journal_issue", None),
            ("container_title", None),
            ("container_editors", [])
        ]),
        "content": {
            "main_institution": None,
            "mentioned_place": None,
            "region": None,
            "country": None,
            "institution_type": None,
            "religious_order": None,
            "temporal_coverage": None,
            "document_type": None
        },
        "remarks": None
    }

    # Detect publication type
    # Article: has "dans:" or "in:" followed by journal name
    # Chapter: has "dans" or "in" followed by book title with editors
    if re.search(r',\s+dans:\s+', reference_text, re.IGNORECASE) or re.search(r',\s+in:\s+', reference_text, re.IGNORECASE) or re.search(r',\s+in\s+', reference_text, re.IGNORECASE):
        # Check if it's a chapter (has editors) or article (journal)
        if re.search(r'\béd\.\b|\bed\.\b|\bdir\.\b|\bhrsg\.\b|\beds\.\b', reference_text, re.IGNORECASE):
            result["publication"]["publication_type"] = "chapter"
        else:
            result["publication"]["publication_type"] = "article"

    # Extract authors/editors from the beginning
    # Pattern: LASTNAME Firstname or Firstname LASTNAME, often with (éd.) or similar
    author_match = re.match(r'^([^,]+(?:\([^)]+\))?(?:,\s+[^,]+(?:\([^)]+\))?)*?)(?:,\s+["\']|,\s+[A-Z][^,]*?:)', reference_text)
    if author_match:
        author_str = author_match.group(1).strip()
        # Split by " et ", "–", "-" for multiple authors
        authors = re.split(r'\s+et\s+|\s+and\s+|–|-(?=\s+[A-Z])', author_str)
        # Clean each author name
        cleaned_authors = []
        for author in authors:
            # Remove (éd.), (ed.), etc.
            author = re.sub(r'\s*\([^)]*\)', '', author).strip()
            if author and len(author) > 2:
                cleaned_authors.append(author)
        if cleaned_authors:
            result["publication"]["auteurs"] = cleaned_authors

    # Extract title (usually after authors, before publication info)
    # Title is often in quotes or between commas before the place/journal
    title_match = re.search(r'(?:,\s+|^)(["\']?[^,"]+["\']?)(?:,\s+(?:dans|in|[A-Z][a-z]+,))', reference_text)
    if title_match:
        title = title_match.group(1).strip()
        # Remove quotes if present
        title = re.sub(r'^["\']|["\']$', '', title)
        if title:
            result["publication"]["title"] = title

    # Extract dates (4-digit years or ranges)
    date_match = re.search(r'\b(\d{4}(?:-\d{4})?)\b', reference_text)
    if date_match:
        result["publication"]["publication_dates"] = date_match.group(1)

    # Extract volume information
    vol_match = re.search(r'(\d+\s+vol(?:umes?)?\.?|\d+\s+Bände?|vol(?:umes?)?\s+\d+)', reference_text, re.IGNORECASE)
    if vol_match:
        result["publication"]["volume"] = vol_match.group(1)

    # Extract tome
    tome_match = re.search(r'(t\.\s+\d+|tome\s+\d+|Band\s+\d+)', reference_text, re.IGNORECASE)
    if tome_match:
        result["publication"]["tome"] = tome_match.group(1)

    # Extract pages
    page_match = re.search(r'(p(?:p)?\.\s*\d+(?:-\d+)?|S\.\s*\d+(?:-\d+)?)', reference_text, re.IGNORECASE)
    if page_match:
        result["publication"]["pages"] = page_match.group(1)

    # Extract place of publication (usually a city name before publisher or date)
    place_match = re.search(r',\s+([A-Z][a-zé-]+(?:-[A-Z][a-zé-]+)?),\s+(?:[A-Z]|[\d])', reference_text)
    if place_match:
        result["publication"]["place_of_publication"] = place_match.group(1)

    # Extract publisher (after place, before date)
    publisher_match = re.search(r',\s+[A-Z][a-zé-]+,\s+([A-Z][^,]+?)(?:,\s+\d{4}|\s+\d{4})', reference_text)
    if publisher_match:
        result["publication"]["publisher"] = publisher_match.group(1).strip()

    # Extract institution information from title
    inst_patterns = [
        (r"(?:abbaye|abbey|Abtei)\s+(?:de\s+|d\')?([A-Z][^,;\.]+)", "abbey"),
        (r"(?:prieuré|priory|Priorat)\s+(?:de\s+|d\')?([A-Z][^,;\.]+)", "priory"),
        (r"(?:chapitre|chapter|Kapitel)\s+(?:de\s+|of\s+)?([A-Z][^,;\.]+)", "cathedral chapter"),
        (r"(?:monastère|monastery|monasterium|Kloster)\s+(?:de\s+|d\')?([A-Z][^,;\.]+)", "monastery"),
        (r"(?:cathédrale|cathedral|Kathedrale)\s+(?:de\s+|d\')?([A-Z][^,;\.]+)", "cathedral chapter"),
    ]

    for pattern, inst_type in inst_patterns:
        match = re.search(pattern, reference_text, re.IGNORECASE)
        if match:
            result["content"]["main_institution"] = match.group(0)
            result["content"]["institution_type"] = inst_type
            # Extract place name
            place_name = match.group(1).strip()
            # Clean up the place name
            place_name = re.sub(r'\s+\([^)]+\).*', '', place_name)
            place_name = re.sub(r',.*', '', place_name)
            if place_name:
                result["content"]["mentioned_place"] = place_name
            break

    # Try to infer country from context
    if result["content"]["main_institution"]:
        # French indicators
        if any(word in reference_text.lower() for word in ['abbaye', 'prieuré', 'chapitre', 'cartulaire']):
            result["content"]["country"] = "France"
        # German indicators
        elif any(word in reference_text.lower() for word in ['abtei', 'kloster', 'urkunden']):
            result["content"]["country"] = "Germany"
        # Belgian indicators
        elif any(word in reference_text.lower() for word in ['hainaut', 'flandre', 'bruges', 'mons', 'liège', 'bruxelles']):
            result["content"]["country"] = "Belgium"

    # Extract temporal coverage from title
    temporal_match = re.search(r'\(([IVX]+e?-[IVX]+e?\s+siècles?|[IVX]+e?\s+siècle|\d{3,4}-\d{3,4})\)', reference_text)
    if temporal_match:
        result["content"]["temporal_coverage"] = temporal_match.group(1)

    # Detect document type
    if any(word in reference_text.lower() for word in ['cartulaire', 'cartulary']):
        result["content"]["document_type"] = "cartulary"
    elif any(word in reference_text.lower() for word in ['chartes', 'charters', 'urkunden']):
        result["content"]["document_type"] = "collection"
    elif 'recueil' in reference_text.lower():
        result["content"]["document_type"] = "collection"

    return result


def save_json(data, output_path):
    """Save JSON data to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    START_LINE = 1251
    END_LINE = 1500

    base_dir = Path('/home/user/CEMA-metadata_all')
    liste_file = base_dir / 'liste-tout.txt'
    json_dir = base_dir / 'json-corrected'

    # Create output directory
    json_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print(f"PROCESSING REFERENCES {START_LINE}-{END_LINE}")
    print("=" * 70)

    # Read and process references
    references = []
    with open(liste_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            if START_LINE <= line_num <= END_LINE:
                if '→' in line:
                    reference_text = line.split('→', 1)[1].strip()
                    references.append((line_num, reference_text))

    print(f"\nProcessing {len(references)} references...\n")

    success_count = 0
    for line_num, reference_text in references:
        output_file = json_dir / f'reference_{line_num:04d}.json'

        # Skip if already exists
        if output_file.exists():
            print(f"  ✓ Line {line_num} (already exists)")
            success_count += 1
            continue

        try:
            result = parse_reference(line_num, reference_text)
            save_json(result, output_file)
            success_count += 1
            if line_num % 10 == 0:
                print(f"  ✓ Processed {line_num - START_LINE + 1}/{len(references)}")
        except Exception as e:
            print(f"  ✗ Line {line_num}: {e}")

    print(f"\n{'=' * 70}")
    print("PROCESSING COMPLETE!")
    print("=" * 70)
    print(f"Successfully processed: {success_count}/{len(references)}")
    print(f"Output directory: {json_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
