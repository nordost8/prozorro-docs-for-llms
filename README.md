# Prozorro API Docs for LLMs

**The complete Prozorro Open Procurement API documentation — cleaned, filtered, and packaged as [`llms.txt`](https://llmstxt.org/) so you can drop it straight into any LLM context.**

![Pages](https://img.shields.io/badge/pages-197-blue)
![Size](https://img.shields.io/badge/llms--full.txt-16.3%20MB-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Standard](https://img.shields.io/badge/standard-llms.txt-orange)

---

## Files

| File | Size | What it is |
|---|---|---|
| [`llms.txt`](./llms.txt) | 36 KB | Index — titles, source URLs, one-line descriptions of every page |
| [`llms-full.txt`](./llms-full.txt) | 16.3 MB | Full content — all 197 documentation pages concatenated |

## Who is this for

- **LLM / AI developers** building apps on top of Prozorro data — load `llms-full.txt` into context and your model instantly knows the full API
- **Anti-corruption researchers** and civic tech projects that need structured Prozorro API knowledge
- Anyone integrating with Ukrainian public procurement who doesn't want to read 300 HTML pages

## How to use

```python
# Load full docs into your LLM context
with open("llms-full.txt") as f:
    prozorro_docs = f.read()

# Or use llms.txt as a lightweight index
with open("llms.txt") as f:
    index = f.read()
```

Or simply attach `llms-full.txt` to your Claude / ChatGPT / Gemini conversation.

## What's inside

Prozorro's documentation site has **301 pages** total. After automatically filtering out pure navigation pages — table-of-contents pages, empty index overviews, pages with just links — **197 pages** of real API content remain. Nothing was lost: the 104 excluded pages contained zero API information (they were menus).

The 197 kept pages include:
- HTTP request/response examples for every endpoint
- Full JSON schemas for all data types (Tender, Bid, Award, Contract, Complaint…)
- Workflow diagrams (rendered as DOT source, readable by LLMs)
- Configuration tables per procurement procedure type
- Tutorials for all 15+ procedure types (belowThreshold, openEU, ESCO, cfaua…)

## Why both Ukrainian and English?

The documentation is intentionally bilingual — this reflects the source material, not a processing artifact.

**English** — technical layer written by the OpenProcurement team:
HTTP methods, API field names, endpoint paths, status values, schema descriptions, algorithm explanations.

**Ukrainian** — legal and domain-specific content:
Test JSON payloads use real Ukrainian data (`"Державне управління справами"`, `"м. Київ"`), legal qualification criteria quote Ukrainian procurement law verbatim, and some procedure-specific descriptions are in Ukrainian.

For LLMs this is actually an advantage — the model learns both the technical API structure (English) and the real-world Ukrainian procurement context it will encounter in production data.

## How it was built

```
Step 1 — Scrape    301 pages from prozorro-api-docs.readthedocs.io via r.jina.ai (HTML → Markdown)
Step 2 — Clean     deterministic regex strips sidebar nav, ads, Sphinx boilerplate — no LLM needed
Step 3 — Filter    GPT-4o-mini classifies each page: real API content vs navigation-only
Step 4 — Build     197 pages → llms.txt index + llms-full.txt concatenation
```

Rebuild scripts are in [`scripts/`](./scripts/) if you want to regenerate or adapt for another docs site.

## llms.txt standard

This project follows the [llms.txt](https://llmstxt.org/) convention proposed by
[Jeremy Howard](https://github.com/jph00) (fast.ai):

- `llms.txt` — a structured index with titles and source URLs
- `llms-full.txt` — full content for loading directly into LLM context

## Related

- [AI-Driven Corruption Radar](https://github.com/nordost8/AI-Driven-Corruption-Radar-Powered-by-Prozorro-Open-Data) — the project this was built for
- [Prozorro Open Procurement API docs](https://prozorro-api-docs.readthedocs.io/en/latest/) — original source

## License

MIT
