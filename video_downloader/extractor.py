"""Fallback extractor: scrape a web page to find embedded video URLs."""

import re
import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Regex patterns to find video stream URLs inside page source / JS
_PATTERNS = [
    r'["\']?(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)["\']?',
    r'["\']?(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)["\']?',
    r'file\s*:\s*["\']([^"\']+)["\']',
    r'source\s*:\s*["\']([^"\']+)["\']',
    r'videoUrl\s*[=:]\s*["\']([^"\']+)["\']',
    r'streamUrl\s*[=:]\s*["\']([^"\']+)["\']',
    r'hlsUrl\s*[=:]\s*["\']([^"\']+)["\']',
    r'src\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
]


def _unique(seq):
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


def scrape_page(url, log=None):
    """
    Fetch *url* and return (direct_urls, iframe_urls).
    direct_urls: list of m3u8/mp4 URLs found in page source.
    iframe_urls: list of iframe src values to try recursively.
    """
    if log:
        log(f"Scraping page: {url}")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        if log:
            log(f"Failed to fetch page: {e}")
        return [], []

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Collect raw text: full HTML + all <script> contents
    texts = [html]
    for tag in soup.find_all("script"):
        if tag.string:
            texts.append(tag.string)

    direct = []
    for text in texts:
        for pat in _PATTERNS:
            direct.extend(re.findall(pat, text))

    # Filter: keep only http(s) URLs
    direct = [u for u in direct if u.startswith("http")]

    # iframes – may be embedded players
    iframes = []
    for tag in soup.find_all("iframe"):
        src = tag.get("src") or tag.get("data-src")
        if src and src.startswith("http"):
            iframes.append(src)

    return _unique(direct), _unique(iframes)


def find_video_urls(page_url, log=None):
    """
    Try to find playable video URLs from *page_url*.
    Recursively checks iframes one level deep.
    Returns a list of candidate URLs (m3u8 preferred first).
    """
    direct, iframes = scrape_page(page_url, log)

    # Also try each iframe page
    for iframe_url in iframes:
        if log:
            log(f"Checking iframe: {iframe_url}")
        d2, _ = scrape_page(iframe_url, log)
        direct.extend(d2)

    # Sort: m3u8 first, then mp4
    m3u8 = [u for u in _unique(direct) if ".m3u8" in u]
    mp4 = [u for u in _unique(direct) if ".mp4" in u and u not in m3u8]
    rest = [u for u in _unique(direct) if u not in m3u8 and u not in mp4]

    return m3u8 + mp4 + rest
