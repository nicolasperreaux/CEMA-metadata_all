#!/usr/bin/env python3
"""
Process remaining bibliographic references 2001-5083 from liste-tout.txt
Creates JSON files with proper metadata structure.
"""

import json
import re
from pathlib import Path
from collections import OrderedDict


def create_json_structure(line_num):
    """Create the base JSON structure with reference_number as FIRST field."""
    return {
        "publication": OrderedDict([
            ("reference_number", str(line_num)),
            ("publication_type", None),
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


def extract_authors(text):
    """Extract authors from the beginning of the reference."""
    authors = []

    # Pattern: LASTNAME Initials or LASTNAME Firstname
    # Handles multiple authors separated by ' et ', ' and ', '-', ','
    author_pattern = r'^([A-ZÀ-ÝÑ][A-ZÀ-ÝÑ\s\'-]+(?:\s+[A-ZÀ-ÝÑ]\.?[A-ZÀ-ÝÑ]\.?|\s+[A-ZÀ-ÝÑ][a-zà-ýñ\-]+)+)'

    match = re.match(author_pattern, text)
    if match:
        author_str = match.group(1)
        # Remove editor markers
        author_str = re.sub(r'\s*\([^)]*éd\.[^)]*\)', '', author_str)

        # Split by common separators
        if ' et ' in author_str:
            parts = author_str.split(' et ')
        elif ' and ' in author_str:
            parts = author_str.split(' and ')
        elif ' - ' in author_str:
            parts = author_str.split(' - ')
        else:
            parts = [author_str]

        for part in parts:
            clean = part.strip(' ,')
            if clean and len(clean) > 2:
                authors.append(clean)

    return authors if authors else []


def extract_title(text):
    """Extract the title from the reference."""
    # Remove author part first
    text_without_author = re.sub(r'^[A-ZÀ-ÝÑ][A-ZÀ-ÝÑ\s\'-]+(?:\s+[A-ZÀ-ÝÑ]\.?[A-ZÀ-ÝÑ]\.?|\s+[A-ZÀ-ÝÑ][a-zà-ýñ\-]+)+[\.,]\s*', '', text)

    # Look for title in quotes or before specific keywords
    patterns = [
        r'^(?:"|«|")([^"»"]+)(?:"|»|")',  # Quoted title
        r'^([^,]+?)(?:,\s+(?:dans|in|dans:|in:))',  # Before dans/in
        r'^\((éd\.)\),\s+([^,]+)',  # After (éd.)
        r'^([^,]+?)(?:,\s+\d{4})',  # Before year
    ]

    for pattern in patterns:
        match = re.search(pattern, text_without_author)
        if match:
            if '(éd.)' in pattern:
                title = match.group(2) if match.lastindex >= 2 else match.group(1)
            else:
                title = match.group(1)
            title = title.strip(' ,"«»""')
            if len(title) > 5:
                return title

    # Fallback: take first reasonable chunk
    parts = text_without_author.split(',')
    if parts and len(parts[0]) > 5:
        return parts[0].strip(' ,"«»""')

    return None


def extract_publication_dates(text):
    """Extract publication year(s)."""
    # Look for 4-digit years
    patterns = [
        r'\b(\d{4}(?:-\d{4})?)\b',  # Single year or range
        r'\b(\d{4};\s*\d{4})\b',  # Multiple years with semicolon
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Return the last year found (usually publication date)
            return matches[-1]

    return None


def extract_place(text):
    """Extract place of publication."""
    # Pattern: capitalized city name before comma and year
    pattern = r',\s+([A-ZÀ-ÝÑ][a-zà-ýñ\-]+(?:-[A-ZÀ-ÝÑ][a-zà-ýñ\-]+)?),\s+(?:\d{4}|[A-ZÀ-ÝÑ])'
    matches = re.findall(pattern, text)
    if matches:
        return matches[-1]  # Last match is usually publication place

    return None


def extract_volume_info(text):
    """Extract volume, tome, and page information."""
    info = {'volume': None, 'tome': None, 'pages': None}

    # Volume patterns
    vol_patterns = [
        (r'\b(\d+\s+vol(?:umes?)?\.?)', 'volume'),
        (r'\b(vol\.?\s+\d+)', 'volume'),
        (r'\b(\d+\s+Bände?)', 'volume'),
        (r'\b(V\.\d+)', 'volume'),
    ]

    for pattern, key in vol_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and not info[key]:
            info[key] = match.group(1)

    # Tome patterns
    tome_patterns = [
        r'\b(t\.?\s*\d+)',
        r'\b(tome\s+\d+)',
        r'\b(Band\s+\d+)',
    ]

    for pattern in tome_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['tome'] = match.group(1)
            break

    # Page patterns
    page_patterns = [
        r'\b(p\.?\s*\d+(?:-\d+)?)',
        r'\b(pp\.?\s*\d+(?:-\d+)?)',
        r'\b(S\.?\s*\d+(?:-\d+)?)',
    ]

    for pattern in page_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['pages'] = match.group(1)
            break

    return info


def extract_series(text):
    """Extract series information from parentheses."""
    pattern = r'\(([^)]*(?:Collection|Series|Publications|Monumenta|Commission)[^)]*)\)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        series = max(matches, key=len)  # Get longest match
        if len(series) > 10:
            return series
    return None


def detect_publication_type(text):
    """Determine publication type."""
    text_lower = text.lower()

    # Check for article patterns
    if re.search(r',\s+dans:\s+', text) or re.search(r',\s+dans\s+', text):
        # Check if it's a journal article
        if any(word in text_lower for word in ['revue', 'bulletin', 'annales', 'journal', 'mémoires']):
            return 'article'
        # Otherwise it's likely a chapter
        return 'book_chapter'

    if re.search(r',\s+in:\s+', text) or re.search(r',\s+in\s+', text):
        return 'book_chapter'

    # Check for thesis
    if 'th.' in text_lower or 'thèse' in text_lower or 'thesis' in text_lower:
        return 'thesis'

    # Default to book
    return 'book'


def extract_journal_info(text, pub_type):
    """Extract journal title and volume/issue."""
    info = {'journal_title': None, 'journal_volume': None, 'journal_issue': None}

    if pub_type != 'article':
        return info

    # Look for journal title after "dans:"
    match = re.search(r'dans:\s+([^,]+?)(?:,\s*\d+)', text, re.IGNORECASE)
    if match:
        info['journal_title'] = match.group(1).strip()

        # Try to extract volume/issue
        vol_match = re.search(r',\s+(\d+)\s+\((\d{4})\)', text)
        if vol_match:
            info['journal_volume'] = vol_match.group(1)

    return info


def detect_country(text):
    """Detect country from text."""
    text_lower = text.lower()

    # Belgium indicators
    belgium_words = ['hainaut', 'flandre', 'brabant', 'liège', 'mons', 'bruxelles',
                     'bruges', 'namur', 'anvers', 'antwerpen', 'gent', 'vlaanderen']
    if any(word in text_lower for word in belgium_words):
        return 'Belgium'

    # France indicators
    france_words = ['paris', 'lyon', 'abbaye', 'prieuré', 'france', 'normandie',
                    'bretagne', 'bourgogne', 'champagne']
    if any(word in text_lower for word in france_words):
        return 'France'

    # Spain indicators
    spain_words = ['santiago', 'galicia', 'madrid', 'españa', 'catedral']
    if any(word in text_lower for word in spain_words):
        return 'Spain'

    # England indicators
    england_words = ['england', 'london', 'oxford', 'cambridge', 'somerset',
                     'glastonbury', 'worcester']
    if any(word in text_lower for word in england_words):
        return 'England'

    # Germany indicators
    germany_words = ['deutschland', 'abtei', 'kloster', 'urkundenbuch']
    if any(word in text_lower for word in germany_words):
        return 'Germany'

    return None


def extract_institution_type(text):
    """Extract institution type."""
    text_lower = text.lower()

    if 'abbaye' in text_lower or 'abbé' in text_lower or 'abbey' in text_lower:
        return 'abbey'
    elif 'prieuré' in text_lower or 'priory' in text_lower:
        return 'priory'
    elif 'monastère' in text_lower or 'monasterium' in text_lower or 'mosteiro' in text_lower:
        return 'monastery'
    elif 'cathédrale' in text_lower or 'cathedral' in text_lower or 'catedral' in text_lower:
        return 'cathedral'
    elif 'chapitre' in text_lower or 'chapter' in text_lower:
        return 'chapter'
    elif 'hôpital' in text_lower or 'hospital' in text_lower:
        return 'hospital'
    elif 'église' in text_lower or 'church' in text_lower:
        return 'church'

    return None


def detect_document_type(text):
    """Detect document type."""
    text_lower = text.lower()

    if 'cartulaire' in text_lower or 'cartulary' in text_lower:
        return 'cartulary'
    elif 'charte' in text_lower or 'charter' in text_lower:
        return 'charter'
    elif 'oorkonde' in text_lower or 'urkunde' in text_lower:
        return 'charter'
    elif 'actes' in text_lower or 'acta' in text_lower:
        return 'acts'
    elif 'registre' in text_lower or 'register' in text_lower:
        return 'register'
    elif 'tumbo' in text_lower:
        return 'cartulary'
    elif 'histoire' in text_lower or 'history' in text_lower or 'geschiedenis' in text_lower:
        return 'history'
    elif 'catalogue' in text_lower:
        return 'catalogue'

    return None


def parse_reference(line_num, text):
    """Parse a complete reference into JSON structure."""
    result = create_json_structure(line_num)

    # Extract all components
    result['publication']['auteurs'] = extract_authors(text)
    result['publication']['title'] = extract_title(text)
    result['publication']['publication_dates'] = extract_publication_dates(text)
    result['publication']['place_of_publication'] = extract_place(text)
    result['publication']['publication_type'] = detect_publication_type(text)

    vol_info = extract_volume_info(text)
    result['publication']['volume'] = vol_info['volume']
    result['publication']['tome'] = vol_info['tome']
    result['publication']['pages'] = vol_info['pages']

    result['publication']['series'] = extract_series(text)

    # Journal info for articles
    if result['publication']['publication_type'] == 'article':
        journal_info = extract_journal_info(text, 'article')
        result['publication']['journal_title'] = journal_info['journal_title']
        result['publication']['journal_volume'] = journal_info['journal_volume']

    # Content metadata
    result['content']['country'] = detect_country(text)
    result['content']['institution_type'] = extract_institution_type(text)
    result['content']['document_type'] = detect_document_type(text)

    return result


def save_json(data, filepath):
    """Save JSON with proper formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    START_LINE = 2001
    END_LINE = 5083

    base_dir = Path('/home/user/CEMA-metadata_all')
    liste_file = base_dir / 'liste-tout.txt'
    json_dir = base_dir / 'json-corrected'

    json_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print(f"PROCESSING REFERENCES {START_LINE}-{END_LINE}")
    print("=" * 70)

    # Read all references
    references = []
    with open(liste_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            if START_LINE <= line_num <= END_LINE:
                text = line.strip()
                if text:
                    references.append((line_num, text))

    print(f"\nProcessing {len(references)} references...\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for idx, (line_num, text) in enumerate(references, 1):
        output_file = json_dir / f'reference_{line_num:04d}.json'

        # Skip if already exists
        if output_file.exists():
            skip_count += 1
            if idx % 100 == 0:
                print(f"  Progress: {idx}/{len(references)} ({idx/len(references)*100:.1f}%)")
            continue

        try:
            result = parse_reference(line_num, text)
            save_json(result, output_file)
            success_count += 1

            if idx % 100 == 0:
                print(f"  Progress: {idx}/{len(references)} ({idx/len(references)*100:.1f}%)")

        except Exception as e:
            error_count += 1
            print(f"  ERROR on line {line_num}: {e}")

    print(f"\n{'=' * 70}")
    print("PROCESSING COMPLETE!")
    print("=" * 70)
    print(f"Successfully processed: {success_count}")
    print(f"Skipped (already exist): {skip_count}")
    print(f"Errors: {error_count}")
    print(f"Total: {success_count + skip_count + error_count}/{len(references)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
