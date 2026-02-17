from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.database.models import Natjecaj, Izdavatelj, AISazetek, ScrapingLog


# ==================== IZDAVATELJI ====================

def create_izdavatelj(db: Session, naziv: str, url: str = None, tip: str = None, opis: str = None) -> Izdavatelj:
    """Create new izdavatelj"""
    izdavatelj = Izdavatelj(naziv=naziv, url=url, tip=tip, opis=opis)
    db.add(izdavatelj)
    db.commit()
    db.refresh(izdavatelj)
    return izdavatelj


def get_izdavatelj_by_name(db: Session, naziv: str) -> Optional[Izdavatelj]:
    """Get izdavatelj by name"""
    return db.query(Izdavatelj).filter(Izdavatelj.naziv == naziv).first()


def get_or_create_izdavatelj(db: Session, naziv: str, **kwargs) -> Izdavatelj:
    """Get existing or create new izdavatelj"""
    izdavatelj = get_izdavatelj_by_name(db, naziv)
    if not izdavatelj:
        izdavatelj = create_izdavatelj(db, naziv, **kwargs)
    return izdavatelj


def get_all_izdavatelji(db: Session) -> List[Izdavatelj]:
    """Get all izdavatelji"""
    return db.query(Izdavatelj).all()


# ==================== NATJEČAJI ====================

def create_natjecaj(db: Session, **kwargs) -> Natjecaj:
    """Create new natjecaj"""
    natjecaj = Natjecaj(**kwargs)
    db.add(natjecaj)
    db.commit()
    db.refresh(natjecaj)
    return natjecaj


def get_natjecaj_by_id(db: Session, natjecaj_id: int) -> Optional[Natjecaj]:
    """Get natjecaj by ID"""
    return db.query(Natjecaj).filter(Natjecaj.id == natjecaj_id).first()


def get_all_natjecaji(db: Session, skip: int = 0, limit: int = 100) -> List[Natjecaj]:
    """Get all natjecaji with pagination"""
    return db.query(Natjecaj).offset(skip).limit(limit).all()


def get_active_natjecaji(db: Session) -> List[Natjecaj]:
    """Get all active natjecaji (status=active and rok_prijave in future)"""
    today = datetime.utcnow()
    return db.query(Natjecaj).filter(
        and_(
            Natjecaj.status == "active",
            Natjecaj.rok_prijave >= today
        )
    ).all()


def get_expiring_soon_natjecaji(db: Session, days: int = 30) -> List[Natjecaj]:
    """Get natjecaji expiring in next N days"""
    today = datetime.utcnow()
    future_date = today + timedelta(days=days)
    
    return db.query(Natjecaj).filter(
        and_(
            Natjecaj.status == "active",
            Natjecaj.rok_prijave >= today,
            Natjecaj.rok_prijave <= future_date
        )
    ).order_by(Natjecaj.rok_prijave).all()


def search_natjecaji(
    db: Session,
    search_term: str = None,
    kategorija: str = None,
    podrucje: str = None,
    izdavatelj_id: int = None,
    min_iznos: float = None,
    max_iznos: float = None,
    rok_od: datetime = None,
    rok_do: datetime = None
) -> List[Natjecaj]:
    """Advanced search for natjecaji"""
    query = db.query(Natjecaj)
    
    if search_term:
        query = query.filter(
            or_(
                Natjecaj.naziv.ilike(f"%{search_term}%"),
                Natjecaj.opis.ilike(f"%{search_term}%")
            )
        )
    
    if kategorija:
        query = query.filter(Natjecaj.kategorija == kategorija)
    
    if podrucje:
        query = query.filter(Natjecaj.podrucje_istrazivanja == podrucje)
    
    if izdavatelj_id:
        query = query.filter(Natjecaj.izdavatelj_id == izdavatelj_id)
    
    if min_iznos:
        query = query.filter(Natjecaj.iznos_financiranja >= min_iznos)
    
    if max_iznos:
        query = query.filter(Natjecaj.iznos_financiranja <= max_iznos)
    
    if rok_od:
        query = query.filter(Natjecaj.rok_prijave >= rok_od)
    
    if rok_do:
        query = query.filter(Natjecaj.rok_prijave <= rok_do)
    
    return query.order_by(desc(Natjecaj.rok_prijave)).all()


def update_natjecaj(db: Session, natjecaj_id: int, **kwargs) -> Optional[Natjecaj]:
    """Update natjecaj"""
    natjecaj = get_natjecaj_by_id(db, natjecaj_id)
    if natjecaj:
        for key, value in kwargs.items():
            setattr(natjecaj, key, value)
        natjecaj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(natjecaj)
    return natjecaj


def delete_natjecaj(db: Session, natjecaj_id: int) -> bool:
    """Delete natjecaj"""
    natjecaj = get_natjecaj_by_id(db, natjecaj_id)
    if natjecaj:
        db.delete(natjecaj)
        db.commit()
        return True
    return False


# ==================== AI SAŽETCI ====================

def create_ai_sazetek(db: Session, natjecaj_id: int, sazetek: str, **kwargs) -> AISazetek:
    """Create AI generated summary"""
    ai_sazetek = AISazetek(natjecaj_id=natjecaj_id, sazetek=sazetek, **kwargs)
    db.add(ai_sazetek)
    db.commit()
    db.refresh(ai_sazetek)
    return ai_sazetek


def get_ai_sazetek_by_natjecaj(db: Session, natjecaj_id: int) -> Optional[AISazetek]:
    """Get AI summary for natjecaj"""
    return db.query(AISazetek).filter(AISazetek.natjecaj_id == natjecaj_id).first()


# ==================== SCRAPING LOGS ====================

def create_scraping_log(db: Session, **kwargs) -> ScrapingLog:
    """Create scraping log entry"""
    log = ScrapingLog(**kwargs)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_recent_scraping_logs(db: Session, limit: int = 10) -> List[ScrapingLog]:
    """Get recent scraping logs"""
    return db.query(ScrapingLog).order_by(desc(ScrapingLog.created_at)).limit(limit).all()


# ==================== STATISTIKE ====================

def get_statistics(db: Session) -> dict:
    """Get database statistics"""
    return {
        "total_natjecaji": db.query(Natjecaj).count(),
        "active_natjecaji": db.query(Natjecaj).filter(Natjecaj.status == "active").count(),
        "total_izdavatelji": db.query(Izdavatelj).count(),
        "total_ai_sazetci": db.query(AISazetek).count(),
    }
