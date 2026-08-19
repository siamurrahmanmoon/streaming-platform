# 🎬 Advanced Anime & Movie Video Uploader

এটি একটি সম্পূর্ণ অটোমেটেড, মডুলার পাইথন স্ক্রিপ্ট যা ভিডিও ফাইল স্ক্যান করে, অটোমেটিকভাবে মেটাডাটা (TMDB/OMDb) ফেচ করে, ভিডিওগুলো স্ট্রিমিং প্ল্যাটফর্মে (DoodStream, MixDrop, StreamTape) আপলোড করে, ইমেজগুলো Supabase Storage-এ সেভ করে এবং সমস্ত তথ্য Supabase ডাটাবেসে রেকর্ড করে।

---

## ✨ মূল ফিচারসমূহ

###  স্মার্ট ফাইল পার্সিং
- ফাইলের নাম থেকে অটোমেটিক **Title, Year, Season, Episode, Language** এবং **Quality** ডিটেক্ট করে
- Movie এবং TV Series আলাদা করতে সক্ষম
- URL-encoded brackets (`5B`/`5D`) হ্যান্ডেল করে
- Multiple language detection (Original, Hindi, Bengali, etc.)

### 🌐 ডুয়াল মেটাডাটা সোর্স
- প্রথমে **TMDB API** থেকে মেটাডাটা খোঁজে
- না পেলে অটোমেটিক fallback হিসেবে **OMDb API** ব্যবহার করে
- Keywords/Tags অটোমেটিক fetch করে

### 🖼️ Supabase Storage ইন্টিগ্রেশন
- পোস্টার, ব্যানার এবং থাম্বনেইল সরাসরি Supabase Storage-এ অপ্টিমাইজড ফোল্ডার স্ট্রাকচারে (`{tmdb_id}/s{season}/{type}.jpg`) আপলোড করে
- Duplicate image detection এবং caching

### 🛡️ আনম্যাচড ফাইল হ্যান্ডলিং
- যদি কোনো ফাইলের মেটাডাটা পাওয়া না যায়, তবে সেটি ভিডিও আপলোড না করেই একটি আলাদা `unmatched_videos` ফোল্ডারে সরিয়ে নেয়

### ⚡ কনকারেন্ট আপলোড
- একসাথে একাধিক ফাইল প্রসেসিং এবং আপলোডের সুবিধা (Concurrency Limit কনফিগারযোগ্য)
- Bandwidth throttling support

### 🔄 কন্টিনিউয়াস স্ক্যানিং
- নির্দিষ্ট সময় পর পর (যেমন: ০ সেকেন্ড) ফোল্ডার অটোমেটিক স্ক্যান করে নতুন ফাইল খুঁজে বের করে

### 🗂️ সেফ আর্কাইভ
- আপলোড সফল হলে ফাইলগুলো ডিলিট না করে `archive/success` বা `archive/failed` ফোল্ডারে মুভ করে

### ️ Normalized Database Schema
- **Multi-language support**: Original এবং Dubbed versions আলাদা করে manage করা হয়
- **Cross-language watch history sync**: এক ভাষায় দেখা progress অন্য ভাষায় sync হয়
- **Relational data**: Seasons, Episodes, Video Sources, Genres, Tags আলাদা table এ organize করা

### 📊 অ্যাডভান্সড ট্যাগিং সিস্টেম
- TMDB থেকে অটোমেটিক Keywords fetch করে `media_tags` table এ save করে
- Future recommendation engine এবং advanced search এর জন্য প্রস্তুত

### 🔐 Production-Grade Security
- RLS (Row Level Security) ready
- Service Role Key দিয়ে backend operations
- Anon Key দিয়ে frontend operations

---

## 📋 প্রিরিকুইজিট (Prerequisites)

- **Python 3.10+**
- একটি সক্রিয় [Supabase](https://supabase.com/) অ্যাকাউন্ট
- [TMDB API Key](https://www.themoviedb.org/settings/api) (ফ্রি)
- [OMDb API Key](https://www.omdbapi.com/apikey.aspx) (ফ্রি, fallback-এর জন্য)
- DoodStream / MixDrop / StreamTape অ্যাকাউন্ট (যেগুলো ব্যবহার করতে চান)
- [Telegram Bot](https://t.me/BotFather) (অপশনাল, alerts এর জন্য)

---

## ️ ইনস্টলেশন ও সেটআপ

### ১. রিপোজিটরি ক্লোন ও ভার্চুয়াল এনভায়রনমেন্ট তৈরি

```bash
# প্রজেক্ট ফোল্ডারে যান
cd anime-streaming-platform/backend

# ভার্চুয়াল এনভায়রনমেন্ট তৈরি ও অ্যাক্টিভেট করুন (Windows)
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# প্রয়োজনীয় প্যাকেজ ইনস্টল করুন
pip install -r requirements.txt
```

### ২. Supabase Database Setup

Supabase **SQL Editor** এ গিয়ে নিচের SQL কোড রান করুন:

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Media Table (Core)
CREATE TABLE media (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  parent_media_id UUID REFERENCES media(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  overview TEXT,
  poster_url TEXT,
  backdrop_url TEXT,
  media_type TEXT NOT NULL CHECK (media_type IN ('movie', 'tv_series', 'anime')),
  release_year INTEGER,
  status TEXT DEFAULT 'released',
  language_code TEXT DEFAULT 'en',
  version_type TEXT DEFAULT 'original' CHECK (version_type IN ('original', 'dubbed')),
  tmdb_id INTEGER,
  total_episodes INTEGER DEFAULT 0,
  original_language TEXT,
  popularity_score FLOAT DEFAULT 0,
  search_vector TSVECTOR,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_media_parent ON media(parent_media_id);
CREATE INDEX idx_media_language ON media(language_code);
CREATE INDEX idx_media_search ON media USING GIN(search_vector);
CREATE INDEX idx_media_popularity ON media(popularity_score);
CREATE INDEX idx_media_type_status ON media(media_type, status);

-- Genres
CREATE TABLE genres (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  slug TEXT UNIQUE NOT NULL
);

CREATE TABLE media_genres (
  media_id UUID REFERENCES media(id) ON DELETE CASCADE,
  genre_id UUID REFERENCES genres(id) ON DELETE CASCADE,
  PRIMARY KEY (media_id, genre_id)
);

-- Tags
CREATE TABLE media_tags (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  media_id UUID REFERENCES media(id) ON DELETE CASCADE,
  tag_name TEXT NOT NULL,
  tag_type TEXT
);
CREATE INDEX idx_tags_media ON media_tags(media_id);

-- Seasons & Episodes
CREATE TABLE seasons (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  media_id UUID REFERENCES media(id) ON DELETE CASCADE,
  season_number INTEGER NOT NULL,
  title TEXT,
  UNIQUE(media_id, season_number)
);

CREATE TABLE episodes (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  season_id UUID REFERENCES seasons(id) ON DELETE CASCADE,
  episode_number INTEGER NOT NULL,
  title TEXT NOT NULL,
  overview TEXT,
  thumbnail_url TEXT,
  duration_minutes INTEGER,
  air_date DATE,
  UNIQUE(season_id, episode_number)
);

-- Video Sources
CREATE TABLE video_sources (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  episode_id UUID REFERENCES episodes(id) ON DELETE CASCADE,
  media_id UUID REFERENCES media(id) ON DELETE CASCADE,
  server_name TEXT NOT NULL,
  quality TEXT NOT NULL,
  video_url TEXT NOT NULL,
  is_default BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(episode_id, server_name, quality),
  UNIQUE(media_id, server_name, quality)
);

-- Analytics
CREATE TABLE video_analytics (
  media_id UUID REFERENCES media(id) ON DELETE CASCADE PRIMARY KEY,
  total_views INTEGER DEFAULT 0,
  total_watch_time_seconds BIGINT DEFAULT 0,
  average_rating FLOAT DEFAULT 0,
  rating_count INTEGER DEFAULT 0,
  completion_rate FLOAT DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Triggers
CREATE OR REPLACE FUNCTION update_media_search_vector() 
RETURNS TRIGGER AS $$ 
BEGIN 
  NEW.search_vector := to_tsvector('english', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.overview, '')); 
  RETURN NEW; 
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_media_search_update 
BEFORE INSERT OR UPDATE ON media 
FOR EACH ROW EXECUTE FUNCTION update_media_search_vector();

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_media_updated_at 
BEFORE UPDATE ON media 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### ৩. Supabase Storage Bucket তৈরি

1. Supabase Dashboard এ যান
2. **Storage** section এ ক্লিক করুন
3. **New Bucket** এ ক্লিক করে `posters` নামে একটি bucket তৈরি করুন
4. Bucket টি **Public** করুন

### ৪. Environment Variables সেটআপ

প্রজেক্টের root এ `.env` ফাইল তৈরি করুন:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
SUPABASE_STORAGE_BUCKET=posters

# DoodStream API
DOODSTREAM_API_KEY=your_doodstream_api_key

# MixDrop API
MIXDROP_API_URL=https://ul.mixdrop.ag/api
MIXDROP_EMAIL=your_mixdrop_email
MIXDROP_KEY=your_mixdrop_key

# StreamTape API
STREAMTAPE_LOGIN=your_streamtape_login
STREAMTAPE_PASSWORD=your_streamtape_password

# Video Folder
VIDEO_FOLDER=./videos

# TheMovieDB API
TMDB_API_KEY=your_tmdb_api_key

# OMDb API (Fallback)
OMDB_API_KEY=your_omdb_api_key

# Alert Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

---

##  প্রজেক্ট স্ট্রাকচার

```
anime-streaming-platform/
├── backend/
│   ├── .env                    # Environment variables
│   ├── config.py               # Configuration settings
│   ├── main.py                 # Main application entry point
│   ├── requirements.txt        # Python dependencies
│   ├── README.md               # This file
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── alerts.py           # Telegram/Discord notifications
│   │   ├── cleanup.py          # Orphaned files cleanup
│   │   ├── concurrency.py      # Upload concurrency control
│   │   ├── db_manager.py       # Normalized database operations
│   │   ├── disk_monitor.py     # Disk space monitoring
│   │   ├── file_manager.py     # File operations (archive, move)
│   │   ├── image_uploader.py   # Supabase Storage uploads
│   │   ├── integrity.py        # File integrity checks
│   │   ├── logger.py           # Logging configuration
│   │   ├── metadata.py         # TMDB/OMDb metadata fetching
│   │   ├── models.py           # Data models (VideoMetadata)
│   │   ├── omdb_fetcher.py     # OMDb API fallback
│   │   ├── parser.py           # Filename parsing logic
│   │   ├── processor.py        # Main video processing logic
│   │   ├── retry.py            # Retry with backoff
│   │   ├── scanner.py          # Folder scanning & duplicate check
│   │   └── uploaders.py        # DoodStream/MixDrop/StreamTape uploaders
│   │
│   ├── videos/                 # Input folder (scan here)
│   ├── archive/
│   │   ├── success/            # Successfully uploaded files
│   │   ── failed/             # Failed uploads
│   ── unmatched_videos/       # Files without metadata
│
└── frontend/                   # (Future) React/Next.js frontend
```

---

## 🚀 ব্যবহার (Usage)

### অ্যাপ রান করা

```bash
# ভার্চুয়াল এনভায়রনমেন্ট অ্যাক্টিভেট করুন
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# অ্যাপ রান করুন
python main.py
```

### আউটপুট উদাহরণ

```
======================================================================
📋 ADVANCED MODULAR CONFIGURATION
======================================================================
🌐 Video: Dood:✅ | Mix:✅ | ST:✅
🎨 Images: ✅ Supabase (posters)
⚡ Concurrency: 3 files | Retries: 3
💾 Scan: ✅ Continuous (30s)
======================================================================

2026-08-20 10:00:00 | INFO     | __main__:__init__:25 - 🚀 Starting Auto Scan Video Uploader...
🧹 Checking for orphaned files older than 7 days...
🔄 Continuous scan mode ENABLED. Press Ctrl+C to stop.
 Scan Cycle #1 | 📂 videos |  Scanning...
📁 Found 1 new videos to upload
⚡ Concurrent Upload Limit: 3 files at a time

🎨 Fetching metadata for: My Anime Title [Hindi] (TV Series) ...
✅ TMDB Matched: My Anime Title (2024) | Type: TV Series
📅 Final Match: My Anime Title (2024) | Type: TV Series | Status: Returning Series
📤 Uploading poster to Supabase Storage...
✅ Poster uploaded: https://...supabase.co/storage/v1/object/public/posters/12345/s1/poster.jpg

Dood: My_Anime_Title_Hindi-S01E01: 100%|████████████| 108M/108M [00:45<00:00, 2.40MB/s]
ST: My_Anime_Title_Hindi-S01E01: 100%|████████████| 111M/111M [00:20<00:00, 5.65MB/s]
Mix: My_Anime_Title_Hindi-S01E01: 100%|████████████| 111M/111M [00:22<00:00, 4.87MB/s]

✅ Database Updated: Media ID 7fd646af-... | Episode ID f1319676-... | Links: 3/3
2026-08-20 10:02:00 | INFO     | utils.alerts:send_telegram_photo:58 - ✅ Telegram photo sent successfully!
✅ All 1 videos processed in this batch!
```

---

## 🎬 ফাইল নামের ফরম্যাট

### TV Series / Anime
```
Title [Language] - S01E01 - 1080P.mp4
Title (2024) [Hindi] - S02E05 - 720P.mkv
Title - S01E01 - 480P.mp4
```

### Movies
```
Title [Language] - 1080P.mp4
Title (2024) [Hindi] - 720P.mkv
Title - 480P.mp4
```

### উদাহরণ
- `Naruto Shippuden [Hindi] - S01E01 - 1080P.mp4`
- `Attack on Titan [Original] - S03E12 - 720P.mkv`
- `Avengers Endgame (2019) [Hindi] - 1080P.mp4`

---

## ⚙️ কনফিগারেশন অপশন

`config.py` ফাইলে সব কনফিগারেশন পরিবর্তন করা যায়:

### Core Settings
```python
ENABLE_CONTINUOUS_SCAN = True          # Continuous scanning mode
SCAN_INTERVAL_SECONDS = 30             # Scan interval (seconds)
ENABLE_DATABASE_SAVE = True            # Save to database
CHECK_DUPLICATE_IN_DB = True           # Check for duplicates
```

### Platform Toggles
```python
ENABLE_DOODSTREAM = True               # Enable DoodStream upload
ENABLE_MIXDROP = True                  # Enable MixDrop upload
ENABLE_STREAMTAPE = True               # Enable StreamTape upload
```

### Performance
```python
MAX_CONCURRENT_UPLOADS = 3             # Max parallel uploads
BANDWIDTH_LIMIT_MBPS = 0               # 0 = no limit
MAX_RETRIES = 3                        # Max retry attempts
TIMEOUT_PER_FILE = 3600                # Timeout per file (seconds)
```

### File Handling
```python
ENABLE_SAFE_ARCHIVE = True             # Archive files after upload
ARCHIVE_SUCCESS_FOLDER = "./archive/success"
ARCHIVE_FAILED_FOLDER = "./archive/failed"
ENABLE_SUBTITLE_NFO_SUPPORT = True     # Package subtitles with video
ENABLE_INTEGRITY_CHECK = True          # Check file integrity
```

### Orphan Cleanup
```python
ENABLE_ORPHAN_CLEANUP = True           # Clean old files
ORPHAN_DAYS_LIMIT = 7                  # Days before cleanup
```

### Disk Management
```python
DISK_WARNING_THRESHOLD = 90.0          # Warn at 90% usage
DISK_CRITICAL_THRESHOLD = 95.0         # Stop at 95% usage
CHECK_DISK_BEFORE_UPLOAD = True        # Check disk space
```

---

## 🗃️ Database Schema Details

### Tables Overview

| Table | Description |
|-------|-------------|
| `media` | Main table for Movies, TV Series, Anime with multi-language support |
| `seasons` | TV Series seasons |
| `episodes` | Individual episodes |
| `video_sources` | Video URLs from different platforms (DoodStream, MixDrop, etc.) |
| `genres` | Genre list (Action, Drama, etc.) |
| `media_genres` | Many-to-many relationship between media and genres |
| `media_tags` | Keywords and tags from TMDB |
| `video_analytics` | View counts, ratings, watch time |

### Multi-Language Support

```
Original (Korean)
├── id: uuid-1
├── title: "My Bias, My Boss"
├── language_code: "ko"
├── version_type: "original"
└── parent_media_id: NULL

Dubbed (Hindi)
├── id: uuid-2
├── title: "My Bias, My Boss"
├── language_code: "hi"
── version_type: "dubbed"
── parent_media_id: uuid-1  ← Links to Original
```

---

## 🔐 RLS (Row Level Security) Setup

### Backend (Python Uploader) - RLS DISABLED রাখুন
- `SERVICE_ROLE_KEY` ব্যবহার করে
- RLS bypass করে full access পায়

### Frontend (React/Next.js) - RLS ENABLE করতে হবে
- `ANON_KEY` ব্যবহার করবে
- RLS policies enforce হবে

### RLS Policies Example

```sql
-- Enable RLS
ALTER TABLE media ENABLE ROW LEVEL SECURITY;

-- Public can view
CREATE POLICY "Public can view media"
ON media FOR SELECT
TO public
USING (true);

-- Authenticated users can manage
CREATE POLICY "Authenticated users can manage media"
ON media FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);
```

---

## 📊 Monitoring & Alerts

### Telegram Alerts
- ✅ Successful upload with poster image
- ❌ Failed uploads
- ️ Unmatched videos
- 🚨 Critical errors (disk space, etc.)

### Discord Webhook
- Same alerts as Telegram
- Embedded message format

### Logging
- All operations logged with `loguru`
- Log files stored in `logs/` directory

---

##  Troubleshooting

### DoodStream SSL Error
```
SSLEOFError(8, 'EOF occurred in violation of protocol')
```
**Solution:** Already fixed with `verify=False` and `"Connection": "close"` header.

### Duplicate Files
```
⏭️  Already in database: filename.mp4
```
**Solution:** File already uploaded. Delete local copy or remove from database.

### Metadata Not Found
```
⚠️ No metadata found in TMDB or OMDb for: Title
```
**Solution:** 
1. Check filename format
2. Ensure title matches TMDB/OMDb
3. File moved to `unmatched_videos/` folder

### Database Connection Error
```
 Supabase Error: ...
```
**Solution:**
1. Check `.env` file
2. Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
3. Check internet connection

---

## 🚀 Production Deployment

### Docker (Coming Soon)
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "main.py"]
```

### Systemd Service (Linux)
```ini
[Unit]
Description=Anime Video Uploader
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/backend
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

##  License

MIT License - Feel free to use and modify.

---

## 🤝 Contributing

Contributions welcome! Please open an issue or pull request.

---

## 📧 Contact

For questions or support, open an issue on GitHub.

---

## 🎯 Future Roadmap

- [ ] Docker support
- [ ] Web dashboard for monitoring
- [ ] Automatic subtitle download
- [ ] Quality-based upload priority
- [ ] Multi-server distribution
- [ ] Frontend React/Next.js app
- [ ] Advanced recommendation engine
- [ ] User watch history sync across languages

---

**Happy Uploading! 🎬✨**