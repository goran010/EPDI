from typing import List, Dict, Optional, Set
from datetime import datetime
import re
import sys
import os
from urllib.parse import urljoin

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scrapers.base_scraper import BaseScraper


class HAMAGBICROScraper(BaseScraper):
    """Scraper for HAMAG-BICRO website"""
    
    def __init__(self):
        super().__init__(
            source_name="HAMAG-BICRO",
            base_url="https://hamagbicro.hr"
        )
        self.listing_url = f"{self.base_url}/natjecaji/"
        self.wp_api_base = f"{self.base_url}/wp-json/wp/v2"
    
    def scrape(self) -> List[Dict]:
        """Scrape natječaji from HAMAG-BICRO website."""
        self.log("Starting scrape...")
        natjecaji = self._scrape_via_wp_api()
        if natjecaji:
            self.log(f"Scraping completed via WP API. Found {len(natjecaji)} natjecaji.")
            return natjecaji

        self.log("WP API scrape returned no data, falling back to HTML parsing.")
        natjecaji = self._scrape_via_html()
        self.log(f"Scraping completed via HTML fallback. Found {len(natjecaji)} natjecaji.")
        return natjecaji

    def _fetch_json(self, url: str, timeout: int = 30) -> Optional[dict]:
        try:
            response = self.session.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return response.json(), response.headers
        except Exception as e:
            self.log(f"Error fetching JSON from {url}: {e}")
            return None

    def _get_category_id(self, category_slug: str) -> Optional[int]:
        categories_url = f"{self.wp_api_base}/categories?slug={category_slug}"
        result = self._fetch_json(categories_url)
        if not result:
            return None

        categories, _ = result
        if not categories:
            return None
        return categories[0].get("id")

    def _scrape_via_wp_api(self) -> List[Dict]:
        natjecaji: List[Dict] = []
        seen_urls: Set[str] = set()

        category_id = self._get_category_id("natjecaji")
        if not category_id:
            self.log("Could not resolve 'natjecaji' category id from WP API.")
            return natjecaji

        page = 1
        total_pages = 1

        while page <= total_pages:
            posts_url = (
                f"{self.wp_api_base}/posts"
                f"?categories={category_id}&per_page=100&page={page}&_embed=1"
            )
            result = self._fetch_json(posts_url)
            if not result:
                break

            posts, headers = result
            try:
                total_pages = int(headers.get("X-WP-TotalPages", "1"))
            except ValueError:
                total_pages = 1

            for post in posts:
                natjecaj = self._parse_wp_post(post)
                if not natjecaj:
                    continue

                post_url = natjecaj.get("url")
                if post_url and post_url in seen_urls:
                    continue

                if post_url:
                    seen_urls.add(post_url)

                natjecaji.append(natjecaj)

            page += 1
            self.wait(0.2)

        return natjecaji

    def _parse_wp_post(self, post: dict) -> Optional[Dict]:
        title_html = post.get("title", {}).get("rendered", "")
        title = self.clean_text(self._strip_html(title_html))
        if not title:
            return None

        post_url = post.get("link")
        if post_url:
            post_url = urljoin(self.base_url, post_url)

        excerpt_html = post.get("excerpt", {}).get("rendered", "")
        content_html = post.get("content", {}).get("rendered", "")
        opis = self.clean_text(self._strip_html(excerpt_html))
        if not opis:
            opis = self.clean_text(self._strip_html(content_html))[:1200]

        datum_objave = self._parse_iso_datetime(post.get("date"))

        kategorije = []
        embedded_terms = post.get("_embedded", {}).get("wp:term", [])
        for term_group in embedded_terms:
            for term in term_group:
                if term.get("taxonomy") == "category":
                    name = self.clean_text(term.get("name", ""))
                    if name:
                        kategorije.append(name)

        natjecaj = {
            "naziv": title,
            "url": post_url,
            "opis": opis,
            "kategorija": self._resolve_kategorija(kategorije),
            "podrucje_istrazivanja": "Opće",
            "datum_objave": datum_objave,
            "status": self._resolve_status(kategorije),
        }

        return natjecaj

    def _scrape_via_html(self) -> List[Dict]:
        natjecaji: List[Dict] = []
        seen_urls: Set[str] = set()

        max_pages = self._discover_max_pages(self.listing_url)

        for page in range(1, max_pages + 1):
            page_url = self.listing_url if page == 1 else f"{self.listing_url}page/{page}/"
            html = self.fetch_page(page_url)
            if not html:
                continue

            soup = self.parse_html(html)
            cards = soup.select("div.post-wrapper article.news-v1")

            for card in cards:
                natjecaj = self._parse_html_card(card)
                if not natjecaj:
                    continue

                post_url = natjecaj.get("url")
                if post_url and post_url in seen_urls:
                    continue

                if post_url:
                    seen_urls.add(post_url)

                natjecaji.append(natjecaj)

            self.wait(0.2)

        return natjecaji

    def _discover_max_pages(self, first_page_url: str) -> int:
        html = self.fetch_page(first_page_url)
        if not html:
            return 1

        soup = self.parse_html(html)
        page_links = soup.select("section.ff-pagination a[data-page-id]")
        max_page = 1

        for link in page_links:
            page_id = link.get("data-page-id")
            if page_id and page_id.isdigit():
                max_page = max(max_page, int(page_id))

        return max_page

    def _parse_html_card(self, card) -> Optional[Dict]:
        title_link = card.select_one("h3.news-v1-heading-title a")
        if not title_link:
            return None

        title = self.clean_text(title_link.get_text())
        post_url = urljoin(self.base_url, title_link.get("href", ""))

        category_items = card.select(".ffb-categories-1-1 .ff-term-90, .ffb-categories-1-1 .ff-term-94, .ffb-categories-1-1 span[class^='ff-term-']")
        kategorije = [self.clean_text(item.get_text()) for item in category_items if self.clean_text(item.get_text())]

        date_text_elem = card.select_one(".ffb-date-5-1")
        date_text = self.clean_text(date_text_elem.get_text()) if date_text_elem else ""
        datum_objave = self._parse_hr_date(date_text)

        return {
            "naziv": title,
            "url": post_url,
            "opis": "",
            "kategorija": self._resolve_kategorija(kategorije),
            "podrucje_istrazivanja": "Opće",
            "datum_objave": datum_objave,
            "status": self._resolve_status(kategorije),
        }

    def _resolve_kategorija(self, categories: List[str]) -> str:
        if not categories:
            return "Natječaji"

        filtered = [c for c in categories if c.lower() not in {"natječaji", "vijesti i najave", "vijesti i najave (naslovna)", "otvoreni natječaji"}]
        if filtered:
            return filtered[0]
        return categories[0]

    def _resolve_status(self, categories: List[str]) -> str:
        normalized = {c.lower() for c in categories}
        if "otvoreni natječaji" in normalized:
            return "active"
        return "active"

    def _strip_html(self, html: str) -> str:
        if not html:
            return ""
        return re.sub(r"<[^>]+>", " ", html)

    def _parse_iso_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _parse_hr_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None

        month_map = {
            "siječnja": 1,
            "veljače": 2,
            "ožujka": 3,
            "travnja": 4,
            "svibnja": 5,
            "lipnja": 6,
            "srpnja": 7,
            "kolovoza": 8,
            "rujna": 9,
            "listopada": 10,
            "studenoga": 11,
            "prosinca": 12,
        }

        match = re.search(r"(\d{1,2})\.\s*([a-zčćđšž]+)\s*(\d{4})\.", date_str.lower())
        if not match:
            return None

        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        month = month_map.get(month_name)

        if not month:
            return None

        try:
            return datetime(year, month, day)
        except ValueError:
            return None


# Test scraper
if __name__ == "__main__":
    scraper = HAMAGBICROScraper()
    results = scraper.scrape()
    
    print(f"\n{'='*50}")
    print(f"RESULTS: {len(results)} natjecaji found")
    print(f"{'='*50}\n")
    
    for i, natjecaj in enumerate(results, 1):
        print(f"{i}. {natjecaj.get('naziv', 'N/A')}")
        print(f"   URL: {natjecaj.get('url', 'N/A')}")
        print(f"   Rok: {natjecaj.get('rok_prijave', 'N/A')}")
        print()
