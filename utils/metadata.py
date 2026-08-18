import os
import aiohttp
import asyncio
from typing import Optional, Dict
from tqdm import tqdm
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config
from utils.image_uploader import upload_image_to_supabase

_metadata_locks = {}

class TMDBMetadataFetcher:
    def __init__(self):
        self.api_key = os.getenv('TMDB_API_KEY')
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session: await self.session.close()

    # ✅ TV Series Search
    async def search_tv(self, title: str, season: int, year: Optional[int] = None) -> Optional[Dict]:
        if not self.api_key: return None
        try:
            params = {'api_key': self.api_key, 'query': title, 'language': 'en-US'}
            if year: params['first_air_date_year'] = str(year)
            
            async with self.session.get(f"{self.base_url}/search/tv", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('results'):
                        for result in data['results']:
                            if result.get('name', '').lower() == title.lower():
                                return await self.get_tv_details(result['id'], season)
                        return await self.get_tv_details(data['results'][0]['id'], season)
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB TV search error: {e}")
            return None

    # ✅ Movie Search
    async def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        if not self.api_key: return None
        try:
            params = {'api_key': self.api_key, 'query': title, 'language': 'en-US'}
            if year: params['primary_release_year'] = str(year)
            
            async with self.session.get(f"{self.base_url}/search/movie", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('results'):
                        for result in data['results']:
                            if result.get('title', '').lower() == title.lower():
                                return await self.get_movie_details(result['id'])
                        return await self.get_movie_details(data['results'][0]['id'])
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB Movie search error: {e}")
            return None

    async def get_tv_details(self, tv_id: int, season: int) -> Optional[Dict]:
        try:
            async with self.session.get(f"{self.base_url}/tv/{tv_id}", params={'api_key': self.api_key, 'language': 'en-US'}) as response:
                if response.status == 200:
                    tv_data = await response.json()
                    release_date_str = tv_data.get('first_air_date', '')
                    return {
                        'tmdb_id': tv_id, 'media_type': 'TV Series',
                        'release_year': int(release_date_str.split('-')[0]) if release_date_str else 0,
                        'tmdb_status': tv_data.get('status', ''),
                        'total_seasons': tv_data.get('number_of_seasons', 0),
                        'total_episodes': tv_data.get('number_of_episodes', 0),
                        'original_language': tv_data.get('original_language', ''),
                        'networks': [n['name'] for n in tv_data.get('networks', [])],
                        'creators': [c['name'] for c in tv_data.get('created_by', [])],
                        'overview': tv_data.get('overview', ''),
                        'genres': [{'name': g['name']} for g in tv_data.get('genres', [])],
                        'vote_average': float(tv_data.get('vote_average', 0.0)),
                        'poster_path': tv_data.get('poster_path'),
                        'backdrop_path': tv_data.get('backdrop_path'),
                    }
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB TV details error: {e}")
            return None

    # ✅ Movie Details
    async def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        try:
            async with self.session.get(f"{self.base_url}/movie/{movie_id}", params={'api_key': self.api_key, 'language': 'en-US'}) as response:
                if response.status == 200:
                    m_data = await response.json()
                    release_date_str = m_data.get('release_date', '')
                    return {
                        'tmdb_id': movie_id, 'media_type': 'Movie',
                        'release_year': int(release_date_str.split('-')[0]) if release_date_str else 0,
                        'tmdb_status': m_data.get('status', ''),
                        'total_seasons': 0, 'total_episodes': 0,
                        'original_language': m_data.get('original_language', ''),
                        'networks': [n['name'] for n in m_data.get('production_companies', [])], 
                        'creators': [c['name'] for c in m_data.get('created_by', [])], # Fixed: creators should be created_by
                        'overview': m_data.get('overview', ''),
                        'genres': [{'name': g['name']} for g in m_data.get('genres', [])],
                        'vote_average': float(m_data.get('vote_average', 0.0)),
                        'poster_path': m_data.get('poster_path'),
                        'backdrop_path': m_data.get('backdrop_path'),
                    }
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB Movie details error: {e}")
            return None

    async def fetch_image_bytes(self, image_path: str) -> Optional[bytes]:
        if not image_path: return None
        try:
            async with self.session.get(f"{self.image_base_url}{image_path}") as response:
                if response.status == 200: return await response.read()
            return None
        except Exception as e:
            tqdm.write(f"❌ Image fetch error: {e}")
            return None


# ✅ ফিক্সড এবং অপ্টিমাইজড ভার্সন
async def fetch_and_process_metadata(uploader, title: str, media_type: str, season: int = None, year: int = None) -> Optional[Dict]:
    lock_key = f"{title}_{media_type}_{season or 'movie'}"
    if lock_key not in _metadata_locks:
        _metadata_locks[lock_key] = asyncio.Lock()
        
    async with _metadata_locks[lock_key]:
        # 1. Check DB
        try:
            query = uploader.supabase.table('videos').select('poster_url, tmdb_id, release_year').eq('title', title).eq('media_type', media_type)
            if season is not None: 
                query = query.eq('season', season)
            else: 
                query = query.is_('season', None) # ✅ মুভির জন্য সঠিক NULL চেক
            
            result = query.not_.is_('poster_url', None).limit(1).execute()
            
            if result.data and len(result.data) > 0 and result.data[0].get('poster_url'):
                tqdm.write(f"✅ {media_type} '{title}' metadata found in DB. Reusing...")
                return result.data[0]
        except Exception as e:
            tqdm.write(f"⚠️ DB check failed: {e}")

        # 2. Fetch from TMDB based on Media Type
        tqdm.write(f"\n🎨 Fetching TMDB metadata for: {title} ({media_type}) {'(' + str(year) + ')' if year else ''}...")
        async with TMDBMetadataFetcher() as tmdb:
            if media_type == 'Movie':
                metadata = await tmdb.search_movie(title, year)
            else:
                metadata = await tmdb.search_tv(title, season, year)
                
            if not metadata:
                tqdm.write(f"⚠️ No TMDB metadata found for {title}")
                return None

            tqdm.write(f"📅 Matched: {title} ({metadata.get('release_year')}) | Type: {metadata.get('media_type')} | Status: {metadata.get('tmdb_status')}")

            tmdb_id = metadata.get('tmdb_id')
            image_urls = {'poster_url': '', 'banner_url': '', 'thumbnail_url': ''}

            # 3. Upload Images (✅ FIX: tmdb_id পাস করা হচ্ছে title এর বদলে)
            if metadata.get('poster_path'):
                img_bytes = await tmdb.fetch_image_bytes(metadata['poster_path'])
                if img_bytes:
                    url = await upload_image_to_supabase(uploader, img_bytes, 'poster', tmdb_id, season or 1)
                    if url: image_urls['poster_url'] = url
                await asyncio.sleep(0.5)

            if metadata.get('backdrop_path'):
                img_bytes = await tmdb.fetch_image_bytes(metadata['backdrop_path'])
                if img_bytes:
                    url = await upload_image_to_supabase(uploader, img_bytes, 'banner', tmdb_id, season or 1)
                    if url: image_urls['banner_url'] = url
                    
                    url = await upload_image_to_supabase(uploader, img_bytes, 'thumbnail', tmdb_id, season or 1)
                    if url: image_urls['thumbnail_url'] = url
                await asyncio.sleep(0.5)

            # 4. Update DB
            if any(image_urls.values()):
                full_meta = {**metadata, **image_urls}
                try:
                    query = uploader.supabase.table('videos').select('id').eq('title', title).eq('media_type', media_type)
                    if season is not None: 
                        query = query.eq('season', season)
                    else: 
                        query = query.is_('season', None)
                    
                    res = query.execute()
                    for row in res.data:
                        uploader.supabase.table('videos').update({
                            'tmdb_id': full_meta.get('tmdb_id'),
                            'media_type': full_meta.get('media_type'),
                            'release_year': full_meta.get('release_year'),
                            'total_seasons': full_meta.get('total_seasons'),
                            'total_episodes': full_meta.get('total_episodes'),
                            'tmdb_status': full_meta.get('tmdb_status'),
                            'original_language': full_meta.get('original_language'),
                            'networks': full_meta.get('networks'),
                            'creators': full_meta.get('creators'),
                            'overview': full_meta.get('overview'),
                            'genres': full_meta.get('genres'),
                            'vote_average': full_meta.get('vote_average'),
                            'poster_url': full_meta.get('poster_url'),
                            'banner_url': full_meta.get('banner_url'),
                            'thumbnail_url': full_meta.get('thumbnail_url'),
                            'updated_at': datetime.now().isoformat()
                        }).eq('id', row['id']).execute()
                    
                    count = len(res.data)
                    if count == 0:
                        tqdm.write(f"ℹ️ Metadata fetched. Will be saved when current file saves to DB.")
                    else:
                        tqdm.write(f"✅ Metadata updated in DB for {count} files!")
                except Exception as e:
                    tqdm.write(f"❌ Error saving metadata to DB: {e}")
                
                return full_meta
                
            return metadata