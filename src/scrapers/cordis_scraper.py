"""
CORDIS (EU Research Portal) scraper using their public JSON search API.

CORDIS Search API: https://cordis.europa.eu/search?q=...&p=PAGE&num=NUM&format=json
Returns mixed content types; this scraper focuses on 'programme' items which represent
EU funding calls (Horizon Europe, ERC, MSCA, etc.).
"""
from typing import List, Dict, Optional, Set
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scrapers.base_scraper import BaseScraper


class CORDISScraper(BaseScraper):
    """Scraper for CORDIS EU research portal - extracts open funding calls."""

    SEARCH_URL = "https://cordis.europa.eu/search"
    PROGRAMME_BASE_URL = "https://cordis.europa.eu/programme/id"

    # Queries that reliably return 'programme' type hits (funding calls)
    QUERIES = [
        "horizon europe funding call 2025 2026",
        "ERC grant call horizon 2025 2026",
        "MSCA fellowship call 2025 2026",
        "horizon research innovation open call",
    ]

    # How many results to request per API page
    PAGE_SIZE = 100

    # Maximum number of pages per query to avoid excessive requests
    MAX_PAGES = 5

    def __init__(self):
        super().__init__(
            source_name="CORDIS",
            base_url="https://cordis.europa.eu",
        )
        self.headers["Accept"] = "application/json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape(self) -> List[Dict]:
        """Run all configured queries and return deduplicated programme items."""
        self.log("Starting CORDIS scrape via JSON API...")
        natjecaji: List[Dict] = []
        seen_ids: Set[str] = set()

        for query in self.QUERIES:
            self.log(f"Query: {query!r}")
            results = self._scrape_query(query, seen_ids)
            natjecaji.extend(results)
            self.log(f"  → {len(results)} new programmes found")
            self.wait(1.0)

        self.log(f"CORDIS scraping complete. Total: {len(natjecaji)} programmes.")
        return natjecaji

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scrape_query(self, query: str, seen_ids: Set[str]) -> List[Dict]:
        """Paginate through a single query and collect programme-type items."""
        results: List[Dict] = []
        page = 1

        while page <= self.MAX_PAGES:
            data = self._fetch_search_page(query, page)
            if not data:
                break

            header = data.get("result", {}).get("header", {})
            total_hits = int(header.get("totalHits", 0) or 0)

            if total_hits == 0:
                self.log(f"  No results for page {page}")
                break

            hits_raw = data.get("hits", {})
            hits = hits_raw.get("hit", [])
            if not isinstance(hits, list):
                hits = [hits] if hits else []

            if not hits:
                break

            for hit in hits:
                programme = hit.get("programme")
                if not isinstance(programme, dict):
                    continue  # skip project / result content types

                programme_id = programme.get("id", "")
                if not programme_id or programme_id in seen_ids:
                    continue

                seen_ids.add(programme_id)
                parsed = self._parse_programme(programme)
                if parsed:
                    results.append(parsed)

            # Check if there are more pages
            fetched_so_far = (page - 1) * self.PAGE_SIZE + len(hits)
            if fetched_so_far >= total_hits:
                break

            page += 1
            self.wait(0.5)

        return results

    def _fetch_search_page(self, query: str, page: int) -> Optional[dict]:
        """Fetch one page of JSON search results from CORDIS."""
        params = {
            "q": query,
            "p": page,
            "num": self.PAGE_SIZE,
            "srt": "Relevance:decreasing",
            "format": "json",
        }
        try:
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            errors = data.get("result", {}).get("header", {}).get("errors")
            if errors:
                self.log(f"  API error for query {query!r}: {errors}")
                return None
            return data
        except Exception as e:
            self.log(f"  Error fetching page {page} for query {query!r}: {e}")
            return None

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_programme(self, programme: dict) -> Optional[Dict]:
        """Convert a raw CORDIS programme dict into our standard natjecaj format."""
        programme_id = programme.get("id", "")
        title = self.clean_text(programme.get("title", ""))
        if not title:
            return None

        code = programme.get("code", programme_id)
        framework = programme.get("frameworkProgramme", "")

        # Build canonical URL
        url = f"{self.PROGRAMME_BASE_URL}/{programme_id}"

        # Description: prefer objective (HTML), fall back to teaser
        objective_html = programme.get("objective", "") or ""
        teaser = programme.get("teaser", "") or ""
        opis_raw = self._strip_html(objective_html) if objective_html.strip() else teaser
        opis = self.clean_text(opis_raw)[:3000]

        # Determine category from framework / code
        kategorija = self._resolve_kategorija(framework, code, title)

        # Try to extract deadline from description text
        rok_prijave = self._extract_deadline(opis_raw)

        # Try to extract funding amount from description text
        iznos = self._extract_amount(opis_raw)

        return {
            "naziv": title,
            "url": url,
            "opis": opis,
            "kategorija": kategorija,
            "podrucje_istrazivanja": self._resolve_research_area(title + " " + opis[:500]),
            "iznos_financiranja": iznos,
            "rok_prijave": rok_prijave,
            "datum_objave": None,
            "status": "active",
            "izvor": self.source_name,
        }

    # ------------------------------------------------------------------
    # Field resolvers
    # ------------------------------------------------------------------

    def _resolve_kategorija(self, framework: str, code: str, title: str) -> str:
        fw = framework.upper()
        combined = (code + " " + title).upper()
        if "ERC" in combined or "ERC" in fw:
            return "ERC Grant"
        if "MSCA" in combined or "MARIE" in combined:
            return "MSCA Fellowship"
        if "EURATOM" in combined:
            return "EURATOM"
        if "HORIZON" in fw or "HORIZON" in combined:
            return "Horizon Europe"
        if framework:
            return framework
        return "EU Funding"

    def _resolve_research_area(self, text: str) -> str:
        text_lower = text.lower()
        area_keywords = {
            "ICT": ["ict", "digital", "artificial intelligence", "ai ", "software", "cyber", "computing", "data science"],
            "Medicina": ["health", "medical", "medicine", "biomedical", "clinical", "pharmaceutical", "cancer"],
            "Energetika": ["energy", "fusion", "nuclear", "renewable", "solar", "wind", "battery"],
            "Okoliš": ["environment", "climate", "ecology", "sustainable", "green", "biodiversity"],
            "Inženjerstvo": ["engineering", "materials", "manufacturing", "robotics", "nanotechnology"],
            "Društvene znanosti": ["social", "society", "education", "humanities", "economics", "governance"],
        }
        for area, keywords in area_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return area
        return "Multidisciplinarno"

    def _extract_deadline(self, text: str) -> Optional[datetime]:
        """Try to extract a deadline date from description text."""
        # Patterns like: "deadline: 12 March 2026", "by 2026-06-30", "closing date 30/09/2026"
        patterns = [
            r"deadline[:\s]+(\d{1,2}[\s\-/]\w+[\s\-/]\d{4})",
            r"closing date[:\s]+(\d{1,2}[\s\-/]\w+[\s\-/]\d{4})",
            r"submission deadline[:\s]+(\d{1,2}[\s\-/]\w+[\s\-/]\d{4})",
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date = self._parse_flexible_date(match.group(1))
                if date and date > datetime.now():
                    return date
        return None

    def _parse_flexible_date(self, date_str: str) -> Optional[datetime]:
        """Try multiple date formats."""
        date_str = date_str.strip()
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%d-%m-%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        """Try to extract the maximum funding amount in EUR from description text."""
        # Look for patterns like "EUR 2.5 million", "up to €1 500 000", "2,500,000 EUR"
        patterns = [
            r"(?:up\s+to\s+)?(?:EUR|€)\s*([\d\s,.]+)\s*(million|billion|m\b|bn\b)?",
            r"([\d\s,.]+)\s*(million|billion)?\s*(?:EUR|€|euros?)",
            r"total\s+budget\s+of\s+(?:EUR\s*)?([\d\s,.]+)\s*(million|billion)?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(" ", "").replace(",", "")
                multiplier_str = (match.group(2) or "").lower()
                try:
                    amount = float(amount_str)
                    if "billion" in multiplier_str or "bn" in multiplier_str:
                        amount *= 1_000_000_000
                    elif "million" in multiplier_str or "m" in multiplier_str:
                        amount *= 1_000_000
                    if amount > 0:
                        return amount
                except (ValueError, IndexError):
                    continue
        return None

    @staticmethod
    def _strip_html(html: str) -> str:
        """Strip HTML tags from text."""
        if not html:
            return ""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Normalise whitespace
        return " ".join(text.split())


if __name__ == "__main__":
    scraper = CORDISScraper()
    results = scraper.scrape()

    print(f"\n{'='*60}")
    print(f"CORDIS RESULTS: {len(results)} funding programmes found")
    print(f"{'='*60}\n")

    for i, item in enumerate(results[:10], 1):
        print(f"{i}. {item.get('naziv', 'N/A')}")
        print(f"   Kategorija:  {item.get('kategorija', 'N/A')}")
        print(f"   Područje:    {item.get('podrucje_istrazivanja', 'N/A')}")
        print(f"   Rok prijave: {item.get('rok_prijave', 'N/A')}")
        print(f"   Iznos:       {item.get('iznos_financiranja', 'N/A')}")
        print(f"   URL:         {item.get('url', 'N/A')}")
        print()
