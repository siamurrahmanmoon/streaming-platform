import os
import re
import json
import sys
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from supabase import create_client, Client
import aiohttp
import aioftp
from tqdm import tqdm
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

import config
from utils.retry import retry_with_backoff
from utils.integrity import check_file_integrity
from utils.concurrency import limiter
from utils.file_manager import prepare_and_package, safe_archive_files
from utils.cleanup import cleanup_orphaned_files
from utils.scanner import scan_and_upload
from utils.metadata import fetch_and_process_metadata
from utils.logger import get_logger
from utils.alerts import alert_manager
from utils.disk_monitor import disk_monitor
from utils.rate_limiter import rate_limiter

log = get_logger("main")

@dataclass
class VideoMetadata:
    file_path: str
    file_name: str
    file_size: int
    title: str
    media_type: str = "TV Series"
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_number: Optional[str] = None
    languages: List[str] = field(default_factory=lambda: ['Original'])
    language_tag: str = "original"
    quality: str = "unknown"
    upload_date: str = ""
    doodstream_url: str = ""
    mixdrop_url: str = ""
    streamtape_url: str = ""
    status: str = "pending"
    release_year: int = 0
    total_seasons: int = 0
    total_episodes: int = 0
    tmdb_status: str = ""
    original_language: str = ""
    networks: List[str] = field(default_factory=list)
    creators: List[str] = field(default_factory=list)
    tmdb_id: int = 0
    overview: str = ""
    genres: List[Dict[str, str]] = field(default_factory=list)
    vote_average: float = 0.0
    poster_url: str = ""
    banner_url: str = ""
    thumbnail_url: str = ""

class AnimeVideoUploader:
    def __init__(self):
        config.print_config()
        log.info("🚀 Starting Anime Video Uploader...")

        if config.CHECK_DISK_BEFORE_UPLOAD:
            video_folder = os.getenv('VIDEO_FOLDER', './videos')
            asyncio.create_task(disk_monitor.check_and_alert(video_folder))

        supabase_url = os.getenv('SUPABASE_URL')
        
        # Standard client for Database operations
        self.supabase = create_client(supabase_url, os.getenv('SUPABASE_KEY'))

        # Service role client for Storage operations (Bypasses RLS)
        service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        if service_key:
            self.supabase_storage = create_client(supabase_url, service_key)
        else:
            tqdm.write("⚠️ SUPABASE_SERVICE_ROLE_KEY missing. Storage uploads may fail due to RLS.")
            self.supabase_storage = self.supabase

        self.dood_ftp_server = os.getenv('DOODSTREAM_FTP_SERVER', config.DOODSTREAM_FTP_SERVER)
        self.dood_username = os.getenv('DOODSTREAM_USERNAME')
        self.dood_password = os.getenv('DOODSTREAM_PASSWORD')
        self.mixdrop_api_url = os.getenv('MIXDROP_API_URL', config.MIXDROP_API_URL)
        self.mixdrop_email = os.getenv('MIXDROP_EMAIL')
        self.mixdrop_key = os.getenv('MIXDROP_KEY')
        self.streamtape_login = os.getenv('STREAMTAPE_LOGIN')
        self.streamtape_key = os.getenv('STREAMTAPE_PASSWORD')

    def parse_video_filename(self, filename: str) -> Optional[Dict]:
        stem = Path(filename).stem.replace('_', ' ').strip()

        # TV Series Regex
        tv_match = re.search(
            r'^(?P<title>.*?)\s*(?:\((?P<year>\d{4})\))?\s*(?:\[(?P<language>[^\]]+)\])?\s*[-]\s*S(?P<season>\d+)E(?P<episode>\d+)\s*[-]\s*(?P<quality>\d{3,4}[Pp])$',
            stem, re.IGNORECASE
        )
        if tv_match:
            return self._build_metadata_dict(tv_match, 'TV Series')

        # Movie Regex
        movie_match = re.search(
            r'^(?P<title>.*?)\s*(?:\((?P<year>\d{4})\))?\s*(?:\[(?P<language>[^\]]+)\])?\s*[-]?\s*(?P<quality>\d{3,4}[Pp])$',
            stem, re.IGNORECASE
        )
        if movie_match:
            return self._build_metadata_dict(movie_match, 'Movie')

        return None

    def _build_metadata_dict(self, match, media_type: str) -> Dict:
        title = match.group('title').strip()
        year_str = match.groupdict().get('year')

        # Extract an unparenthesized year from anywhere in the title.
        if not year_str:
            year_match = re.search(r'\b(19|20)\d{2}\b', title)
            if year_match:
                year_str = year_match.group(0)
                title = re.sub(r'\s*\b' + year_str + r'\b\s*', ' ', title).strip()

        lang_str = match.group('language')
        season_str = match.groupdict().get('season')
        episode_str = match.groupdict().get('episode')
        langs = ['Original']
        if lang_str:
            langs = [l.strip().title() for l in re.split(r'\s*[|/&,-]\s*', lang_str) if l.strip()]

        return {
            'media_type': media_type,
            'title': title,
            'year': int(year_str) if year_str else None,
            'season': int(season_str) if season_str else None,
            'episode': int(episode_str) if episode_str else None,
            'episode_number': f"S{season_str}E{episode_str}" if season_str else None,
            'languages': langs,
            'language_tag': lang_str.strip() if lang_str else 'original',
            'quality': (match.group('quality') or 'unknown').upper()
        }

    @retry_with_backoff()
    async def upload_to_doodstream_ftp(self, file_path: str) -> Optional[str]:
        if not config.ENABLE_DOODSTREAM or not self.dood_username: return None
        async with limiter:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            try:
                async with aioftp.Client.context(self.dood_ftp_server, user=self.dood_username, password=self.dood_password) as client:
                    with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"📤 Dood: {file_name[:30]}", leave=False) as pbar:
                        async with client.upload_stream(file_name) as stream:
                            with open(file_path, 'rb') as f:
                                while True:
                                    chunk = await limiter.throttled_read(f, config.FTP_CHUNK_SIZE)
                                    if not chunk: break
                                    await stream.write(chunk)
                                    pbar.update(len(chunk))
                return f"https://doodstream.com/d/{file_name}"
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Too Many Requests" in error_str:
                    await rate_limiter.check_rate_limit("DoodStream", 429)
                log.error(f"❌ DoodStream Error: {e}")
                raise

    @retry_with_backoff()
    async def upload_to_mixdrop(self, file_path: str) -> Optional[str]:
        if not config.ENABLE_MIXDROP or not self.mixdrop_email: return None
        async with limiter:
            file_name = os.path.basename(file_path)
            try:
                form_data = aiohttp.FormData()
                form_data.add_field('email', self.mixdrop_email)
                form_data.add_field('key', self.mixdrop_key)
                async with aiohttp.ClientSession() as session:
                    with open(file_path, 'rb') as f:
                        form_data.add_field('file', f, filename=file_name)
                        async with session.post(self.mixdrop_api_url, data=form_data, timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_PER_FILE)) as resp:
                            result = await resp.json()
                            if result.get('success'):
                                return result['result'].get('url') or f"https://mixdrop.ag/f/{result['result'].get('fileref', '')}"
                            raise Exception(result.get('message', 'Unknown API Error'))
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Too Many Requests" in error_str:
                    await rate_limiter.check_rate_limit("MixDrop", 429)
                log.error(f"❌ MixDrop Error: {e}")
                raise

    @retry_with_backoff()
    async def upload_to_streamtape(self, file_path: str) -> Optional[str]:
        if not config.ENABLE_STREAMTAPE or not self.streamtape_login: return None
        async with limiter:
            file_name = os.path.basename(file_path)
            try:
                params = {'login': self.streamtape_login, 'key': self.streamtape_key}
                async with aiohttp.ClientSession() as session:
                    async with session.get(config.STREAMTAPE_API_URL, params=params) as resp:
                        result = await resp.json()
                        if result.get('status') != 200: raise Exception(result.get('msg', 'Unknown'))
                        upload_url = result['result']['url']
                    
                    with open(file_path, 'rb') as f:
                        form_data = aiohttp.FormData()
                        form_data.add_field('file1', f, filename=file_name)
                        async with session.post(upload_url, data=form_data, timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_PER_FILE)) as resp:
                            text = await resp.text()
                            try:
                                upload_result = json.loads(text)
                            except json.JSONDecodeError:
                                upload_result = {}

                            if upload_result.get('status') not in (None, 200):
                                raise Exception(upload_result.get('msg', 'Upload failed'))

                            result = upload_result.get('result', {})
                            if isinstance(result, dict):
                                public_url = result.get('link') or result.get('video_link')
                                if public_url:
                                    return public_url

                                file_id = result.get('id') or result.get('file') or result.get('linkid')
                                if file_id:
                                    return f"https://streamtape.com/v/{file_id}/{quote(file_name)}"

                            match = re.search(r'(https://(?:streamtape\.com|tapecontent\.net)/[^\s"<>]+)', text)
                            if match:
                                return match.group(1)

                            raise Exception("Upload completed but no StreamTape file link was returned")
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Too Many Requests" in error_str:
                    await rate_limiter.check_rate_limit("StreamTape", 429)
                log.error(f"❌ StreamTape Error: {e}")
                raise

    def save_to_supabase(self, metadata: VideoMetadata):
        if not config.ENABLE_DATABASE_SAVE: 
            return None
        try:
            return self.supabase.table('videos').upsert({
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
            return None

    async def upload_single_video(self, original_file_path: str):
        if config.CHECK_DISK_BEFORE_UPLOAD:
            video_folder = os.getenv('VIDEO_FOLDER', './videos')
            is_ok = await disk_monitor.check_and_alert(video_folder)
            if not is_ok:
                log.error("🚨 Disk space critical! Skipping upload.")
                await alert_manager.notify_critical(
                    "Upload Skipped",
                    f"Disk space critical. File skipped: {original_file_path}"
                )
                return

        if not os.path.exists(original_file_path):
            tqdm.write(f"⚠️ File not found, skipping: {original_file_path}")
            return

        # 1. Integrity Check
        if config.ENABLE_INTEGRITY_CHECK and not check_file_integrity(original_file_path):
            tqdm.write(f"❌ Integrity check failed: {original_file_path}")
            safe_archive_files([original_file_path], "failed")
            return

        file_name = os.path.basename(original_file_path)
        parsed = self.parse_video_filename(file_name)
        if not parsed:
            tqdm.write(f"❌ Could not parse: {file_name}")
            safe_archive_files([original_file_path], "failed")
            return

        # 2. Fetch metadata before uploading the video.
        metadata_obj = None
        if config.ENABLE_TMDB_METADATA:
            try:
                tqdm.write("\n🔍 Checking metadata BEFORE upload...")
                metadata_obj = await fetch_and_process_metadata(
                    self,
                    parsed['title'],
                    parsed['media_type'],
                    parsed.get('season'),
                    parsed.get('year')
                )

                if not metadata_obj:
                    tqdm.write("❌ No metadata found! Moving to unmatched folder...")
                    await alert_manager.notify_unmatched_video(
                        file_name, parsed['title'], parsed.get('year')
                    )
                    await self._move_to_unmatched(original_file_path, file_name)
                    return

                tqdm.write("✅ Metadata verified! Proceeding with upload...")
            except Exception as e:
                log.error(f"⚠️ Metadata fetch failed: {e}")
                # Metadata errors should not prevent the video upload.

        files_to_archive = [original_file_path]
        upload_path = original_file_path
        upload_file_name = file_name

        # 3. Prepare & Package (if subtitles/NFO exist)
        if config.ENABLE_SUBTITLE_NFO_SUPPORT:
            path = Path(original_file_path)
            has_related = any((path.parent / f"{path.stem}{ext}").exists() for ext in config.SUBTITLE_EXTENSIONS | config.NFO_EXTENSIONS)
            if has_related:
                tqdm.write(f"📦 Packaging with Subtitles/NFO...")
                upload_path, files_to_archive = prepare_and_package(original_file_path)
                upload_file_name = os.path.basename(upload_path)

        file_size = os.path.getsize(upload_path)
        
        # 4. Create Metadata Object
        metadata = VideoMetadata(
            file_path=original_file_path, 
            file_name=upload_file_name, 
            file_size=file_size,
            title=parsed['title'],
            media_type=parsed['media_type'],
            season=parsed['season'], 
            episode=parsed['episode'],
            episode_number=parsed['episode_number'], 
            languages=parsed['languages'],
            language_tag=parsed['language_tag'], 
            quality=parsed['quality'],
            upload_date=datetime.now().isoformat()
        )

        if metadata_obj:
            metadata.tmdb_id = metadata_obj.get('tmdb_id', 0)
            metadata.release_year = metadata_obj.get('release_year', 0)
            metadata.total_seasons = metadata_obj.get('total_seasons', 0)
            metadata.total_episodes = metadata_obj.get('total_episodes', 0)
            metadata.tmdb_status = metadata_obj.get('tmdb_status', '')
            metadata.original_language = metadata_obj.get('original_language', '')
            metadata.networks = metadata_obj.get('networks', [])
            metadata.creators = metadata_obj.get('creators', [])
            metadata.overview = metadata_obj.get('overview', '')
            metadata.genres = metadata_obj.get('genres', [])
            metadata.vote_average = metadata_obj.get('vote_average', 0.0)
            metadata.poster_url = metadata_obj.get('poster_url', '')
            metadata.banner_url = metadata_obj.get('banner_url', '')
            metadata.thumbnail_url = metadata_obj.get('thumbnail_url', '')

        tqdm.write(f"\n📤 Uploading: {upload_file_name} ({file_size / (1024*1024):.2f} MB)")

        # 5. Concurrent Video Uploads
        upload_tasks = {}
        if config.ENABLE_DOODSTREAM:
            upload_tasks['doodstream_url'] = self.upload_to_doodstream_ftp(upload_path)
        if config.ENABLE_STREAMTAPE:
            upload_tasks['streamtape_url'] = self.upload_to_streamtape(upload_path)
        if config.ENABLE_MIXDROP:
            upload_tasks['mixdrop_url'] = self.upload_to_mixdrop(upload_path)

        results = await asyncio.gather(*upload_tasks.values(), return_exceptions=True)
        for field_name, result in zip(upload_tasks, results):
            if not isinstance(result, Exception) and result:
                setattr(metadata, field_name, str(result))

        uploaded_count = sum(1 for url in [metadata.doodstream_url, metadata.mixdrop_url, metadata.streamtape_url] if url)
        metadata.status = "completed" if uploaded_count >= 1 else "failed"

        # 6. Safe Archive
        safe_archive_files(files_to_archive, metadata.status)

        # 7. Cleanup Temp ZIP if created
        if upload_path != original_file_path and os.path.exists(upload_path):
            try:
                os.remove(upload_path)
                staging_dir = Path(upload_path).parent
                if not any(staging_dir.iterdir()): staging_dir.rmdir()
            except Exception as e:
                tqdm.write(f"⚠️ Temp cleanup failed: {e}")

        # 8. Save to DB
        db_result = self.save_to_supabase(metadata)
        if db_result and metadata.status == "completed":
            tqdm.write(f"✅ DB Updated: {metadata.status} | Links: {uploaded_count}/3")
            await alert_manager.notify_video_upload_success(metadata)
        elif metadata.status == "failed":
            tqdm.write("❌ Upload Failed!")
            await alert_manager.notify_critical(
                "Upload Failed",
                f"File: {file_name}\nNo platform upload succeeded."
            )
        elif not db_result:
            tqdm.write(f"⚠️ DB Save failed!")

    async def _move_to_unmatched(self, file_path: str, file_name: str):
        """Move a video without metadata to the manual-review folder."""
        try:
            unmatched_folder = Path(config.UNMATCHED_VIDEOS_FOLDER)
            unmatched_folder.mkdir(parents=True, exist_ok=True)

            dest_path = unmatched_folder / file_name
            counter = 1
            while dest_path.exists():
                stem = Path(file_name).stem
                suffix = Path(file_name).suffix
                dest_path = unmatched_folder / f"{stem}_{counter}{suffix}"
                counter += 1

            shutil.move(file_path, str(dest_path))
            tqdm.write(f"📁 Moved to unmatched: {dest_path.name}")
            tqdm.write("💡 Tip: Rename the file to match TMDB/OMDb naming convention")
        except Exception as e:
            tqdm.write(f"❌ Failed to move to unmatched folder: {e}")

async def main():
    try:
        uploader = AnimeVideoUploader()
        video_folder = os.getenv('VIDEO_FOLDER', './videos')
        
        if config.ENABLE_ORPHAN_CLEANUP:
            cleanup_orphaned_files(video_folder)

        if config.ENABLE_CONTINUOUS_SCAN:
            tqdm.write("🔄 Continuous scan mode ENABLED. Press Ctrl+C to stop.")
            scan_count = 1
            while True:
                tqdm.write(f"\n{'='*60}\n🔍 Scan Cycle #{scan_count}\n{'='*60}")
                await scan_and_upload(uploader, video_folder)
                tqdm.write(f"\n⏳ Waiting {config.SCAN_INTERVAL_SECONDS}s before next scan...")
                await asyncio.sleep(config.SCAN_INTERVAL_SECONDS)
                scan_count += 1
        else:
            await scan_and_upload(uploader, video_folder)
            tqdm.write("✅ Single scan completed.")
            
    except KeyboardInterrupt:
        tqdm.write("\n\n🛑 Stopped by user. Exiting gracefully...")
    except Exception as e:
        tqdm.write(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent))
    asyncio.run(main())