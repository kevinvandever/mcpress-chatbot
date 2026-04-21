"""
Website Metadata Scraper for Article Metadata Quality
Feature: article-metadata-quality

Fetches and parses article metadata (title, author) from the MC Press
website (mcpressonline.com). Used as a fallback when the Excel spreadsheet
does not contain a match for a given article.

The scraper uses the article URL from the export spreadsheet (Joomla-style
slug URLs), NOT a constructed numeric ID URL.

Uses aiohttp for async HTTP requests and regex-based HTML parsing
(BeautifulSoup is not available in this project).
"""

import re
import html
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ScrapedMetadata:
    """Metadata scraped from an MC Press article page."""
    title: Optional[str] = None
    author: Optional[str] = None
    source_url: Optional[str] = None


class WebsiteMetadataScraper:
    """
    Scrapes article metadata from mcpressonline.com.

    Fetches the article page using the URL from the export spreadsheet
    and extracts title and author from the HTML content using regex patterns.
    """

    TIMEOUT = 10  # seconds
    USER_AGENT = "MCPressChatbot/1.0"

    async def scrape_article(self, article_url: str) -> Optional[ScrapedMetadata]:
        """
        Fetch article page and extract title + author from HTML.

        Args:
            article_url: Full URL to the MC Press article page.

        Returns:
            ScrapedMetadata with extracted title/author, or None on
            404, timeout, or parse failure.
        """
        if not article_url or not article_url.strip():
            logger.debug("scrape_article called with empty URL — skipping.")
            return None

        article_url = article_url.strip()

        headers = {
            "User-Agent": self.USER_AGENT,
        }

        timeout = aiohttp.ClientTimeout(total=self.TIMEOUT)

        try:
            async with aiohttp.ClientSession(
                timeout=timeout, headers=headers
            ) as session:
                async with session.get(article_url) as response:
                    if response.status == 404:
                        logger.debug(
                            "Article page returned 404: %s", article_url
                        )
                        return None

                    if response.status != 200:
                        logger.warning(
                            "Unexpected HTTP %d from %s",
                            response.status,
                            article_url,
                        )
                        return None

                    html_content = await response.text()

        except aiohttp.ClientError as exc:
            logger.warning(
                "HTTP client error fetching %s: %s", article_url, exc
            )
            return None
        except TimeoutError:
            logger.warning(
                "Timeout (%ds) fetching %s", self.TIMEOUT, article_url
            )
            return None
        except Exception as exc:
            logger.warning(
                "Unexpected error fetching %s: %s", article_url, exc
            )
            return None

        if not html_content or not html_content.strip():
            logger.warning("Empty HTML response from %s", article_url)
            return None

        title = self.extract_title_from_html(html_content)
        author = self.extract_author_from_html(html_content)

        if title is None and author is None:
            logger.debug(
                "Could not extract any metadata from %s", article_url
            )
            return None

        return ScrapedMetadata(
            title=title,
            author=author,
            source_url=article_url,
        )

    # ------------------------------------------------------------------
    # HTML extraction helpers
    # ------------------------------------------------------------------

    def extract_title_from_html(self, html_content: str) -> Optional[str]:
        """
        Extract article title from HTML content.

        Looks for (in priority order):
        1. <h1> tag content (most specific — typically the article title)
        2. <h2> tag with article-title-related class/id
        3. <meta property="og:title"> content
        4. <title> tag content (least specific — may include site name)

        Args:
            html_content: Raw HTML string.

        Returns:
            Cleaned title string, or None if not found.
        """
        if not html_content:
            return None

        # 1. Try <h1> tag — most likely the article title
        h1_match = re.search(
            r'<h1[^>]*>\s*(.*?)\s*</h1>',
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        if h1_match:
            title = self._clean_html_text(h1_match.group(1))
            if title and len(title) > 2:
                return title

        # 2. Try <h2> with article-title-related class or id
        h2_match = re.search(
            r'<h2[^>]*(?:class|id)\s*=\s*["\'][^"\']*(?:title|article|heading)[^"\']*["\'][^>]*>\s*(.*?)\s*</h2>',
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        if h2_match:
            title = self._clean_html_text(h2_match.group(1))
            if title and len(title) > 2:
                return title

        # 3. Try og:title meta tag
        og_match = re.search(
            r'<meta\s+(?:[^>]*?)property\s*=\s*["\']og:title["\']\s+content\s*=\s*["\']([^"\']+)["\']',
            html_content,
            re.IGNORECASE,
        )
        if not og_match:
            # Also try reversed attribute order
            og_match = re.search(
                r'<meta\s+(?:[^>]*?)content\s*=\s*["\']([^"\']+)["\']\s+property\s*=\s*["\']og:title["\']',
                html_content,
                re.IGNORECASE,
            )
        if og_match:
            title = self._clean_html_text(og_match.group(1))
            if title and len(title) > 2:
                return title

        # 4. Fallback to <title> tag
        title_match = re.search(
            r'<title[^>]*>\s*(.*?)\s*</title>',
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        if title_match:
            title = self._clean_html_text(title_match.group(1))
            if title and len(title) > 2:
                # Strip common site-name suffixes
                # e.g. "Article Title - MC Press Online" → "Article Title"
                title = re.sub(
                    r'\s*[-|–—]\s*MC\s*Press.*$',
                    '',
                    title,
                    flags=re.IGNORECASE,
                ).strip()
                if title:
                    return title

        return None

    def extract_author_from_html(self, html_content: str) -> Optional[str]:
        """
        Extract author name from HTML content.

        Looks for (in priority order):
        1. "By: Author Name" or "By Author Name" or "Written by Author Name"
           patterns in the text
        2. <meta name="author"> content
        3. Elements with author-related class/id attributes

        Args:
            html_content: Raw HTML string.

        Returns:
            Cleaned author name string, or None if not found.
        """
        if not html_content:
            return None

        # 1. "By" / "Written by" / "By:" patterns in text
        #    Match "By Author Name" where the name is capitalized words
        #    The pattern handles: "By: John Smith", "By John Smith",
        #    "Written by John Smith", "By: John A. Smith"
        by_patterns = [
            # "By: Author Name" or "By Author Name" (with optional colon)
            r'(?:Written\s+by|By)\s*:?\s+([A-Z][a-zA-Z.\'-]+(?:\s+[A-Z][a-zA-Z.\'-]+){0,4})',
        ]

        for pattern in by_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                # Take the first match that looks like a real author name
                for match in matches:
                    author = match.strip()
                    if self._is_plausible_author(author):
                        return author

        # 2. <meta name="author"> tag
        meta_match = re.search(
            r'<meta\s+(?:[^>]*?)name\s*=\s*["\']author["\']\s+content\s*=\s*["\']([^"\']+)["\']',
            html_content,
            re.IGNORECASE,
        )
        if not meta_match:
            meta_match = re.search(
                r'<meta\s+(?:[^>]*?)content\s*=\s*["\']([^"\']+)["\']\s+name\s*=\s*["\']author["\']',
                html_content,
                re.IGNORECASE,
            )
        if meta_match:
            author = self._clean_html_text(meta_match.group(1))
            if author and self._is_plausible_author(author):
                return author

        # 3. Elements with author-related class or id
        author_el_match = re.search(
            r'<(?:span|div|p|a)[^>]*(?:class|id)\s*=\s*["\'][^"\']*author[^"\']*["\'][^>]*>\s*(.*?)\s*</(?:span|div|p|a)>',
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        if author_el_match:
            author = self._clean_html_text(author_el_match.group(1))
            # Strip leading "By" / "By:" if present
            author = re.sub(
                r'^(?:Written\s+by|By)\s*:?\s*',
                '',
                author,
                flags=re.IGNORECASE,
            ).strip()
            if author and self._is_plausible_author(author):
                return author

        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_html_text(text: str) -> str:
        """
        Remove HTML tags and decode entities from a text fragment.

        Args:
            text: Raw text that may contain HTML tags and entities.

        Returns:
            Cleaned plain-text string.
        """
        if not text:
            return ""

        # Remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', text)

        # Decode HTML entities (e.g. &amp; → &, &#39; → ')
        cleaned = html.unescape(cleaned)

        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned

    @staticmethod
    def _is_plausible_author(name: str) -> bool:
        """
        Check whether a string looks like a plausible author name.

        Filters out common false positives from HTML parsing.

        Args:
            name: Candidate author name string.

        Returns:
            True if the name looks like a real person's name.
        """
        if not name or len(name) < 3:
            return False

        # Too long to be a name
        if len(name) > 80:
            return False

        # Must contain at least one letter
        if not re.search(r'[a-zA-Z]', name):
            return False

        # Reject strings that are all digits
        if name.replace(' ', '').isdigit():
            return False

        # Reject common false positives
        false_positives = {
            'admin', 'editor', 'staff', 'team', 'unknown',
            'anonymous', 'contributor', 'guest', 'author',
            'mc press', 'mc press online', 'mcpress',
        }
        if name.lower().strip() in false_positives:
            return False

        return True
