import os

# ═══════════════════════════════════════════════════════════
# Core Settings
# ═══════════════════════════════════════════════════════════
ENABLE_CONTINUOUS_SCAN = True
SCAN_INTERVAL_SECONDS = 30
ENABLE_DATABASE_SAVE = True
CHECK_DUPLICATE_IN_DB = True

# ═══════════════════════════════════════════════════════════
# Platform Toggles (Video)
# ═══════════════════════════════════════════════════════════
ENABLE_DOODSTREAM = True
ENABLE_MIXDROP = True
ENABLE_STREAMTAPE = True

# ═══════════════════════════════════════════════════════════
# TMDB & Image Storage Settings (Optimized)
# ═══════════════════════════════════════════════════════════
ENABLE_TMDB_METADATA = True
REQUIRE_YEAR_IN_FILENAME = True
ENABLE_IMAGE_STORAGE = True
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "posters")
UNMATCHED_VIDEOS_FOLDER = os.getenv("UNMATCHED_VIDEOS_FOLDER", "./unmatched_videos")

# ═══════════════════════════════════════════════════════════
# File Handling & Archive
# ═══════════════════════════════════════════════════════════
ENABLE_SAFE_ARCHIVE = True
ARCHIVE_SUCCESS_FOLDER = "./archive/success"
ARCHIVE_FAILED_FOLDER = "./archive/failed"
ENABLE_SUBTITLE_NFO_SUPPORT = True
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass"}
NFO_EXTENSIONS = {".nfo"}
ENABLE_INTEGRITY_CHECK = True

# ═══════════════════════════════════════════════════════════
# Orphan Cleanup
# ═══════════════════════════════════════════════════════════
ENABLE_ORPHAN_CLEANUP = True
ORPHAN_DAYS_LIMIT = 7
QUARANTINE_FOLDER = "./quarantine"

# ═══════════════════════════════════════════════════════════
# RESOURCE MANAGEMENT
# ═══════════════════════════════════════════════════════════
CHECK_DISK_BEFORE_UPLOAD = True  # Check disk space before each upload

# ═══════════════════════════════════════════════════════════
# Performance & API
# ═══════════════════════════════════════════════════════════
MAX_CONCURRENT_UPLOADS = 3
MAX_RETRIES = 3
RETRY_DELAY_BASE = 5
TIMEOUT_PER_FILE = 3600
SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".flv", ".webm", ".wmv", ".m4v"}
MIXDROP_API_URL = "https://ul.mixdrop.ag/api"
STREAMTAPE_API_URL = "https://api.streamtape.com/file/ul"


def print_config():
    print("\n" + "=" * 70)
    print("📋 ADVANCED MODULAR CONFIGURATION")
    print("=" * 70)
    print(
        f"🌐 Video: Dood:{'✅' if ENABLE_DOODSTREAM else '❌'} | Mix:{'✅' if ENABLE_MIXDROP else '❌'} | ST:{'✅' if ENABLE_STREAMTAPE else '❌'}"
    )
    print(
        f"🎨 Images: {'✅ Supabase (' + SUPABASE_STORAGE_BUCKET + ')' if ENABLE_IMAGE_STORAGE else '❌ Disabled'}"
    )
    print(f"⚡ Concurrency: {MAX_CONCURRENT_UPLOADS} files | Retries: {MAX_RETRIES}")
    print(
        f"💾 Scan: {'✅ Continuous (' + str(SCAN_INTERVAL_SECONDS) + 's)' if ENABLE_CONTINUOUS_SCAN else '❌ Single Run'}"
    )
    print("=" * 70 + "\n")
