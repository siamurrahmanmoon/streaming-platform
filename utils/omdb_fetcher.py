import os
import aiohttp
from typing import Optional, Dict
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

class OMDbMetadataFetcher:
    """Fallback metadata fetcher using OMDb API"""
    
    def __init__(self):
        self.api_key = os.getenv('OMDB_API_KEY')
        self.base_url = "http://www.omdbapi.com/"
        
    async def search(self, title: str, year: Optional[int] = None, media_type: str = "series") -> Optional[Dict]:
        """Search OMDb for movie or series"""
        if not self.api_key:
            return None
            
        try:
            params = {
                'apikey': self.api_key,
                's': title,  # Search parameter
                'type': 'movie' if media_type == 'Movie' else 'series'
            }
            
            if year:
                params['y'] = str(year)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('Response') == 'True' and data.get('Search'):
                            # Return first result
                            return data['Search'][0]
            return None
        except Exception as e:
            print(f"❌ OMDb search error: {e}")
            return None
    
    async def get_details(self, imdb_id: str) -> Optional[Dict]:
        """Get detailed info using IMDB ID"""
        if not self.api_key:
            return None
            
        try:
            params = {
                'apikey': self.api_key,
                'i': imdb_id,
                'plot': 'full'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('Response') == 'True':
                            return self._parse_omdb_data(data)
            return None
        except Exception as e:
            print(f"❌ OMDb details error: {e}")
            return None
    
    def _parse_omdb_data(self, data: Dict) -> Dict:
        """Parse OMDb response to match our format"""
        return {
            'tmdb_id': 0,  # OMDb doesn't provide TMDB ID
            'imdb_id': data.get('imdbID', ''),
            'media_type': 'Movie' if data.get('Type') == 'movie' else 'TV Series',
            'title': data.get('Title', ''),
            'release_year': int(data.get('Year', '0')) if data.get('Year', '').isdigit() else 0,
            'runtime': data.get('Runtime', ''),
            'genres': [{'name': g.strip()} for g in data.get('Genre', '').split(',')],
            'overview': data.get('Plot', ''),
            'director': data.get('Director', ''),
            'actors': [a.strip() for a in data.get('Actors', '').split(',')],
            'vote_average': float(data.get('imdbRating', '0')) if data.get('imdbRating', '') != 'N/A' else 0.0,
            'poster_url': data.get('Poster', '') if data.get('Poster', '') != 'N/A' else '',
            'backdrop_path': None,  # OMDb doesn't provide backdrop
            'tmdb_status': 'Ended' if data.get('Status', '') == 'ended' else '',
            'total_seasons': int(data.get('totalSeasons', '1')) if data.get('totalSeasons', '').isdigit() else 1,
            'total_episodes': 0,
            'original_language': '',
            'networks': [],
            'creators': [c.strip() for c in data.get('Creator', '').split(',')] if data.get('Creator') else []
        }