from typing import List, Dict
from datetime import datetime
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scrapers.hamag_scraper import HAMAGBICROScraper
from src.scrapers.hrzz_scraper import HRZZScraper
from src.database.database import get_db_session
from src.database.crud import (
    get_or_create_izdavatelj,
    create_natjecaj,
    create_scraping_log,
    get_all_natjecaji
)
from src.database.models import Natjecaj


class ScraperManager:
    """Manages all scrapers and coordinates scraping operations"""
    
    def __init__(self):
        self.scrapers = {
            'HAMAG-BICRO': HAMAGBICROScraper(),
            'HRZZ': HRZZScraper(),
        }
    
    def run_all_scrapers(self) -> Dict:
        """Run all scrapers and save results to database"""
        print("\n" + "="*60)
        print(" STARTING SCRAPING PROCESS")
        print("="*60 + "\n")
        
        overall_stats = {
            'total_scraped': 0,
            'total_saved': 0,
            'total_updated': 0,
            'errors': 0,
            'sources': []
        }
        
        for source_name, scraper in self.scrapers.items():
            print(f"\n Processing source: {source_name}")
            print("-" * 60)
            
            start_time = time.time()
            
            try:
                # Scrape data
                natjecaji = scraper.scrape()
                
                # Save to database
                stats = self.save_to_database(source_name, natjecaji)
                
                execution_time = time.time() - start_time
                
                # Update overall stats
                overall_stats['total_scraped'] += len(natjecaji)
                overall_stats['total_saved'] += stats['added']
                overall_stats['total_updated'] += stats['updated']
                
                # Log scraping activity
                self.log_scraping_activity(
                    source_name,
                    status="success",
                    natjecaji_pronadeni=len(natjecaji),
                    natjecaji_dodani=stats['added'],
                    natjecaji_azurirani=stats['updated'],
                    execution_time=execution_time
                )
                
                overall_stats['sources'].append({
                    'name': source_name,
                    'status': 'success',
                    'count': len(natjecaji),
                    'time': execution_time
                })
                
                print(f"  {source_name}: {len(natjecaji)} natjecaji scraped in {execution_time:.2f}s")
                
            except Exception as e:
                print(f" Error scraping {source_name}: {e}")
                overall_stats['errors'] += 1
                
                self.log_scraping_activity(
                    source_name,
                    status="failed",
                    error_message=str(e),
                    execution_time=time.time() - start_time
                )
                
                overall_stats['sources'].append({
                    'name': source_name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        print("\n" + "="*60)
        print(" SCRAPING SUMMARY")
        print("="*60)
        print(f"Total scraped: {overall_stats['total_scraped']}")
        print(f"Total saved: {overall_stats['total_saved']}")
        print(f"Total updated: {overall_stats['total_updated']}")
        print(f"Errors: {overall_stats['errors']}")
        print("="*60 + "\n")
        
        return overall_stats
    
    def save_to_database(self, source_name: str, natjecaji: List[Dict]) -> Dict:
        """Save scraped natjecaji to database"""
        stats = {'added': 0, 'updated': 0, 'skipped': 0}
        
        with get_db_session() as db:
            # Get or create izdavatelj
            izdavatelj = get_or_create_izdavatelj(
                db,
                naziv=source_name,
                tip="national" if source_name in ['HAMAG-BICRO', 'HRZZ'] else "international"
            )
            
            for natjecaj_data in natjecaji:
                try:
                    # Check if natjecaj already exists (by URL, then naziv for same izdavatelj)
                    existing = None
                    if natjecaj_data.get('url'):
                        existing = db.query(Natjecaj).filter(
                            Natjecaj.url == natjecaj_data.get('url')
                        ).first()

                    if not existing:
                        existing = db.query(Natjecaj).filter(
                            Natjecaj.izdavatelj_id == izdavatelj.id,
                            Natjecaj.naziv == natjecaj_data.get('naziv')
                        ).first()
                    
                    if existing:
                        # Update existing
                        for key, value in natjecaj_data.items():
                            setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        stats['updated'] += 1
                    else:
                        # Create new
                        create_natjecaj(
                            db,
                            izdavatelj_id=izdavatelj.id,
                            **natjecaj_data
                        )
                        stats['added'] += 1
                        
                except Exception as e:
                    print(f" Error saving natjecaj: {e}")
                    stats['skipped'] += 1
        
        return stats
    
    def log_scraping_activity(self, izvor: str, status: str, **kwargs):
        """Log scraping activity to database"""
        try:
            with get_db_session() as db:
                create_scraping_log(
                    db,
                    izvor=izvor,
                    status=status,
                    **kwargs
                )
        except Exception as e:
            print(f"  Error logging activity: {e}")
    
    def get_scraper_by_name(self, name: str):
        """Get specific scraper by name"""
        return self.scrapers.get(name)
    
    def run_single_scraper(self, source_name: str) -> List[Dict]:
        """Run single scraper by name"""
        scraper = self.get_scraper_by_name(source_name)
        if not scraper:
            raise ValueError(f"Scraper '{source_name}' not found")
        
        print(f"\n Running {source_name} scraper...")
        natjecaji = scraper.scrape()
        
        stats = self.save_to_database(source_name, natjecaji)
        print(f" Saved {stats['added']} new, updated {stats['updated']} existing")
        
        return natjecaji


if __name__ == "__main__":
    # Initialize database
    from src.database.database import init_db
    init_db()
    
    # Run scrapers
    manager = ScraperManager()
    results = manager.run_all_scrapers()
