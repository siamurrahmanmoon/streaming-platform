import os
import aiohttp
import asyncio
from pathlib import Path
from typing import Optional, Dict
from tqdm import tqdm
import sys
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
import config
from utils.image_uploader import upload_image_to_supabase

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
    
    async def search_anime(self, anime_name: str, season: int) -> Optional[Dict]:
        if not self.api_key:
            tqdm.write("⚠️ TMDB_API_KEY missing in .env")
            return None
        try:
            async with self.session.get(f"{self.base_url}/search/tv", params={
                'api_key': self.api_key, 'query': anime_name, 'language': 'en-US'
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('results'):
                        for result in data['results']:
                            if result.get('name', '').lower() == anime_name.lower():
                                return await self.get_tv_details(result['id'], season)
                        return await self.get_tv_details(data['results'][0]['id'], season)
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB search error: {e}")
            return None
    
    async def get_tv_details(self, tv_id: int, season: int) -> Optional[Dict]:
        try:
            async with self.session.get(f"{self.base_url}/tv/{tv_id}", params={
                'api_key': self.api_key, 'language': 'en-US'
            }) as response:
                if response.status == 200:
                    tv_data = await response.json()
                    season_data = next((s for s in tv_data.get('seasons', []) if s.get('season_number') == season), {})
                    
                    return {
                        'tmdb_id': tv_id,
                        'overview': tv_data.get('overview'),
                        'genres': [g['name'] for g in tv_data.get('genres', [])],
                        'vote_average': tv_data.get('vote_average'),
                        'poster_path': tv_data.get('poster_path'),
                        'backdrop_path': tv_data.get('backdrop_path'),
                        'season_overview': season_data.get('overview')
                    }
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB details error: {e}")
            return None

    async def fetch_image_bytes(self, image_path: str) -> Optional[bytes]:
        """Fetches image directly into memory (no disk I/O)"""
        if not image_path: return None
        try:
            async with self.session.get(f"{self.image_base_url}{image_path}") as response:
                if response.status == 200:
                    return await response.read()
            return None
        except Exception as e:
            tqdm.write(f"❌ Image fetch error: {e}")
            return None


async def fetch_and_process_season_metadata(uploader, anime_name: str, season: int) -> Optional[Dict]:
    """Checks DB first. If no images, fetches from TMDB and uploads to Supabase Storage."""
    
    # 1. Check if season already has images in DB
    try:
        result = uploader.supabase.table('videos').select(
            'poster_url, banner_url, thumbnail_url, tmdb_id'
        ).eq('title', anime_name).eq('season', season).not_.is_('poster_url', None).limit(1).execute()
        
        if result.data and len(result.data) > 0 and result.data[0].get('poster_url'):
            tqdm.write(f"✅ Season {season} images found in DB. Reusing...")
            return result.data[0]
    except Exception as e:
        tqdm.write(f"⚠️ DB check for images failed: {e}")

    # 2. Fetch from TMDB
    tqdm.write(f"\n🎨 Fetching TMDB metadata for: {anime_name} S{season}...")
    async with TMDBMetadataFetcher() as tmdb:
        metadata = await tmdb.search_anime(anime_name, season)
        if not metadata:
            tqdm.write(f"⚠️ No TMDB metadata found for {anime_name}")
            return None

        # 3. Fetch bytes and Upload to Supabase Storage directly
        image_urls = {'poster_url': '', 'banner_url': '', 'thumbnail_url': ''}

        # Poster
        if metadata.get('poster_path'):
            tqdm.write(f"📥 Fetching poster bytes...")
            img_bytes = await tmdb.fetch_image_bytes(metadata['poster_path'])
            if img_bytes:
                url = await upload_image_to_supabase(uploader, img_bytes, 'poster', anime_name, season)
                if url: image_urls['poster_url'] = url
            await asyncio.sleep(1) # Rate limit protection

        # Banner & Thumbnail (using backdrop)
        if metadata.get('backdrop_path'):
            tqdm.write(f"📥 Fetching backdrop bytes...")
            img_bytes = await tmdb.fetch_image_bytes(metadata['backdrop_path'])
            if img_bytes:
                url = await upload_image_to_supabase(uploader, img_bytes, 'banner', anime_name, season)
                if url: image_urls['banner_url'] = url
                
                url = await upload_image_to_supabase(uploader, img_bytes, 'thumbnail', anime_name, season)
                if url: image_urls['thumbnail_url'] = url
            await asyncio.sleep(1)

        # 4. Update DB for ALL episodes of this season
        if any(image_urls.values()):
            full_meta = {**metadata, **image_urls}
            try:
                res = uploader.supabase.table('videos').select('id').eq('title', anime_name).eq('season', season).execute()
                for row in res.data:
                    uploader.supabase.table('videos').update({
                        'tmdb_id': full_meta.get('tmdb_id'),
                        'overview': full_meta.get('overview'),
                        'genres': full_meta.get('genres'),
                        'vote_average': full_meta.get('vote_average'),
                        'poster_url': full_meta.get('poster_url'),
                        'banner_url': full_meta.get('banner_url'),
                        'thumbnail_url': full_meta.get('thumbnail_url'),
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', row['id']).execute()
                tqdm.write(f"✅ Season metadata & images saved to DB for {len(res.data)} episodes!")
            except Exception as e:
                tqdm.write(f"❌ Error saving season metadata to DB: {e}")
            
            return full_meta
            
        return metadata