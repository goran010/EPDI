from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Izdavatelj(Base):
    """Model za izdavatelje natječaja"""
    __tablename__ = "izdavatelji"
    
    id = Column(Integer, primary_key=True, index=True)
    naziv = Column(String(255), nullable=False, unique=True)
    url = Column(String(500))
    tip = Column(String(50))  # "national" ili "international"
    opis = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    natjecaji = relationship("Natjecaj", back_populates="izdavatelj")


class Natjecaj(Base):
    """Model za natječaje"""
    __tablename__ = "natjecaji"
    
    id = Column(Integer, primary_key=True, index=True)
    naziv = Column(String(500), nullable=False)
    izdavatelj_id = Column(Integer, ForeignKey("izdavatelji.id"))
    
    # Osnovni podaci
    url = Column(String(1000))
    kategorija = Column(String(200))  # npr. "Znanstveno istraživanje", "Inovacije"
    podrucje_istrazivanja = Column(String(200))  # npr. "ICT", "Medicina", "Društvene znanosti"
    
    # Financijski podaci
    iznos_financiranja = Column(Float)  # u EUR
    valuta = Column(String(10), default="EUR")
    min_iznos = Column(Float)
    max_iznos = Column(Float)
    
    # Rokovi
    datum_objave = Column(DateTime)
    rok_prijave = Column(DateTime)
    datum_pocetka = Column(DateTime)
    datum_zavrsetka = Column(DateTime)
    
    # Ostali podaci
    opis = Column(Text)
    uvjeti = Column(Text)
    dokumenti_url = Column(String(1000))
    status = Column(String(50), default="active")  # active, expired, closed
    
    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    izdavatelj = relationship("Izdavatelj", back_populates="natjecaji")
    ai_sazetci = relationship("AISazetek", back_populates="natjecaj")


class AISazetek(Base):
    """Model za AI generirane sažetke natječaja"""
    __tablename__ = "ai_sazetci"
    
    id = Column(Integer, primary_key=True, index=True)
    natjecaj_id = Column(Integer, ForeignKey("natjecaji.id"))
    
    sazetek = Column(Text, nullable=False)
    kljucne_rijeci = Column(String(500))
    preporuka_relevantnosti = Column(String(50))  # "visoka", "srednja", "niska"
    
    # AI Metadata
    model_koristen = Column(String(100))  # npr. "gpt-4", "claude-3"
    temperatura = Column(Float, default=0.7)
    token_count = Column(Integer)
    
    # Transparentnost (EU AI Act)
    ai_generated = Column(Boolean, default=True)
    disclaimer_shown = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    natjecaj = relationship("Natjecaj", back_populates="ai_sazetci")


class ScrapingLog(Base):
    """Model za logiranje scraping aktivnosti"""
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    izvor = Column(String(200), nullable=False)
    url = Column(String(1000))
    status = Column(String(50))  # "success", "failed", "partial"
    natjecaji_pronadeni = Column(Integer, default=0)
    natjecaji_dodani = Column(Integer, default=0)
    natjecaji_azurirani = Column(Integer, default=0)
    error_message = Column(Text)
    execution_time = Column(Float)  # u sekundama
    created_at = Column(DateTime, default=datetime.utcnow)
