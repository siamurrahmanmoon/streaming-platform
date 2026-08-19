import os
import asyncio
from pathlib import Path
from tqdm import tqdm
import sys

# Ensure parent directory is in path for config import
sys.path.append(str(Path(__file__).parent.parent))
import config
from utils.processor import process_single_video


async def scan_and_upload(supabase_client, supabase_storage_client, folder_path: str):
    """
    Scans the folder for new videos, checks DB for duplicates,
    and uploads them concurrently based on config.MAX_CONCURRENT_UPLOADS.
    """
    if not os.path.exists(folder_path):
        tqdm.write(f"❌ Folder not found: {folder_path}")
        return

    video_extensions = set(ext.lower() for ext in config.SUPPORTED_EXTENSIONS)
    video_files = []

    tqdm.write(f"🔍 Scanning folder: {folder_path}\n")

    # 1. Scan files and check duplicates
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if Path(file).suffix.lower() in video_extensions:
                file_path = os.path.join(root, file)

                if config.CHECK_DUPLICATE_IN_DB:
                    try:
                        # ✅ Updated: Using supabase_client directly instead of uploader.supabase
                        result = (
                            supabase_client.table("videos")
                            .select("id")
                            .eq("file_path", file_path)
                            .execute()
                        )
                        if len(result.data) == 0:
                            video_files.append(file_path)
                        else:
                            tqdm.write(f"⏭️  Already in database: {file}")
                            try:
                                os.remove(file_path)
                                tqdm.write(f"🗑️  Deleted local duplicate: {file}")
                            except OSError as e:
                                tqdm.write(
                                    f"⚠️  Could not delete local duplicate {file}: {e}"
                                )
                    except Exception as e:
                        tqdm.write(f"⚠️ DB check failed for {file}, adding anyway: {e}")
                        video_files.append(file_path)
                else:
                    video_files.append(file_path)

    if not video_files:
        tqdm.write("✅ No new videos found in this scan!")
        return

    tqdm.write(f"\n📁 Found {len(video_files)} new videos to upload")
    tqdm.write(
        f"⚡ Concurrent Upload Limit: {config.MAX_CONCURRENT_UPLOADS} files at a time\n"
    )

    # 2. Setup Semaphore for Concurrency Control
    max_concurrent = max(1, config.MAX_CONCURRENT_UPLOADS)  # Ensure at least 1
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_limit(video_index, file_path):
        async with semaphore:
            await process_single_video(
                file_path, supabase_client, supabase_storage_client, video_index
            )

    # 3. Execute Concurrently
    tasks = [
        process_with_limit(video_index, file_path)
        for video_index, file_path in enumerate(video_files)
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    tqdm.write(f"\n{'='*70}")
    tqdm.write(f"✅ All {len(video_files)} videos processed in this batch!")
    tqdm.write(f"{'='*70}")
