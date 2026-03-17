# FIDIT AI Assistant 🔬

AI asistent za analitiku podataka o javnim natječajima i izvorima financiranja za FIDIT znanstvenike.

## 📋 Opis

FIDIT AI Assistant je aplikacija bazirana na LLM tehnologiji koja automatizirano prikuplja i analizira podatke o javnim natječajima i dostupnim izvorima financiranja. Sustav kombinira web scraping, strukturiranu bazu podataka i AI funkcionalnosti za olakšavanje praćenja natječaja i ubrzavanje procesa pronalaženja relevantnih mogućnosti financiranja.

### Ključne funkcionalnosti

- 🌐 **Automatski web scraping** nacionalnih i međunarodnih izvora natječaja
- 💾 **Strukturirana baza podataka** s detaljnim informacijama o natječajima
- 🤖 **AI sažetci** natječaja korištenjem LLM tehnologije
- 🔍 **Napredno pretraživanje i filtriranje** po različitim kriterijima
- 📊 **Interaktivni dashboard** s vizualizacijama i statistikom
- ⚠️ **EU AI Act compliance** - transparentnost i disclaimeri

## 🏗️ Arhitektura

```
┌─────────────────────────────────────────┐
│     Streamlit Frontend (Port 8501)      │
│  - Dashboard                             │
│  - Pretraživanje                        │
│  - Vizualizacije                        │
└──────────────┬──────────────────────────┘
               │ HTTP REST API
               ▼
┌─────────────────────────────────────────┐
│      FastAPI Backend (Port 8000)        │
│  - REST API endpoints                   │
│  - LLM integracija                      │
│  - Business logika                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      PostgreSQL/SQLite Database         │
│  - natjecaji                            │
│  - izdavatelji                          │
│  - ai_sazetci                           │
│  - scraping_logs                        │
└─────────────────────────────────────────┘
               ▲
               │
┌──────────────┴──────────────────────────┐
│      Web Scraping Module                │
│  - HAMAG-BICRO scraper                  │
│  - HRZZ scraper                         │
│  - Scheduler                            │
└─────────────────────────────────────────┘
```

## 🚀 Quick Start

### Preduvjeti

- Python 3.10+
- Docker & Docker Compose (opcionalno)
- PostgreSQL (opcionalno, koristi se SQLite po defaultu)

### Instalacija

#### 1. Kloniraj repozitorij

```bash
git clone <repository-url>
cd fidit-ai-assistant
```

#### 2. Kreiraj virtualno okruženje

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ili
venv\Scripts\activate  # Windows
```

#### 3. Instaliraj dependencies

```bash
pip install -r requirements.txt
```

#### 4. Konfiguriraj environment varijable

```bash
cp .env.example .env
# Uredi .env i dodaj svoje API ključeve
```

#### 5. Inicijaliziraj bazu podataka

```bash
python src/database/database.py
```

#### 6. Pokreni aplikaciju

**Backend (FastAPI):**

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
# API dostupan na: http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

**Frontend (Streamlit):**

```bash
streamlit run frontend/app.py
# Dashboard dostupan na: http://localhost:8501
```

### Docker Deployment

```bash
# Pokreni sve servise
docker-compose up -d

# Provjeri status
docker-compose ps

# Zaustavi servise
docker-compose down
```

## 📚 Korištenje

### 1. Prikupljanje podataka (Web Scraping)

```bash
# Ručno pokretanje scrapinga
python src/scrapers/scraper_manager.py
```

Ili koristi API endpoint:

```bash
curl -X POST http://localhost:8000/api/scrape
```

### 2. Pretraživanje natječaja

Preko Streamlit dashboarda:

1. Otvori http://localhost:8501
2. Idi na stranicu "Pretraživanje"
3. Koristi filtere za pretraživanje

Ili koristi API:

```bash
curl "http://localhost:8000/api/search?q=inovacije&kategorija=Znanstveno"
```

### 3. Generiranje AI sažetaka

```bash
curl -X POST http://localhost:8000/api/natjecaji/1/summary
```

## 🔌 API Endpoints

| Endpoint                       | Metoda | Opis                          |
| ------------------------------ | ------ | ----------------------------- |
| `/api/natjecaji`               | GET    | Dohvati sve natječaje         |
| `/api/natjecaji/{id}`          | GET    | Dohvati specifičan natječaj   |
| `/api/natjecaji/expiring/soon` | GET    | Natječaji koji uskoro istječu |
| `/api/search`                  | GET    | Pretraži natječaje            |
| `/api/statistics`              | GET    | Statistika sustava            |
| `/api/natjecaji/{id}/summary`  | POST   | Generiraj AI sažetak          |
| `/api/scrape`                  | POST   | Pokreni web scraping          |
| `/api/izdavatelji`             | GET    | Dohvati sve izdavatelje       |
| `/health`                      | GET    | Health check                  |

Detaljnu API dokumentaciju možeš vidjeti na: http://localhost:8000/docs

## 🗄️ Baza podataka

### Shema

**natjecaji**

- id, naziv, url, kategorija, podrucje_istrazivanja
- iznos_financiranja, rok_prijave, status
- opis, uvjeti, dokumenti_url

**izdavatelji**

- id, naziv, url, tip (national/international)

**ai_sazetci**

- id, natjecaj_id, sazetek, kljucne_rijeci
- preporuka_relevantnosti, model_koristen
- ai_generated, disclaimer_shown

**scraping_logs**

- id, izvor, status, natjecaji_pronadeni
- execution_time, error_message

## 🤖 AI Funkcionalnosti

Aplikacija koristi Large Language Models za:

- **Generiranje sažetaka** natječaja
- **Ekstrakciju ključnih riječi**
- **Procjenu relevantnosti** za FIDIT istraživače

### EU AI Act Compliance

**Transparentnost**: Korisnici su jasno obaviješteni o AI-generiranom sadržaju  
 **Disclaimeri**: Sažeci su označeni kao informativni, ne zamjenjuju službene dokumente  
 **Privatnost**: Sustav ne prikuplja osobne podatke  
 **Javni izvori**: Koriste se samo javno dostupne informacije  
 **Ograničenja**: Jasno navedena ograničenja točnosti AI sadržaja

## 🛠️ Tehnologije

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Frontend**: Streamlit, Plotly
- **Web Scraping**: BeautifulSoup4, Selenium, Requests
- **AI/LLM**: OpenAI API, LangChain
- **Database**: PostgreSQL / SQLite
- **Deployment**: Docker, Docker Compose

## 📝 Izvori podataka

### Nacionalni

- HAMAG-BICRO
- Hrvatska zaklada za znanost (HRZZ)
- Ministarstvo znanosti i obrazovanja
- EU strukturni fondovi

### Međunarodni

- Horizon Europe
- ERC Grants
- Marie Skłodowska-Curie Actions

## 🧪 Testiranje

```bash
# Unit testovi
pytest tests/

# Test coverage
pytest --cov=src tests/
```

## 📊 Monitoring i Logging

- Scraping aktivnosti se logiraju u bazu (`scraping_logs`)
- API zahtjevi se logiraju standardnim FastAPI loggerom
- Health check endpoint: `/health`

## 🔐 Sigurnost

- API ključevi se čuvaju u `.env` fajlu (nije commitan u Git)
- Nema prikupljanja osobnih podataka
- Samo javno dostupne informacije

## 🐛 Troubleshooting

### Problem: Database connection error

**Rješenje**: Provjeri `DATABASE_URL` u `.env` fajlu

### Problem: Scraping ne radi

**Rješenje**: Provjeri internet konekciju i dostupnost izvora

### Problem: AI sažetci se ne generiraju

**Rješenje**: Provjeri `OPENAI_API_KEY` ili `ANTHROPIC_API_KEY` u `.env`

## 📄 Licenca

MIT License - vidi LICENSE fajl za detalje

## 👥 Autor

FIDIT Tim - Fakultet informatike i digitalnih tehnologija

## 🤝 Doprinos

Pull requestovi su dobrodošli! Za veće izmjene molimo prvo otvorite issue.

---

**Napomena**: Ovo je edukacijski projekt razvijen u sklopu testiranja AI aplikacija.
