# Prozorro API Docs Scraper

Collects the full [Prozorro Open Procurement API](https://prozorro-api-docs.readthedocs.io/en/latest/)
documentation and converts it into clean, LLM-ready Markdown files.

Designed for RAG pipelines and LLM fine-tuning on Ukrainian public procurement data.

## What it does

**Step 1** — Crawls all 300+ documentation pages via BFS, fetches each through
[r.jina.ai](https://r.jina.ai) for clean Markdown conversion, and saves them
into a `docs/` directory tree that mirrors the URL structure.
Graphviz state-machine diagrams get their real image URLs restored from the original HTML.

**Step 2** — Runs a Cursor (or Claude) CLI agent on each file to strip
sidebar navigation, ads, and Sphinx boilerplate, writing clean files to `docs_clean/`.
Fully resumable: already-processed files are skipped on re-run.

**Step 3** — Verifies consistency between `docs/` and `docs_clean/` and
reports any files that still need cleaning.

## Output structure

```
docs/
├── overview.md
├── basic-actions/
│   ├── authentication.md
│   ├── errors.md
│   └── feed.md
├── standard/
│   ├── bid.md
│   ├── contract.md
│   └── ...
├── tendering/
│   ├── open/tutorial.md          ← full HTTP request/response examples
│   ├── belowthreshold/tutorial.md
│   └── ...
└── ...

docs_clean/                       ← same structure, cleaned content
```

## Requirements

```bash
pip install requests beautifulsoup4
```

A Cursor or Claude CLI must be available for Step 2.

## Usage

### Step 1 — Scrape

```bash
python step1_scrape.py
```

Resumable: if interrupted, re-run — non-empty files are skipped automatically.

### Step 2 — Clean

Configure your CLI agent in `step2_cleanup.py` (line ~40):

```python
AGENT_CMD = ["cursor", "agent"]   # Cursor CLI
# or
AGENT_CMD = ["claude", "-p"]      # Claude Code CLI
```

Test on a few files first:

```bash
python step2_cleanup.py --dry-run --limit 5
python step2_cleanup.py --limit 5
```

Then run the full cleanup (re-run if interrupted — it resumes automatically):

```bash
python step2_cleanup.py
```

### Step 3 — Verify

```bash
python step3_verify.py
```

If issues remain, re-run Step 2 (already-clean files are skipped).
When everything looks good:

```bash
python step3_verify.py --delete-stubs
```

This removes stub files (pages with no real content) from `docs_clean/`
and leaves only the actual API documentation.

## How resumability works

- **Step 1**: skips files in `docs/` that are already non-empty
- **Step 2**: skips files in `docs_clean/` that already have content or a `<!-- STUB -->` marker
- Both steps can be interrupted and restarted at any time with no data loss

## Rate limiting

r.jina.ai may rate-limit requests. The scraper uses exponential backoff
(up to 4 retries per page). If you hit persistent 429 errors, increase
`REQUEST_DELAY` in `step1_scrape.py` (default: 1.5 seconds).

## License

MIT
