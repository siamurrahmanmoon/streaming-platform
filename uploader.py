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

# Import configuration
import config

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

        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        self.supabase = create_client(supabase_url, supabase_key)

        self.dood_ftp_server = os.getenv('DOODSTREAM_FTP_SERVER', config.DOODSTREAM_FTP_SERVER)
        self.dood_username = os.getenv('DOODSTREAM_USERNAME')
        self.dood_password = os.getenv('DOODSTREAM_PASSWORD')

        self.mixdrop_api_url = os.getenv('MIXDROP_API_URL', config.MIXDROP_API_URL)
        self.mixdrop_email = os.getenv('MIXDROP_EMAIL')
        self.mixdrop_key = os.getenv('MIXDROP_KEY')

        self.streamtape_login = os.getenv('STREAMTAPE_LOGIN')
        self.streamtape_key = os.getenv('STREAMTAPE_PASSWORD')

        self._validate_credentials()

    def _validate_credentials(self):
        missing = []
        if config.ENABLE_DOODSTREAM and (not self.dood_username or not self.dood_password):
            missing.append('DOODSTREAM')
        if config.ENABLE_MIXDROP and (not self.mixdrop_email or not self.mixdrop_key):
            missing.append('MIXDROP')
        if config.ENABLE_STREAMTAPE and (not self.streamtape_login or not self.streamtape_key):
            missing.append('STREAMTAPE')
        if missing:
            tqdm.write(f"⚠️ Missing credentials for enabled platforms: {', '.join(missing)}")

    def parse_video_filename(self, filename: str) -> Optional[Dict]:
        stem = Path(filename).stem
        stem = stem.replace('_', ' ')
        stem = re.sub(r'\s+', ' ', stem).strip()

        match = re.search(
            r'^(?P<anime>.*?)\s*(?:\[(?P<language>[^\]]+)\])?\s*[-]\s*S(?P<season>\d+)E(?P<episode>\d+)\s*[-]\s*(?P<quality>\d{3,4}[Pp])$',
            stem,
            re.IGNORECASE,
        )

        if not match:
            return None

        anime_name = match.group('anime').strip()
        language_str = match.group('language')
        quality = (match.group('quality') or 'unknown').upper()
        season = int(match.group('season'))
        episode = int(match.group('episode'))

        language_map = {
            'hi': 'Hindi', 'hindi': 'Hindi', 'en': 'English', 'english': 'English', 'eng': 'English',
            'ja': 'Japanese', 'japanese': 'Japanese', 'jp': 'Japanese', 'bn': 'Bangla', 'bangla': 'Bangla', 'bengali': 'Bangla',
            'ta': 'Tamil', 'tamil': 'Tamil', 'te': 'Telugu', 'telugu': 'Telugu', 'ur': 'Urdu', 'urdu': 'Urdu',
            'ar': 'Arabic', 'arabic': 'Arabic', 'fr': 'French', 'french': 'French', 'es': 'Spanish', 'spanish': 'Spanish',
            'de': 'German', 'german': 'German', 'ko': 'Korean', 'korean': 'Korean', 'zh': 'Chinese', 'chinese': 'Chinese', 'cn': 'Chinese',
            'original': 'Original', 'jap': 'Original', 'sub': 'Subbed', 'dub': 'Dubbed',
        }

        if language_str:
            lang_parts = re.split(r'\s*[|/&,-]\s*', language_str)
            languages = []
            for lang in lang_parts:
                lang = lang.strip().lower()
                normalized = language_map.get(lang, lang.title())
                if normalized not in languages:
                    languages.append(normalized)
            if not languages:
                languages = ['Original']
            language_tag = language_str.strip()
        else:
            languages = ['Original']
            language_tag = 'original'

        return {
            'anime_name': anime_name, 'season': season, 'episode': episode,
            'episode_number': f'S{season}E{episode}', 'languages': languages,
            'language_tag': language_tag, 'quality': quality,
        }

    async def upload_to_doodstream_ftp(self, file_path: str) -> Optional[str]:
        if not config.ENABLE_DOODSTREAM or not self.dood_username or not self.dood_password:
            return None
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            tqdm.write(f"📡 Connecting to DoodStream FTP...")

            async with aioftp.Client.context(self.dood_ftp_server, user=self.dood_username, password=self.dood_password) as client:
                with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"📤 DoodStream: {file_name[:40]}", file=sys.stdout, leave=False) as pbar:
                    async with client.upload_stream(file_name) as stream:
                        with open(file_path, 'rb') as f:
                            while chunk := f.read(config.FTP_CHUNK_SIZE):
                                await stream.write(chunk)
                                pbar.update(len(chunk))
            tqdm.write(f"✅ DoodStream upload complete!")
            return f"https://doodstream.com/d/{file_name}"
        except Exception as e:
            tqdm.write(f"❌ DoodStream FTP error: {e}")
            return None

    async def upload_to_mixdrop(self, file_path: str) -> Optional[str]:
        if not config.ENABLE_MIXDROP or not self.mixdrop_email or not self.mixdrop_key:
            return None
        try:
            file_name = os.path.basename(file_path)
            tqdm.write(f"📡 Uploading to MixDrop (Direct)...")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                form_data.add_field('email', self.mixdrop_email)
                form_data.add_field('key', self.mixdrop_key)
                with open(file_path, 'rb') as f:
                    form_data.add_field('file', f, filename=file_name)
                    async with session.post(self.mixdrop_api_url, data=form_data, headers=headers, timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_PER_FILE)) as response:
                        response_text = await response.text()
                        if response_text.strip().startswith('<html>') or 'cloudflare' in response_text.lower():
                            tqdm.write(f"❌ MixDrop blocked by Cloudflare (HTML response).")
                            return None
                        try:
                            result = json.loads(response_text)
                            if result.get('success'):
                                res = result.get('result', {})
                                fileref = res.get('fileref', '')
                                file_url = res.get('url') or f"https://mixdrop.ag/f/{fileref}"
                                tqdm.write(f"✅ MixDrop upload complete!")
                                return file_url
                            else:
                                tqdm.write(f"❌ MixDrop API Error: {result.get('message', 'Unknown')}")
                                return None
                        except json.JSONDecodeError:
                            tqdm.write(f"❌ MixDrop returned invalid JSON: {response_text[:150]}")
                            return None
        except Exception as e:
            tqdm.write(f"❌ MixDrop upload error: {e}")
            return None

    async def upload_to_mixdrop_remote(self, source_url: str, file_name: str) -> Optional[str]:
        if not self.mixdrop_email or not self.mixdrop_key:
            return None
        try:
            tqdm.write(f"🔄 Triggering MixDrop Remote Upload from: {source_url[:60]}...")
            async with aiohttp.ClientSession() as session:
                params = {'email': self.mixdrop_email, 'key': self.mixdrop_key, 'url': source_url}
                async with session.get(config.MIXDROP_REMOTE_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    result = await response.json()
                    if result.get('success'):
                        file_id = result['result'].get('id', '')
                        tqdm.write(f"✅ MixDrop Remote Upload initiated!")
                        return f"https://mixdrop.ag/f/{file_id}"
                    else:
                        tqdm.write(f"❌ MixDrop Remote Upload failed: {result.get('message', 'Unknown')}")
                        return None
        except Exception as e:
            tqdm.write(f"❌ MixDrop remote upload error: {e}")
            return None

    async def upload_to_streamtape(self, file_path: str) -> Optional[str]:
        if not config.ENABLE_STREAMTAPE or not self.streamtape_login or not self.streamtape_key:
            return None
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            tqdm.write(f"📡 Getting StreamTape upload URL...")

            async with aiohttp.ClientSession() as session:
                params = {'login': self.streamtape_login, 'key': self.streamtape_key}
                async with session.get(config.STREAMTAPE_API_URL, params=params) as response:
                    result = await response.json()
                    if result.get('status') != 200:
                        tqdm.write(f"❌ StreamTape API error: {result.get('msg', 'Unknown')}")
                        return None
                    upload_url = result['result']['url']
                    tqdm.write(f"✅ Got upload URL")

                tqdm.write(f"📤 Uploading to StreamTape...")
                with open(file_path, 'rb') as f:
                    form_data = aiohttp.FormData()
                    form_data.add_field('file1', f, filename=file_name)
                    with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"📤 StreamTape: {file_name[:40]}", file=sys.stdout, leave=False) as pbar:
                        async with session.post(upload_url, data=form_data, timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_PER_FILE)) as upload_response:
                            response_text = await upload_response.text()
                            response_status = upload_response.status

                try:
                    result = json.loads(response_text)
                    if result.get('status') == 200:
                        file_url = result['result'].get('url', '')
                        if file_url:
                            tqdm.write(f"✅ StreamTape upload complete!")
                            return file_url
                except json.JSONDecodeError:
                    pass

                patterns = [r'(https://streamtape\.com/v/[a-zA-Z0-9]+/[^\s"<]+)', r'v/([a-zA-Z0-9]+)/']
                for pattern in patterns:
                    match = re.search(pattern, response_text)
                    if match:
                        if match.group(0).startswith('http'):
                            tqdm.write(f"✅ StreamTape upload complete (URL parsed)")
                            return match.group(0)
                        else:
                            file_id = match.group(1)
                            tqdm.write(f"✅ StreamTape upload complete (ID parsed)")
                            return f"https://streamtape.com/v/{file_id}/{file_name}"

                if response_status == 200:
                    tqdm.write(f"⚠️ Upload may have succeeded but response format unknown")
                    return f"https://streamtape.com/v/UPLOADED/{file_name}"
                tqdm.write(f"❌ StreamTape upload failed")
                return None
        except Exception as e:
            tqdm.write(f"❌ StreamTape upload error: {e}")
            return None

    def save_to_supabase(self, metadata: VideoMetadata):
        if not config.ENABLE_DATABASE_SAVE:
            return None
        data = {
            'file_path': metadata.file_path, 'file_name': metadata.file_name, 'file_size': metadata.file_size,
            'content_type': 'anime', 'title': metadata.anime_name, 'season': metadata.season, 'episode': metadata.episode,
            'episode_number': metadata.episode_number, 'quality': metadata.quality, 'languages': metadata.languages,
            'language_tag': metadata.language_tag, 'status': metadata.status, 'upload_date': metadata.upload_date,
            'doodstream_url': metadata.doodstream_url, 'mixdrop_url': metadata.mixdrop_url, 'streamtape_url': metadata.streamtape_url,
        }
        try:
            result = self.supabase.table('videos').upsert(data, on_conflict='file_path').execute()
            return result.data
        except Exception as e:
            tqdm.write(f"❌ Supabase save error: {e}")
            return None

    async def upload_single_video(self, file_path: str):
        if not os.path.exists(file_path):
            tqdm.write(f"⚠️ File not found, skipping: {file_path}")
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        parsed = self.parse_video_filename(file_name)
        
        if not parsed:
            tqdm.write(f"❌ Could not parse filename: {file_name}")
            return

        metadata = VideoMetadata(
            file_path=file_path, file_name=file_name, file_size=file_size,
            anime_name=parsed['anime_name'], season=parsed['season'], episode=parsed['episode'],
            episode_number=parsed['episode_number'], languages=parsed['languages'],
            language_tag=parsed['language_tag'], quality=parsed['quality'],
            upload_date=datetime.now().isoformat()
        )

        tqdm.write(f"\n{'='*70}")
        tqdm.write(f"📤 Uploading: {file_name}")
        tqdm.write(f"   Anime: {metadata.anime_name} | Episode: {metadata.episode_number} | Quality: {metadata.quality}")
        tqdm.write(f"   Languages: {', '.join(metadata.languages)} | Size: {file_size / (1024*1024):.2f} MB")
        tqdm.write(f"{'='*70}")

        tasks = []
        if config.ENABLE_DOODSTREAM:
            tasks.append(asyncio.create_task(self.upload_to_doodstream_ftp(file_path)))
        if config.ENABLE_STREAMTAPE:
            tasks.append(asyncio.create_task(self.upload_to_streamtape(file_path)))
        if config.ENABLE_MIXDROP:
            tasks.append(asyncio.create_task(self.upload_to_mixdrop(file_path)))

        if not tasks:
            tqdm.write("⚠️ No platforms enabled in config.py. Skipping upload.")
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)

        idx = 0
        if config.ENABLE_DOODSTREAM:
            res = results[idx]
            metadata.doodstream_url = str(res) if not isinstance(res, Exception) and res else ""
            idx += 1
        if config.ENABLE_STREAMTAPE:
            res = results[idx]
            metadata.streamtape_url = str(res) if not isinstance(res, Exception) and res else ""
            idx += 1
        if config.ENABLE_MIXDROP:
            res = results[idx]
            metadata.mixdrop_url = str(res) if not isinstance(res, Exception) and res else ""
            idx += 1

        if config.ENABLE_MIXDROP_REMOTE_FALLBACK and not metadata.mixdrop_url and metadata.streamtape_url:
            tqdm.write(f"\n🔄 MixDrop direct failed/disabled. Trying Remote Upload from StreamTape...")
            mixdrop_remote_url = await self.upload_to_mixdrop_remote(metadata.streamtape_url, file_name)
            if mixdrop_remote_url:
                metadata.mixdrop_url = mixdrop_remote_url
                tqdm.write(f"✅ MixDrop Remote Upload URL: {mixdrop_remote_url}")

        uploaded_count = sum([1 for url in [metadata.doodstream_url, metadata.mixdrop_url, metadata.streamtape_url] if url])
        
        if uploaded_count == 3:
            metadata.status = "completed"
            tqdm.write(f"\n✅ All 3 platforms uploaded successfully!")
        elif uploaded_count >= 1:
            metadata.status = "completed"
            tqdm.write(f"\n⚠️ {uploaded_count}/3 platforms successful. Marked as completed.")
        else:
            metadata.status = "failed"
            tqdm.write(f"\n❌ All uploads failed!")

        db_result = self.save_to_supabase(metadata)
        
        if config.ENABLE_DATABASE_SAVE:
            if db_result:
                tqdm.write(f"✅ Database updated: {metadata.status}")
            else:
                tqdm.write(f"⚠️ Database save failed!")

        if config.AUTO_DELETE_AFTER_UPLOAD and db_result and metadata.status == "completed":
            try:
                os.remove(file_path)
                tqdm.write(f"🗑️ Local file deleted successfully: {file_name}")
            except PermissionError:
                tqdm.write(f"⚠️ Permission denied: Could not delete {file_name}. File might be in use.")
            except Exception as e:
                tqdm.write(f"⚠️ Failed to delete local file: {file_name}. Error: {e}")
        elif metadata.status != "completed":
            tqdm.write(f"⚠️ Upload incomplete/failed. Keeping local file for retry.")
        elif not db_result and config.ENABLE_DATABASE_SAVE:
            tqdm.write(f"⚠️ Upload succeeded, but DB save failed. KEEPING local file as backup.")

        if config.PRINT_URLS_AFTER_UPLOAD:
            if metadata.doodstream_url: tqdm.write(f"   🎬 DoodStream: {metadata.doodstream_url}")
            if metadata.streamtape_url: tqdm.write(f"   🎬 StreamTape: {metadata.streamtape_url}")
            if metadata.mixdrop_url: tqdm.write(f"   🎬 MixDrop: {metadata.mixdrop_url}")

        tqdm.write(f"{'='*70}\n")

    async def scan_and_upload(self, folder_path: str):
        if not os.path.exists(folder_path):
            tqdm.write(f"❌ Folder not found: {folder_path}")
            return

        video_extensions = set(ext.lower() for ext in config.SUPPORTED_EXTENSIONS)
        video_files = []

        tqdm.write(f"🔍 Scanning folder: {folder_path}\n")

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if Path(file).suffix.lower() in video_extensions:
                    file_path = os.path.join(root, file)
                    
                    if config.CHECK_DUPLICATE_IN_DB:
                        try:
                            result = self.supabase.table('videos').select('id').eq('file_path', file_path).execute()
                            if len(result.data) == 0:
                                video_files.append(file_path)
                            else:
                                tqdm.write(f"⏭️  Already in database: {file}")
                        except Exception as e:
                            tqdm.write(f"⚠️ DB check failed for {file}, adding anyway: {e}")
                            video_files.append(file_path)
                    else:
                        video_files.append(file_path)

        if not video_files:
            tqdm.write("✅ No new videos found in this scan!")
            return

        tqdm.write(f"\n📁 Found {len(video_files)} new videos to upload\n")

        for i, file_path in enumerate(video_files, 1):
            tqdm.write(f"\n[{i}/{len(video_files)}]")
            await self.upload_single_video(file_path)

        tqdm.write(f"\n{'='*70}")
        tqdm.write(f"🎉 Current scan & upload batch completed!")
        tqdm.write(f"{'='*70}")


async def main():
    try:
        uploader = AnimeVideoUploader()
        video_folder = os.getenv('VIDEO_FOLDER', './videos')
        
        if config.ENABLE_CONTINUOUS_SCAN:
            tqdm.write("🔄 Continuous scan mode ENABLED. Press Ctrl+C to stop.")
            scan_count = 1
            while True:
                tqdm.write(f"\n{'='*70}")
                tqdm.write(f"🔍 Starting Scan Cycle #{scan_count}")
                tqdm.write(f"{'='*70}")
                
                await uploader.scan_and_upload(video_folder)
                
                tqdm.write(f"\n⏳ Waiting {config.SCAN_INTERVAL_SECONDS} seconds before next scan...")
                await asyncio.sleep(config.SCAN_INTERVAL_SECONDS)
                scan_count += 1
        else:
            tqdm.write("📌 Single scan mode. Running once and exiting.")
            await uploader.scan_and_upload(video_folder)
            tqdm.write("✅ Script finished successfully.")
            
    except KeyboardInterrupt:
        tqdm.write("\n\n🛑 Continuous scan stopped by user (Ctrl+C). Exiting gracefully...")
    except Exception as e:
        tqdm.write(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())