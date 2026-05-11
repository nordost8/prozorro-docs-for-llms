#!/usr/bin/env python3
"""
Step 3 — OpenAI Classifier
============================
Classifies each cleaned file: does it contain real API documentation?
Runs up to 10 parallel API calls. Fully resumable.

Resumability:
  - Files already marked <!-- STUB --> are skipped.
  - Files already processed (kept) are tracked in step3_done.txt.
  - Re-running picks up only unprocessed files.

Models:
  gpt-4o-mini  — files < 20 KB  (cheap)
  gpt-4o       — files ≥ 20 KB  (better for long content)

Usage:
    python3 step3_classify.py                # process pending files
    python3 step3_classify.py --dry-run      # show what would happen, no writes
    python3 step3_classify.py --reset        # clear progress and restart
"""

import asyncio
import json
import os
import argparse
from pathlib import Path

try:
    from openai import AsyncOpenAI
except ImportError:
    print("Run: pip install openai")
    raise SystemExit(1)

CLEAN_DIR  = Path("docs_clean")
DONE_FILE  = Path("step3_done.txt")
STUB_TEXT  = "<!-- STUB -->"
STUB_MARKER = "<!-- STUB -->\n"

PROMPT = """\
You are reviewing a page from the Prozorro Open Procurement API documentation.

Decide: does this page contain REAL content useful to a developer integrating with Prozorro?

Return {"useful": true} if it has ANY of:
- HTTP request/response examples
- Field/schema descriptions
- API workflow or parameter explanations
- Meaningful code examples

Return {"useful": false} if it is:
- Only navigation links or a table of contents
- Nearly empty (title only, no body content)
- Just a list of links to other pages

Respond with JSON only: {"useful": true} or {"useful": false}

--- PAGE CONTENT ---
"""


def load_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("OPENAI_API_KEY not set. Add to .env or environment.")


def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(DONE_FILE.read_text().splitlines())
    return set()


def mark_done(rel: str) -> None:
    with DONE_FILE.open("a") as f:
        f.write(rel + "\n")


async def classify(client: AsyncOpenAI, path: Path, sem: asyncio.Semaphore) -> tuple[Path, bool]:
    content = path.read_text(encoding="utf-8")
    model   = "gpt-4o-mini"

    async with sem:
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": PROMPT + content[:6_000]}],
                response_format={"type": "json_object"},
                max_tokens=10,
                temperature=0,
            )
            data = json.loads(resp.choices[0].message.content)
            return path, bool(data.get("useful", True))
        except Exception as e:
            print(f"  [ERROR] {path.name}: {e}", flush=True)
            return path, True  # keep on error, don't lose content


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true",
                        help="Classify and print results without writing changes")
    parser.add_argument("--reset", action="store_true",
                        help="Clear step3_done.txt and re-classify everything")
    args = parser.parse_args()

    if args.reset:
        DONE_FILE.unlink(missing_ok=True)
        print("[Step 3] Progress reset.", flush=True)

    done = load_done()
    client = AsyncOpenAI(api_key=load_api_key())
    sem    = asyncio.Semaphore(args.concurrency)

    to_classify: list[Path] = []
    for f in sorted(CLEAN_DIR.rglob("*.md")):
        if f.stat().st_size == 0:
            continue
        content = f.read_text(encoding="utf-8")
        if content.strip().startswith(STUB_TEXT):
            continue
        rel = str(f.relative_to(CLEAN_DIR))
        if rel in done:
            continue
        to_classify.append(f)

    total_done = len(done)
    print(f"[Step 3] Already done: {total_done} | Pending: {len(to_classify)} "
          f"(concurrency={args.concurrency}, dry_run={args.dry_run})\n", flush=True)

    if not to_classify:
        print("[Step 3] Nothing to do.")
        return

    tasks   = [classify(client, f, sem) for f in to_classify]
    results = await asyncio.gather(*tasks)

    kept = stubs = errors = 0
    for path, useful in results:
        rel = str(path.relative_to(CLEAN_DIR))
        if useful:
            print(f"  [KEEP]  {rel}", flush=True)
            kept += 1
            if not args.dry_run:
                mark_done(rel)
        else:
            print(f"  [STUB]  {rel}", flush=True)
            stubs += 1
            if not args.dry_run:
                path.write_text(STUB_MARKER, encoding="utf-8")
                mark_done(rel)

    print(f"\n[Step 3] Done. Kept: {kept} | Stubs: {stubs}")
    print("Next: python3 step4_llms.py")


if __name__ == "__main__":
    asyncio.run(main())
