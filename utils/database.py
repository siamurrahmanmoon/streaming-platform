from typing import Optional
from supabase import Client
from tqdm import tqdm
import config
from utils.logger import get_logger

log = get_logger("database")

def save_to_supabase(supabase_client: Client, metadata) -> Optional[dict]:
    if not config.ENABLE_DATABASE_SAVE: 
        return None
    try:
        return supabase_client.table('videos').upsert({
            'file_path': metadata.file_path, 
            'file_name': metadata.file_name, 
            'file_size': metadata.file_size,         
            'title': metadata.title,
            'content_type': 'anime' if metadata.media_type == 'TV Series' else 'movie',
            'media_type': metadata.media_type,
            'season': metadata.season, 
            'episode': metadata.episode,
            'episode_number': metadata.episode_number, 
            'quality': metadata.quality, 
            'languages': metadata.languages,
            'language_tag': metadata.language_tag,
            'status': metadata.status, 
            'upload_date': metadata.upload_date,
            'doodstream_url': metadata.doodstream_url,
            'mixdrop_url': metadata.mixdrop_url, 
            'streamtape_url': metadata.streamtape_url,
            'tmdb_id': metadata.tmdb_id,
            'release_year': metadata.release_year,
            'total_seasons': metadata.total_seasons,
            'total_episodes': metadata.total_episodes,
            'tmdb_status': metadata.tmdb_status,
            'original_language': metadata.original_language,
            'networks': metadata.networks,
            'creators': metadata.creators,
            'overview': metadata.overview,
            'genres': metadata.genres,
            'vote_average': metadata.vote_average,
            'poster_url': metadata.poster_url,
            'banner_url': metadata.banner_url,
            'thumbnail_url': metadata.thumbnail_url
        }, on_conflict='file_path').execute().data
    except Exception as e:
        tqdm.write(f"❌ Supabase Error: {e}")
        log.error(f"Supabase Error: {e}")
        return None