"""HTML download and text extraction (FR-3, FR-4)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    url: str
    text: str
    crawled_at: datetime


def extract_text(html: str) -> str:
    """Parse HTML, strip non-content tags, and return readable text."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def fetch_page(
    url: str,
    *,
    user_agent: str,
    timeout: int,
) -> PageContent | None:
    """Download a page and extract its textual content."""
    headers = {"User-Agent": user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            logger.warning("Skipping non-HTML content at %s (%s)", url, content_type)
            return None
        text = extract_text(response.text)
        if not text:
            logger.warning("No extractable text at %s", url)
            return None
        return PageContent(url=url, text=text, crawled_at=datetime.now(timezone.utc))
    except requests.RequestException as exc:
        logger.warning("Omitting page (fetch failed) %s: %s", url, exc)
        return None
