#!/usr/bin/env python3
"""
Step 4 — Generate LLM-friendly documentation files
=====================================================
Produces two files from docs_clean/:

  llms.txt       — structured index (titles + source URLs + one-line descriptions)
  llms-full.txt  — all non-STUB pages concatenated, ready to load into LLM context

Usage:
    python3 step4_llms.py [--clean-dir docs_clean] [--out-dir .]
"""

import argparse
import re
from pathlib import Path

CLEAN_DIR = Path("docs_clean")
STUB_MARKER = "<!-- STUB -->"
SOURCE_RE = re.compile(r"<!-- SOURCE: (https?://\S+) -->")
HEADING_RE = re.compile(r"^#{1,2}\s+(.+?)(?:\[]\([^)]*\))?\s*$", re.MULTILINE)
# Strip " — openprocurement.api 2.5 documentation" suffix from titles
TITLE_SUFFIX_RE = re.compile(r"\s*—\s*openprocurement\.api.*$", re.IGNORECASE)


def is_stub(text: str) -> bool:
    return text.strip().startswith(STUB_MARKER) or len(text.strip()) == 0


def extract_source(text: str) -> str:
    m = SOURCE_RE.search(text)
    return m.group(1) if m else ""


def extract_title(text: str, fallback: str = "") -> str:
    m = HEADING_RE.search(text)
    if not m:
        return fallback
    title = m.group(1).strip()
    title = TITLE_SUFFIX_RE.sub("", title)
    return title.strip()


def extract_first_paragraph(text: str) -> str:
    """Return first non-empty, non-heading, non-comment line as description."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("#", "<!--", "|", "```", ">")):
            continue
        if len(line) < 10:
            continue
        return line[:120] + ("…" if len(line) > 120 else "")
    return ""


def collect_pages(clean_dir: Path) -> list[dict]:
    pages = []
    for path in sorted(clean_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if is_stub(text):
            continue
        rel = str(path.relative_to(clean_dir))
        source = extract_source(text)
        title = extract_title(text, fallback=rel)
        desc = extract_first_paragraph(text)
        pages.append({"path": path, "rel": rel, "source": source, "title": title, "desc": desc, "text": text})
    return pages


def build_llms_txt(pages: list[dict]) -> str:
    lines = [
        "# Prozorro Open Procurement API — Documentation",
        "",
        "> Full documentation for the Prozorro Open Procurement API (openprocurement.api 2.5).",
        "> Source: https://prozorro-api-docs.readthedocs.io/en/latest/",
        "",
        "## Documentation Pages",
        "",
    ]
    for p in pages:
        url = p["source"] or f"file://{p['rel']}"
        title = p["title"] or p["rel"]
        desc = f": {p['desc']}" if p["desc"] else ""
        lines.append(f"- [{title}]({url}){desc}")
    lines.append("")
    return "\n".join(lines)


def build_llms_full_txt(pages: list[dict]) -> str:
    parts = [
        "# Prozorro Open Procurement API — Full Documentation",
        "",
        "> This file contains the complete Prozorro API documentation.",
        "> Total pages: " + str(len(pages)),
        "",
        "---",
        "",
    ]
    for p in pages:
        # Strip the SOURCE comment line — it's redundant given the separator
        text = p["text"].strip()
        text = SOURCE_RE.sub("", text).strip()
        parts.append(f"<!-- PAGE: {p['rel']} | SOURCE: {p['source']} -->")
        parts.append("")
        parts.append(text)
        parts.append("")
        parts.append("---")
        parts.append("")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-dir", type=Path, default=CLEAN_DIR)
    parser.add_argument("--out-dir",   type=Path, default=Path("."))
    args = parser.parse_args()

    print(f"[Step 4] Scanning {args.clean_dir} ...", flush=True)
    pages = collect_pages(args.clean_dir)
    print(f"[Step 4] Found {len(pages)} non-stub pages", flush=True)

    llms_path = args.out_dir / "llms.txt"
    llms_full_path = args.out_dir / "llms-full.txt"

    llms_path.write_text(build_llms_txt(pages), encoding="utf-8")
    print(f"[Step 4] Written {llms_path}  ({llms_path.stat().st_size // 1024}KB)", flush=True)

    llms_full_path.write_text(build_llms_full_txt(pages), encoding="utf-8")
    print(f"[Step 4] Written {llms_full_path}  ({llms_full_path.stat().st_size // 1024}KB)", flush=True)

    print(f"\nDone. Load llms-full.txt into your LLM context, or use llms.txt as an index.")


if __name__ == "__main__":
    main()
