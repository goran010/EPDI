from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.database.database import get_db, init_db
from src.database import crud
from src.database.models import Natjecaj, Izdavatelj, AISazetek
from pydantic import BaseModel
from src.llm.llm_service import LLMService
from src.scrapers.scraper_manager import ScraperManager

# Initialize FastAPI
app = FastAPI(
    title="FIDIT AI Assistant API",
    description="API for managing scientific funding opportunities",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_service = LLMService()
scraper_manager = ScraperManager()


# ==================== PYDANTIC SCHEMAS ====================

class NatjecajResponse(BaseModel):
    id: int
    naziv: str
    izdavatelj_naziv: Optional[str] = None
    kategorija: Optional[str] = None
    podrucje_istrazivanja: Optional[str] = None
    iznos_financiranja: Optional[float] = None
    rok_prijave: Optional[datetime] = None
    url: Optional[str] = None
    status: str
    
    class Config:
        from_attributes = True


class StatisticsResponse(BaseModel):
    total_natjecaji: int
    active_natjecaji: int
    total_izdavatelji: int
    total_ai_sazetci: int
    expiring_soon: int


# ==================== API ENDPOINTS ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("Database initialized")


@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "FIDIT AI Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "natjecaji": "/api/natjecaji",
            "statistics": "/api/statistics"
        }
    }


@app.get("/api/natjecaji", response_model=List[NatjecajResponse])
def get_natjecaji(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all natjecaji with pagination"""
    if active_only:
        natjecaji = crud.get_active_natjecaji(db)
    else:
        natjecaji = crud.get_all_natjecaji(db, skip=skip, limit=limit)
    
    # Add izdavatelj naziv to response
    result = []
    for n in natjecaji:
        data = NatjecajResponse.from_orm(n)
        if n.izdavatelj:
            data.izdavatelj_naziv = n.izdavatelj.naziv
        result.append(data)
    
    return result


@app.get("/api/natjecaji/{natjecaj_id}")
def get_natjecaj(natjecaj_id: int, db: Session = Depends(get_db)):
    """Get single natjecaj by ID"""
    natjecaj = crud.get_natjecaj_by_id(db, natjecaj_id)
    if not natjecaj:
        raise HTTPException(status_code=404, detail="Natječaj not found")
    
    return {
        "natjecaj": natjecaj,
        "izdavatelj": natjecaj.izdavatelj,
        "ai_sazetek": natjecaj.ai_sazetci[0] if natjecaj.ai_sazetci else None
    }


@app.get("/api/natjecaji/expiring/soon")
def get_expiring_soon(days: int = 30, db: Session = Depends(get_db)):
    """Get natječaji expiring in next N days"""
    natjecaji = crud.get_expiring_soon_natjecaji(db, days=days)
    return natjecaji


@app.get("/api/search")
def search_natjecaji(
    q: Optional[str] = None,
    kategorija: Optional[str] = None,
    podrucje: Optional[str] = None,
    min_iznos: Optional[float] = None,
    max_iznos: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Advanced search for natječaji"""
    results = crud.search_natjecaji(
        db,
        search_term=q,
        kategorija=kategorija,
        podrucje=podrucje,
        min_iznos=min_iznos,
        max_iznos=max_iznos
    )
    return results


@app.get("/api/statistics", response_model=StatisticsResponse)
def get_statistics(db: Session = Depends(get_db)):
    """Get database statistics"""
    stats = crud.get_statistics(db)
    expiring = len(crud.get_expiring_soon_natjecaji(db, days=30))
    
    return StatisticsResponse(
        total_natjecaji=stats['total_natjecaji'],
        active_natjecaji=stats['active_natjecaji'],
        total_izdavatelji=stats['total_izdavatelji'],
        total_ai_sazetci=stats['total_ai_sazetci'],
        expiring_soon=expiring
    )


@app.post("/api/natjecaji/{natjecaj_id}/summary")
def generate_summary(natjecaj_id: int, db: Session = Depends(get_db)):
    """Generate AI summary for a natjecaj"""
    # Get natjecaj
    natjecaj = crud.get_natjecaj_by_id(db, natjecaj_id)
    if not natjecaj:
        raise HTTPException(status_code=404, detail="Natječaj not found")
    
    # Check if summary already exists
    existing = crud.get_ai_sazetek_by_natjecaj(db, natjecaj_id)
    if existing:
        return {
            "message": "Summary already exists",
            "summary": existing,
            "disclaimer": " AI-generirani sadržaj - provjerite službenu dokumentaciju"
        }
    
    # Generate new summary
    natjecaj_data = {
        'naziv': natjecaj.naziv,
        'opis': natjecaj.opis,
        'kategorija': natjecaj.kategorija,
        'podrucje_istrazivanja': natjecaj.podrucje_istrazivanja,
        'iznos_financiranja': natjecaj.iznos_financiranja,
        'rok_prijave': natjecaj.rok_prijave
    }
    
    summary_data = llm_service.generate_summary(natjecaj_data)
    
    if summary_data:
        # Save to database
        ai_sazetek = crud.create_ai_sazetek(
            db,
            natjecaj_id=natjecaj_id,
            **summary_data
        )
        
        return {
            "message": "Summary generated successfully",
            "summary": ai_sazetek,
            "disclaimer": " AI-generirani sadržaj - provjerite službenu dokumentaciju"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to generate summary")


@app.post("/api/scrape")
def trigger_scraping(source: Optional[str] = None):
    """Trigger web scraping manually"""
    try:
        if source:
            # Run single scraper
            results = scraper_manager.run_single_scraper(source)
            return {
                "message": f"Scraping completed for {source}",
                "count": len(results)
            }
        else:
            # Run all scrapers
            stats = scraper_manager.run_all_scrapers()
            return {
                "message": "Scraping completed for all sources",
                "statistics": stats
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/izdavatelji")
def get_izdavatelji(db: Session = Depends(get_db)):
    """Get all izdavatelji"""
    return crud.get_all_izdavatelji(db)


@app.get("/api/logs/scraping")
def get_scraping_logs(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent scraping logs"""
    return crud.get_recent_scraping_logs(db, limit=limit)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "operational",
            "llm": "operational" if llm_service.enabled else "disabled",
            "scrapers": "operational"
        }
    }


if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
