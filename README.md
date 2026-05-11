# Prozorro API Docs → llms.txt

Converts the full [Prozorro Open Procurement API documentation](https://prozorro-api-docs.readthedocs.io/en/latest/)
(301 pages, ~19 MB) into clean, LLM-ready files following the
[llms.txt standard](https://llmstxt.org/) by [Jeremy Howard](https://github.com/jph00).

Built for the [AI-Driven Corruption Radar](https://github.com/Nordost/AI-Driven-Corruption-Radar-Powered-by-Prozorro-Open-Data)
project to give LLMs instant, structured access to Prozorro API knowledge.

## Output

| File | Size | Contents |
|---|---|---|
| `llms.txt` | ~36 KB | Index: titles + source URLs + one-line descriptions |
| `llms-full.txt` | ~17 MB | All 197 documentation pages concatenated |

Load `llms-full.txt` into your LLM context window, or use `llms.txt` as a
lightweight index and fetch individual pages on demand.

## Pipeline

```
Step 1 — Scrape       docs/           301 raw Markdown pages via r.jina.ai
Step 2 — Clean        docs_clean/     regex strips nav, ads, Sphinx boilerplate
Step 3 — Classify     docs_clean/     OpenAI GPT-4o-mini marks nav-only pages as STUB
Step 4 — Build        llms.txt        index + llms-full.txt full concatenation
                      llms-full.txt
```

`docs/` is the immutable source of truth and is never modified after Step 1.

## Usage

### Step 1 — Scrape all pages

```bash
pip install -r requirements.txt
python3 step1_scrape.py
```

Resumable: non-empty files in `docs/` are skipped on re-run.
Uses [r.jina.ai](https://r.jina.ai) to convert HTML → clean Markdown.

### Step 2 — Regex cleanup

```bash
python3 step2_cleanup.py
```

Strips sidebar navigation, EthicalAds blocks, Sphinx footer, duplicate headings,
and anchor self-links using deterministic regex patterns. No LLM required.

```bash
python3 step2_cleanup.py --reprocess-all   # reset and reprocess everything
```

Resumable: 0-byte files in `docs_clean/` are treated as pending.

### Step 3 — Classify with OpenAI

```bash
cp .env.example .env          # add your OPENAI_API_KEY
python3 step3_classify.py
```

Uses `gpt-4o-mini` to decide whether each page contains real API content
(HTTP examples, schemas, workflows) or is navigation-only.
Navigation-only pages are marked `<!-- STUB -->` and excluded from output.

```bash
python3 step3_classify.py --dry-run    # preview without writing
python3 step3_classify.py --reset      # clear progress and restart
```

Fully resumable via `step3_done.txt` (gitignored).

### Step 4 — Generate llms.txt

```bash
python3 step4_llms.py
```

Produces `llms.txt` (index) and `llms-full.txt` (full content).

## Requirements

```
requests
beautifulsoup4
openai
```

```bash
pip install -r requirements.txt
```

API key in `.env`:
```
OPENAI_API_KEY=sk-...
```

## Results

- 301 pages scraped
- 197 pages with real API content (kept)
- 104 pages discarded as navigation/stub
- `llms-full.txt` — 197 clean documentation pages ready for LLM context

## llms.txt standard

This project follows the [llms.txt](https://llmstxt.org/) convention proposed by
[Jeremy Howard](https://github.com/jph00) (fast.ai) for making web content
structured and accessible to LLMs:

- `llms.txt` — a lightweight index with titles and URLs
- `llms-full.txt` — full content for loading directly into context

## License

MIT
