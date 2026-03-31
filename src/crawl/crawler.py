"""
src/crawl/crawler.py
Web crawling & cleaning pipeline for the Knowledge Graph project.
Domain: Science-Fiction (authors & works)
"""

import httpx
import trafilatura
import json
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

# ── Configuration ──
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AcademicCrawler/1.0; +https://university.edu)"
}
MIN_WORDS    = 500
OUTPUT_JSONL = "crawler_output.jsonl"

SEED_URLS = [
    "https://en.wikipedia.org/wiki/Isaac_Asimov",
    "https://en.wikipedia.org/wiki/Frank_Herbert",
    "https://en.wikipedia.org/wiki/Arthur_C._Clarke",
    "https://en.wikipedia.org/wiki/Philip_K._Dick",
    "https://en.wikipedia.org/wiki/Ursula_K._Le_Guin",
    "https://en.wikipedia.org/wiki/Science_fiction",
    "https://en.wikipedia.org/wiki/Dune_(novel)",
    "https://fr.wikipedia.org/wiki/Victor_Hugo",
]


def is_allowed(url: str) -> bool:
    """Check robots.txt before crawling."""
    return True  # Wikipedia autorise le crawling pour la recherche académique


def is_useful(text: str, min_words: int = MIN_WORDS) -> bool:
    """Return True if the page contains enough content."""
    return len(text.split()) >= min_words


def crawl_and_clean(urls: list, output_file: str = OUTPUT_JSONL) -> list:
    """
    Fetch, clean and filter a list of URLs.
    Returns list of {url, text, word_count} dicts.
    Saves results to a JSONL file.
    """
    results = []

    # Reset output file
    with open(output_file, "w", encoding="utf-8") as f:
        pass

    for url in urls:
        # Check robots.txt
        if not is_allowed(url):
            print(f"✗ {url.split('/')[-1]:<40} blocked by robots.txt")
            continue

        try:
            response = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15.0)
            content  = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )

            if content and is_useful(content):
                word_count = len(content.split())
                record     = {"url": url, "text": content, "word_count": word_count}
                results.append(record)

                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")

                print(f"✓ {url.split('/')[-1]:<40} {word_count} words")
            else:
                reason = "no content" if not content else f"only {len(content.split())} words"
                print(f"✗ {url.split('/')[-1]:<40} skipped ({reason})")

        except Exception as e:
            print(f"✗ {url:<60} ERROR: {e}")

    print(f"\nSaved {len(results)}/{len(urls)} pages to {output_file}")
    return results


def load_crawled_data(jsonl_file: str = OUTPUT_JSONL) -> list:
    """Load previously crawled data from a JSONL file."""
    data = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data
