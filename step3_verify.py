#!/usr/bin/env python3
"""
Step 3 — Verify & Report
=========================
Checks consistency between docs/ and docs_clean/ and reports quality.

Usage:
    python step3_verify.py                  # report only
    python step3_verify.py --reset-problems # clear problematic files → re-run step2
    python step3_verify.py --delete-stubs   # remove STUB files from docs_clean/

Typical workflow after a full step2 run:
    python step3_verify.py --reset-problems
    python step2_cleanup.py                 # re-processes only the reset files
    python step3_verify.py --delete-stubs   # once everything is clean
"""

import argparse
import re
from pathlib import Path

DOCS_DIR = Path("docs")
CLEAN_DIR = Path("docs_clean")
STUB_MARKER = "<!-- STUB -->"
MIN_REAL_LINES = 5

NAV_RE = re.compile(
    r"^\* \[(?:Overview|Basic Actions|Data Standard|Tendering API|Planning API|"
    r"Contracting API|Agreement API|Frameworks API|Relocation API|Violation|"
    r"Medicines|Developers|Чернетки)\]",
    re.MULTILINE,
)
AD_RE = re.compile(r"ethicalads|EthicalAds|mongodb-codedark|Sponsored:", re.IGNORECASE)
FOOTER_RE = re.compile(r"Built with Sphinx|© Copyright", re.IGNORECASE)


def real_line_count(text: str) -> int:
    return sum(
        1 for l in text.splitlines()
        if l.strip()
        and not l.strip().startswith("#")
        and not l.strip().startswith("<!--")
        and not l.strip().startswith("*")
        and not l.strip().startswith(">")
        and l.strip() not in ("---", "* * *")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete-stubs", action="store_true",
                        help="Delete STUB files and empty dirs from docs_clean/")
    parser.add_argument("--reset-problems", action="store_true",
                        help="Clear problematic files in docs_clean/ so step2 re-processes them")
    args = parser.parse_args()

    src_files = {f.relative_to(DOCS_DIR) for f in DOCS_DIR.rglob("*.md")}
    dst_files = {f.relative_to(CLEAN_DIR) for f in CLEAN_DIR.rglob("*.md")} if CLEAN_DIR.exists() else set()

    # ── Consistency check ──────────────────────────────────────────────────
    missing_in_clean = src_files - dst_files
    extra_in_clean   = dst_files - src_files

    # ── Quality check ─────────────────────────────────────────────────────
    not_processed = []
    stubs = []
    has_nav = []
    has_ads = []
    has_footer = []
    too_short = []
    clean = []

    for rel in sorted(src_files):
        dst = CLEAN_DIR / rel
        if not dst.exists() or dst.stat().st_size == 0:
            not_processed.append(rel)
            continue

        text = dst.read_text(encoding="utf-8")
        if STUB_MARKER in text:
            stubs.append(rel)
            continue

        issues = []
        if NAV_RE.search(text):    issues.append("nav")
        if AD_RE.search(text):     issues.append("ads")
        if FOOTER_RE.search(text): issues.append("footer")
        if real_line_count(text) < MIN_REAL_LINES: issues.append("short")

        if "nav"    in issues: has_nav.append(rel)
        if "ads"    in issues: has_ads.append(rel)
        if "footer" in issues: has_footer.append(rel)
        if "short"  in issues: too_short.append(rel)

        if not issues:
            clean.append(rel)

    # ── Report ────────────────────────────────────────────────────────────
    total = len(src_files)
    sep = "=" * 62

    print(f"\n{sep}")
    print(f"  CLEANUP VERIFICATION REPORT")
    print(f"{sep}")
    print(f"  docs/       : {total} files")
    print(f"  docs_clean/ : {len(dst_files)} files")
    print(f"")
    print(f"  ✓ Clean          : {len(clean):>4}  ({len(clean)/total:.0%})")
    print(f"  ⊘ Stubs          : {len(stubs):>4}  (processed, no real content)")
    print(f"  ○ Not processed  : {len(not_processed):>4}  (run step2 again)")
    print(f"  ✗ Still has nav  : {len(has_nav):>4}")
    print(f"  ✗ Still has ads  : {len(has_ads):>4}")
    print(f"  ✗ Still has footer:{len(has_footer):>3}")
    print(f"  ✗ Too short      : {len(too_short):>4}")
    print(f"{sep}")

    if missing_in_clean:
        print(f"\n[!] Files missing in docs_clean/ ({len(missing_in_clean)}):")
        for f in sorted(missing_in_clean)[:10]:
            print(f"    {f}")

    if extra_in_clean:
        print(f"\n[!] Extra files in docs_clean/ ({len(extra_in_clean)}):")
        for f in sorted(extra_in_clean)[:5]:
            print(f"    {f}")

    if not_processed:
        print(f"\n[○] Not yet processed — re-run step2_cleanup.py:")
        for f in sorted(not_processed)[:10]:
            print(f"    {f}")
        if len(not_processed) > 10:
            print(f"    ... and {len(not_processed) - 10} more")

    for label, items in [
        ("nav",    has_nav),
        ("ads",    has_ads),
        ("footer", has_footer),
    ]:
        if items:
            print(f"\n[✗] Still has {label} ({len(items)} files) — re-run step2:")
            for f in items[:5]:
                print(f"    {f}")

    if too_short:
        print(f"\n[✗] Too short after cleanup ({len(too_short)} files):")
        for f in too_short[:10]:
            print(f"    {f}")

    # ── Reset problems → so step2 re-processes them ───────────────────────
    if args.reset_problems:
        problem_files = set(has_nav) | set(has_ads) | set(has_footer) | set(too_short)
        if problem_files:
            print(f"\n[--reset-problems] Clearing {len(problem_files)} problematic files in docs_clean/")
            print(f"  Re-run step2_cleanup.py to re-process them.\n")
            for rel in sorted(problem_files):
                dst = CLEAN_DIR / rel
                if dst.exists():
                    dst.write_bytes(b"")   # reset to 0 bytes → step2 will pick it up
                    print(f"  RESET {rel}")
        else:
            print(f"\n[--reset-problems] No problematic files found — everything is clean!")

    # ── Delete stubs ──────────────────────────────────────────────────────
    if args.delete_stubs and stubs:
        print(f"\n[--delete-stubs] Removing {len(stubs)} stub files from docs_clean/...")
        for rel in stubs:
            dst = CLEAN_DIR / rel
            dst.unlink(missing_ok=True)
            print(f"  DEL {rel}")
        # Remove empty dirs
        for d in sorted(CLEAN_DIR.rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                print(f"  RMDIR {d.relative_to(CLEAN_DIR)}/")

    print(f"\n{sep}")
    if len(clean) == total - len(stubs) and not not_processed:
        print(f"  ✓ All non-stub files are clean.")
        print(f"  Run with --delete-stubs to remove stub files from docs_clean/")
    elif not_processed:
        print(f"  → Re-run: python step2_cleanup.py")
    else:
        problems = len(has_nav) + len(has_ads) + len(has_footer)
        print(f"  → {problems} files need re-cleaning: python step2_cleanup.py")
        print(f"    (processed files are skipped — only problem ones will be re-run)")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
