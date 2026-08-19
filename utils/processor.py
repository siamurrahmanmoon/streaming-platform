import asyncio
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from supabase import Client
from tqdm import tqdm

import config
from utils.alerts import alert_manager
from utils.db_manager import get_db_manager
from utils.disk_monitor import disk_monitor
from utils.file_manager import (
    cleanup_temp_staging,
    move_to_unmatched,
    prepare_and_package,
    safe_archive_files,
)
from utils.integrity import check_file_integrity
from utils.logger import get_logger
from utils.metadata import fetch_and_process_metadata
from utils.models import VideoMetadata
from utils.parser import parse_video_filename
from utils.uploaders import (
    upload_to_doodstream_api,
    upload_to_mixdrop,
    upload_to_streamtape,
)

log = get_logger("processor")


async def process_single_video(
    original_file_path: str,
    supabase_client: Client,
    supabase_storage_client: Client,
    video_index: int = 0,
):
    if config.CHECK_DISK_BEFORE_UPLOAD:
        video_folder = config.VIDEO_FOLDER
        if not await disk_monitor.check_and_alert(video_folder):
            log.error("🚨 Disk space critical! Skipping upload.")
            await alert_manager.notify_critical(
                "Upload Skipped",
                f"Disk space critical. File skipped: {original_file_path}",
            )
            return

    if not os.path.exists(original_file_path):
        tqdm.write(f"⚠️ File not found, skipping: {original_file_path}")
        return

    if config.ENABLE_INTEGRITY_CHECK and not check_file_integrity(original_file_path):
        tqdm.write(f"❌ Integrity check failed: {original_file_path}")
        safe_archive_files([original_file_path], "failed")
        return

    file_name = os.path.basename(original_file_path)
    parsed = parse_video_filename(file_name)
    if not parsed:
        tqdm.write(f"❌ Could not parse: {file_name}")
        safe_archive_files([original_file_path], "failed")
        return

    if config.REQUIRE_YEAR_IN_FILENAME and parsed.get("year") is None:
        tqdm.write(f"❌ Missing year in filename: {file_name}")
        await alert_manager.notify_missing_video_year(file_name, parsed["title"])
        move_to_unmatched(original_file_path, file_name)
        return

    metadata_obj = None
    if config.ENABLE_TMDB_METADATA:
        try:
            metadata_obj = await fetch_and_process_metadata(
                supabase_client,
                supabase_storage_client,
                parsed["title"],
                parsed["media_type"],
                parsed.get("season"),
                parsed.get("year"),
            )
            if not metadata_obj:
                await alert_manager.notify_unmatched_video(
                    file_name, parsed["title"], parsed.get("year")
                )
                move_to_unmatched(original_file_path, file_name)
                return
        except Exception as error:
            log.error(f"⚠️ Metadata fetch or DB save failed: {error}")

    files_to_archive = [original_file_path]
    upload_path = original_file_path
    upload_file_name = file_name
    if config.ENABLE_SUBTITLE_NFO_SUPPORT:
        path = Path(original_file_path)
        if any(
            (path.parent / f"{path.stem}{extension}").exists()
            for extension in config.SUBTITLE_EXTENSIONS | config.NFO_EXTENSIONS
        ):
            upload_path, files_to_archive = prepare_and_package(original_file_path)
            upload_file_name = os.path.basename(upload_path)

    metadata = VideoMetadata(
        file_path=original_file_path,
        file_name=upload_file_name,
        file_size=os.path.getsize(upload_path),
        title=parsed["title"],
        media_type=parsed["media_type"],
        season=parsed["season"],
        episode=parsed["episode"],
        episode_number=parsed["episode_number"],
        languages=parsed["languages"],
        language_tag=parsed["language_tag"],
        quality=parsed["quality"],
        upload_date=datetime.now().isoformat(),
    )
    if metadata_obj:
        for key, value in metadata_obj.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

    position_base = video_index * 3
    upload_tasks = {}
    loop = asyncio.get_event_loop()
    if config.ENABLE_DOODSTREAM:
        upload_tasks["doodstream_url"] = loop.run_in_executor(
            None,
            upload_to_doodstream_api,
            upload_path,
            os.getenv("DOODSTREAM_API_KEY"),
            position_base,
        )
    if config.ENABLE_STREAMTAPE:
        upload_tasks["streamtape_url"] = loop.run_in_executor(
            None,
            upload_to_streamtape,
            upload_path,
            os.getenv("STREAMTAPE_LOGIN"),
            os.getenv("STREAMTAPE_PASSWORD"),
            position_base + 1,
        )
    if config.ENABLE_MIXDROP:
        upload_tasks["mixdrop_url"] = loop.run_in_executor(
            None,
            upload_to_mixdrop,
            upload_path,
            os.getenv("MIXDROP_EMAIL"),
            os.getenv("MIXDROP_KEY"),
            os.getenv("MIXDROP_API_URL", config.MIXDROP_API_URL),
            position_base + 2,
        )

    results = await asyncio.gather(*upload_tasks.values(), return_exceptions=True)
    for field_name, result in zip(upload_tasks, results):
        if not isinstance(result, Exception) and result:
            setattr(metadata, field_name, str(result))

    uploaded_count = sum(
        bool(url)
        for url in (
            metadata.doodstream_url,
            metadata.mixdrop_url,
            metadata.streamtape_url,
        )
    )
    metadata.status = "completed" if uploaded_count else "failed"
    safe_archive_files(files_to_archive, metadata.status)
    if upload_path != original_file_path:
        cleanup_temp_staging(upload_path)

    # ==========================================
    # NEW NORMALIZED DATABASE SAVE LOGIC
    # ==========================================
    db_manager = get_db_manager(supabase_client)

    if not config.ENABLE_DATABASE_SAVE:
        return

    # 1. Prepare video sources list
    video_sources = []
    if metadata.doodstream_url:
        video_sources.append(
            {
                "server_name": "DoodStream",
                "quality": metadata.quality,
                "video_url": metadata.doodstream_url,
                "is_default": True,
            }
        )
    if metadata.mixdrop_url:
        video_sources.append(
            {
                "server_name": "MixDrop",
                "quality": metadata.quality,
                "video_url": metadata.mixdrop_url,
            }
        )
    if metadata.streamtape_url:
        video_sources.append(
            {
                "server_name": "StreamTape",
                "quality": metadata.quality,
                "video_url": metadata.streamtape_url,
            }
        )

    try:
        # 2. Save/Get Media ID
        media_id = db_manager.ensure_media_exists(
            title=metadata.title,
            media_type=metadata.media_type,
            language_tag=metadata.language_tag,
            year=metadata.release_year,
            metadata=asdict(metadata),
        )

        if media_id:
            # 3. Save Genres
            db_manager.save_genres(media_id, metadata.genres)
            db_manager.save_tags(media_id, metadata.keywords)

            # 4. Handle Series (Seasons & Episodes) vs Movies
            episode_id = None
            if (
                metadata.media_type == "TV Series"
                and metadata.season
                and metadata.episode
            ):
                season_id = db_manager.ensure_season_exists(media_id, metadata.season)
                if season_id:
                    episode_title = f"Episode {metadata.episode}"
                    episode_id = db_manager.ensure_episode_exists(
                        season_id, metadata.episode, episode_title
                    )

            # 5. Save Video Sources
            if video_sources:
                db_manager.save_video_sources(episode_id, media_id, video_sources)

            tqdm.write(
                f"✅ Database Updated: Media ID {media_id} | Episode ID {episode_id} "
                f"| Links: {len(video_sources)}/3"
            )
            if metadata.status == "completed":
                await alert_manager.notify_video_upload_success(metadata)
        else:
            tqdm.write("⚠️ Failed to save media to database!")
    except Exception as error:
        log.exception(f"❌ Normalized database save failed: {error}")
        tqdm.write(f"❌ Database save failed: {error}")
