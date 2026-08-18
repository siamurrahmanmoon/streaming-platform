# ═══════════════════════════════════════════════════════════
# CONFIGURATION FILE - Anime Video Uploader (Advanced Modular)
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# Continuous Scan Settings
# ═══════════════════════════════════════════════════════════
ENABLE_CONTINUOUS_SCAN = True      # True হলে বারবার স্ক্যান করবে, False হলে শুধু একবার স্ক্যান করবে
SCAN_INTERVAL_SECONDS = 60         # দুটি স্ক্যানের মধ্যে বিরতি (সেকেন্ডে)

# ═══════════════════════════════════════════════════════════
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
# FILE HANDLING & ARCHIVE SETTINGS (Safe Mode)
# ═══════════════════════════════════════════════════════════
AUTO_DELETE_AFTER_UPLOAD = False  # ⚠️ Legacy: নতুন সিস্টেমে ENABLE_SAFE_ARCHIVE ব্যবহার করুন
ENABLE_SAFE_ARCHIVE = True        # True = আপলোড শেষে ফাইল ডিলিট না করে Archive ফোল্ডারে মুভ করবে
ARCHIVE_SUCCESS_FOLDER = "./archive/success"
ARCHIVE_FAILED_FOLDER = "./archive/failed"

ENABLE_SUBTITLE_NFO_SUPPORT = True # True হলে .srt, .nfo ফাইলগুলো ভিডিওর সাথে ZIP করে আপলোড করবে
SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.ass'}
NFO_EXTENSIONS = {'.nfo'}

ENABLE_INTEGRITY_CHECK = True      # True হলে আপলোডের আগে ফাইলের সাইজ/হ্যাশ চেক করবে

# ═══════════════════════════════════════════════════════════
# ORPHANED FILE CLEANUP
# ═══════════════════════════════════════════════════════════
ENABLE_ORPHAN_CLEANUP = True       # True হলে পুরনো/অরফান ফাইলগুলো Quarantine ফোল্ডারে সরিয়ে দেবে
ORPHAN_DAYS_LIMIT = 7              # কত দিনের পুরনো ফাইল অরফান ধরা হবে
QUARANTINE_FOLDER = "./quarantine"

# ═══════════════════════════════════════════════════════════
# DATABASE SETTINGS
# ═══════════════════════════════════════════════════════════
ENABLE_DATABASE_SAVE = True     
CHECK_DUPLICATE_IN_DB = True    

# ═══════════════════════════════════════════════════════════
# UPLOAD & PERFORMANCE SETTINGS
# ═══════════════════════════════════════════════════════════
MAX_CONCURRENT_UPLOADS = 5         # একসাথে সর্বোচ্চ কতটি ফাইল আপলোড হবে (Concurrency Limit)
BANDWIDTH_LIMIT_MBPS = 0           # 0 = Unlimited, 10 = 10 MB/s (Bandwidth Throttling)
MAX_RETRIES = 3                    # ফেইল করলে কতবার রিট্রাই করবে (Exponential Backoff)
TIMEOUT_PER_FILE = 3600            # প্রতিটি ফাইলের সর্বোচ্চ সময় (সেকেন্ডে)
RETRY_DELAY_BASE = 5               # seconds - প্রথম রিট্রাইয়ের আগে কত সেকেন্ড অপে

# ═══════════════════════════════════════════════════════════
# FILE HANDLING SETTINGS
# ═══════════════════════════════════════════════════════════
SUPPORTED_EXTENSIONS = [
    '.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.wmv', '.m4v'
]

# ═══════════════════════════════════════════════════════════
# FTP SETTINGS (DoodStream)
# ═══════════════════════════════════════════════════════════
FTP_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB

# ═══════════════════════════════════════════════════════════
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
    print("📋 CURRENT CONFIGURATION (Advanced Modular System)")
    print("="*70)
    print(f"🌐 Platforms:")
    print(f"  • DoodStream:  {'✅ ENABLED' if ENABLE_DOODSTREAM else '❌ DISABLED'}")
    print(f"  • MixDrop:     {'✅ ENABLED' if ENABLE_MIXDROP else '❌ DISABLED'}")
    print(f"  • StreamTape:  {'✅ ENABLED' if ENABLE_STREAMTAPE else '❌ DISABLED'}")
    
    print(f"\n⚡ Performance & Upload:")
    print(f"  • Concurrent Uploads:    {MAX_CONCURRENT_UPLOADS} files")
    print(f"  • Bandwidth Limit:       {'Unlimited' if BANDWIDTH_LIMIT_MBPS == 0 else f'{BANDWIDTH_LIMIT_MBPS} MB/s'}")
    print(f"  • Max Retries:           {MAX_RETRIES} (Exponential Backoff)")
    print(f"  • Timeout per File:      {TIMEOUT_PER_FILE}s ({TIMEOUT_PER_FILE/60:.1f} min)")
    
    print(f"\n🛡️ Safety & Archive:")
    print(f"  • Safe Archive (Move):   {'✅ YES' if ENABLE_SAFE_ARCHIVE else '❌ NO (Will Delete)'}")
    print(f"  • Subtitle/NFO Support:  {'✅ YES' if ENABLE_SUBTITLE_NFO_SUPPORT else '❌ NO'}")
    print(f"  • Integrity Check:       {'✅ YES' if ENABLE_INTEGRITY_CHECK else '❌ NO'}")
    print(f"  • Orphan Cleanup:        {'✅ YES' if ENABLE_ORPHAN_CLEANUP else '❌ NO'} ({ORPHAN_DAYS_LIMIT} days)")
    
    print(f"\n💾 Database & Scan:")
    print(f"  • Continuous Scan:       {'✅ YES' if ENABLE_CONTINUOUS_SCAN else '❌ NO'} ({SCAN_INTERVAL_SECONDS}s interval)")
    print(f"  • Database Save:         {'✅ YES' if ENABLE_DATABASE_SAVE else '❌ NO'}")
    print(f"  • Check Duplicates:      {'✅ YES' if CHECK_DUPLICATE_IN_DB else '❌ NO'}")
    print("="*70 + "\n")