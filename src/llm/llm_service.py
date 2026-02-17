from typing import Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.settings import settings

# Try to import OpenAI, handle if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("  OpenAI library not available. AI summaries will be disabled.")


class LLMService:
    """Service for generating AI summaries of natječaji using LLMs"""
    
    def __init__(self, model: str = "gpt-4", temperature: float = 0.7):
        self.model = model
        self.temperature = temperature
        
        if OPENAI_AVAILABLE and settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
            print("  LLM Service disabled - no API key configured")
    
    def generate_summary(self, natjecaj_data: Dict) -> Optional[Dict]:
        """
        Generate AI summary for a natjecaj
        
        Returns:
            Dict with 'sazetek', 'kljucne_rijeci', 'preporuka_relevantnosti'
            or None if generation failed
        """
        if not self.enabled:
            return self._generate_fallback_summary(natjecaj_data)
        
        try:
            # Prepare prompt
            prompt = self._build_prompt(natjecaj_data)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=500
            )
            
            # Extract response
            summary_text = response.choices[0].message.content.strip()
            
            # Parse structured response
            result = self._parse_response(summary_text)
            
            # Add metadata
            result['model_koristen'] = self.model
            result['temperatura'] = self.temperature
            result['token_count'] = response.usage.total_tokens
            result['ai_generated'] = True
            result['disclaimer_shown'] = True
            
            return result
            
        except Exception as e:
            print(f" Error generating AI summary: {e}")
            return self._generate_fallback_summary(natjecaj_data)
    
    def _get_system_prompt(self) -> str:
        """System prompt for AI"""
        return """Ti si AI asistent specijaliziran za analizu natječaja i izvora financiranja za znanstvena istraživanja.
Tvoj zadatak je generirati KRATAK, INFORMATIVAN i OBJEKTIVAN sažetak natječaja.

VAŽNO - EU AI Act Compliance:
- Budi transparentan da je ovo AI-generirani sadržaj
- Sažetak je samo informativne prirode
- Korisnik mora provjeriti službene dokumente
- Ne smije zamijeniti službenu natječajnu dokumentaciju

Format odgovora:
SAŽETAK: [2-3 rečenice koje objašnjavaju suštinu natječaja]
KLJUČNE RIJEČI: [3-5 ključnih riječi odvojenih zarezom]
RELEVANTNOST: [visoka/srednja/niska - procjena za FIDIT znanstvenike]
"""
    
    def _build_prompt(self, natjecaj_data: Dict) -> str:
        """Build prompt from natjecaj data"""
        naziv = natjecaj_data.get('naziv', 'N/A')
        opis = natjecaj_data.get('opis', 'Nema opisa')
        kategorija = natjecaj_data.get('kategorija', 'N/A')
        podrucje = natjecaj_data.get('podrucje_istrazivanja', 'N/A')
        iznos = natjecaj_data.get('iznos_financiranja', 'N/A')
        rok = natjecaj_data.get('rok_prijave', 'N/A')
        
        prompt = f"""Analiziraj sljedeći natječaj i generiraj sažetak:

NAZIV: {naziv}
KATEGORIJA: {kategorija}
PODRUČJE: {podrucje}
IZNOS FINANCIRANJA: {iznos} EUR
ROK PRIJAVE: {rok}

OPIS:
{opis}

Generiraj strukturiran odgovor prema zadanom formatu."""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse structured response from AI"""
        result = {
            'sazetek': '',
            'kljucne_rijeci': '',
            'preporuka_relevantnosti': 'srednja'
        }
        
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('SAŽETAK:'):
                result['sazetek'] = line.replace('SAŽETAK:', '').strip()
            elif line.startswith('KLJUČNE RIJEČI:'):
                result['kljucne_rijeci'] = line.replace('KLJUČNE RIJEČI:', '').strip()
            elif line.startswith('RELEVANTNOST:'):
                relevantnost = line.replace('RELEVANTNOST:', '').strip().lower()
                if relevantnost in ['visoka', 'srednja', 'niska']:
                    result['preporuka_relevantnosti'] = relevantnost
        
        # Fallback if parsing failed
        if not result['sazetek']:
            result['sazetek'] = response_text
        
        return result
    
    def _generate_fallback_summary(self, natjecaj_data: Dict) -> Dict:
        """Generate simple fallback summary when AI is not available"""
        naziv = natjecaj_data.get('naziv', 'Natječaj')
        kategorija = natjecaj_data.get('kategorija', 'N/A')
        
        return {
            'sazetek': f"Natječaj '{naziv}' u kategoriji {kategorija}. Za detaljne informacije molimo provjerite službenu dokumentaciju.",
            'kljucne_rijeci': kategorija,
            'preporuka_relevantnosti': 'srednja',
            'model_koristen': 'fallback',
            'temperatura': 0.0,
            'token_count': 0,
            'ai_generated': False,
            'disclaimer_shown': True
        }
    
    def batch_generate_summaries(self, natjecaji_list: list) -> list:
        """Generate summaries for multiple natječaji"""
        results = []
        
        for natjecaj in natjecaji_list:
            summary = self.generate_summary(natjecaj)
            if summary:
                results.append({
                    'natjecaj_id': natjecaj.get('id'),
                    'summary': summary
                })
        
        return results


# EU AI Act Compliance Disclaimer
EU_AI_ACT_DISCLAIMER = """
 AI-GENERIRANI SADRŽAJ - VAŽNO OBAVJEŠTENJE

Ovaj sažetak je generiran korištenjem AI tehnologije (Large Language Model).

NAPOMENA:
• Sažetak je INFORMATIVNE prirode i služi samo kao pomoć pri pretraživanju
• AI model može napraviti greške ili netočno interpretirati podatke
• Ovaj sažetak NE ZAMJENJUJE službenu natječajnu dokumentaciju
• UVIJEK provjerite službene dokumente izdavatelja prije prijave

Za službene i ažurne informacije molimo posjetite povezanu službenu stranicu natječaja.

U skladu s EU AI Actom, obavještavamo vas da ovaj sadržaj generira AI sustav.
"""


if __name__ == "__main__":
    # Test LLM service
    service = LLMService()
    
    test_natjecaj = {
        'naziv': 'Test Natječaj za Inovacije',
        'opis': 'Natječaj za financiranje inovativnih projekata u području ICT-a',
        'kategorija': 'Inovacije',
        'podrucje_istrazivanja': 'ICT',
        'iznos_financiranja': 50000,
        'rok_prijave': '2024-12-31'
    }
    
    print("Testing LLM Service...\n")
    summary = service.generate_summary(test_natjecaj)
    
    if summary:
        print("  Summary generated:")
        print(f"Sažetak: {summary['sazetek']}")
        print(f"Ključne riječi: {summary['kljucne_rijeci']}")
        print(f"Relevantnost: {summary['preporuka_relevantnosti']}")
        print(f"\n{EU_AI_ACT_DISCLAIMER}")
