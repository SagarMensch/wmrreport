import re
from collections import defaultdict

def extract():
    with open('search_results.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    terms = {
        'NIRM': r'(?i)\bnirm\b',
        'Alstansim': r'(?i)alstan',
        'PDO': r'(?i)\bpdo\b',
        'Location PO': r'(?i)location.?po',
        'Cluster': r'(?i)cluster',
        'Flowline': r'(?i)flowline',
        'Rig ID': r'(?i)rig.?id',
        'Rig': r'(?i)\brig\b',
    }

    results = {k: [] for k in terms}

    for line in lines:
        for term, pattern in terms.items():
            if re.search(pattern, line):
                results[term].append(line.strip())

    with open('summary_terms.md', 'w', encoding='utf-8') as f:
        f.write('# Term Extractions\n\n')
        for term, matches in results.items():
            f.write(f'## {term} (Total: {len(matches)})\n')
            
            # Deduplicate by line content (split by colon to remove line numbers)
            seen_content = set()
            unique_matches = []
            for match in matches:
                parts = match.split(':', 2)
                if len(parts) >= 3:
                    content = parts[2].strip()
                    if content not in seen_content:
                        seen_content.add(content)
                        unique_matches.append(match)
            
            # Write up to 15 unique matches for context
            for m in unique_matches[:15]:
                f.write(f'- {m}\n')
            f.write('\n')

if __name__ == '__main__':
    extract()
