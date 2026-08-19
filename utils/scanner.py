import os
import asyncio
from pathlib import Path
from tqdm import tqdm
import sys

# Ensure parent directory is in path for config import
sys.path.append(str(Path(__file__).parent.parent))
import config
from utils.parser import parse_video_filename
from utils.processor import process_single_video


def _video_exists_in_normalized_database(supabase_client, file_name: str) -> bool:
    parsed = parse_video_filename(file_name)
    if not parsed:
        return False

    db_media_type = "tv_series" if parsed["media_type"] == "TV Series" else "movie"
    language_code = (
        "en"
        if parsed["language_tag"].lower() == "original"
        else parsed["language_tag"].lower()
    )
    media_query = (
        supabase_client.table("media")
        .select("id")
        .eq("title", parsed["title"])
        .eq("media_type", db_media_type)
        .eq("language_code", language_code)
    )
    if parsed.get("year") is not None:
        media_query = media_query.eq("release_year", parsed["year"])

    media_result = media_query.limit(1).execute()
    if not media_result.data:
        return False

    media_id = media_result.data[0]["id"]
    source_query = (
        supabase_client.table("video_sources")
        .select("id")
        .eq("quality", parsed["quality"])
    )

    if parsed["media_type"] == "TV Series":
        season_result = (
            supabase_client.table("seasons")
            .select("id")
            .eq("media_id", media_id)
            .eq("season_number", parsed["season"])
            .limit(1)
            .execute()
        )
        if not season_result.data:
            return False

        episode_result = (
            supabase_client.table("episodes")
            .select("id")
            .eq("season_id", season_result.data[0]["id"])
            .eq("episode_number", parsed["episode"])
            .limit(1)
            .execute()
        )
        if not episode_result.data:
            return False
        source_query = source_query.eq("episode_id", episode_result.data[0]["id"])
    else:
        source_query = source_query.eq("media_id", media_id)

    return bool(source_query.limit(1).execute().data)


async def scan_and_upload(supabase_client, supabase_storage_client, folder_path: str):
    """
    Scans the folder for new videos, checks DB for duplicates,
    and uploads them concurrently based on config.MAX_CONCURRENT_UPLOADS.
    """
    status_line_open = True

    def write_scan_message(message: str):
        nonlocal status_line_open
        if status_line_open:
            print()
            status_line_open = False
        tqdm.write(message)

    if not os.path.exists(folder_path):
        write_scan_message(f"❌ Folder not found: {folder_path}")
        return

    video_extensions = set(ext.lower() for ext in config.SUPPORTED_EXTENSIONS)
    video_files = []

    # 1. Scan files and check duplicates
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if Path(file).suffix.lower() in video_extensions:
                file_path = os.path.join(root, file)

                parsed = parse_video_filename(file)
                if (
                    config.REQUIRE_YEAR_IN_FILENAME
                    and parsed
                    and parsed.get("year") is None
                ):
                    video_files.append(file_path)
                    continue

                if config.CHECK_DUPLICATE_IN_DB:
                    try:
                        if not _video_exists_in_normalized_database(
                            supabase_client, file
                        ):
                            video_files.append(file_path)
                        else:
                            write_scan_message(f"⏭️  Already in database: {file}")
                            try:
                                os.remove(file_path)
                                write_scan_message(
                                    f"🗑️  Deleted local duplicate: {file}"
                                )
                            except OSError as e:
                                write_scan_message(
                                    f"⚠️  Could not delete local duplicate {file}: {e}"
                                )
                    except Exception as e:
                        write_scan_message(
                            f"⚠️ DB check failed for {file}, adding anyway: {e}"
                        )
                        video_files.append(file_path)
                else:
                    video_files.append(file_path)

    if not video_files:
        return

    write_scan_message(f"📁 Found {len(video_files)} new videos to upload")
    write_scan_message(
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

    write_scan_message(f"✅ All {len(video_files)} videos processed in this batch!")
