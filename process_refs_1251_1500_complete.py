#!/usr/bin/env python3
"""
Process bibliographic references 1251-1500 from liste-tout.txt
Creates JSON files with detailed metadata extraction.
"""

import json
import re
from pathlib import Path
from collections import OrderedDict


class ReferenceParser:
    """Parse bibliographic references into structured JSON."""

    def __init__(self):
        self.french_abbeys = {
            'Saint-Martin-des-Champs': ('Île-de-France', 'Cluniac'),
            'Saint-Martin de Pontoise': ('Île-de-France', 'Benedictine'),
            'Saint-Germain-des-Prés': ('Île-de-France', 'Benedictine'),
            'Cluny': ('Bourgogne', 'Cluniac'),
            'Villers': ('Brabant Wallon', 'Cistercian'),
            'Waulsort': ('Namur', 'Benedictine'),
            'Affligem': ('Brabant Flamand', 'Benedictine'),
        }

    def create_empty_result(self, line_num):
        """Create an empty result structure."""
        return {
            "publication": OrderedDict([
                ("reference_number", str(line_num)),
                ("publication_type", "monograph"),
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

    def extract_authors(self, text):
        """Extract author names from beginning of reference."""
        authors = []

        # Pattern 1: LASTNAME Firstname (éd.)
        pattern1 = r'^([A-ZÀ-Ý][A-ZÀ-Ý\s\'-]+(?:\s+[A-ZÀ-Ý][a-zà-ý\-]+)+(?:\s+\([^)]+\))?)'
        match = re.match(pattern1, text)
        if match:
            author_str = match.group(1)
            # Split by ' et ', ' and ', ' - '
            for sep in [' et ', ' and ', ' - ']:
                if sep in author_str:
                    parts = author_str.split(sep)
                    for part in parts:
                        clean = re.sub(r'\s*\([^)]*\)', '', part).strip()
                        if clean:
                            authors.append(clean)
                    return authors

            # Single author
            clean = re.sub(r'\s*\([^)]*\)', '', author_str).strip()
            if clean:
                authors.append(clean)

        return authors

    def extract_title(self, text):
        """Extract the main title."""
        # Look for title after comma, possibly in quotes or italics
        patterns = [
            r',\s+(?:"|«)([^"»]+)(?:"|»)',  # Quoted title
            r',\s+([A-Z][^,]+?)(?:,\s+(?:dans|in|[A-Z][a-zà-ý]+,))',  # Title before dans/in
            r'(?:éd\.\)),\s+([^,]+?)(?:,|$)',  # Title after (éd.)
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group(1).strip()
                # Clean up
                title = title.strip('"\'«»')
                if len(title) > 10:  # Reasonable title length
                    return title

        return None

    def extract_publication_info(self, text):
        """Extract publication place, publisher, and dates."""
        info = {'place': None, 'publisher': None, 'dates': None}

        # Dates (4-digit year or range)
        date_match = re.search(r'\b(\d{4}(?:-\d{4})?)\b', text)
        if date_match:
            info['dates'] = date_match.group(1)

        # Place and publisher: City, Publisher, Year
        place_pub_pattern = r',\s+([A-ZÀ-Ý][a-zà-ýé\-]+(?:-[A-ZÀ-Ý][a-zà-ýé\-]+)?),\s+([^,]+?),\s+\d{4}'
        match = re.search(place_pub_pattern, text)
        if match:
            info['place'] = match.group(1).strip()
            info['publisher'] = match.group(2).strip()

        return info

    def extract_volume_info(self, text):
        """Extract volume, tome, and page information."""
        info = {'volume': None, 'tome': None, 'pages': None}

        # Volume
        vol_patterns = [
            r'(\d+\s+volumes?)',
            r'(\d+\s+vol\.?)',
            r'(\d+\s+Bände?)',
            r'(vol\.?\s+\d+)',
        ]
        for pattern in vol_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['volume'] = match.group(1)
                break

        # Tome
        tome_patterns = [
            r'(t\.\s+\d+)',
            r'(tome\s+\d+)',
            r'(Band\s+\d+)',
        ]
        for pattern in tome_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['tome'] = match.group(1)
                break

        # Pages
        page_patterns = [
            r'(p\.?\s*\d+(?:-\d+)?)',
            r'(pp\.?\s*\d+(?:-\d+)?)',
            r'(S\.?\s*\d+(?:-\d+)?)',
        ]
        for pattern in page_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['pages'] = match.group(1)
                break

        return info

    def extract_series(self, text):
        """Extract series information."""
        # Series usually in parentheses or after specific keywords
        series_patterns = [
            r'\(([^)]*(?:Collection|Series|Publications|Monumenta)[^)]*)\)',
            r'\(([^)]*(?:collection|série)[^)]*)\)',
        ]
        for pattern in series_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                series = match.group(1).strip()
                if len(series) > 5:
                    return series
        return None

    def detect_publication_type(self, text):
        """Determine if reference is monograph, article, or chapter."""
        # Article: has "dans:" followed by journal name
        if re.search(r',\s+dans:\s+[A-Z]', text):
            # Check for journal patterns
            if re.search(r'(?:Revue|Bulletin|Annales|Mémoires|Journal)', text):
                return 'article'
            # Check for editors (indicates chapter)
            if re.search(r'\béd\.\b|\bed\.\b|\bdir\.\b', text):
                return 'chapter'
            return 'article'

        # Check for "in" pattern (English)
        if re.search(r',\s+in\s+[A-Z]', text) or re.search(r',\s+in:\s+[A-Z]', text):
            return 'chapter'

        return 'monograph'

    def extract_institution_info(self, text):
        """Extract institution, place, and type information."""
        info = {
            'institution': None,
            'place': None,
            'type': None,
            'order': None,
            'region': None,
            'country': None
        }

        # Institution patterns
        patterns = [
            (r"(?:abbaye|abbé)\s+(?:de\s+|d\')?([A-ZÀ-Ý][a-zà-ýé\-]+(?:-[A-ZÀ-Ý][a-zà-ýé\-]+)*)", 'abbey'),
            (r"(?:prieuré)\s+(?:de\s+|d\')?([A-ZÀ-Ý][a-zà-ýé\-]+(?:-[A-ZÀ-Ý][a-zà-ýé\-]+)*)", 'priory'),
            (r"(?:monastère|monasterium)\s+(?:de\s+|d\')?([A-ZÀ-Ý][a-zà-ýé\-]+(?:-[A-ZÀ-Ý][a-zà-ýé\-]+)*)", 'monastery'),
            (r"(?:chapitre|chapter)\s+(?:de\s+|d\')?([A-ZÀ-Ý][a-zà-ýé\-]+(?:-[A-ZÀ-Ý][a-zà-ýé\-]+)*)", 'cathedral chapter'),
            (r"(?:couvent)\s+(?:de\s+|des\s+)?([A-ZÀ-Ý][a-zà-ýé\-]+)", 'convent'),
        ]

        for pattern, inst_type in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                place_name = match.group(1)
                info['institution'] = match.group(0)
                info['place'] = place_name
                info['type'] = inst_type
                break

        # Detect country
        if any(word in text.lower() for word in ['hainaut', 'flandre', 'flandre', 'brabant', 'liège', 'mons', 'bruxelles', 'bruges']):
            info['country'] = 'Belgium'
        elif any(word in text.lower() for word in ['abbaye', 'prieuré', 'paris', 'versailles', 'pontoise', 'france']):
            info['country'] = 'France'
        elif any(word in text.lower() for word in ['abtei', 'kloster', 'gent', 'vlaanderen']):
            if 'gent' in text.lower() or 'vlaanderen' in text.lower():
                info['country'] = 'Belgium'
            else:
                info['country'] = 'Germany'

        # Extract temporal coverage
        temporal_patterns = [
            r'\(([IVX]+e?-[IVX]+e?\s+(?:siècles?|centuries?))\)',
            r'\(([IVX]+e?\s+(?:siècle|century))\)',
            r'\((\d{3,4}-\d{3,4})\)',
        ]
        for pattern in temporal_patterns:
            match = re.search(pattern, text)
            if match:
                return {**info, 'temporal_coverage': match.group(1)}

        return info

    def extract_document_type(self, text):
        """Determine document type."""
        if re.search(r'\bcartulai?re\b', text, re.IGNORECASE):
            return 'cartulary'
        elif re.search(r'\b(?:recueil|collection)\b', text, re.IGNORECASE):
            return 'collection'
        elif re.search(r'\bchartes\b', text, re.IGNORECASE):
            return 'collection'
        elif re.search(r'\bdocuments?\b', text, re.IGNORECASE):
            return 'collection'
        return None

    def parse(self, line_num, reference_text):
        """Parse a complete reference."""
        result = self.create_empty_result(line_num)

        # Extract components
        result['publication']['publication_type'] = self.detect_publication_type(reference_text)

        authors = self.extract_authors(reference_text)
        if authors:
            result['publication']['auteurs'] = authors

        title = self.extract_title(reference_text)
        if title:
            result['publication']['title'] = title

        pub_info = self.extract_publication_info(reference_text)
        if pub_info['place']:
            result['publication']['place_of_publication'] = pub_info['place']
        if pub_info['publisher']:
            result['publication']['publisher'] = pub_info['publisher']
        if pub_info['dates']:
            result['publication']['publication_dates'] = pub_info['dates']

        vol_info = self.extract_volume_info(reference_text)
        if vol_info['volume']:
            result['publication']['volume'] = vol_info['volume']
        if vol_info['tome']:
            result['publication']['tome'] = vol_info['tome']
        if vol_info['pages']:
            result['publication']['pages'] = vol_info['pages']

        series = self.extract_series(reference_text)
        if series:
            result['publication']['series'] = series

        inst_info = self.extract_institution_info(reference_text)
        if inst_info['institution']:
            result['content']['main_institution'] = inst_info['institution']
        if inst_info['place']:
            result['content']['mentioned_place'] = inst_info['place']
        if inst_info['type']:
            result['content']['institution_type'] = inst_info['type']
        if inst_info['order']:
            result['content']['religious_order'] = inst_info['order']
        if inst_info.get('region'):
            result['content']['region'] = inst_info['region']
        if inst_info['country']:
            result['content']['country'] = inst_info['country']
        if inst_info.get('temporal_coverage'):
            result['content']['temporal_coverage'] = inst_info['temporal_coverage']

        doc_type = self.extract_document_type(reference_text)
        if doc_type:
            result['content']['document_type'] = doc_type

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

    # Read references
    references = []
    with open(liste_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            if START_LINE <= line_num <= END_LINE:
                reference_text = line.strip()
                if reference_text:  # Skip empty lines
                    references.append((line_num, reference_text))

    print(f"\nProcessing {len(references)} references...\n")

    parser = ReferenceParser()
    success_count = 0
    error_count = 0

    for idx, (line_num, reference_text) in enumerate(references, 1):
        output_file = json_dir / f'reference_{line_num:04d}.json'

        # Skip if already exists
        if output_file.exists():
            success_count += 1
            if idx % 50 == 0:
                print(f"  Progress: {idx}/{len(references)} ({idx/len(references)*100:.1f}%)")
            continue

        try:
            result = parser.parse(line_num, reference_text)
            save_json(result, output_file)
            success_count += 1

            if idx % 50 == 0:
                print(f"  Progress: {idx}/{len(references)} ({idx/len(references)*100:.1f}%)")

        except Exception as e:
            error_count += 1
            print(f"  ✗ Line {line_num}: {e}")

    print(f"\n{'=' * 70}")
    print("PROCESSING COMPLETE!")
    print("=" * 70)
    print(f"Successfully processed: {success_count}/{len(references)}")
    print(f"Errors: {error_count}")
    print(f"Output directory: {json_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
