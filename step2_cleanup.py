#!/usr/bin/env python3
"""
Step 2 — Regex Cleanup (no LLM)
================================
Strips sidebar nav, ads, and boilerplate from scraped Prozorro docs using regex.
Fully resumable: 0-byte files in docs_clean/ = pending.

Usage:
    python3 step2_cleanup.py                # process pending files only
    python3 step2_cleanup.py --reprocess-all  # reset and reprocess everything
"""

import re
import argparse
from pathlib import Path

DOCS_DIR  = Path("docs")
CLEAN_DIR = Path("docs_clean")
STUB_MARKER = "<!-- STUB -->\n"
MIN_CONTENT_LINES = 3  # below this → STUB (OpenAI step3 will do finer classification)

# ── Regex patterns applied in order ────────────────────────────────────────────

REMOVALS = [
    # Plain-text sidebar nav block (Jina renders some pages without markdown links):
    # starts with " openprocurement.api" and ends with "View page source\n"
    r'(?ms)^ openprocurement\.api\n.*?View page source\n',
    # Logo line
    r'\[openprocurement\.api !\[Image \d+: Logo\][^\n]*\n?',
    # Sidebar nav bullets linking to readthedocs (any indentation depth)
    r'(?m)^[ \t]*\*[ \t]+\[.+?\]\(https://prozorro-api-docs\.readthedocs\.io[^)]*\)\n?',
    # Breadcrumb: standalone openprocurement.api link
    r'(?m)^\[openprocurement\.api\]\(https://[^)]+\)\n?',
    # Breadcrumb: empty link bullet [](url)
    r'(?m)^\*[ \t]+\[\]\(https://[^)]+\)\n?',
    # Breadcrumb: "View page source" bullet or plain link
    r'(?m)^\*[ \t]+\[View page source\][^\n]*\n?',
    r'(?m)^\[View page source\]\([^)]+\)\n?',
    # EthicalAds sponsored image+link block
    r'\[!\[.*?(?:ethicalads|EthicalAds)[^\]]*\][^\n]*\n?',
    r'(?mi)^\[.*?(?:Ads by EthicalAds|ethicalads\.io|server\.ethicalads)[^\n]*\n?',
    r'_\[Ad by EthicalAds\][^\n]*\n?',
    r'!\[Image \d+\]\(https://(?:server|media)\.ethicalads\.io/[^)]+\)\n?',
    # Ad copy plain text that appears immediately before "Ads by EthicalAds"
    r'(?m)^[^\n]{20,300}\n(?=Ads by EthicalAds\n?)',
    r'(?m)^Ads by EthicalAds\n?',
    r'(?m)^Close Ad\n?',
    # Sphinx / Read the Docs footer — markdown and plain-text variants
    r'(?m)^© Copyright[^\n]*\n?',
    r'(?m)^ ?Built with \[Sphinx\][^\n]*\n?',
    r'(?m)^Built with Sphinx using a theme[^\n]*\n?',
    r'(?m)^\[Previous\][^\n]*\[Next\][^\n]*\n?',
    r'(?m)^ ?Previous\n?',
    r'(?m)^Next ?$\n?',
    # MongoDB Atlas sponsored footer line
    r'(?m)^Build and run apps in over[^\n]*\n?',
    # Horizontal rules left alone after removal
    r'(?m)^[ \t]*\*[ \t]*\*[ \t]*\*[ \t]*\n',
    r'(?m)^---+\n',
]

def clean_content(text: str) -> str:
    for pattern in REMOVALS:
        text = re.sub(pattern, '', text)

    # Strip " — openprocurement.api 2.5 documentation" from headings
    text = re.sub(
        r'(?m)^(#{1,3}[^\n]+?)\s+—\s+openprocurement\.api[^\n]*$',
        r'\1', text
    )

    # Strip anchor self-links from headings: [](url) or [](url "Link to this heading")
    text = re.sub(r'\[[^\]]{0,10}\]\([^)]*"Link to this heading"[^)]*\)', '', text)
    text = re.sub(r'\[\]\(https://prozorro-api-docs\.readthedocs\.io[^)]*\)', '', text)

    # Remove breadcrumb plain-text bullet: "* PageTitle" just before "# PageTitle"
    text = re.sub(r'(?m)^\*[ \t]+([^[\n\*]{3,80}?)\s*\n(\n*)(?=# )', r'\2', text)

    # Remove duplicate first h1 when same title appears again below
    text = re.sub(
        r'^(# [^\n]+)\n((?:[^\n]*\n){0,6})\n(# [^\n]+)\n',
        lambda m: m.group(0) if m.group(1).lower() != m.group(3).lower() else m.group(2) + '\n' + m.group(3) + '\n',
        text, flags=re.MULTILINE
    )

    # Collapse 3+ blank lines → 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip() + '\n'


def has_real_content(text: str) -> bool:
    """Rough check — step3 OpenAI does the real classification."""
    lines = [l.strip() for l in text.splitlines()
             if l.strip() and not l.strip().startswith(('<!-- SOURCE', '#', '*', '|', '>', '---', '```'))]
    return len(lines) >= MIN_CONTENT_LINES


def mirror_tree() -> None:
    CLEAN_DIR.mkdir(exist_ok=True)
    for src in DOCS_DIR.rglob("*.md"):
        dst = CLEAN_DIR / src.relative_to(DOCS_DIR)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            dst.touch()


def pending_files() -> list[tuple[Path, Path]]:
    return [
        (src, CLEAN_DIR / src.relative_to(DOCS_DIR))
        for src in sorted(DOCS_DIR.rglob("*.md"))
        if (dst := CLEAN_DIR / src.relative_to(DOCS_DIR)) and
           (not dst.exists() or dst.stat().st_size == 0)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reprocess-all", action="store_true",
                        help="Reset all docs_clean files and reprocess from scratch")
    args = parser.parse_args()

    if args.reprocess_all:
        print("[Step 2] Resetting all docs_clean files ...", flush=True)
        for dst in CLEAN_DIR.rglob("*.md"):
            dst.write_bytes(b"")

    print("[Step 2] Mirroring docs/ → docs_clean/ ...", flush=True)
    mirror_tree()

    pending = pending_files()
    total   = sum(1 for _ in DOCS_DIR.rglob("*.md"))
    already = total - len(pending)
    print(f"[Step 2] Total: {total} | Already done: {already} | Pending: {len(pending)}\n", flush=True)

    cleaned = stubs = 0
    for src, dst in pending:
        text = src.read_text(encoding="utf-8")
        result = clean_content(text)
        rel = str(src.relative_to(DOCS_DIR))
        orig_size = src.stat().st_size

        if not has_real_content(result):
            dst.write_text(STUB_MARKER, encoding="utf-8")
            print(f"  [STUB]  {rel}", flush=True)
            stubs += 1
        else:
            dst.write_text(result, encoding="utf-8")
            new_size = dst.stat().st_size
            reduction = 1 - new_size / max(orig_size, 1)
            print(f"  [OK]    {rel}  ({orig_size//1024}KB → {new_size//1024}KB, -{reduction:.0%})", flush=True)
            cleaned += 1

    print(f"\n[Step 2] Done. Cleaned: {cleaned} | Stubs: {stubs}")
    print("Next: python3 step3_classify.py")


if __name__ == "__main__":
    main()
