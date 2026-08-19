import os
import asyncio
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
        log.info("🚀 Starting Auto Scan Video Uploader...")

        if config.CHECK_DISK_BEFORE_UPLOAD:
            video_folder = os.getenv("VIDEO_FOLDER", "./videos")
            asyncio.create_task(disk_monitor.check_and_alert(video_folder))

        supabase_url = os.getenv("SUPABASE_URL")

        # Standard client for Database operations
        # Note: This client will be subject to RLS policies
        # SUPABASE_SERVICE_ROLE_KEY ← এটি RLS bypass করে
        self.supabase = create_client(
            supabase_url, os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )

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
            scan_name = os.path.basename(os.path.normpath(video_folder))
            while True:
                scan_status = (
                    f"🔍 Scan Cycle #{scan_count} | 📂 {scan_name} | 🔄 Scanning..."
                )
                print(f"\r{scan_status}   ", end="", flush=True)
                await scan_and_upload(
                    context.supabase, context.supabase_storage, video_folder
                )

                for seconds_left in range(config.SCAN_INTERVAL_SECONDS, 0, -1):
                    wait_status = (
                        f"🔍 Scan Cycle #{scan_count} | 📂 {scan_name} | "
                        f"⏳ Next scan in {seconds_left}s..."
                    )
                    print(f"\r{wait_status}   ", end="", flush=True)
                    await asyncio.sleep(1)
                scan_count += 1
        else:
            await scan_and_upload(
                context.supabase, context.supabase_storage, video_folder
            )
            tqdm.write("✅ Single scan completed.")

    except Exception as e:
        tqdm.write(f"❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        tqdm.write("\n\n🛑 Stopped by user. Exiting gracefully...")
