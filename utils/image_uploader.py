import os
import re
from pathlib import Path
from typing import Optional
from tqdm import tqdm
import sys

sys.path.append(str(Path(__file__).parent.parent))
import config

def sanitize_filename(name: str) -> str:
    """Removes special characters and makes filename safe for storage"""
    name = re.sub(r'[^\w\s-]', '', name).strip()
    return re.sub(r'[-\s]+', '_', name)

async def upload_image_to_supabase(uploader, image_bytes: bytes, image_type: str, anime_name: str, season: int) -> Optional[str]:
    """Uploads image bytes directly to Supabase Storage"""
    if not config.ENABLE_IMAGE_STORAGE:
        return None

    bucket_name = config.SUPABASE_STORAGE_BUCKET
    safe_anime_name = sanitize_filename(anime_name)
    
    # Organized folder structure: anime_name/season_X/type.jpg
    file_name = f"{safe_anime_name}_S{season}_{image_type}.jpg"
    file_path = f"{safe_anime_name}/season_{season}/{file_name}"

    try:
        tqdm.write(f"📤 Uploading {image_type} to Supabase Storage ({bucket_name})...")
        
        storage_client = getattr(uploader, 'supabase_storage', uploader.supabase)

        # 1. Upload file to Supabase
        storage_client.storage.from_(bucket_name).upload(
            file_path,
            image_bytes,
            {"content-type": "image/jpeg"}
        )

        # 2. Get Public URL
        public_url = storage_client.storage.from_(bucket_name).get_public_url(file_path)
        tqdm.write(f"✅ {image_type.capitalize()} uploaded successfully to Supabase!")
        return public_url

    except Exception as e:
        tqdm.write(f"❌ Supabase Storage upload failed for {image_type}: {e}")
        return None