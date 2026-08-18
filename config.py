import os

# ═══════════════════════════════════════════════════════════
# Continuous Scan Settings
# ═══════════════════════════════════════════════════════════
ENABLE_CONTINUOUS_SCAN = True
SCAN_INTERVAL_SECONDS = 60

# ═══════════════════════════════════════════════════════════
# PLATFORM TOGGLE (Video Upload)
# ═══════════════════════════════════════════════════════════
ENABLE_DOODSTREAM = True      
ENABLE_MIXDROP = False         
ENABLE_STREAMTAPE = False      

# ═══════════════════════════════════════════════════════════
# TMDB METADATA & IMAGE STORAGE SETTINGS (Supabase)
# ═══════════════════════════════════════════════════════════
ENABLE_TMDB_METADATA = True
ENABLE_IMAGE_STORAGE = True
SUPABASE_STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'Poster')  # Default bucket name if not set in .env

# ═══════════════════════════════════════════════════════════
# MIXDROP CHAIN UPLOAD
# ═══════════════════════════════════════════════════════════
ENABLE_MIXDROP_REMOTE_FALLBACK = True

# ═══════════════════════════════════════════════════════════
# FILE HANDLING & ARCHIVE SETTINGS
# ═══════════════════════════════════════════════════════════
ENABLE_SAFE_ARCHIVE = False
ARCHIVE_SUCCESS_FOLDER = "./archive/success"
ARCHIVE_FAILED_FOLDER = "./archive/failed"

ENABLE_SUBTITLE_NFO_SUPPORT = True
SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.ass'}
NFO_EXTENSIONS = {'.nfo'}

ENABLE_INTEGRITY_CHECK = True

# ═══════════════════════════════════════════════════════════
# ORPHANED FILE CLEANUP
# ═══════════════════════════════════════════════════════════
ENABLE_ORPHAN_CLEANUP = True
ORPHAN_DAYS_LIMIT = 7
QUARANTINE_FOLDER = "./quarantine"

# ═══════════════════════════════════════════════════════════
# DATABASE SETTINGS
# ═══════════════════════════════════════════════════════════
ENABLE_DATABASE_SAVE = True     
CHECK_DUPLICATE_IN_DB = True    

# ═══════════════════════════════════════════════════════════
# UPLOAD & PERFORMANCE SETTINGS
# ═══════════════════════════════════════════════════════════
MAX_CONCURRENT_UPLOADS = 2
BANDWIDTH_LIMIT_MBPS = 0
MAX_RETRIES = 3
RETRY_DELAY_BASE = 5
TIMEOUT_PER_FILE = 3600

# ═══════════════════════════════════════════════════════════
# FILE & API SETTINGS
# ═══════════════════════════════════════════════════════════
SUPPORTED_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.wmv', '.m4v']
FTP_CHUNK_SIZE = 8 * 1024 * 1024

MIXDROP_API_URL = "https://ul.mixdrop.ag/api"
MIXDROP_REMOTE_API_URL = "https://api.mixdrop.ag/remotedl/add"
STREAMTAPE_API_URL = "https://api.streamtape.com/file/ul"
DOODSTREAM_FTP_SERVER = "ftp.doodstream.com"

# ═══════════════════════════════════════════════════════════
# LOGGING & DISPLAY
# ═══════════════════════════════════════════════════════════
SHOW_PROGRESS_BARS = True
VERBOSE_LOGGING = False
PRINT_URLS_AFTER_UPLOAD = True

def print_config():
    print("\n" + "="*70)
    print("📋 ADVANCED MODULAR CONFIGURATION")
    print("="*70)
    print(f"🌐 Video Platforms: Dood:{'✅' if ENABLE_DOODSTREAM else '❌'} | Mix:{'✅' if ENABLE_MIXDROP else '❌'} | ST:{'✅' if ENABLE_STREAMTAPE else '❌'}")
    print(f"🎨 Image Storage: {'✅ Supabase (' + SUPABASE_STORAGE_BUCKET + ')' if ENABLE_IMAGE_STORAGE else '❌ Disabled'}")
    print(f"⚡ Concurrent Uploads: {MAX_CONCURRENT_UPLOADS} files | Retries: {MAX_RETRIES}")
    print(f"🛡️ Safe Archive: {'✅' if ENABLE_SAFE_ARCHIVE else '❌'} | TMDB Metadata: {'✅' if ENABLE_TMDB_METADATA else '❌'}")
    print(f"💾 Continuous Scan: {'✅' if ENABLE_CONTINUOUS_SCAN else '❌'} ({SCAN_INTERVAL_SECONDS}s)")
    print("="*70 + "\n")