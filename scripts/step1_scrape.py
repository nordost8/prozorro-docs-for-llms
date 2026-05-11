#!/usr/bin/env python3
"""
Step 1 — Prozorro API Documentation Scraper
============================================
Crawls all pages of https://prozorro-api-docs.readthedocs.io/en/latest/
and saves each page as a clean Markdown file via r.jina.ai.

Output: docs/ directory tree mirroring the URL structure.

Usage:
    pip install requests beautifulsoup4
    python step1_scrape.py

Resume: if interrupted, delete the last incomplete file and re-run.
Already-saved non-empty files are skipped automatically.
"""

import re
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ── Config ─────────────────────────────────────────────────────────────────

ROOT_URL = "https://prozorro-api-docs.readthedocs.io/en/latest/overview.html"
BASE_URL = "https://prozorro-api-docs.readthedocs.io/en/latest/"
JINA_PREFIX = "https://r.jina.ai/"
OUTPUT_DIR = Path("docs")
REQUEST_DELAY = 1.5       # seconds between Jina requests (respect rate limits)
CRAWL_DELAY = 0.3         # seconds between BFS HTML fetches
MIN_CONTENT_LENGTH = 200  # skip pages shorter than this after cleaning

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ProzorroDocsScraper/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

EXCLUDED_SUFFIXES = (".js", ".css", ".png", ".jpg", ".svg", ".pdf", ".rst.txt")
EXCLUDED_SEGMENTS = {"_sources", "genindex", "search", "py-modindex", "_static"}

# ── URL helpers ────────────────────────────────────────────────────────────

def normalize(url: str) -> str:
    return urlparse(url)._replace(fragment="").geturl()


def in_scope(url: str) -> bool:
    if not url.startswith(BASE_URL):
        return False
    if any(url.endswith(s) for s in EXCLUDED_SUFFIXES):
        return False
    return not (set(urlparse(url).path.strip("/").split("/")) & EXCLUDED_SEGMENTS)


def url_to_path(url: str) -> Path:
    """Map a docs URL to a local .md file path under OUTPUT_DIR."""
    rel = urlparse(url).path.removeprefix("/en/latest/").strip("/")
    if rel.endswith(".html"):
        rel = rel[:-5] + ".md"
    elif not rel or "." not in Path(rel).name:
        rel = (rel + "/index").strip("/") + ".md"
    return OUTPUT_DIR / rel

# ── Phase 1: BFS link discovery ────────────────────────────────────────────

def discover_urls() -> list[str]:
    """BFS over raw HTML to discover all in-scope documentation URLs."""
    visited: set[str] = set()
    queue: deque[str] = deque([normalize(ROOT_URL)])
    order: list[str] = []

    print("[Phase 1] BFS crawl — discovering all pages...", flush=True)
    while queue:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        order.append(url)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup.find_all("a", href=True):
                child = normalize(urljoin(url, tag["href"]))
                if child not in visited and in_scope(child):
                    queue.append(child)
        except requests.RequestException as e:
            print(f"  [!] Crawl failed: {url} — {e}", flush=True)

        time.sleep(CRAWL_DELAY)

    print(f"[Phase 1] Found {len(order)} pages\n", flush=True)
    return order


def build_tree(urls: list[str]) -> None:
    """Pre-create the full directory + empty file structure."""
    print("[Phase 1] Building directory tree...", flush=True)
    for url in urls:
        path = url_to_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()
    print(f"[Phase 1] Tree ready under ./{OUTPUT_DIR}/\n", flush=True)

# ── Phase 2: Fetch content via Jina ────────────────────────────────────────

def fetch_jina(url: str, retries: int = 4) -> str | None:
    """Fetch a page via r.jina.ai with exponential backoff on 429/5xx."""
    jina_url = f"{JINA_PREFIX}{url}"
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(jina_url, headers=HEADERS, timeout=120)
            if resp.status_code == 429:
                wait = delay * (2 ** attempt)
                print(f"  [~] Rate limited — waiting {wait:.0f}s (attempt {attempt}/{retries})", flush=True)
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = delay * attempt
                print(f"  [~] Server error {resp.status_code} — retrying in {wait:.0f}s", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            print(f"  [!] Attempt {attempt} failed: {e}", flush=True)
            if attempt < retries:
                time.sleep(delay * attempt)
    return None


def fetch_html(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        return None


def extract_img_urls(html: str, page_url: str) -> list[str]:
    """Extract absolute <img src> URLs from original HTML (for fixing Jina blanks)."""
    soup = BeautifulSoup(html, "html.parser")
    return [urljoin(page_url, img["src"]) for img in soup.find_all("img", src=True)]


def fix_image_urls(markdown: str, img_urls: list[str]) -> str:
    """
    Jina outputs ![alt text]() with an empty URL for server-rendered images
    (e.g. Graphviz diagrams). Replace with the correct URLs from original HTML.
    """
    if not img_urls:
        return markdown

    img_iter = iter(img_urls)

    def replace(m: re.Match) -> str:
        url_in_md = m.group(1)
        if url_in_md.strip():
            return m.group(0)          # already has a URL
        try:
            real = next(img_iter)
            return m.group(0)[: m.start(1) - m.start()] + real + ")"
        except StopIteration:
            return m.group(0)

    return re.compile(r"!\[.*?\]\(([^)]*)\)", re.DOTALL).sub(replace, markdown)


def strip_jina_header(text: str) -> str:
    """Remove Jina's metadata preamble (Title / URL Source / Markdown Content:)."""
    m = re.search(r"Markdown Content:\s*\n", text)
    return text[m.end():] if m else text


def fill_pages(urls: list[str]) -> None:
    total = len(urls)
    saved = skipped = failed = 0

    print("[Phase 2] Fetching pages via r.jina.ai...", flush=True)
    for i, url in enumerate(urls, 1):
        path = url_to_path(url)

        # Resume: skip already-saved non-empty files
        if path.exists() and path.stat().st_size > 0:
            print(f"[{i}/{total}] SKIP (already saved) {path}", flush=True)
            skipped += 1
            continue

        print(f"[{i}/{total}] {url}", flush=True)

        html = fetch_html(url)
        img_urls = extract_img_urls(html, url) if html else []

        raw = fetch_jina(url)
        if raw is None:
            print("  [!] Failed after retries — leaving empty", flush=True)
            failed += 1
            time.sleep(REQUEST_DELAY)
            continue

        content = strip_jina_header(raw)
        if img_urls:
            content = fix_image_urls(content, img_urls)

        if "404 Not Found" in content or len(content.strip()) < MIN_CONTENT_LENGTH:
            print(f"  [x] Skipped (404 or too short)", flush=True)
            skipped += 1
            time.sleep(REQUEST_DELAY)
            continue

        header = f"<!-- SOURCE: {url} -->\n\n"
        path.write_text(header + content, encoding="utf-8")
        saved += 1
        imgs = content.count("![")
        print(f"  [+] {path} ({path.stat().st_size/1024:.0f} KB, {imgs} images)", flush=True)

        if i < total:
            time.sleep(REQUEST_DELAY)

    print(f"\n[Phase 2] Done. Saved: {saved} | Skipped: {skipped} | Failed: {failed}")
    print(f"Next: python step2_cleanup.py\n")

# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    urls = discover_urls()
    if not urls:
        print("[!] No URLs found.")
        return
    build_tree(urls)
    fill_pages(urls)


if __name__ == "__main__":
    main()
