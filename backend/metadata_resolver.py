"""
Metadata Resolver for Article Metadata Quality
Feature: article-metadata-quality

Orchestrates multi-source metadata resolution with priority ordering:
1. Excel spreadsheet lookup (fastest, most reliable)
2. MC Press website scraping (using URL from Excel data)
3. PDF content extraction via AuthorExtractor
4. Default values (filename as title, "Unknown Author")

Short-circuits when Excel provides both title and author.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

try:
    from excel_lookup_service import ExcelLookupService
    from website_metadata_scraper import WebsiteMetadataScraper
    from author_extractor import AuthorExtractor
except ImportError:
    from backend.excel_lookup_service import ExcelLookupService
    from backend.website_metadata_scraper import WebsiteMetadataScraper
    from backend.author_extractor import AuthorExtractor

logger = logging.getLogger(__name__)


@dataclass
class ResolvedMetadata:
    """Result of multi-source metadata resolution."""
    title: str
    authors: List[str]
    source: str  # "excel", "website", "pdf", "default"
    article_url: Optional[str] = None


class MetadataResolver:
    """
    Resolves article metadata from multiple sources in priority order.

    Resolution chain:
        Excel lookup → Website scraping → PDF extraction → Defaults

    Accepts ExcelLookupService, WebsiteMetadataScraper, and AuthorExtractor
    as constructor dependencies for testability and flexibility.
    """

    def __init__(
        self,
        excel_lookup: ExcelLookupService,
        website_scraper: WebsiteMetadataScraper,
        author_extractor: AuthorExtractor,
    ):
        self._excel_lookup = excel_lookup
        self._website_scraper = website_scraper
        self._author_extractor = author_extractor

    async def resolve(
        self, filename: str, pdf_path: Optional[str] = None
    ) -> ResolvedMetadata:
        """
        Resolve metadata for a numeric-filename article.

        Resolution order:
        1. Excel spreadsheet lookup
        2. MC Press website scraping (using URL from export spreadsheet)
        3. PDF content extraction (if pdf_path provided)
        4. Default values (filename as title, 'Unknown Author')

        Args:
            filename: The PDF filename (e.g. "27814.pdf").
            pdf_path: Optional filesystem path to the PDF for author extraction.

        Returns:
            ResolvedMetadata with title, authors list, source attribution,
            and optional article_url.
        """
        # Strip extension for default title
        default_title = filename.rsplit(".pdf", 1)[0] if filename.endswith(".pdf") else filename

        logger.info("Resolving metadata for '%s'", filename)

        # ------------------------------------------------------------------
        # Step 1: Excel lookup
        # ------------------------------------------------------------------
        excel_entry = self._excel_lookup.lookup_by_filename(filename)

        if excel_entry is not None:
            excel_title = excel_entry.title.strip() if excel_entry.title else ""
            excel_author = excel_entry.author.strip() if excel_entry.author else ""
            article_url = excel_entry.url

            has_title = bool(excel_title)
            has_author = bool(excel_author)

            if has_title and has_author:
                # Short-circuit: Excel has everything we need
                authors = self._excel_lookup.parse_authors(excel_author)
                if not authors:
                    authors = [excel_author] if excel_author else ["Unknown Author"]

                logger.info(
                    "Resolved '%s' from Excel (short-circuit): title='%s', authors=%s",
                    filename,
                    excel_title,
                    authors,
                )
                return ResolvedMetadata(
                    title=excel_title,
                    authors=authors,
                    source="excel",
                    article_url=article_url,
                )

            # Excel has partial data — carry forward what we have and continue
            logger.info(
                "Excel partial match for '%s': title=%s, author=%s — continuing resolution",
                filename,
                repr(excel_title) if has_title else "missing",
                repr(excel_author) if has_author else "missing",
            )
        else:
            excel_title = ""
            excel_author = ""
            article_url = None
            has_title = False
            has_author = False
            logger.info("No Excel match for '%s' — trying website scraping", filename)

        # ------------------------------------------------------------------
        # Step 2: Website scraping (using article_url from Excel data)
        # ------------------------------------------------------------------
        scraped_title = None
        scraped_author = None

        if article_url:
            try:
                scraped = await self._website_scraper.scrape_article(article_url)
                if scraped is not None:
                    scraped_title = scraped.title.strip() if scraped.title else None
                    scraped_author = scraped.author.strip() if scraped.author else None
                    logger.info(
                        "Website scrape for '%s' (%s): title=%s, author=%s",
                        filename,
                        article_url,
                        repr(scraped_title),
                        repr(scraped_author),
                    )
                else:
                    logger.info(
                        "Website scrape returned None for '%s' (%s)",
                        filename,
                        article_url,
                    )
            except Exception as exc:
                logger.warning(
                    "Website scraping failed for '%s' (%s): %s",
                    filename,
                    article_url,
                    exc,
                )
        else:
            logger.info(
                "No article URL available for '%s' — skipping website scraping",
                filename,
            )

        # Merge: prefer Excel values, fill gaps from website
        resolved_title = excel_title if has_title else (scraped_title or "")
        resolved_author = excel_author if has_author else (scraped_author or "")

        # Determine source so far
        if resolved_title and resolved_author:
            # We have both — figure out the primary source
            if has_title and has_author:
                source = "excel"
            elif has_title or has_author:
                # Mixed: some from Excel, some from website
                source = "website" if (scraped_title or scraped_author) else "excel"
            else:
                source = "website"

            authors = self._excel_lookup.parse_authors(resolved_author)
            if not authors:
                authors = [resolved_author] if resolved_author else ["Unknown Author"]

            logger.info(
                "Resolved '%s' from %s: title='%s', authors=%s",
                filename,
                source,
                resolved_title,
                authors,
            )
            return ResolvedMetadata(
                title=resolved_title,
                authors=authors,
                source=source,
                article_url=article_url,
            )

        # ------------------------------------------------------------------
        # Step 3: PDF extraction via AuthorExtractor
        # ------------------------------------------------------------------
        pdf_author = None
        if pdf_path:
            try:
                pdf_author = self._author_extractor.extract_author(pdf_path)
                if pdf_author:
                    pdf_author = pdf_author.strip()
                    logger.info(
                        "PDF extraction for '%s': author='%s'",
                        filename,
                        pdf_author,
                    )
                else:
                    logger.info(
                        "PDF extraction returned no author for '%s'",
                        filename,
                    )
            except Exception as exc:
                logger.warning(
                    "PDF author extraction failed for '%s': %s",
                    filename,
                    exc,
                )

        # Merge PDF results with whatever we have so far
        final_title = resolved_title if resolved_title else None
        final_author = resolved_author if resolved_author else pdf_author

        if final_title or final_author:
            source = "pdf" if (not resolved_title and not resolved_author) else (
                "excel" if (has_title or has_author) else "website"
            )
            # If only the PDF contributed the author and nothing else, source is "pdf"
            if not resolved_title and not resolved_author and pdf_author:
                source = "pdf"

            title = final_title if final_title else default_title
            if final_author:
                authors = self._excel_lookup.parse_authors(final_author)
                if not authors:
                    authors = [final_author]
            else:
                authors = ["Unknown Author"]

            logger.info(
                "Resolved '%s' from %s: title='%s', authors=%s",
                filename,
                source,
                title,
                authors,
            )
            return ResolvedMetadata(
                title=title,
                authors=authors,
                source=source,
                article_url=article_url,
            )

        # ------------------------------------------------------------------
        # Step 4: Defaults
        # ------------------------------------------------------------------
        logger.warning(
            "All metadata sources failed for '%s' — using defaults",
            filename,
        )
        return ResolvedMetadata(
            title=default_title,
            authors=["Unknown Author"],
            source="default",
            article_url=article_url,
        )
