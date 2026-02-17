from typing import List, Dict, Optional, Set
from datetime import datetime
import re
import sys
import os
import time
from urllib.parse import urljoin

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scrapers.base_scraper import BaseScraper

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class HRZZScraper(BaseScraper):
    """Scraper for Hrvatska zaklada za znanost (HRZZ) website"""
    
    def __init__(self):
        super().__init__(
            source_name="HRZZ",
            base_url="https://hrzz.hr"
        )
        self.open_calls_url = f"{self.base_url}/prijava/otvoreni-natjecaji/"
    
    def scrape(self) -> List[Dict]:
        """Scrape otvoreni natječaji from HRZZ website using Selenium for accordion clicking."""
        self.log("Starting scrape with Selenium accordion expansion...")
        
        if not SELENIUM_AVAILABLE:
            self.log("ERROR: Selenium not available. Install with: pip install selenium")
            return []
        
        natjecaji: List[Dict] = []
        seen_keys: Set[str] = set()
        
        driver = self._create_driver()
        if not driver:
            self.log("Failed to create Selenium driver")
            return natjecaji
        
        try:
            self.log(f"Loading page: {self.open_calls_url}")
            driver.get(self.open_calls_url)
            
            # Wait for accordion to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.ekit-accordion--toggler"))
            )
            
            # Find all accordion togglers
            togglers = driver.find_elements(By.CSS_SELECTOR, "a.ekit-accordion--toggler")
            self.log(f"Found {len(togglers)} accordion items")
            
            for idx, toggler in enumerate(togglers):
                try:
                    # Get title text before clicking
                    title_elem = toggler.find_element(By.CSS_SELECTOR, "span.ekit-accordion-title")
                    title_text = self.clean_text(title_elem.text)
                    
                    if not self._is_call_code(title_text):
                        self.log(f"Skipping non-call-code: {title_text}")
                        continue
                    
                    # Check if already expanded
                    is_expanded = toggler.get_attribute("aria-expanded") == "true"
                    
                    if not is_expanded:
                        # Scroll into view and click
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", toggler)
                        time.sleep(0.3)  # Small delay for smooth scrolling
                        toggler.click()
                        time.sleep(0.5)  # Wait for accordion to expand
                    
                    # Now extract data from expanded accordion
                    natjecaj_data = self._parse_accordion_item(driver, toggler, title_text)
                    
                    if natjecaj_data:
                        dedupe_key = (natjecaj_data.get("url") or "") + "|" + natjecaj_data.get("naziv", "")
                        if dedupe_key not in seen_keys:
                            seen_keys.add(dedupe_key)
                            natjecaji.append(natjecaj_data)
                            self.log(f"[{idx+1}/{len(togglers)}] Found: {natjecaj_data['naziv']}")
                    
                except Exception as e:
                    self.log(f"Error processing accordion item {idx+1}: {e}")
                    continue
            
        except TimeoutException:
            self.log("Timeout waiting for accordion elements to load")
        except Exception as e:
            self.log(f"Error during scraping: {e}")
        finally:
            driver.quit()
        
        self.log(f"Scraping completed. Found {len(natjecaji)} natjecaji.")
        return natjecaji
    
    def _create_driver(self):
        """Create headless Chrome driver."""
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument(f"user-agent={self.session.headers.get('User-Agent', 'Mozilla/5.0')}")
            
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            self.log(f"Failed to create driver: {e}")
            return None
    
    def _parse_accordion_item(self, driver, toggler, title_text: str) -> Optional[Dict]:
        """Parse data from an expanded accordion item."""
        try:
            # Find the content container using data-target attribute
            data_target = toggler.get_attribute("data-target")
            if not data_target:
                return None
            
            # Remove leading # from ID selector
            content_id = data_target.lstrip("#")
            content_elem = driver.find_element(By.ID, content_id)
            
            # Extract raw text
            raw_text = self.clean_text(content_elem.text)
            if not raw_text:
                return None
            
            opis = raw_text[:2500]
            
            # Extract links using BeautifulSoup for easier parsing
            soup = self.parse_html(content_elem.get_attribute("innerHTML"))
            call_url = self._extract_call_url(soup)
            
            return {
                "naziv": title_text,
                "url": call_url,
                "opis": opis,
                "kategorija": "Znanstveno istraživanje",
                "podrucje_istrazivanja": "Multidisciplinarno",
                "datum_objave": self._extract_publish_date(raw_text),
                "rok_prijave": self._extract_deadline(raw_text),
                "status": "active",
                "izvor": self.source_name,
            }
        except NoSuchElementException:
            self.log(f"Content element not found for: {title_text}")
            return None
        except Exception as e:
            self.log(f"Error parsing accordion content: {e}")
            return None


    def _is_call_code(self, value: str) -> bool:
        """Check if string matches HRZZ call code pattern (e.g., PDIP-2026, IP-2026, UIP-2026, IPS-2026-02)."""
        return bool(re.match(r"^[A-ZŠĐČĆŽ]{2,}(?:-[A-ZŠĐČĆŽ]{2,})?-\d{4}(?:-\d{2})?$", value))

    def _extract_call_url(self, container) -> str:
        """Extract the most relevant URL from accordion content."""
        preferred = []
        fallback = []

        for link in container.select("a[href]"):
            href = link.get("href", "")
            text = self.clean_text(link.get_text(" ", strip=True)).lower()
            full_url = urljoin(self.base_url, href)

            if not href:
                continue

            if "tekst natječaja" in text or "call for proposals" in text:
                preferred.append(full_url)
            else:
                fallback.append(full_url)

        if preferred:
            return preferred[0]
        if fallback:
            return fallback[0]
        return self.open_calls_url

    def _extract_publish_date(self, text: str) -> Optional[datetime]:
        match = re.search(r"datum\s+raspisivanja[^:]*:\s*([^\.]+\.)", text, flags=re.IGNORECASE)
        if not match:
            return None
        return self._parse_hr_date(match.group(1))

    def _extract_deadline(self, text: str) -> Optional[datetime]:
        match = re.search(r"rok\s+za\s+prijavu[^:]*:\s*([^\.]+\.)", text, flags=re.IGNORECASE)
        if not match:
            return None
        return self._parse_hr_date(match.group(1))

    def _parse_hr_date(self, date_text: str) -> Optional[datetime]:
        months = {
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
            "studenog": 11,
            "prosinca": 12,
        }

        normalized = self.clean_text(date_text.lower())
        match = re.search(r"(\d{1,2})\.\s*([a-zčćđšž]+)\s*(\d{4})\.", normalized)
        if not match:
            return None

        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        month = months.get(month_name)
        if not month:
            return None

        time_match = re.search(r"(\d{1,2})[:\.](\d{2})", normalized)
        hour = int(time_match.group(1)) if time_match else 0
        minute = int(time_match.group(2)) if time_match else 0

        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            return None


if __name__ == "__main__":
    scraper = HRZZScraper()
    results = scraper.scrape()
    
    print(f"\n{'='*50}")
    print(f"RESULTS: {len(results)} natjecaji found")
    print(f"{'='*50}\n")
    
    for i, natjecaj in enumerate(results, 1):
        print(f"{i}. {natjecaj.get('naziv', 'N/A')}")
