"""Website crawler with internal-link discovery (FR-2)."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Event
from typing import Callable
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from website_to_chroma.html_processor import PageContent, extract_text
from website_to_chroma.tab_configs import Tab1Config

logger = logging.getLogger(__name__)


@dataclass
class CrawlState:
    visited: set[str] = field(default_factory=set)
    pending: deque[str] = field(default_factory=deque)
    failed: list[str] = field(default_factory=list)


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication (strip fragment, trailing slash)."""
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    normalized = parsed._replace(path=path, fragment="").geturl()
    return normalized


def is_internal_link(url: str, base_domain: str) -> bool:
    parsed = urlparse(url)
    if not parsed.scheme:
        return True
    if parsed.scheme not in ("http", "https"):
        return False
    return parsed.netloc == base_domain or parsed.netloc.endswith(f".{base_domain}")


def _path_prefix(url: str) -> str:
    return urlparse(url).path.rstrip("/") or "/"


def _path_segments(url: str) -> list[str]:
    return [segment for segment in _path_prefix(url).split("/") if segment]


def _parent_path(url: str) -> str:
    segments = _path_segments(url)
    if not segments:
        return "/"
    if len(segments) == 1:
        return "/"
    return "/" + "/".join(segments[:-1])


def is_child_of_start_url(url: str, start_url: str) -> bool:
    """Return True if url is the start URL or a descendant path under it."""
    prefix = _path_prefix(start_url)
    url_path = _path_prefix(url)

    if prefix == "/":
        return True
    if url_path == prefix:
        return True
    return url_path.startswith(prefix + "/")


def is_same_level_as_start_url(url: str, start_url: str) -> bool:
    """Return True if url shares the same parent path and depth as the start URL."""
    url_path = _path_prefix(url)
    start_path = _path_prefix(start_url)
    if url_path == start_path:
        return True
    return (
        _parent_path(url_path) == _parent_path(start_path)
        and len(_path_segments(url_path)) == len(_path_segments(start_path))
    )


def _sibling_root_for_url(url: str, start_url: str) -> str | None:
    """Return the sibling path prefix for url, or None if not under a sibling subtree."""
    start_path = _path_prefix(start_url)
    url_path = _path_prefix(url)
    start_parent = _parent_path(start_path)
    start_depth = len(_path_segments(start_path))
    url_segments = _path_segments(url_path)

    if len(url_segments) < start_depth:
        return None

    if start_parent == "/":
        sibling_root = "/" + url_segments[0]
    else:
        sibling_root = f"{start_parent}/{url_segments[start_depth - 1]}"

    if sibling_root == start_path:
        return None
    if (
        _parent_path(sibling_root) == start_parent
        and len(_path_segments(sibling_root)) == start_depth
    ):
        return sibling_root
    return None


def is_in_sibling_subtree(url: str, start_url: str) -> bool:
    """Return True if url is a start-path sibling or a descendant of one."""
    sibling_root = _sibling_root_for_url(url, start_url)
    if sibling_root is None:
        return False
    url_path = _path_prefix(url)
    return url_path == sibling_root or url_path.startswith(sibling_root + "/")


def is_crawlable_url(
    url: str,
    start_url: str,
    base_domain: str,
    *,
    all_internal_links: bool = False,
    include_start_descendants: bool = True,
    include_siblings: bool = False,
) -> bool:
    if not is_internal_link(url, base_domain):
        return False
    if all_internal_links:
        return True
    if include_start_descendants and is_child_of_start_url(url, start_url):
        return True
    if include_siblings and is_in_sibling_subtree(url, start_url):
        return True
    if _path_prefix(url) == _path_prefix(start_url):
        return True
    return False


def extract_internal_links(
    html: str,
    page_url: str,
    base_domain: str,
    start_url: str,
    *,
    all_internal_links: bool = False,
    include_start_descendants: bool = True,
    include_siblings: bool = False,
) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(page_url, href)
        absolute = normalize_url(absolute)
        if is_crawlable_url(
            absolute,
            start_url,
            base_domain,
            all_internal_links=all_internal_links,
            include_start_descendants=include_start_descendants,
            include_siblings=include_siblings,
        ):
            links.append(absolute)
    return links


def _describe_crawl_scope(config: Tab1Config) -> str:
    if config.all_internal_links:
        return f"all internal links on {config.base_domain}"
    parts: list[str] = []
    if config.include_start_descendants:
        parts.append("start URL and descendants")
    if config.include_siblings:
        parts.append("siblings and their descendants")
    return " and ".join(parts) if parts else "start URL only"


def _fetch_html(url: str, config: Tab1Config) -> str | None:
    headers = {"User-Agent": config.user_agent}
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=config.request_timeout,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return None
        return response.text
    except requests.RequestException as exc:
        logger.warning("Omitting page (fetch failed) %s: %s", url, exc)
        return None


ProgressCallback = Callable[[int, int, str], None]


def crawl_website(
    config: Tab1Config,
    *,
    on_progress: ProgressCallback | None = None,
    cancel_event: Event | None = None,
) -> list[PageContent]:
    """
    Crawl pages starting from config.start_url.

    Returns PageContent for each successfully processed page.
    """
    state = CrawlState()
    start = normalize_url(config.start_url)
    state.pending.append(start)
    logger.info("Crawl scope: %s", _describe_crawl_scope(config))

    pages: list[PageContent] = []
    pages_crawled = 0

    while state.pending and pages_crawled < config.max_pages:
        if cancel_event and cancel_event.is_set():
            logger.info("Crawl cancelled after %d pages", pages_crawled)
            break

        url = state.pending.popleft()
        if url in state.visited:
            continue
        state.visited.add(url)

        logger.info("Crawling (%d/%d): %s", pages_crawled + 1, config.max_pages, url)
        if on_progress:
            on_progress(pages_crawled, config.max_pages, url)

        try:
            html = _fetch_html(url, config)
            if html is None:
                state.failed.append(url)
                continue

            text = extract_text(html)
            if not text:
                logger.warning("Omitting page (no extractable text): %s", url)
                state.failed.append(url)
                continue

            page = PageContent(url=url, text=text, crawled_at=datetime.now(timezone.utc))
            pages_crawled += 1
            pages.append(page)
            if on_progress:
                on_progress(pages_crawled, config.max_pages, url)

            for link in extract_internal_links(
                html,
                url,
                config.base_domain,
                start,
                all_internal_links=config.all_internal_links,
                include_start_descendants=config.include_start_descendants,
                include_siblings=config.include_siblings,
            ):
                if link not in state.visited:
                    state.pending.append(link)
        except Exception as exc:
            logger.warning("Omitting page (processing error) %s: %s", url, exc)
            state.failed.append(url)
        finally:
            if config.crawl_delay > 0:
                time.sleep(config.crawl_delay)

    if state.failed:
        logger.warning("Failed to crawl %d URL(s): %s", len(state.failed), state.failed)
    logger.info(
        "Crawl finished: %d pages crawled, %d visited, %d failed",
        pages_crawled,
        len(state.visited),
        len(state.failed),
    )
    return pages
