# Prozorro API Docs for LLMs

Complete [Prozorro Open Procurement API](https://prozorro-api-docs.readthedocs.io/en/latest/)
documentation converted into LLM-ready files following the
[llms.txt standard](https://llmstxt.org/) by [Jeremy Howard](https://github.com/jph00).

Built for the [AI-Driven Corruption Radar](https://github.com/nordost8/AI-Driven-Corruption-Radar-Powered-by-Prozorro-Open-Data) project.

## Files

| File | Size | Description |
|---|---|---|
| [`llms.txt`](./llms.txt) | 36 KB | Index of all pages — titles, URLs, one-line descriptions |
| [`llms-full.txt`](./llms-full.txt) | 16.3 MB | Full documentation — all 197 pages concatenated, ready to load into LLM context |

## How to use

Load `llms-full.txt` directly into your LLM context window to give it full knowledge
of the Prozorro API — endpoints, schemas, request/response examples, workflows.

Use `llms.txt` as a lightweight index if you want to fetch specific pages on demand.

## What's inside

The Prozorro API documentation site has **301 pages** total. After filtering out
pure navigation pages (table of contents, index pages, empty overviews) that carry
no actual API content, **197 pages** remain — every page with real information:
HTTP request/response examples, field schemas, workflow descriptions, and configuration tables.

Nothing was lost — the 104 excluded pages were navigation-only (e.g. `index.html`,
`overview.html` with just links to subpages). All actual API documentation is included.

## How it was built

```
Step 1 — Scrape    301 pages crawled from prozorro-api-docs.readthedocs.io via r.jina.ai
Step 2 — Clean     regex strips sidebar nav, ads, Sphinx boilerplate (deterministic, no LLM)
Step 3 — Filter    GPT-4o-mini classifies each page: real content vs navigation-only
Step 4 — Build     197 pages → llms.txt index + llms-full.txt full concatenation
```

Scripts are in the [`scripts/`](./scripts/) folder if you want to regenerate or adapt for another docs site.

## llms.txt standard

The [llms.txt](https://llmstxt.org/) convention by [Jeremy Howard](https://github.com/jph00) (fast.ai)
defines a standard way to make web documentation accessible to LLMs:

- `llms.txt` — structured index with titles and source URLs
- `llms-full.txt` — full content for direct loading into context

## License

MIT
