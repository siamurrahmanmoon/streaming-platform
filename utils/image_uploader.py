import os
from typing import Optional
from tqdm import tqdm
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config

async def upload_image_to_supabase(uploader, image_bytes: bytes, image_type: str, tmdb_id: int, season: int) -> Optional[str]:
    if not config.ENABLE_IMAGE_STORAGE:
        return None

    bucket_name = config.SUPABASE_STORAGE_BUCKET.lower()
    file_name = f"{image_type}.jpg"
    file_path = f"{tmdb_id}/s{season}/{file_name}"

    try:
        tqdm.write(f"📤 Uploading {image_type} to Supabase Storage...")
        
        storage_client = getattr(uploader, 'supabase_storage', uploader.supabase)

        # ✅ FIX: upsert=True সরিয়ে দেওয়া হয়েছে যাতে পুরনো ভার্সনেও কাজ করে
        storage_client.storage.from_(bucket_name).upload(
            file_path,
            image_bytes,
            {"content-type": "image/jpeg", "cache-control": "public, max-age=31536000"}
        )

        public_url = storage_client.storage.from_(bucket_name).get_public_url(file_path)
        tqdm.write(f"✅ {image_type.capitalize()} uploaded: {public_url}")
        return public_url

    except Exception as e:
        error_str = str(e).lower()
        
        # ✅ SMART FIX: যদি ডুপ্লিকেট এরর আসে, তার মানে ফাইলটি ইতিমধ্যেই আপলোড হয়ে গেছে।
        # সেক্ষেত্রে আমরা শুধু তার URL টি জেনারেট করে রিটার্ন করে দেব।
        if "409" in error_str or "duplicate" in error_str or "already exists" in error_str:
            storage_client = getattr(uploader, 'supabase_storage', uploader.supabase)
            public_url = storage_client.storage.from_(bucket_name).get_public_url(file_path)
            tqdm.write(f"ℹ️ {image_type.capitalize()} already exists in Storage. Using existing URL.")
            return public_url
        
        tqdm.write(f"❌ Supabase Storage upload failed for {image_type}: {e}")
        return None