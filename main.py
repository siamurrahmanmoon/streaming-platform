import os
import sys
import asyncio
from pathlib import Path
from supabase import create_client
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

import config
from utils.logger import get_logger
from utils.cleanup import cleanup_orphaned_files
from utils.scanner import scan_and_upload
from utils.disk_monitor import disk_monitor

log = get_logger("main")


class AppContext:
    """Holds shared resources and clients for the application."""

    def __init__(self):
        config.print_config()
        log.info("🚀 Starting Anime Video Uploader...")

        if config.CHECK_DISK_BEFORE_UPLOAD:
            video_folder = os.getenv("VIDEO_FOLDER", "./videos")
            asyncio.create_task(disk_monitor.check_and_alert(video_folder))

        supabase_url = os.getenv("SUPABASE_URL")

        # Standard client for Database operations
        self.supabase = create_client(supabase_url, os.getenv("SUPABASE_KEY"))

        # Service role client for Storage operations (Bypasses RLS)
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if service_key:
            self.supabase_storage = create_client(supabase_url, service_key)
        else:
            tqdm.write(
                "⚠️ SUPABASE_SERVICE_ROLE_KEY missing. Storage uploads may fail due to RLS."
            )
            self.supabase_storage = self.supabase


async def main():
    try:
        context = AppContext()
        video_folder = os.getenv("VIDEO_FOLDER", "./videos")

        if config.ENABLE_ORPHAN_CLEANUP:
            cleanup_orphaned_files(video_folder)

        if config.ENABLE_CONTINUOUS_SCAN:
            tqdm.write("🔄 Continuous scan mode ENABLED. Press Ctrl+C to stop.")
            scan_count = 1
            while True:
                tqdm.write(f"\n{'='*60}\n🔍 Scan Cycle #{scan_count}\n{'='*60}")
                # ✅ FIXED: Pass both supabase (for DB) and supabase_storage (for Images)
                await scan_and_upload(
                    context.supabase, context.supabase_storage, video_folder
                )
                tqdm.write(
                    f"\n⏳ Waiting {config.SCAN_INTERVAL_SECONDS}s before next scan..."
                )
                await asyncio.sleep(config.SCAN_INTERVAL_SECONDS)
                scan_count += 1
        else:
            # ✅ FIXED: Pass both clients here too
            await scan_and_upload(
                context.supabase, context.supabase_storage, video_folder
            )
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
