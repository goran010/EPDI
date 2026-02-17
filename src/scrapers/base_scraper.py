from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
import requests
from typing import List, Dict, Optional
from datetime import datetime
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.settings import settings


class BaseScraper(ABC):
    """Base class for all web scrapers"""
    
    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.headers = {
            'User-Agent': settings.user_agent
        }
        self.session = requests.Session()
    
    def fetch_page(self, url: str, timeout: int = 30) -> Optional[str]:
        """Fetch HTML content from URL"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html, 'html.parser')
    
    @abstractmethod
    def scrape(self) -> List[Dict]:
        """
        Main scraping method - must be implemented by subclasses
        Returns list of dictionaries with natjecaj data
        """
        pass
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return " ".join(text.split()).strip()
    
    def parse_date(self, date_str: str, format: str = "%d.%m.%Y") -> Optional[datetime]:
        """Parse date string to datetime"""
        try:
            return datetime.strptime(date_str.strip(), format)
        except (ValueError, AttributeError):
            return None
    
    def parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse monetary amount from string"""
        try:
            # Remove currency symbols, spaces, dots (thousands separator)
            cleaned = amount_str.replace('EUR', '').replace('€', '').replace('.', '').replace(',', '.').strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def wait(self, seconds: float = 1.0):
        """Wait between requests to be polite"""
        time.sleep(seconds)
    
    def log(self, message: str):
        """Simple logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{self.source_name}] {message}")
