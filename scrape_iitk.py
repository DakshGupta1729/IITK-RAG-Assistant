"""
IITK RAG System — Scraper
--------------------------
Fetches and cleans content from IIT Kanpur's public web pages into a structured
corpus (corpus.jsonl) ready for indexing by the retrieval backend.

Each output line is a JSON object matching the project's shared document schema:
  doc_id, source_url, title, category, subcategory, text,
  scraped_at, content_hash, doc_type

Usage:
    python scrape_iitk.py

Notes:
- Add / edit SOURCES below to control which pages get scraped and how they're categorized.
- Respects robots.txt and rate-limits requests per domain.
- Safe to re-run: existing corpus.jsonl entries are replaced based on content_hash,
  so re-running does not duplicate unchanged documents.
"""

import hashlib
import json
import time
import uuid
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = "corpus.jsonl"
REQUEST_DELAY_SECONDS = 2
USER_AGENT = "IITK-RAG-Bot/0.1 (+student-project; contact: <your-email>)"

# Add / edit entries here to expand coverage. category must be one of the fixed enum values.
SOURCES = [
    {"url": "https://www.iitk.ac.in/new/about-iitk", "category": "history", "subcategory": None},
    {"url": "https://www.iitk.ac.in/new/history", "category": "history", "subcategory": None},
    {"url": "https://www.iitk.ac.in/doaa/academic-programmes", "category": "academics", "subcategory": None},
    {"url": "https://www.iitk.ac.in/doso/", "category": "facilities", "subcategory": "Dean of Students"},
    {"url": "https://www.iitk.ac.in/doso/hostels", "category": "hostel", "subcategory": None},
    {"url": "https://students.iitk.ac.in/gymkhana/", "category": "clubs", "subcategory": "Gymkhana"},
    {"url": "https://www.antaragni.in/", "category": "fests", "subcategory": "Antaragni"},
    {"url": "https://www.techkriti.org/", "category": "fests", "subcategory": "Techkriti"},
    # NOTE: PDF-based sources (fee structure, ordinances) need pdfplumber-based extraction —
    # see extract_pdf() below and add their direct PDF URLs here as doc_type "pdf" once located.
]

VALID_CATEGORIES = {
    "academics", "fees", "facilities", "clubs",
    "fests", "history", "hostel", "admissions", "other",
}


def is_allowed_by_robots(url: str) -> bool:
    """Check robots.txt for the given URL's domain before fetching."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        # If robots.txt can't be read, err on the side of allowing but log it.
        print(f"  [warn] could not read robots.txt for {parsed.netloc}, proceeding cautiously")
        return True


def fetch_html(url: str) -> str | None:
    """Fetch raw HTML for a URL with a polite user agent and basic error handling."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  [error] failed to fetch {url}: {e}")
        return None


def clean_html_to_text(html: str) -> tuple[str, str]:
    """
    Strip nav/footer/script/style boilerplate from raw HTML and return
    (title, cleaned_text). Cleaned text preserves headings and lists as
    lightweight markdown so table/list structure isn't lost.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "form", "iframe"]):
        tag.decompose()
    for tag in soup.find_all(class_=lambda c: c and any(
        kw in c.lower() for kw in ["nav", "footer", "sidebar", "menu", "cookie", "breadcrumb"]
    )):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "td"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if el.name in ("h1", "h2"):
            lines.append(f"\n## {text}\n")
        elif el.name in ("h3", "h4"):
            lines.append(f"\n### {text}\n")
        elif el.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    cleaned = "\n".join(lines)
    # Collapse excessive blank lines left over from removed elements
    cleaned = "\n".join(line for line in cleaned.splitlines() if line.strip() != "") 
    return title, cleaned


def make_record(url: str, title: str, text: str, category: str, subcategory: str | None) -> dict:
    assert category in VALID_CATEGORIES, f"Invalid category: {category}"
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "doc_id": str(uuid.uuid4()),
        "source_url": url,
        "title": title,
        "category": category,
        "subcategory": subcategory,
        "text": text,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
        "doc_type": "html",
    }


def load_existing_hashes(path: str) -> dict[str, str]:
    """Map source_url -> content_hash from a previous run, to support incremental re-scraping."""
    hashes = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    hashes[rec["source_url"]] = rec["content_hash"]
                except (json.JSONDecodeError, KeyError):
                    continue
    except FileNotFoundError:
        pass
    return hashes


def run():
    print(f"Starting IITK scrape — {len(SOURCES)} configured sources\n")
    existing_hashes = load_existing_hashes(OUTPUT_FILE)
    records = []
    skipped, updated, new = 0, 0, 0

    for source in SOURCES:
        url = source["url"]
        print(f"Fetching: {url}")

        if not is_allowed_by_robots(url):
            print("  [skip] disallowed by robots.txt")
            continue

        html = fetch_html(url)
        if html is None:
            continue

        title, text = clean_html_to_text(html)
        if len(text.strip()) < 50:
            print("  [warn] extracted text is suspiciously short, skipping (likely JS-rendered page)")
            continue

        record = make_record(url, title, text, source["category"], source["subcategory"])

        if existing_hashes.get(url) == record["content_hash"]:
            print("  [unchanged] content identical to previous run")
            skipped += 1
        elif url in existing_hashes:
            print("  [updated] content changed since last run")
            updated += 1
        else:
            print("  [new] first time scraping this URL")
            new += 1

        records.append(record)
        time.sleep(REQUEST_DELAY_SECONDS)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nDone. Wrote {len(records)} documents to {OUTPUT_FILE}")
    print(f"  new: {new} | updated: {updated} | unchanged: {skipped}")
    print("\nCoverage by category:")
    by_cat = {}
    for r in records:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    for cat, count in sorted(by_cat.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    run()
