from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str = "sqlite:///./data/fidit.db"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # LLM APIs
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Scraping
    scraping_interval_hours: int = 24
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Application
    debug: bool = True
    log_level: str = "INFO"
    
    # Frontend
    streamlit_server_port: int = 8501
    streamlit_server_address: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Data sources configuration
DATA_SOURCES = {
    "national": [
        {
            "name": "HAMAG-BICRO",
            "url": "https://www.hamagbicro.hr/usluge/potpora-poduzetnistvu/",
            "type": "html",
            "enabled": True
        },
        {
            "name": "HRZZ",
            "url": "https://hrzz.hr/natjecaji/",
            "type": "html",
            "enabled": True
        }
    ],
    "international": [
        {
            "name": "Horizon Europe",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "type": "dynamic",
            "enabled": True
        }
    ]
}
