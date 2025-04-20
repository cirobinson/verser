import re

def parse_verses_from_text(raw_text):
    lines = raw_text.strip().split("\n")
    verses = []
    for line in lines:
        match = re.match(r"\d+\)\s*(\w+\.\s*\d+:\d+)\s+(.*)", line.strip())
        if match:
            ref, text = match.groups()
            verses.append({"ref": ref.strip(), "text": text.strip()})
    return verses
