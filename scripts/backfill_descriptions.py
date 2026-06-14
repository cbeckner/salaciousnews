#!/usr/bin/env python3
"""Backfill missing/oversized meta `Description` front matter fields.

For posts with an empty `Description:`, generates a ~155-char description
from the first sentence(s) of the article body. For posts whose existing
`Description` is too long for a meta tag (>200 chars / multi-paragraph),
trims it down to the first sentence(s) within the limit.
"""
import glob
import re

MAX_LEN = 155

DESC_RE = re.compile(r'^Description:[ \t]*(\"(?:[^"\\]|\\.)*\"|[^\n]*)', re.M)
SHORTCODE_RE = re.compile(r"\{\{<.*?>\}\}", re.S)
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
EMPHASIS_RE = re.compile(r"[*_]{1,3}")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def clean_text(text: str) -> str:
    text = SHORTCODE_RE.sub("", text)
    text = LINK_RE.sub(r"\1", text)
    text = EMPHASIS_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_description(sentences: list[str]) -> str:
    """Pack sentences into a single description <= MAX_LEN chars."""
    desc = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = (desc + " " + sentence).strip() if desc else sentence
        if len(candidate) <= MAX_LEN:
            desc = candidate
            continue
        if not desc:
            # Single sentence already too long: hard-truncate on a word boundary.
            truncated = candidate[:MAX_LEN].rsplit(" ", 1)[0]
            return truncated.rstrip(",;: ") + "…"
        break
    return desc


def yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def generate_from_body(body: str) -> str:
    paragraphs = [p for p in body.split("\n\n") if p.strip()]
    sentences: list[str] = []
    for para in paragraphs:
        cleaned = clean_text(para)
        if not cleaned:
            continue
        sentences.extend(SENTENCE_SPLIT_RE.split(cleaned))
        if sentences:
            break
    return build_description(sentences)


def shorten_existing(existing: str) -> str:
    cleaned = clean_text(existing)
    sentences = SENTENCE_SPLIT_RE.split(cleaned)
    return build_description(sentences)


def process_file(path: str) -> bool:
    text = open(path, encoding="utf-8").read()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False
    front_matter, body = parts[1], parts[2]

    m = DESC_RE.search(front_matter)
    if not m:
        return False
    raw_val = m.group(1).strip()
    existing = raw_val[1:-1] if raw_val.startswith('"') and raw_val.endswith('"') else raw_val

    if existing == "":
        new_desc = generate_from_body(body)
    elif len(existing) > 200:
        new_desc = shorten_existing(existing)
    else:
        return False

    if not new_desc:
        return False

    new_line = f'Description: "{yaml_escape(new_desc)}"'
    new_front_matter = front_matter[: m.start()] + new_line + front_matter[m.end() :]
    new_text = "---" + new_front_matter + "---" + body
    open(path, "w", encoding="utf-8").write(new_text)
    return True


def main():
    changed = 0
    for path in sorted(glob.glob("content/*/*.md")):
        if process_file(path):
            changed += 1
    print(f"Updated {changed} files")


if __name__ == "__main__":
    main()
