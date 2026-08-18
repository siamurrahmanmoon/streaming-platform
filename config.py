# ═══════════════════════════════════════════════════════════
# CONFIGURATION FILE - Anime Video Uploader
# ═══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
# PLATFORM TOGGLE - কোন প্ল্যাটফর্মে আপলোড হবে (True/False)
# ═══════════════════════════════════════════════════════════
ENABLE_DOODSTREAM = True      
ENABLE_MIXDROP = False         
ENABLE_STREAMTAPE = False      

# ═══════════════════════════════════════════════════════════
# MIXDROP CHAIN UPLOAD - ফলব্যাক সিস্টেম
# ═══════════════════════════════════════════════════════════
ENABLE_MIXDROP_REMOTE_FALLBACK = True  # MixDrop Direct ফেইল করলে StreamTape থেকে Remote Upload

# ═══════════════════════════════════════════════════════════
# AUTO DELETE SETTINGS - লোকাল ফাইল ডিলিট
# ═══════════════════════════════════════════════════════════
AUTO_DELETE_AFTER_UPLOAD = False  # True = আপলোড ও DB সেভ সফল হলে লোকাল ফাইল ডিলিট হবে

# ═══════════════════════════════════════════════════════════
# DATABASE SETTINGS
# ═══════════════════════════════════════════════════════════
ENABLE_DATABASE_SAVE = True     
CHECK_DUPLICATE_IN_DB = True    

# ══════════════════════════════════════════════════════════
# UPLOAD SETTINGS
# ══════════════════════════════════════════════════════════
CONCURRENT_UPLOADS = True       
MAX_RETRIES = 3                 
TIMEOUT_PER_FILE = 3600         

# ══════════════════════════════════════════════════════════
# FILE HANDLING SETTINGS
# ═══════════════════════════════════════════════════════════
SUPPORTED_EXTENSIONS = [
    '.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.wmv', '.m4v'
]

# ═══════════════════════════════════════════════════════════
# FTP SETTINGS (DoodStream)
# ═══════════════════════════════════════════════════════════
FTP_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB

# ══════════════════════════════════════════════════════════
# API ENDPOINTS 
# ═══════════════════════════════════════════════════════════
MIXDROP_API_URL = "https://ul.mixdrop.ag/api"
MIXDROP_REMOTE_API_URL = "https://api.mixdrop.ag/remotedl/add"
STREAMTAPE_API_URL = "https://api.streamtape.com/file/ul"
DOODSTREAM_FTP_SERVER = "ftp.doodstream.com"

# ═══════════════════════════════════════════════════════════
# LOGGING & DISPLAY SETTINGS
# ═══════════════════════════════════════════════════════════
SHOW_PROGRESS_BARS = True       
VERBOSE_LOGGING = False         
PRINT_URLS_AFTER_UPLOAD = True  

# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════
def print_config():
    """বর্তমান কনফিগারেশন দেখান"""
    print("\n" + "="*70)
    print("📋 CURRENT CONFIGURATION (from config.py)")
    print("="*70)
    print(f"Platforms:")
    print(f"  • DoodStream:  {'✅ ENABLED' if ENABLE_DOODSTREAM else '❌ DISABLED'}")
    print(f"  • MixDrop:     {'✅ ENABLED' if ENABLE_MIXDROP else '❌ DISABLED'}")
    print(f"  • StreamTape:  {'✅ ENABLED' if ENABLE_STREAMTAPE else '❌ DISABLED'}")
    print(f"\nSettings:")
    print(f"  • Auto Delete Files:     {'✅ YES' if AUTO_DELETE_AFTER_UPLOAD else '❌ NO (Safe Mode)'}")
    print(f"  • Concurrent Uploads:    {'✅ YES' if CONCURRENT_UPLOADS else '❌ NO'}")
    print(f"  • MixDrop Remote Fallback: {'✅ YES' if ENABLE_MIXDROP_REMOTE_FALLBACK else '❌ NO'}")
    print(f"  • Database Save:         {'✅ YES' if ENABLE_DATABASE_SAVE else '❌ NO'}")
    print(f"  • Check Duplicates:      {'✅ YES' if CHECK_DUPLICATE_IN_DB else '❌ NO'}")
    print(f"  • Timeout per File:      {TIMEOUT_PER_FILE}s ({TIMEOUT_PER_FILE/60:.1f} min)")
    print("="*70 + "\n")