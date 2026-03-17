from typing import List, Dict, Optional, Set
from datetime import datetime
import re
import sys
import os
from urllib.parse import urljoin

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scrapers.base_scraper import BaseScraper


class MINGOScraper(BaseScraper):
    """Scraper for Ministry of Economy public calls (MINGO)."""

    OPEN_CALLS_URL = (
        "https://mingo.gov.hr/javni-pozivi-i-natjecaji-7371/"
        "javni-pozivi-i-natjecaji-ministarstva/"
        "otvoreni-javni-pozivi-i-natjecaji/7390"
    )

    MONTH_MAP = {
        "siječnja": 1,
        "sijecnja": 1,
        "veljače": 2,
        "veljace": 2,
        "ožujka": 3,
        "ozujka": 3,
        "travnja": 4,
        "svibnja": 5,
        "lipnja": 6,
        "srpnja": 7,
        "kolovoza": 8,
        "rujna": 9,
        "listopada": 10,
        "studenoga": 11,
        "studenog": 11,
        "prosinca": 12,
    }

    def __init__(self):
        super().__init__(
            source_name="MINGO",
            base_url="https://mingo.gov.hr",
        )

    def scrape(self) -> List[Dict]:
        """Scrape MINGO open calls from FAQ-like content blocks."""
        self.log("Starting scrape...")
        html = self.fetch_page(self.OPEN_CALLS_URL)
        if not html:
            return []

        soup = self.parse_html(html)
        container = soup.select_one("#faqContainer")
        if not container:
            self.log("FAQ container not found.")
            return []

        questions = container.select("div.faqPitanje")
        answers = container.select("div.faqOdgovor")

        if not questions:
            self.log("No call entries found.")
            return []

        entries: List[Dict] = []
        seen_keys: Set[str] = set()

        for idx, question in enumerate(questions):
            answer = answers[idx] if idx < len(answers) else None
            parsed = self._parse_entry(question, answer)
            if not parsed:
                continue

            dedupe_key = f"{parsed.get('naziv', '')}|{parsed.get('url', '')}"
            if dedupe_key in seen_keys:
                continue

            seen_keys.add(dedupe_key)
            entries.append(parsed)

        self.log(f"Scraping completed. Found {len(entries)} natjecaji.")
        return entries

    def _parse_entry(self, question, answer) -> Optional[Dict]:
        heading_raw = self.clean_text(question.get_text(" ", strip=True))
        if not heading_raw:
            return None

        datum_objave = self._extract_publish_date_from_heading(heading_raw)
        naziv = self._strip_heading_date(heading_raw)
        if not naziv:
            naziv = heading_raw

        opis = ""
        dokumenti_url = None
        if answer:
            opis_block = answer.select_one(".opis")
            if opis_block:
                opis = self.clean_text(opis_block.get_text(" ", strip=True))
            else:
                opis = self.clean_text(answer.get_text(" ", strip=True))

            first_link = answer.select_one("a[href]")
            if first_link and first_link.get("href"):
                dokumenti_url = urljoin(self.base_url, first_link.get("href"))

        if not opis:
            opis = naziv

        rok_prijave = self._extract_deadline(opis)
        iznos = self._extract_amount(opis)

        return {
            "naziv": naziv[:500],
            "url": dokumenti_url or self.OPEN_CALLS_URL,
            "opis": opis[:3000],
            "kategorija": self._resolve_kategorija(naziv + " " + opis[:500]),
            "podrucje_istrazivanja": self._resolve_podrucje(naziv + " " + opis[:500]),
            "iznos_financiranja": iznos,
            "rok_prijave": rok_prijave,
            "datum_objave": datum_objave,
            "dokumenti_url": dokumenti_url,
            "status": "active",
            "izvor": self.source_name,
        }

    def _extract_publish_date_from_heading(self, heading: str) -> Optional[datetime]:
        # 03.03.2026. ... or 31. 3. 2025. ...
        numeric_match = re.match(r"\s*(\d{1,2})\.?\s*(?:\.\s*)?(\d{1,2})\.?\s*(?:\.\s*)?(\d{4})\.?", heading)
        if numeric_match:
            day = int(numeric_match.group(1))
            month = int(numeric_match.group(2))
            year = int(numeric_match.group(3))
            try:
                return datetime(year, month, day)
            except ValueError:
                return None

        text_match = re.match(r"\s*(\d{1,2})\.\s*([a-zA-ZčćđšžČĆĐŠŽ]+)\s*(\d{4})\.?", heading)
        if text_match:
            day = int(text_match.group(1))
            month_name = text_match.group(2).lower()
            month = self.MONTH_MAP.get(month_name)
            year = int(text_match.group(3))
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    return None

        return None

    def _strip_heading_date(self, heading: str) -> str:
        cleaned = re.sub(
            r"^\s*(\d{1,2}\s*\.?\s*(?:\d{1,2}|[a-zA-ZčćđšžČĆĐŠŽ]+)\s*\.?\s*\d{4}\.?)\s*[-–]?\s*",
            "",
            heading,
        )
        return self.clean_text(cleaned)

    def _extract_deadline(self, text: str) -> Optional[datetime]:
        if not text:
            return None

        lowered = text.lower()

        keyword_patterns = [
            r"rok[^\n\r]{0,120}?\bdo\b\s*([^\.\n\r]+)",
            r"prijave[^\n\r]{0,120}?\bdo\b\s*([^\.\n\r]+)",
            r"zaprimaju[^\n\r]{0,120}?\bdo\b\s*([^\.\n\r]+)",
            r"podnose[^\n\r]{0,120}?\bdo\b\s*([^\.\n\r]+)",
            r"otvoren[^\n\r]{0,120}?\bdo\b\s*([^\.\n\r]+)",
        ]

        for pattern in keyword_patterns:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                date_in_segment = self._parse_first_date(match.group(1))
                if date_in_segment:
                    return date_in_segment

        return None

    def _parse_first_date(self, text: str) -> Optional[datetime]:
        numeric = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\.?", text)
        if numeric:
            day = int(numeric.group(1))
            month = int(numeric.group(2))
            year = int(numeric.group(3))
            try:
                return datetime(year, month, day)
            except ValueError:
                return None

        textual = re.search(r"(\d{1,2})\.\s*([a-zA-ZčćđšžČĆĐŠŽ]+)\s*(\d{4})\.?", text)
        if textual:
            day = int(textual.group(1))
            month_name = textual.group(2).lower()
            month = self.MONTH_MAP.get(month_name)
            year = int(textual.group(3))
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    return None

        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        if not text:
            return None

        matches = re.finditer(
            r"(\d[\d\.\s]*,\d{2}|\d[\d\.\s]*)(?:\s*)(milijuna|milijun|tisuća|tisuca)?\s*(?:eur|eura|€)",
            text,
            flags=re.IGNORECASE,
        )

        found_values: List[float] = []
        for match in matches:
            raw_amount = match.group(1)
            multiplier = (match.group(2) or "").lower()

            normalized = raw_amount.replace(" ", "").replace(".", "").replace(",", ".")
            try:
                value = float(normalized)
            except ValueError:
                continue

            if "milijun" in multiplier:
                value *= 1_000_000
            elif "tisu" in multiplier:
                value *= 1_000

            if value > 0:
                found_values.append(value)

        if not found_values:
            return None
        return max(found_values)

    def _resolve_kategorija(self, text: str) -> str:
        lowered = text.lower()
        if "stipendir" in lowered:
            return "Stipendije"
        if "poduzet" in lowered or "obrt" in lowered or "zadrug" in lowered:
            return "Potpora poduzetništvu"
        if "npoo" in lowered or "eu" in lowered:
            return "EU programi"
        if "potroša" in lowered or "potrosa" in lowered:
            return "Zaštita potrošača"
        return "Javni poziv"

    def _resolve_podrucje(self, text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ["digital", "ict", "kiberneti", "ai", "tehnolog"]):
            return "ICT"
        if any(token in lowered for token in ["energ", "klima", "emis", "održiv", "odrziv"]):
            return "Energetika"
        if any(token in lowered for token in ["obraz", "učenik", "ucenik", "nastavnik", "mentor"]):
            return "Obrazovanje"
        return "Multidisciplinarno"


if __name__ == "__main__":
    scraper = MINGOScraper()
    results = scraper.scrape()
    print(f"Found {len(results)} entries")
    for idx, item in enumerate(results[:10], 1):
        print(f"{idx}. {item.get('naziv')}")