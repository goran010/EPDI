"""
Demo data script - Populate database with sample data for testing
"""
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.database.database import init_db, get_db_session
from src.database.crud import create_izdavatelj, create_natjecaj, create_ai_sazetek


def create_demo_data():
    """Create demo data for testing"""
    
    print("🎯 Creating demo data...")
    
    # Initialize database
    init_db()
    
    with get_db_session() as db:
        # Create izdavatelji
        print("\n📝 Creating izdavatelji...")
        
        hamag = create_izdavatelj(
            db,
            naziv="HAMAG-BICRO",
            url="https://www.hamagbicro.hr",
            tip="national",
            opis="Hrvatska agencija za malo gospodarstvo, inovacije i investicije"
        )
        
        hrzz = create_izdavatelj(
            db,
            naziv="HRZZ",
            url="https://hrzz.hr",
            tip="national",
            opis="Hrvatska zaklada za znanost"
        )
        
        horizon = create_izdavatelj(
            db,
            naziv="Horizon Europe",
            url="https://ec.europa.eu/info/funding-tenders/",
            tip="international",
            opis="EU Framework Programme for Research and Innovation"
        )
        
        erc = create_izdavatelj(
            db,
            naziv="ERC",
            url="https://erc.europa.eu/",
            tip="international",
            opis="European Research Council"
        )
        
        print(f"  Created {4} izdavatelji")
        
        # Create sample natjecaji
        print("\n📝 Creating natjecaji...")
        
        natjecaji_data = [
            {
                "naziv": "Potpora za digitalizaciju MSP-ova",
                "izdavatelj_id": hamag.id,
                "kategorija": "Potpora poduzetništvu",
                "podrucje_istrazivanja": "ICT",
                "iznos_financiranja": 50000,
                "rok_prijave": datetime.now() + timedelta(days=45),
                "opis": "Natječaj za financiranje projekata digitalne transformacije malih i srednjih poduzeća. Pokriva troškove implementacije ICT rješenja, obuke zaposlenika i tehnološke modernizacije.",
                "url": "https://www.hamagbicro.hr/natjecaj/digitalizacija-2024",
                "status": "active"
            },
            {
                "naziv": "HRZZ - Istraživački projekti",
                "izdavatelj_id": hrzz.id,
                "kategorija": "Znanstveno istraživanje",
                "podrucje_istrazivanja": "Multidisciplinarno",
                "iznos_financiranja": 200000,
                "rok_prijave": datetime.now() + timedelta(days=60),
                "opis": "Natječaj za financiranje temeljnih i primijenjenih znanstvenih istraživanja u svim znanstvenim područjima. Projekt može trajati do 4 godine.",
                "url": "https://hrzz.hr/natjecaj/ip-2024",
                "status": "active"
            },
            {
                "naziv": "AI u zdravstvu - inovacije",
                "izdavatelj_id": hamag.id,
                "kategorija": "Inovacije",
                "podrucje_istrazivanja": "ICT",
                "iznos_financiranja": 100000,
                "rok_prijave": datetime.now() + timedelta(days=30),
                "opis": "Natječaj za projekte koji primjenjuju umjetnu inteligenciju u zdravstvenom sektoru. Prioritet imaju rješenja za dijagnostiku i personaliziranu medicinu.",
                "url": "https://www.hamagbicro.hr/natjecaj/ai-zdravstvo",
                "status": "active"
            },
            {
                "naziv": "Horizon Europe - EIC Accelerator",
                "izdavatelj_id": horizon.id,
                "kategorija": "Inovacije",
                "podrucje_istrazivanja": "Multidisciplinarno",
                "iznos_financiranja": 2500000,
                "rok_prijave": datetime.now() + timedelta(days=90),
                "opis": "EU program za financiranje visokorizičnih inovacija s potencijalom stvaranja novih tržišta. Kombinacija granta i equity investicije.",
                "url": "https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator",
                "status": "active"
            },
            {
                "naziv": "ERC Starting Grant",
                "izdavatelj_id": erc.id,
                "kategorija": "Znanstveno istraživanje",
                "podrucje_istrazivanja": "Multidisciplinarno",
                "iznos_financiranja": 1500000,
                "rok_prijave": datetime.now() + timedelta(days=120),
                "opis": "Grant za perspektivne mlade istraživače koji žele započeti vlastitu istraživačku grupu. Za istraživače 2-7 godina nakon doktorata.",
                "url": "https://erc.europa.eu/funding/starting-grants",
                "status": "active"
            },
            {
                "naziv": "Cybersecurity istraživanje",
                "izdavatelj_id": hrzz.id,
                "kategorija": "Znanstveno istraživanje",
                "podrucje_istrazivanja": "ICT",
                "iznos_financiranja": 150000,
                "rok_prijave": datetime.now() + timedelta(days=75),
                "opis": "Natječaj za istraživačke projekte u području kibernetičke sigurnosti, kriptografije i zaštite podataka.",
                "url": "https://hrzz.hr/natjecaj/cyber-2024",
                "status": "active"
            },
            {
                "naziv": "Green Tech inovacije",
                "izdavatelj_id": hamag.id,
                "kategorija": "Inovacije",
                "podrucje_istrazivanja": "Multidisciplinarno",
                "iznos_financiranja": 75000,
                "rok_prijave": datetime.now() + timedelta(days=20),
                "opis": "Podrška za razvoj ekološki prihvatljivih tehnologija i rješenja za održivi razvoj. Prioritet: obnovljiva energija i kružno gospodarstvo.",
                "url": "https://www.hamagbicro.hr/natjecaj/greentech",
                "status": "active"
            },
            {
                "naziv": "MSCA Postdoctoral Fellowships",
                "izdavatelj_id": horizon.id,
                "kategorija": "Znanstveno istraživanje",
                "podrucje_istrazivanja": "Multidisciplinarno",
                "iznos_financiranja": 180000,
                "rok_prijave": datetime.now() + timedelta(days=105),
                "opis": "Marie Skłodowska-Curie stipendije za postdoktorsko usavršavanje. Podrška za međunarodnu mobilnost istraživača.",
                "url": "https://marie-sklodowska-curie-actions.ec.europa.eu/",
                "status": "active"
            },
            {
                "naziv": "Blockchain tehnologije",
                "izdavatelj_id": hamag.id,
                "kategorija": "Inovacije",
                "podrucje_istrazivanja": "ICT",
                "iznos_financiranja": 80000,
                "rok_prijave": datetime.now() + timedelta(days=15),
                "opis": "Potpora za razvoj blockchain rješenja u različitim sektorima. Fokus na praktičnim primjenama i skalabilnosti.",
                "url": "https://www.hamagbicro.hr/natjecaj/blockchain-2024",
                "status": "active"
            },
            {
                "naziv": "Biomedicinska istraživanja",
                "izdavatelj_id": hrzz.id,
                "kategorija": "Znanstveno istraživanje",
                "podrucje_istrazivanja": "Medicina",
                "iznos_financiranja": 250000,
                "rok_prijave": datetime.now() + timedelta(days=50),
                "opis": "Natječaj za biomedicinska istraživanja s fokusom na nove terapijske pristupe i dijagnostičke metode.",
                "url": "https://hrzz.hr/natjecaj/biomedicina-2024",
                "status": "active"
            }
        ]
        
        created_natjecaji = []
        for nat_data in natjecaji_data:
            natjecaj = create_natjecaj(db, **nat_data)
            created_natjecaji.append(natjecaj)
        
        print(f"  Created {len(created_natjecaji)} natjecaji")
        
        # Create some AI summaries
        print("\n📝 Creating AI summaries...")
        
        sample_summaries = [
            {
                "natjecaj_id": created_natjecaji[0].id,
                "sazetek": "Natječaj nudi financijsku potporu za digitalizaciju malih i srednjih poduzeća kroz implementaciju modernih ICT rješenja i obuku zaposlenika.",
                "kljucne_rijeci": "digitalizacija, MSP, ICT, obuka",
                "preporuka_relevantnosti": "visoka",
                "model_koristen": "gpt-4",
                "temperatura": 0.7,
                "token_count": 150
            },
            {
                "natjecaj_id": created_natjecaji[1].id,
                "sazetek": "Natječaj podržava temeljna i primijenjena znanstvena istraživanja u svim područjima s projektima do 4 godine trajanja.",
                "kljucne_rijeci": "znanstveno istraživanje, temeljna istraživanja, HRZZ",
                "preporuka_relevantnosti": "visoka",
                "model_koristen": "gpt-4",
                "temperatura": 0.7,
                "token_count": 120
            },
            {
                "natjecaj_id": created_natjecaji[2].id,
                "sazetek": "Fokus na inovativne primjene umjetne inteligencije u zdravstvu, posebno u dijagnostici i personaliziranoj medicini.",
                "kljucne_rijeci": "AI, zdravstvo, dijagnostika, medicina",
                "preporuka_relevantnosti": "visoka",
                "model_koristen": "gpt-4",
                "temperatura": 0.7,
                "token_count": 110
            }
        ]
        
        for summary_data in sample_summaries:
            create_ai_sazetek(db, **summary_data)
        
        print(f"  Created {len(sample_summaries)} AI summaries")
    
    print("\n" + "="*60)
    print("  Demo data creation completed successfully!")
    print("="*60)
    print("\n📊 Summary:")
    print(f"  - Izdavatelji: 4")
    print(f"  - Natječaji: {len(natjecaji_data)}")
    print(f"  - AI Sažetci: {len(sample_summaries)}")
    print("\n🚀 You can now run the application and see the demo data!")
    print("="*60 + "\n")


if __name__ == "__main__":
    create_demo_data()
