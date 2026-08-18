import os
import re
import json
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from supabase import create_client, Client
import aiohttp
import aioftp
from tqdm import tqdm
from dotenv import load_dotenv

import config
from utils.retry import retry_with_backoff
from utils.integrity import check_file_integrity
from utils.concurrency import limiter
from utils.file_manager import prepare_and_package, safe_archive_files
from utils.cleanup import cleanup_orphaned_files
from utils.scanner import scan_and_upload  # ✅ নতুন স্ক্যানার মডিউল ইমপোর্ট করা হয়েছে

load_dotenv()

@dataclass
class VideoMetadata:
    file_path: str
    file_name: str
    file_size: int
    anime_name: str
    season: int
    episode: int
    episode_number: str
    languages: List[str]
    language_tag: str
    quality: str
    upload_date: str
    doodstream_url: str = ""
    mixdrop_url: str = ""
    streamtape_url: str = ""
    status: str = "pending"

class AnimeVideoUploader:
    def __init__(self):
        config.print_config()
        self.supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
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
        match = re.search(r'^(?P<anime>.*?)\s*(?:\[(?P<language>[^\]]+)\])?\s*[-]\s*S(?P<season>\d+)E(?P<episode>\d+)\s*[-]\s*(?P<quality>\d{3,4}[Pp])$', stem, re.IGNORECASE)
        if not match: return None
        
        lang_str = match.group('language')
        langs = ['Original']
        if lang_str:
            langs = [l.strip().title() for l in re.split(r'\s*[|/&,-]\s*', lang_str) if l.strip()]
            
        return {
            'anime_name': match.group('anime').strip(), 'season': int(match.group('season')),
            'episode': int(match.group('episode')), 'episode_number': f"S{match.group('season')}E{match.group('episode')}",
            'languages': langs, 'language_tag': lang_str.strip() if lang_str else 'original',
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
                tqdm.write(f"❌ DoodStream Error: {e}")
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
                with open(file_path, 'rb') as f:
                    form_data.add_field('file', f, filename=file_name)
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.mixdrop_api_url, data=form_data, timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_PER_FILE)) as resp:
                        result = await resp.json()
                        if result.get('success'):
                            return result['result'].get('url') or f"https://mixdrop.ag/f/{result['result'].get('fileref', '')}"
                        raise Exception(result.get('message', 'Unknown API Error'))
            except Exception as e:
                tqdm.write(f"❌ MixDrop Error: {e}")
                raise

    @retry_with_backoff()
    async def upload_to_streamtape(self, file_path: str) -> Optional[str]:
        if not config.ENABLE_STREAMTAPE or not self.streamtape_login: return None
        async with limiter:
            file_name = os.path.basename(file_path)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(config.STREAMTAPE_API_URL, params={'login': self.streamtape_login, 'key': self.streamtape_key}) as resp:
                        result = await resp.json()
                        if result.get('status') != 200: raise Exception(result.get('msg', 'Unknown'))
                        upload_url = result['result']['url']
                    
                    with open(file_path, 'rb') as f:
                        form_data = aiohttp.FormData()
                        form_data.add_field('file1', f, filename=file_name)
                        async with session.post(upload_url, data=form_data, timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_PER_FILE)) as resp:
                            text = await resp.text()
                            match = re.search(r'(https://streamtape\.com/v/[a-zA-Z0-9]+/[^\s"<]+)', text)
                            if match: return match.group(0)
                            raise Exception("URL parsing failed")
            except Exception as e:
                tqdm.write(f"❌ StreamTape Error: {e}")
                raise

    def save_to_supabase(self, metadata: VideoMetadata):
        if not config.ENABLE_DATABASE_SAVE: 
            return None
        try:
            return self.supabase.table('videos').upsert({
                'file_path': metadata.file_path, 
                'file_name': metadata.file_name, 
                'file_size': metadata.file_size,         
                'title': metadata.anime_name, 
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
                'streamtape_url': metadata.streamtape_url
            }, on_conflict='file_path').execute().data
        except Exception as e:
            tqdm.write(f"❌ Supabase Error: {e}")
            return None

    async def upload_single_video(self, original_file_path: str):
        if not os.path.exists(original_file_path): return

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

        # 2. Prepare & Package (if subtitles/NFO exist)
        files_to_archive = [original_file_path]
        upload_path = original_file_path
        upload_file_name = file_name

        if config.ENABLE_SUBTITLE_NFO_SUPPORT:
            path = Path(original_file_path)
            has_related = any((path.parent / f"{path.stem}{ext}").exists() for ext in config.SUBTITLE_EXTENSIONS | config.NFO_EXTENSIONS)
            if has_related:
                tqdm.write(f"📦 Packaging with Subtitles/NFO...")
                upload_path, files_to_archive = prepare_and_package(original_file_path)
                upload_file_name = os.path.basename(upload_path)

        file_size = os.path.getsize(upload_path)
        metadata = VideoMetadata(
            file_path=original_file_path, file_name=upload_file_name, file_size=file_size,
            anime_name=parsed['anime_name'], season=parsed['season'], episode=parsed['episode'],
            episode_number=parsed['episode_number'], languages=parsed['languages'],
            language_tag=parsed['language_tag'], quality=parsed['quality'],
            upload_date=datetime.now().isoformat()
        )

        tqdm.write(f"\n📤 Uploading: {upload_file_name} ({file_size / (1024*1024):.2f} MB)")

        # 3. Concurrent Uploads
        tasks = []
        if config.ENABLE_DOODSTREAM: tasks.append(self.upload_to_doodstream_ftp(upload_path))
        if config.ENABLE_STREAMTAPE: tasks.append(self.upload_to_streamtape(upload_path))
        if config.ENABLE_MIXDROP: tasks.append(self.upload_to_mixdrop(upload_path))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        metadata.doodstream_url = str(results[0]) if not isinstance(results[0], Exception) and results[0] else ""
        metadata.streamtape_url = str(results[1]) if len(results)>1 and not isinstance(results[1], Exception) and results[1] else ""
        metadata.mixdrop_url = str(results[2]) if len(results)>2 and not isinstance(results[2], Exception) and results[2] else ""

        # 4. Determine Status
        uploaded_count = sum(1 for url in [metadata.doodstream_url, metadata.mixdrop_url, metadata.streamtape_url] if url)
        metadata.status = "completed" if uploaded_count >= 1 else "failed"

        # 5. Safe Archive
        safe_archive_files(files_to_archive, metadata.status)

        # 6. Cleanup Temp ZIP if created
        if upload_path != original_file_path and os.path.exists(upload_path):
            try:
                os.remove(upload_path)
                staging_dir = Path(upload_path).parent
                if not any(staging_dir.iterdir()): staging_dir.rmdir()
            except Exception as e:
                tqdm.write(f"⚠️ Temp cleanup failed: {e}")

        # 7. Save to DB
        db_result = self.save_to_supabase(metadata)
        if db_result:
            tqdm.write(f"✅ DB Updated: {metadata.status} | Links: {uploaded_count}/3")
        else:
            tqdm.write(f"⚠️ DB Save failed!")

async def main():
    try:
        uploader = AnimeVideoUploader()
        video_folder = os.getenv('VIDEO_FOLDER', './videos')
        
        # Run Orphan Cleanup at startup
        if config.ENABLE_ORPHAN_CLEANUP:
            cleanup_orphaned_files(video_folder)

        if config.ENABLE_CONTINUOUS_SCAN:
            tqdm.write("🔄 Continuous scan mode ENABLED. Press Ctrl+C to stop.")
            scan_count = 1
            while True:
                tqdm.write(f"\n{'='*60}\n🔍 Scan Cycle #{scan_count}\n{'='*60}")
                
                # ✅ নতুন স্ক্যানার ফাংশন কল করা হচ্ছে
                await scan_and_upload(uploader, video_folder)
                
                tqdm.write(f"\n⏳ Waiting {getattr(config, 'SCAN_INTERVAL_SECONDS', 60)}s before next scan...")
                await asyncio.sleep(getattr(config, 'SCAN_INTERVAL_SECONDS', 60))
                scan_count += 1
        else:
            # ✅ নতুন স্ক্যানার ফাংশন কল করা হচ্ছে
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