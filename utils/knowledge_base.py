import os

KB_PATH = os.path.join(os.path.dirname(__file__), '../prompts/gaps_knowledge_base.md')

# Load the entire knowledge base file into memory (simple, as it's not huge)
def load_kb():
    with open(KB_PATH, 'r', encoding='utf-8') as f:
        return f.read()

# Simple section extractor by heading name
def get_kb_section(section_name):
    kb = load_kb()
    lines = kb.split('\n')
    section_lines = []
    in_section = False
    # Normalize the section name for flexible matching
    target = section_name.lower().strip().replace('-', '').replace(' ', '')
    import re
    for line in lines:
        # Remove leading #, dashes, spaces, numbers, and periods for matching
        normalized = line.lower().lstrip('#- ').strip()
        normalized = re.sub(r'^[0-9]+\.?\s*', '', normalized)  # Remove leading numbers and periods
        normalized = normalized.replace('-', '').replace(' ', '')
        if normalized.startswith(target):
            in_section = True
            continue
        if in_section and line.strip().startswith('## '):
            break
        if in_section:
            section_lines.append(line)
    return '\n'.join(section_lines).strip() if section_lines else ''

# Example usage:
# get_kb_section('Quadrant Definitions')
# get_kb_section('Step-by-Step GAPS Process')
