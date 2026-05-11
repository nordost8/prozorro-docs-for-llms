#!/usr/bin/env python3
"""
Step 2 — Cleanup Agent (batched)
==================================
Runs a CLI agent (Cursor or Claude) on batches of files at once.
Each agent session handles BATCH_SIZE files, then a fresh session starts.

State tracking via filesystem:
  docs_clean/x.md  = 0 bytes        → not yet processed
  docs_clean/x.md  = <!-- STUB -->   → processed, no real content
  docs_clean/x.md  = real content    → cleaned ✓

Fully resumable: re-run and only unprocessed (0-byte) files are retried.

Usage:
    python step2_cleanup.py [--dry-run] [--limit N] [--batch-size N]
"""

import argparse
import re
import subprocess
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

DOCS_DIR   = Path("docs")
CLEAN_DIR  = Path("docs_clean")
BATCH_SIZE     = 10            # max files per agent session
MAX_BATCH_BYTES = 40_000       # max total content bytes per batch
STUB_MARKER = "<!-- STUB -->\n"

# CLI agent command — prompt piped via stdin, cleaned content on stdout
AGENT_CMD = ["claude", "-p"]

# ── Prompt ──────────────────────────────────────────────────────────────────

INSTRUCTIONS = """\
You are a Markdown documentation cleaner for the Prozorro Open Procurement API.

══ REMOVE from every file ══════════════════════════════════════════════

1. SIDEBAR NAVIGATION — bullet list near the top linking to prozorro-api-docs.readthedocs.io:
   * [Overview](https://prozorro-api-docs.readthedocs.io/...)
   * [Basic Actions](...)
   * [Data Standard](...)
   Remove ALL such bullets and their nested sub-items.

2. SITE LOGO LINK at the very top:
   [openprocurement.api ![Image N: Logo](...)(...)]

3. ETHICALADS / SPONSORED BLOCKS:
   [![Image N: Sponsored: MongoDB](media.ethicalads...)](...)
   [Develop and launch modern apps...](...)
   _[Ad by EthicalAds]..._   /   [Ads by EthicalAds]   /   Close Ad
   ![Image N](https://server.ethicalads.io/...)
   ![Image N](https://media.ethicalads.io/...)

4. SPHINX FOOTER:
   Built with Sphinx ...  /  © Copyright ...
   View page source  /  [Previous](...)[Next](...) navigation

5. BREADCRUMB NAV (e.g.):
   * [](index.html) * [Developers](...) * Page Name * [View page source](...)

6. Empty horizontal rules (--- or * * *) left after the removals above.

══ KEEP in every file ══════════════════════════════════════════════════

• The <!-- SOURCE: URL --> comment at the very top — ALWAYS keep it
• All headings, paragraphs, field descriptions, validation rules
• HTTP request / response examples, JSON bodies, code blocks, tables
• ALL non-ad images (graphviz diagrams, architecture PNGs, external images)
• Cross-links that are part of the content (not sidebar nav)

══ STUB RULE ════════════════════════════════════════════════════════════

Count REAL content lines: non-empty lines that are not headings (#),
not bullet nav items (*), not horizontal rules.
If fewer than 5 real content lines remain → output __STUB__ for that file.

══ OUTPUT FORMAT ════════════════════════════════════════════════════════

For EACH file output EXACTLY this block (no extra text between blocks):

=== CLEANED: <filepath> ===
<cleaned markdown content, OR the single word __STUB__>
=== END: <filepath> ===

Process ALL files below. Do not skip any. Do not add explanation.
"""


def build_prompt(batch: list[tuple[Path, Path]]) -> str:
    parts = [INSTRUCTIONS, "\n\n══ FILES TO CLEAN ══════════════════════════════════════════\n"]
    for src, dst in batch:
        content = src.read_text(encoding="utf-8")
        rel = str(src.relative_to(DOCS_DIR))
        parts.append(f"\n=== FILE: {rel} ===\n{content}\n=== ENDFILE: {rel} ===\n")
    return "".join(parts)


def parse_output(output: str, batch: list[tuple[Path, Path]]) -> dict[str, str]:
    """Extract cleaned content per filepath from agent output."""
    results: dict[str, str] = {}
    pattern = re.compile(
        r"=== CLEANED: (.+?) ===\n(.*?)\n=== END: \1 ===",
        re.DOTALL,
    )
    for m in pattern.finditer(output):
        filepath = m.group(1).strip()
        content  = m.group(2).strip()
        results[filepath] = content

    # Warn about any files the agent missed
    for src, _ in batch:
        rel = str(src.relative_to(DOCS_DIR))
        if rel not in results:
            print(f"  [WARN] Agent did not return output for: {rel}", flush=True)

    return results


DEBUG_RAW_DIR = Path("/tmp/step2_debug")

def call_agent(prompt: str, batch_idx: int = 0, debug: bool = False) -> str:
    result = subprocess.run(
        AGENT_CMD,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if debug:
        DEBUG_RAW_DIR.mkdir(exist_ok=True)
        raw_path = DEBUG_RAW_DIR / f"batch_{batch_idx:03d}.txt"
        raw_path.write_text(result.stdout, encoding="utf-8")
        print(f"  [DEBUG] Raw output saved to {raw_path}  ({len(result.stdout)} bytes)", flush=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout


# ── Filesystem helpers ───────────────────────────────────────────────────────

def mirror_tree() -> None:
    CLEAN_DIR.mkdir(exist_ok=True)
    for src in DOCS_DIR.rglob("*.md"):
        dst = CLEAN_DIR / src.relative_to(DOCS_DIR)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            dst.touch()


def pending_files() -> list[tuple[Path, Path]]:
    result = []
    for src in sorted(DOCS_DIR.rglob("*.md")):
        dst = CLEAN_DIR / src.relative_to(DOCS_DIR)
        if not dst.exists() or dst.stat().st_size == 0:
            result.append((src, dst))
    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--limit",      type=int, default=0,  help="Process only N files total")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Files per agent session")
    parser.add_argument("--debug",      action="store_true", help="Save raw agent output to /tmp/step2_debug/")
    args = parser.parse_args()

    print("[Step 2] Mirroring docs/ → docs_clean/ ...", flush=True)
    mirror_tree()

    pending = pending_files()
    if args.limit:
        pending = pending[: args.limit]

    total_src  = sum(1 for _ in DOCS_DIR.rglob("*.md"))
    already    = total_src - len(pending_files())
    print(f"[Step 2] Total: {total_src} | Already processed: {already} | Pending: {len(pending)}")
    print(f"[Step 2] Batch size: {args.batch_size} files/session | Dry run: {args.dry_run}\n")

    cleaned = stubs = errors = missed = 0

    # Build batches capped by both file count AND total content bytes
    batches: list[list[tuple[Path, Path]]] = []
    current_batch: list[tuple[Path, Path]] = []
    current_bytes = 0
    for src, dst in pending:
        file_bytes = src.stat().st_size
        if current_batch and (
            len(current_batch) >= args.batch_size
            or current_bytes + file_bytes > MAX_BATCH_BYTES
        ):
            batches.append(current_batch)
            current_batch = []
            current_bytes = 0
        current_batch.append((src, dst))
        current_bytes += file_bytes
    if current_batch:
        batches.append(current_batch)

    for b_idx, batch in enumerate(batches, 1):
        labels = [str(s.relative_to(DOCS_DIR)) for s, _ in batch]
        print(f"── Batch {b_idx}/{len(batches)}  ({len(batch)} files) ──────────────────", flush=True)
        for lbl in labels:
            print(f"   {lbl}", flush=True)

        if args.dry_run:
            print("   [DRY] would call agent\n")
            continue

        prompt = build_prompt(batch)

        try:
            raw_output = call_agent(prompt, batch_idx=b_idx, debug=args.debug)
        except Exception as e:
            print(f"  [ERROR] Agent failed for batch {b_idx}: {e}", flush=True)
            errors += len(batch)
            continue

        results = parse_output(raw_output, batch)

        for src, dst in batch:
            rel = str(src.relative_to(DOCS_DIR))
            if rel not in results:
                missed += 1
                continue

            content = results[rel]
            if content == "__STUB__":
                dst.write_text(STUB_MARKER, encoding="utf-8")
                print(f"  [STUB]  {rel}", flush=True)
                stubs += 1
            else:
                orig_size = src.stat().st_size
                dst.write_text(content, encoding="utf-8")
                new_size  = dst.stat().st_size
                reduction = 1 - new_size / max(orig_size, 1)
                print(f"  [OK]    {rel}  ({orig_size//1024}KB → {new_size//1024}KB, -{reduction:.0%})", flush=True)
                cleaned += 1

        print("", flush=True)

    remaining = len(pending_files())
    print(f"[Step 2] Batch run complete.")
    print(f"  Cleaned: {cleaned} | Stubs: {stubs} | Missed: {missed} | Errors: {errors}")
    print(f"  Still pending: {remaining}")
    if remaining:
        print(f"\n  Re-run to process remaining files.")
        print(f"  Or run: python step3_verify.py --reset-problems && python step2_cleanup.py")
    else:
        print(f"\nNext: python step3_verify.py")


if __name__ == "__main__":
    main()
