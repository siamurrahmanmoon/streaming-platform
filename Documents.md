# 🎬 Advanced Anime & Movie Video Uploader

> এটি একটি সম্পূর্ণ অটোমেটেড, মডুলার পাইথন ব্যাকএন্ড সার্ভিস যা ভিডিও ফোল্ডার স্ক্যান করে, TMDB/OMDb থেকে মেটাডাটা ফেচ করে, ভিডিওগুলো স্ট্রিমিং প্ল্যাটফর্মে (DoodStream, MixDrop, StreamTape) আপলোড করে, ইমেজগুলো Supabase Storage-এ সেভ করে এবং সমস্ত তথ্য Supabase PostgreSQL ডাটাবেজে রেকর্ড করে — সাথে রিয়েল-টাইম Telegram ও Discord নোটিফিকেশন।

---

## 📑 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture & Technology Stack](#architecture--technology-stack)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Windows Portable Build](#windows-portable-build)
- [Docker Deployment](#docker-deployment)
- [Project Structure](#project-structure)
- [Filename Format Convention](#filename-format-convention)
- [Configuration Reference](#configuration-reference)
- [Database Schema](#database-schema)
- [Supabase Storage Setup](#supabase-storage-setup)
- [Row Level Security (RLS)](#row-level-security-rls)
- [Usage & Runtime](#usage--runtime)
- [Monitoring & Alerts](#monitoring--alerts)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)
- [Backup & Restore](#backup--restore)
- [Future Roadmap](#future-roadmap)
- [License & Contributing](#license--contributing)

---

## Overview

**Advanced Anime & Movie Video Uploader** একটি হেডলেস, অ্যাসিংক্রোনাস পাইথন সার্ভিস যা কন্টেন্ট ক্রিয়েটর এবং স্ট্রিমিং প্ল্যাটফর্মের জন্য ডিজাইন করা হয়েছে। এটি সম্পূর্ণ ভিডিও ইনজেশন পাইপলাইন অটোমেট করে — লোকাল ডাইরেক্টরি স্ক্যান করা থেকে শুরু করে ফাইল পার্সিং, মেটাডাটা সংগ্রহ, মাল্টিপল প্ল্যাটফর্মে আপলোড, থাম্বনেইল ও পোস্টার স্টোরেজ এবং সবকিছু একটি নরমালাইজড রিলেশনাল ডাটাবেজে সেভ করা পর্যন্ত।

### 🔄 কাজের প্রক্রিয়া (Pipeline Flow Diagram)

```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│   📂 Folder      │    │   🔍 Filename     │    │   🌐 Metadata     │
│   Scan          │───▶│   Parsing        │───▶│   Fetch           │
│   (Continuous)  │    │                  │    │   (TMDB/OMDb)     │
└─────────────────┘    └──────────────────┘    └───────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│   🗂️ Archive     │    │   💾 Save to      │    │   📤 Upload to    │
│   or            │◀───│   Database        │◀───│   3 Platforms     │
│   Quarantine    │    │   + Notify        │    │   (Concurrent)    │
└─────────────────┘    └──────────────────┘    └───────────────────┘
```

### 📌 এটি কী নয় (What This Is NOT)

এটি একটি **ব্যাকএন্ড-অনলি, CLI-চালিত টুল**। এতে **কোনো ওয়েব UI, ফ্রন্টএন্ড, GUI, বা HTTP সার্ভার নেই**। এটি একটি কন্টিনিউয়াস ব্যাকগ্রাউন্ড প্রসেস হিসাবে চলে যা একটি ফোল্ডার স্ক্যান করে এবং স্বয়ংক্রিয়ভাবে ফাইল প্রসেস করে।

---

## Key Features

### 📁 ১. স্মার্ট ফাইল পার্সিং
- ফাইলের নাম থেকে অটোমেটিক **Title, Year, Season, Episode, Language** এবং **Quality** ডিটেক্ট করে
- Movie এবং TV Series আলাদা করতে সক্ষম
- URL-encoded brackets (`5B`/`5D`) হ্যান্ডেল করে
- বহু-ভাষা ডিটেকশন: Original, Hindi, Bengali, Japanese, English, Korean এবং আরও
- ঐচ্ছিক কঠোর বছর যাচাই (Year Validation) — বছর না থাকলে `unmatched_videos/`-এ মুভ হয়

### 🌐 ২. ডুয়াল মেটাডাটা সোর্স সহ ফলব্যাক
- **প্রাথমিক**: TMDB API (অ্যাসিংক্রোনাস `aiohttp` দিয়ে) — title, overview, genres, keywords, posters, backdrops ফেচ করে
- **ফলব্যাক**: OMDb API — TMDB-তে না পেলে অটোমেটিক IMDB ID লুকআপ
- **ডাটাবেজ ক্যাশ**: Supabase থেকে আগে ফেচ করা মেটাডাটা পুনঃব্যবহার (API কল কমায়)
- **পার-টাইটল লকিং**: একই টাইটেলের জন্য একাধিক কনকারেন্ট API ফেচ ব্লক করে

### 🖼️ ৩. Supabase Storage ইন্টিগ্রেশন
- পোস্টার, ব্যানার এবং থাম্বনেইল Supabase Storage-এ আপলোড করে
- সাজানো ফোল্ডার স্ট্রাকচার: `{tmdb_id}/s{season_number}/{type}.jpg`
- স্মার্ট ডুপ্লিকেট ডিটেকশন (409 Conflict হ্যান্ডলিং — অপ্রয়োজনীয় আপলোড বাদ)

### ⚡ ৪. কনকারেন্ট মাল্টি-প্ল্যাটফর্ম আপলোড
- একসাথে **DoodStream**, **MixDrop**, এবং **StreamTape**-এ আপলোড করে
- কনফিগারযোগ্য কনকারেন্সি লিমিট (ডিফল্ট: ৩টি প্যারালেল আপলোড)
- প্রতিটি আপলোডে `tqdm` প্রগ্রেস বার (বাইট-লেভেল ট্র্যাকিং)
- ট্রানজিয়েন্ট ত্রুটিতে এক্সপোনেনশিয়াল ব্যাকঅফ সহ রিট্রাই ডেকোরেটর

### 🔄 ৫. কন্টিনিউয়াস স্ক্যানিং
- কনফিগারযোগ্য ইন্টারভালে ভিডিও ফোল্ডার স্ক্যান করে (ডিফল্ট: ৩০ সেকেন্ড)
- ডাটাবেজের সাথে ডুপ্লিকেট ডিটেকশন — পুনঃআপলোড বাদ
- সিঙ্গেল-রান মোডও উপলব্ধ (ব্যাচ প্রসেসিংয়ের জন্য)

### 🗂️ ৬. সেফ আর্কাইভ সিস্টেম
- সফলভাবে আপলোড হওয়া ফাইল → `archive/success/`
- ব্যর্থ আপলোড → `archive/failed/`
- মেটাডাটা না পাওয়া ফাইল → `unmatched_videos/`
- N দিনের পুরনো অরফান ফাইল → `quarantine/`
- **কোনো ফাইল ডিলিট হয় না** — সবকিছু নিরাপদে মুভ করা হয়

### 📦 ৭. সাবটাইটেল ও NFO প্যাকেজিং
- ভিডিওর পাশে `.srt`, `.vtt`, `.ass` এবং `.nfo` ফাইল অটোমেটিক ডিটেক্ট করে
- স্ট্রিমিং প্ল্যাটফর্মে আপলোডের আগে ZIP আর্কাইভে প্যাকেজ করে

### 🛡️ ৮. ফাইল ইন্টিগ্রিটি চেক
- প্রসেসিংয়ের আগে ফাইলের অস্তিত্ব এবং পড়ার যোগ্যতা যাচাই করে
- ডিস্ক স্পেস মনিটরিং — সতর্কতা (৯০%) এবং ক্রিটিক্যাল (৯৫%) থ্রেশহোল্ড

### 📊 ৯. নরমালাইজড ডাটাবেজ স্কিমা
- **বহু-ভাষা সমর্থন**: Original এবং Dubbed ভার্সন `parent_media_id` দিয়ে লিঙ্ক করা
- **ক্রস-ল্যাংগুয়েজ ওয়াচ হিস্ট্রি**: এক ভাষায় দেখা progress অন্য ভাষায় sync হয়
- **রিলেশনাল ডিজাইন**: Seasons, Episodes, Video Sources, Genres, Tags — সব আলাদা টেবিলে
- **ফুল-টেক্সট সার্চ**: PostgreSQL `tsvector` অটোমেটিক ট্রিগার আপডেট সহ

### 🏷️ ১০. অ্যাডভান্সড ট্যাগিং সিস্টেম
- TMDB থেকে অটোমেটিক Keywords ফেচ করে `media_tags` টেবিলে সেভ করে
- ভবিষ্যৎ রেকমেন্ডেশন ইঞ্জিন এবং অ্যাডভান্সড সার্চের জন্য প্রস্তুত

### 🔐 ১১. প্রোডাকশন-গ্রেড সিকিউরিটি
- RLS (Row Level Security) রেডি
- ব্যাকএন্ড অপারেশনের জন্য `SERVICE_ROLE_KEY` ব্যবহার
- ভবিষ্যৎ ফ্রন্টএন্ডের জন্য `ANON_KEY` সংরক্ষিত

### 📲 ১২. রিয়েল-টাইম নোটিফিকেশন
- **Telegram**: আপলোড সফল (পোস্টার সহ), ব্যর্থতা, আনম্যাচড ভিডিও, ক্রিটিক্যাল এরর
- **Discord**: এম্বেডেড মেসেজ ফরম্যাটে একই সতর্কতা

---

## Architecture & Technology Stack

### 🏗️ আর্কিটেকচার ডায়াগ্রাম

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                 │
│  (No UI — CLI/Docker/Systemd — Headless Backend Service)           │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                      APPLICATION LAYER                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  main.py  │  │ config.py│  │ scanner  │  │processor │          │
│  │ (Entry)   │  │ (Config) │  │ (Folder) │  │(Pipeline)│          │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                       UTILITIES LAYER                                │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │
│  │ parser │ │metadata│ │uploaders│ │db_mgr  │ │ alerts │          │
│  │        │ │(TMDB)  │ │(3 APIs)│ │(Supa)  │ │(TG/DC) │          │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                       EXTERNAL SERVICES                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │  TMDB    │ │ Supabase │ │DoodStream│ │ Telegram │             │
│  │  OMDb    │ │ (DB+S3)  │ │MixDrop   │ │ Discord  │             │
│  └──────────┘ └──────────┘ │StreamTape│ └──────────┘             │
│                             └──────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

### 🛠️ প্রযুক্তি স্ট্যাক

| স্তর | প্রযুক্তি | ব্যবহার |
|---|---|---|
| **ভাষা** | Python 3.10+ | কোর রানটাইম |
| **অ্যাসিংক্রোনাস রানটাইম** | `asyncio` | Non-blocking I/O ও টাস্ক অর্কেস্ট্রেশন |
| **HTTP (Async)** | `aiohttp` | TMDB মেটাডাটা ফেচিং |
| **HTTP (Sync)** | `requests` | ভিডিও আপলোড (`run_in_executor` দিয়ে) |
| **HTTP (Modern)** | `httpx` | অতিরিক্ত HTTP ক্লায়েন্ট |
| **ডাটাবেজ** | Supabase (PostgreSQL) | মেটাডাটা স্টোরেজ |
| **ক্লাউড স্টোরেজ** | Supabase Storage | ইমেজ হোস্টিং (পোস্টার, থাম্বনেইল) |
| **মেটাডাটা API** | TMDB API (প্রাথমিক), OMDb API (ফলব্যাক) | কন্টেন্ট মেটাডাটা |
| **ভিডিও হোস্টিং** | DoodStream, MixDrop, StreamTape | ভিডিও ফাইল হোস্টিং |
| **নোটিফিকেশন** | Telegram Bot API, Discord Webhooks | রিয়েল-টাইম সতর্কতা |
| **প্রগ্রেস** | `tqdm` | কনসোল প্রগ্রেস বার |
| **লগিং** | `loguru` | রোটেশন সহ স্ট্রাকচার্ড লগিং |
| **কনফিগ** | `python-dotenv` | এনভায়রনমেন্ট ভ্যারিয়েবল ম্যানেজমেন্ট |
| **প্যাকেজিং** | PyInstaller | Windows পোর্টেবল এক্সিকিউটেবল |
| **কন্টেইনারাইজেশন** | Docker + Docker Compose | ডিপ্লয়মেন্ট ও আইসোলেশন |

### 📦 ডিপেন্ডেন্সি লিস্ট (`requirements.txt`)

```
supabase==2.31.0
aiohttp==3.9.1
httpx==0.27.2
websockets==15.0.1
tqdm==4.66.1
python-dotenv==1.0.0
requests==2.31.0
loguru==0.7.3
```

---

## Prerequisites

### 🔴 বাধ্যতামূলক (Required)
- **Python 3.10+** — PATH-এ ইনস্টল ও উপলব্ধ
- **Supabase** প্রজেক্ট — একটি সার্ভিস রোল কী সহ
- **TMDB API Key** — [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)-তে ফ্রি রেজিস্ট্রেশন
- কমপক্ষে একটি ভিডিও হোস্টিং প্ল্যাটফর্ম অ্যাকাউন্ট:
  - [DoodStream](https://doodstream.com/) API key
  - [MixDrop](https://mixdrop.to/) email + key
  - [StreamTape](https://streamtape.com/) login + password

### 🟢 ঐচ্ছিক (Optional)
- **OMDb API Key** — [omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)-তে ফ্রি (TMDB ফলব্যাক হিসেবে)
- **Telegram Bot** — [@BotFather](https://t.me/BotFather)-এর মাধ্যমে তৈরি করুন (আপলোড নোটিফিকেশনের জন্য)
- **Discord Webhook URL** — Discord নোটিফিকেশনের জন্য
- **Docker Engine 20.10+** এবং **Docker Compose 2.0+** (কন্টেইনারাইজড ডিপ্লয়মেন্টের জন্য)

---

## Installation & Setup

### ধাপ ১: রিপোজিটরি ক্লোন ও ভার্চুয়াল এনভায়রনমেন্ট তৈরি

```bash
# রিপোজিটরি ক্লোন করুন
git clone <repository-url>
cd anime-streaming-platform/backend

# ভার্চুয়াল এনভায়রনমেন্ট তৈরি করুন
# Windows:
python -m venv venv
venv\Scripts\activate

# Linux/macOS:
python3 -m venv venv
source venv/bin/activate

# ডিপেন্ডেন্সি ইনস্টল করুন
pip install -r requirements.txt
```

### ধাপ ২: Supabase ডাটাবেজ সেটআপ

আপনার Supabase প্রজেক্টের **SQL Editor**-এ গিয়ে নিচের SQL কোড রান করুন:

```sql
-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- MEDIA TABLE (Core — Movies, TV Series, Anime)
-- ============================================================
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

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_media_parent ON media(parent_media_id);
CREATE INDEX idx_media_language ON media(language_code);
CREATE INDEX idx_media_search ON media USING GIN(search_vector);
CREATE INDEX idx_media_popularity ON media(popularity_score);
CREATE INDEX idx_media_type_status ON media(media_type, status);

-- ============================================================
-- GENRES (Many-to-Many)
-- ============================================================
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

-- ============================================================
-- TAGS (Keywords from TMDB)
-- ============================================================
CREATE TABLE media_tags (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  media_id UUID REFERENCES media(id) ON DELETE CASCADE,
  tag_name TEXT NOT NULL,
  tag_type TEXT
);
CREATE INDEX idx_tags_media ON media_tags(media_id);

-- ============================================================
-- SEASONS
-- ============================================================
CREATE TABLE seasons (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  media_id UUID REFERENCES media(id) ON DELETE CASCADE,
  season_number INTEGER NOT NULL,
  title TEXT,
  UNIQUE(media_id, season_number)
);

-- ============================================================
-- EPISODES
-- ============================================================
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

-- ============================================================
-- VIDEO SOURCES (Upload links per platform)
-- ============================================================
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

-- ============================================================
-- VIDEO ANALYTICS
-- ============================================================
CREATE TABLE video_analytics (
  media_id UUID REFERENCES media(id) ON DELETE CASCADE PRIMARY KEY,
  total_views INTEGER DEFAULT 0,
  total_watch_time_seconds BIGINT DEFAULT 0,
  average_rating FLOAT DEFAULT 0,
  rating_count INTEGER DEFAULT 0,
  completion_rate FLOAT DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-update search_vector on insert/update
CREATE OR REPLACE FUNCTION update_media_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.overview, ''));
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_media_search_update
BEFORE INSERT OR UPDATE ON media
FOR EACH ROW EXECUTE FUNCTION update_media_search_vector();

-- Auto-update updated_at timestamp
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

### ধাপ ৩: Supabase Storage Bucket তৈরি

1. **Supabase Dashboard** → **Storage** সেকশনে যান
2. **New Bucket**-এ ক্লিক করুন
3. নাম: `posters`
4. **Public** সেট করুন
5. **Create Bucket** ক্লিক করুন

### ধাপ ৪: Environment Variables সেটআপ

প্রজেক্টের root-এ `.env` ফাইল তৈরি করুন:

```env
# ─── Supabase ─────────────────────────────────────────────
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
SUPABASE_STORAGE_BUCKET=posters

# ─── DoodStream API ───────────────────────────────────────
DOODSTREAM_API_KEY=your_doodstream_api_key

# ─── MixDrop API ──────────────────────────────────────────
MIXDROP_API_URL=https://ul.mixdrop.ag/api
MIXDROP_EMAIL=your_mixdrop_email
MIXDROP_KEY=your_mixdrop_key

# ─── StreamTape API ───────────────────────────────────────
STREAMTAPE_LOGIN=your_streamtape_login
STREAMTAPE_PASSWORD=your_streamtape_password

# ─── Video Folder ─────────────────────────────────────────
VIDEO_FOLDER=./videos

# ─── TMDB API ─────────────────────────────────────────────
TMDB_API_KEY=your_tmdb_api_key

# ─── OMDb API (Fallback) ─────────────────────────────────
OMDB_API_KEY=your_omdb_api_key

# ─── Alert Configuration ──────────────────────────────────
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

> ⚠️ **সিকিউরিটি**: `.env` ফাইলকে কখনও Git-এ commit করবেন না। নিশ্চিত করুন এটি `.gitignore`-এ আছে।

---

## Windows Portable Build

Windows পোর্টেবল এক্সিকিউটেবল তৈরি করুন — Python ছাড়াই যেকোনো PC-তে চালানো যায়।

### বিল্ড স্টেপস

```bash
# ১. ভার্চুয়াল এনভায়রনমেন্ট অ্যাক্টিভেট এবং ডিপেন্ডেন্সি ইনস্টল
venv\Scripts\activate
pip install -r requirements.txt

# ২. বিল্ড স্ক্রিপ্ট রান করুন
build_windows.bat
```

### আউটপুট

`dist\AnimeUploader\`-এ একটি সম্পূর্ণ পোর্টেবল ফোল্ডার তৈরি হয়:

```
dist/AnimeUploader/
├── AnimeUploader.exe          # স্ট্যান্ডঅ্যালোন এক্সিকিউটেবল
├── run_portable.bat           # লঞ্চ স্ক্রিপ্ট
├── README.md                  # ডকুমেন্টেশন
├── .env                       # আপনার কনফিগারেশন (root থেকে কপি করুন)
├── videos/                    # ভিডিও ফাইল এখানে রাখুন
├── archive/                   # আপলোড হওয়া ফাইল এখানে মুভ হয়
├── unmatched_videos/          # মেটাডাটা ছাড়া ফাইল
├── quarantine/                # অরফান ফাইল
└── logs/                      # অ্যাপ্লিকেশন লগ
```

### অন্য PC-তে ডিপ্লয়

1. `dist\AnimeUploader\` পুরো ফোল্ডার ZIP করুন
2. টার্গেট Windows PC-তে কপি করুন
3. নিশ্চিত করুন `.env`-এ বৈধ API key আছে
4. `run_portable.bat` ডাবল-ক্লিক করে স্টার্ট করুন

> টার্গেট PC-তে Python, pip, বা source code লাগবে না।

### পোর্টেবল বিল্ড আপডেট

1. সোর্স প্রজেক্টে আবার `build_windows.bat` রান করুন
2. পুরনো `dist\AnimeUploader\` ফোল্ডার রিপ্লেস করুন
3. পুরনো `.env`, `videos/`, এবং `archive/` সংরক্ষণ করুন

---

## Docker Deployment

### 🐳 প্রিরিকুইজিট

- **Docker Engine** 20.10+
- **Docker Compose** 2.0+
- ইনস্টল: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) অথবা [Docker Engine](https://docs.docker.com/engine/install/) (Linux)

### 🚀 দ্রুত শুরু — Docker Compose দিয়ে

```bash
# backend ডাইরেক্টরিতে যান
cd anime-streaming-platform/backend

# .env কনফিগার করুন (উপরের Environment Variables দেখুন)

# ডিটাচড মোডে স্টার্ট করুন
docker-compose up -d

# লাইভ লগ দেখুন
docker-compose logs -f anime-uploader

# সার্ভিস বন্ধ করুন
docker-compose down
```

### 📦 ম্যানুয়াল Docker Build ও Run

```bash
# ইমেজ বিল্ড করুন
docker build -t anime-uploader .

# কন্টেইনার রান করুন
docker run -d \
  --name anime-uploader \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/videos:/app/videos \
  -v $(pwd)/unmatched_videos:/app/unmatched_videos \
  -v $(pwd)/archive:/app/archive \
  -v $(pwd)/quarantine:/app/quarantine \
  anime-uploader

# লগ দেখুন
docker logs -f anime-uploader

# বন্ধ / রিস্টার্ট
docker stop anime-uploader
docker restart anime-uploader
```

**Windows PowerShell:**

```powershell
docker run -d `
  --name anime-uploader `
  --restart unless-stopped `
  --env-file .env `
  -v ${PWD}/logs:/app/logs `
  -v ${PWD}/videos:/app/videos `
  -v ${PWD}/unmatched_videos:/app/unmatched_videos `
  -v ${PWD}/archive:/app/archive `
  -v ${PWD}/quarantine:/app/quarantine `
  anime-uploader
```

### 📄 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# সিস্টেম ডিপেন্ডেন্সি
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# পাইথন ডিপেন্ডেন্সি (ক্যাশড লেয়ার)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# অ্যাপ্লিকেশন কোড
COPY . .

# প্রয়োজনীয় ডাইরেক্টরি তৈরি
RUN mkdir -p /app/videos \
    /app/archive/success \
    /app/archive/failed \
    /app/unmatched_videos \
    /app/quarantine \
    /app/logs

# ডিফল্ট এনভায়রনমেন্ট
ENV VIDEO_FOLDER=/app/videos
ENV UNMATCHED_VIDEOS_FOLDER=/app/unmatched_videos

# হেলথ চেক
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "main.py"]
```

### 📝 docker-compose.yml

```yaml
version: "3.8"

services:
  anime-uploader:
    build: .
    container_name: anime-uploader
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./videos:/app/videos
      - ./unmatched_videos:/app/unmatched_videos
      - ./archive:/app/archive
      - ./quarantine:/app/quarantine
    environment:
      - VIDEO_FOLDER=/app/videos
      - UNMATCHED_VIDEOS_FOLDER=/app/unmatched_videos
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
```

### 📁 ভলিউম ম্যাপিং

| হোস্ট পাথ | কন্টেইনার পাথ | উদ্দেশ্য |
|---|---|---|
| `./videos` | `/app/videos` | ইনপুট ফোল্ডার — নতুন ভিডিও এখানে রাখুন |
| `./archive/success` | `/app/archive/success` | সফলভাবে আপলোড হওয়া ফাইল |
| `./archive/failed` | `/app/archive/failed` | ব্যর্থ আপলোড |
| `./unmatched_videos` | `/app/unmatched_videos` | মেটাডাটা ছাড়া ফাইল |
| `./quarantine` | `/app/quarantine` | অরফান ফাইল (N দিনের পুরনো) |
| `./logs` | `/app/logs` | অ্যাপ্লিকেশন লগ |

### 🐳 Docker ম্যানেজমেন্ট কমান্ড

```bash
# কন্টেইনার ম্যানেজমেন্ট
docker ps                          # চলমান কন্টেইনার
docker ps -a                       # সব কন্টেইনার
docker stop anime-uploader         # বন্ধ করুন
docker start anime-uploader        # শুরু করুন
docker restart anime-uploader      # রিস্টার্ট করুন
docker rm anime-uploader           # মুছে ফেলুন
docker rm -f anime-uploader        # ফোর্স রিমুভ

# ইমেজ ম্যানেজমেন্ট
docker images                      # ইমেজ লিস্ট
docker rmi anime-uploader          # ইমেজ রিমুভ
docker image prune -a              # অপ্রয়োজনীয় ইমেজ ক্লিন

# লগ ও ডিবাগিং
docker logs -f anime-uploader      # রিয়েল-টাইম লগ
docker logs --tail 100 anime-uploader  # শেষ ১০০ লাইন
docker exec -it anime-uploader /bin/bash  # কন্টেইনারে শেল

# Compose কমান্ড
docker-compose up -d               # ব্যাকগ্রাউন্ডে শুরু
docker-compose down                # বন্ধ ও রিমুভ
docker-compose restart             # রিস্টার্ট
docker-compose ps                  # স্ট্যাটাস
docker-compose logs -f             # লাইভ লগ
docker-compose up -d --build       # রিবিল্ড ও শুরু
docker-compose down -v             # ভলিউম সহ রিমুভ (⚠️ ডেটা মুছে যায়)
```

### 🔐 Docker সিকিউরিটি বেস্ট প্র্যাকটিস

1. **`.env` ফাইল কখনও Git-এ commit করবেন না** — `.gitignore`-এ নিশ্চিত করুন
2. **নন-রুট ইউজার** ব্যবহার করুন (Dockerfile-এ যোগ করুন):
   ```dockerfile
   RUN useradd -m appuser && chown -R appuser:appuser /app
   USER appuser
   ```
3. **রিসোর্স লিমিট** সেট করুন (`memory: 512M`, `cpus: '1.0'`)
4. **লগ রোটেশন** কনফিগার করুন (ডিস্ক ফুল হওয়া প্রতিরোধে)

### 🔄 Watchtower দিয়ে অটো-আপডেট

```yaml
# docker-compose.yml-এ যোগ করুন
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 3600  # প্রতি ঘণ্টায় চেক করবে
```

### 🐛 Docker ট্রাবলশুটিং

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| কন্টেইনার সাথে সাথে বন্ধ | `.env` অনুপস্থিত বা ভুল | `docker run -it --rm --env-file .env anime-uploader` দিয়ে চালান |
| ভলিউমে পারমিশন ডিনাইড | হোস্ট ফোল্ডার পারমিশন | `chmod -R 755 ./videos ./archive ./logs` |
| নেটওয়ার্ক সমস্যা (Supabase/API) | DNS বা সংযোগ | `docker run --dns 8.8.8.8 --env-file .env anime-uploader` |
| বেশি মেমোরি ব্যবহার | বড় ফাইল প্রসেসিং | মেমোরি লিমিট: `docker run -m 512m --env-file .env anime-uploader` |
| লগ খুব বড় | রোটেশন নেই | `docker-compose.yml`-এ `logging` কনফিগার করুন |

---

## Project Structure

```
anime-streaming-platform/backend/
│
├── main.py                     # অ্যাপ্লিকেশন এন্ট্রি পয়েন্ট (asyncio-based)
├── config.py                   # সেন্ট্রালাইজড কনফিগারেশন (২৫+ সেটিংস)
├── requirements.txt            # পাইথন ডিপেন্ডেন্সি
├── .env                        # এনভায়রনমেন্ট ভ্যারিয়েবল (API keys, secrets)
├── .gitignore                  # Git ইগনোর রুলস
├── .dockerignore               # Docker বিল্ড ইগনোর রুলস
│
├── Dockerfile                  # Docker ইমেজ ডেফিনিশন
├── docker-compose.yml          # Docker Compose সার্ভিস কনফিগ
├── Docker Documention.md       # Docker ডিপ্লয়মেন্ট গাইড
│
├── AnimeUploader.spec          # PyInstaller বিল্ড স্পেক (Windows)
├── build_windows.bat           # Windows পোর্টেবল বিল্ড স্ক্রিপ্ট
├── run_uploader.bat            # সোর্স থেকে চালান (venv অটো-ক্রিয়েট)
├── run_portable.bat            # পোর্টেবল ডিস্ট্রিবিউশন থেকে চালান
│
├── Documents.md                # এই ডকুমেন্টেশন ফাইল
│
├── utils/                      # কোর ইউটিলিটি মডিউল (১৭টি ফাইল)
│   ├── __init__.py
│   ├── alerts.py               # Telegram ও Discord নোটিফিকেশন
│   ├── cleanup.py              # অরফান ফাইল কোয়ারেন্টাইন লজিক
│   ├── db_manager.py           # নরমালাইজড ডাটাবেজ CRUD অপারেশন
│   ├── disk_monitor.py         # ডিস্ক স্পেস মনিটরিং
│   ├── file_manager.py         # ফাইল অপারেশন (archive, move, ZIP)
│   ├── image_uploader.py       # Supabase Storage ইমেজ আপলোড
│   ├── integrity.py            # ফাইল ইন্টিগ্রিটি চেক
│   ├── logger.py               # Loguru-based লগিং
│   ├── metadata.py             # TMDB মেটাডাটা ফেচিং (async)
│   ├── models.py               # VideoMetadata dataclass (৩৭টি ফিল্ড)
│   ├── omdb_fetcher.py         # OMDb API ফলব্যাক ফেচার
│   ├── parser.py               # Regex-based ফাইলনেম পার্সিং
│   ├── processor.py            # মূল ভিডিও প্রসেসিং পাইপলাইন
│   ├── retry.py                # রিট্রাই ডেকোরেটর (exponential backoff)
│   ├── scanner.py              # ফোল্ডার স্ক্যানিং ও ডুপ্লিকেট ডিটেকশন
│   └── uploaders.py            # DoodStream/MixDrop/StreamTape আপলোডার
│
├── videos/                     # ইনপুট ফোল্ডার — ভিডিও ফাইল এখানে রাখুন
├── archive/
│   ├── success/                # সফলভাবে আপলোড হওয়া ফাইল
│   └── failed/                 # ব্যর্থ আপলোড
├── unmatched_videos/           # মেটাডাটা ছাড়া ফাইল
├── quarantine/                 # অরফান ফাইল
├── temp_tmdb_images/           # অস্থায়ী TMDB ইমেজ ক্যাশ
├── logs/                       # অ্যাপ্লিকেশন লগ
│
├── build/                      # PyInstaller বিল্ড আর্টিফ্যাক্ট
├── dist/                       # Windows পোর্টেবল ডিস্ট্রিবিউশন
├── venv/                       # Python ভার্চুয়াল এনভায়রনমেন্ট
└── __pycache__/                # Python বাইটকোড ক্যাশ
```

---

## Filename Format Convention

### 📺 TV Series / Anime

```
Title (Year) [Language]-S{Season}E{Episode}-{Quality}.mp4
```

**উদাহরণ:**
```
Naruto Shippuden (2007) [Hindi]-S01E01-1080P.mp4
Attack on Titan (2013) [Japanese]-S03E12-720P.mkv
ONE PIECE (1999) [Hindi]-S1E4-480P.mp4
My Hero Academia (2016) [Bengali]-S04E10-1080P.mp4
```

### 🎬 Movies

```
Title (Year) [Language]-{Quality}.mp4
```

**উদাহরণ:**
```
Avengers Endgame (2019) [Hindi]-1080P.mp4
Your Name (2016) [Japanese]-1080P.mkv
Spirited Away (2001) [Bengali]-720P.mp4
```

### ✅ সমর্থিত ভিডিও এক্সটেনশন

`.mp4`, `.avi`, `.mkv`, `.mov`, `.flv`, `.webm`, `.wmv`, `.m4v`

### 📌 নোট

- `REQUIRE_YEAR_IN_FILENAME = True` হলে `Title (Year)` অংশ **বাধ্যতামূলক**। বছর ছাড়া ফাইল `unmatched_videos/`-এ মুভ হয় এবং Telegram অ্যালার্ট যায়।
- ভাষা ডিটেকশন সমর্থন করে: `Original`, `Hindi`, `Bengali`, `Japanese`, `English`, `Korean`, `Thai`, `Chinese`, `Portuguese`, `Spanish`, `French` এবং আরও।
- URL-encoded brackets (`5B`/`5D`) অটোমেটিক ডিকোড হয়।

---

## Configuration Reference

সমস্ত কনফিগারেশন `config.py`-এ সেন্ট্রালাইজড। সংবেদনশীল মান `os.getenv()` দিয়ে `.env` থেকে লোড হয়।

### ⚙️ কোর সেটিংস

| সেটিং | ডিফল্ট | বিবরণ |
|---|---|---|
| `ENABLE_CONTINUOUS_SCAN` | `True` | কন্টিনিউয়াস ফোল্ডার স্ক্যানিং |
| `SCAN_INTERVAL_SECONDS` | `30` | স্ক্যান সাইকেলের মধ্যে সেকেন্ড |
| `ENABLE_DATABASE_SAVE` | `True` | Supabase-এ মেটাডাটা সেভ |
| `CHECK_DUPLICATE_IN_DB` | `True` | ডাটাবেজে থাকা ফাইল স্কিপ |
| `VIDEO_FOLDER` | `./videos` | ইনপুট ভিডিও ডাইরেক্টরি |

### 🌐 প্ল্যাটফর্ম টগল

| সেটিং | ডিফল্ট | বিবরণ |
|---|---|---|
| `ENABLE_DOODSTREAM` | `True` | DoodStream-এ আপলোড |
| `ENABLE_MIXDROP` | `True` | MixDrop-এ আপলোড |
| `ENABLE_STREAMTAPE` | `True` | StreamTape-এ আপলোড |

### 🎨 মেটাডাটা ও স্টোরেজ

| সেটিং | ডিফল্ট | বিবরণ |
|---|---|---|
| `ENABLE_TMDB_METADATA` | `True` | TMDB থেকে মেটাডাটা ফেচ |
| `REQUIRE_YEAR_IN_FILENAME` | `True` | ফাইলনেমে বছর বাধ্যতামূলক |
| `ENABLE_IMAGE_STORAGE` | `True` | Supabase Storage-এ ইমেজ আপলোড |
| `SUPABASE_STORAGE_BUCKET` | `posters` | স্টোরেজ বাকেট নাম |
| `UNMATCHED_VIDEOS_FOLDER` | `./unmatched_videos` | আনম্যাচড ফাইল ডাইরেক্টরি |

### 🗂️ ফাইল হ্যান্ডলিং ও আর্কাইভ

| সেটিং | ডিফল্ট | বিবরণ |
|---|---|---|
| `ENABLE_SAFE_ARCHIVE` | `True` | প্রসেসিংয়ের পর ফাইল আর্কাইভ |
| `ARCHIVE_SUCCESS_FOLDER` | `./archive/success` | সফল আর্কাইভ পাথ |
| `ARCHIVE_FAILED_FOLDER` | `./archive/failed` | ব্যর্থ আর্কাইভ পাথ |
| `ENABLE_SUBTITLE_NFO_SUPPORT` | `True` | সাবটাইটেল/NFO ভিডিওর সাথে প্যাকেজ |
| `SUBTITLE_EXTENSIONS` | `{.srt, .vtt, .ass}` | সাবটাইটেল এক্সটেনশন |
| `NFO_EXTENSIONS` | `{.nfo}` | NFO এক্সটেনশন |
| `ENABLE_INTEGRITY_CHECK` | `True` | আপলোডের আগে ফাইল যাচাই |

### 🧹 অরফান ক্লিনআপ

| সেটিং | ডিফল্ট | বিবরণ |
|---|---|---|
| `ENABLE_ORPHAN_CLEANUP` | `True` | অটোমেটিক অরফান ফাইল ক্লিন |
| `ORPHAN_DAYS_LIMIT` | `7` | অরফান ধরা হওয়ার আগে দিন |
| `QUARANTINE_FOLDER` | `./quarantine` | কোয়ারেন্টাইন ডাইরেক্টরি |

### ⚡ পারফরম্যান্স ও API

| সেটিং | ডিফল্ট | বিবরণ |
|---|---|---|
| `MAX_CONCURRENT_UPLOADS` | `3` | ম্যাক্স সিমুলটেনিয়াস আপলোড |
| `MAX_RETRIES` | `3` | প্রতি আপলোডে রিট্রাই লিমিট |
| `RETRY_DELAY_BASE` | `5` | এক্সপোনেনশিয়াল ব্যাকঅফ বেস ডিলে (সেকেন্ড) |
| `TIMEOUT_PER_FILE` | `3600` | প্রতি ফাইল আপলোড টাইমআউট (সেকেন্ড) |
| `CHECK_DISK_BEFORE_UPLOAD` | `True` | আপলোডের আগে ডিস্ক স্পেস যাচাই |

### 🔌 সমর্থিত এক্সটেনশন

```python
SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".flv", ".webm", ".wmv", ".m4v"}
```

### 🌍 API এন্ডপয়েন্ট

```python
MIXDROP_API_URL = "https://ul.mixdrop.ag/api"
STREAMTAPE_API_URL = "https://api.streamtape.com/file/ul"
```

---

## Database Schema

### 🗃️ টেবিল ওভারভিউ

| টেবিল | বিবরণ |
|---|---|
| `media` | কোর টেবিল — Movies, TV Series, Anime (বহু-ভাষা সমর্থন সহ) |
| `seasons` | TV Series সিজন |
| `episodes` | প্রতি সিজনের এপিসোড |
| `video_sources` | প্রতিটি হোস্টিং প্ল্যাটফর্মের ভিডিও URL |
| `genres` | জেনার লুকআপ টেবিল |
| `media_genres` | ম্যানি-টু-ম্যানি: media ↔ genres |
| `media_tags` | TMDB থেকে Keywords ও tags |
| `video_analytics` | ভিউ কাউন্ট, রেটিং, ওয়াচ টাইম, কমপ্লিশন রেট |

### 📐 Entity Relationship Diagram (Simplified)

```
media ──────────┬─────────────── seasons ──────── episodes ──────── video_sources
                │
                ├─────────────── media_genres ──── genres
                │
                ├─────────────── media_tags
                │
                ├─────────────── video_analytics
                │
                └─────────────── media (self-referencing via parent_media_id)
```

### 🌍 বহু-ভাষা আর্কিটেকচার

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
├── version_type: "dubbed"
└── parent_media_id: uuid-1  ← Original-এর সাথে লিংক

Dubbed (Bengali)
├── id: uuid-3
├── title: "My Bias, My Boss"
├── language_code: "bn"
├── version_type: "dubbed"
└── parent_media_id: uuid-1  ← Original-এর সাথে লিংক
```

এই স্ট্রাকচার সক্ষম করে:
- **ক্রস-ল্যাংগুয়েজ ওয়াচ হিস্ট্রি সিংক**: Hindi-তে Episode 3 দেখা হলে Korean ভার্সনের progress আপডেট হয়
- **ইন্ডিপেনডেন্ট ভিডিও সোর্স**: প্রতিটি ভাষার নিজস্ব আপলোড লিংক
- **ইউনিফাইড মেটাডাটা**: সব ভার্সনে শেয়ার করা poster, backdrop, overview

---

## Supabase Storage Setup

### 🪣 বাকেট কনফিগারেশন

| প্রপার্টি | মান |
|---|---|
| বাকেট নাম | `posters` |
| ভিজিবিলিটি | Public |
| ফাইল সাইজ লিমিট | ডিফল্ট (১ GB) |
| অনুমোদিত MIME টাইপ | `image/jpeg`, `image/png`, `image/webp` |

### 📁 আপলোড পাথ স্ট্রাকচার

```
posters/
├── {tmdb_id}/
│   ├── poster.jpg              # Movie/Series পোস্টার
│   ├── backdrop.jpg            # Backdrop/banner ইমেজ
│   └── s{season_number}/
│       ├── poster.jpg          # সিজন-স্পেসিফিক পোস্টার
│       └── thumbnail.jpg       # এপিসোড থাম্বনেইল
```

### 🔁 ডুপ্লিকেট হ্যান্ডলিং

আপলোডার ইমেজ আপলোডের আগে অস্তিত্ব চেক করে:
- ইমেজ আগে থেকে থাকলে (Supabase থেকে 409 Conflict) **স্কিপ** করা হয় — অপ্রয়োজনীয় আপলোড বাদ
- ডাটাবেজ থেকে URL ফেরত দেওয়া হয়, অপ্রয়োজনীয় API কল এড়ানো হয়

---

## Row Level Security (RLS)

### 🔐 ব্যাকএন্ড (Python Uploader)
- `SERVICE_ROLE_KEY` ব্যবহার করে — **RLS বাইপাস** করে সম্পূর্ণ ডাটাবেজ অ্যাক্সেস
- ব্যাকএন্ড অপারেশনের জন্য RLS **ডিসেবল** থাকে

### 🖥️ ভবিষ্যৎ ফ্রন্টএন্ড (React/Next.js)
- `ANON_KEY` ব্যবহার করবে — **RLS পলিসি enforce** করবে
- ফ্রন্টএন্ড ডিপ্লয়মেন্টের আগে RLS পলিসি কনফিগার করতে হবে

### 🔑 RLS পলিসি উদাহরণ

```sql
-- সব টেবিলে RLS এনাবল
ALTER TABLE media ENABLE ROW LEVEL SECURITY;
ALTER TABLE seasons ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_sources ENABLE ROW LEVEL SECURITY;

-- পাবলিক রিড অ্যাক্সেস
CREATE POLICY "Public can view media"
ON media FOR SELECT
TO public
USING (true);

-- অথেন্টিকেটেড ফুল অ্যাক্সেস
CREATE POLICY "Authenticated users can manage media"
ON media FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);
```

---

## Usage & Runtime

### 🚀 অ্যাপ রান করা

```bash
# ভার্চুয়াল এনভায়রনমেন্ট অ্যাক্টিভেট করুন
# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

# আপলোডার রান করুন
python main.py
```

### 📤 আউটপুট উদাহরণ

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

### ⏹️ অ্যাপ বন্ধ করা

- **সোর্স মোড**: টার্মিনালে `Ctrl+C` চাপুন
- **পোর্টেবল মোড**: Command Prompt-এ `Ctrl+C` চাপুন
- **Docker মোড**: `docker-compose down` অথবা `docker stop anime-uploader`

---

## Monitoring & Alerts

### 📱 Telegram অ্যালার্ট

| ইভেন্ট | ফরম্যাট |
|---|---|
| ✅ সফল আপলোড | পোস্টার ইমেজ সহ ফটো মেসেজ, টাইটেল, প্ল্যাটফর্ম লিংক |
| ❌ ব্যর্থ আপলোড | এরর ডিটেইল ও ফাইলনেম সহ টেক্সট মেসেজ |
| ⚠️ আনম্যাচড ভিডিও | ফাইলনেম ও কারণ (মেটাডাটা নেই) সহ অ্যালার্ট |
| 🚨 ক্রিটিক্যাল এরর | ডিস্ক স্পেস ওয়ার্নিং, ডাটাবেজ কানেকশন ফেইল |

### 💬 Discord ওয়েবহুক অ্যালার্ট

Telegram-এর মতো একই ইভেন্ট, Discord embeds আকারে রঙিন কোডিং সহ:
- 🟢 সবুজ — সফল
- 🔴 লাল — ব্যর্থ
- 🟡 হলুদ — ওয়ার্নিং

### 💽 ডিস্ক স্পেস মনিটরিং

| থ্রেশহোল্ড | অ্যাকশন |
|---|---|
| > 90% ব্যবহার | Telegram/Discord-এ ওয়ার্নিং অ্যালার্ট |
| > 95% ব্যবহার | ক্রিটিক্যাল অ্যালার্ট — আপলোড পজ হতে পারে |

---

## Logging

`loguru` দিয়ে অটোমেটিক রোটেশন সহ:

| লগ ফাইল | ম্যাক্স সাইজ | রিটেনশন | কন্টেন্ট |
|---|---|---|---|
| `logs/app_YYYY-MM-DD.log` | 10 MB | 30 দিন | সব অ্যাপ্লিকেশন ইভেন্ট |
| `logs/errors_YYYY-MM-DD.log` | 5 MB | 60 দিন | শুধু এরর ও এক্সেপশন |

### 📋 লগ ফিচার
- টাইমস্ট্যাম্পসহ এন্ট্রি — মডিউল/ফাংশন/লাইন রেফারেন্স সহ
- সাইজ লিমিট পৌঁছালে অটোমেটিক ফাইল রোটেশন
- দ্রুত ডিবাগিংয়ের জন্য আলাদা এরর লগ
- কালার কোডিং সহ কনসোল আউটপুট

---

## Troubleshooting

### 🔧 DoodStream SSL এরর
```
SSLEOFError(8, 'EOF occurred in violation of protocol')
```
**স্ট্যাটাস**: কোডবেসে ইতিমধ্যে `verify=False` এবং `"Connection": "close"` হেডার দিয়ে ঠিক করা হয়েছে।

### 🔧 ডুপ্লিকেট ফাইল ডিটেকশন
```
⏭️  Already in database: filename.mp4
```
**সমাধান**: ফাইলটি আগে আপলোড হয়ে গেছে। লোকাল কপি ডিলিট করুন অথবা ডাটাবেজ থেকে রেকর্ড রিমুভ করে পুনরায় আপলোড করুন।

### 🔧 মেটাডাটা নট ফাউন্ড
```
⚠️ No metadata found in TMDB or OMDb for: Title
```
**সমাধান**:
1. ফাইলনেম ফরম্যাট কনভেনশন অনুযায়ী আছে কিনা যাচাই করুন
2. টাইটেল TMDB/OMDb-তে সঠিকভাবে মিলেছে কিনা দেখুন
3. `REQUIRE_YEAR_IN_FILENAME = True` হলে `Title (Year)` উপস্থিত আছে কিনা নিশ্চিত করুন
4. ফাইলটি অটোমেটিক `unmatched_videos/`-এ মুভ হবে

### 🔧 ডাটাবেজ কানেকশন এরর
```
 Supabase Error: ...
```
**সমাধান**:
1. `.env`-এ সঠিক `SUPABASE_URL` ও `SUPABASE_SERVICE_ROLE_KEY` আছে কিনা যাচাই করুন
2. ইন্টারনেট কানেক্টিভিটি চেক করুন
3. Supabase প্রজেক্ট সক্রিয় আছে কিনা (পজ করা নয়) নিশ্চিত করুন

### 🔧 আপলোড টাইমআউট
```
⏰ Upload timeout for: filename.mp4
```
**সমাধান**:
1. `config.py`-এ `TIMEOUT_PER_FILE` বাড়ান
2. নেটওয়ার্ক ব্যান্ডউইথ ও স্থিতিশীলতা চেক করুন
3. `MAX_CONCURRENT_UPLOADS` কমিয়ে 1 বা 2 করুন

### 🔧 বেশি মেমোরি ব্যবহার
**সমাধান**:
1. `MAX_CONCURRENT_UPLOADS` কমিয়ে 1 বা 2 করুন
2. বড় ফাইল মেমোরিতে জমে আছে কিনা দেখুন
3. দীর্ঘ চলমান ডিপ্লয়মেন্টে পর্যায়ক্রমে অ্যাপ রিস্টার্ট করুন

---

## Production Deployment

### 🐧 Systemd সার্ভিস (Linux)

```ini
[Unit]
Description=Anime Video Uploader
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=your_user
Group=your_group
WorkingDirectory=/path/to/backend
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PATH=/path/to/venv/bin

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/path/to/backend/videos /path/to/backend/archive /path/to/backend/logs

[Install]
WantedBy=multi-user.target
```

```bash
# সার্ভিস এনাবল ও স্টার্ট করুন
sudo systemctl enable anime-uploader
sudo systemctl start anime-uploader

# স্ট্যাটাস চেক করুন
sudo systemctl status anime-uploader

# লগ দেখুন
sudo journalctl -u anime-uploader -f
```

### ✅ প্রোডাকশন ডিপ্লয়মেন্ট চেকলিস্ট

- [ ] `.env` ফাইল বৈধ API keys দিয়ে কনফিগার করা হয়েছে
- [ ] ভলিউম ডাইরেক্টরি তৈরি করা হয়েছে (`mkdir -p videos archive/success archive/failed logs quarantine unmatched_videos`)
- [ ] Docker রিসোর্স লিমিট সেট করা হয়েছে (memory: 512M, CPU: 1.0)
- [ ] লগ রোটেশন কনফিগার করা হয়েছে (max-size: 10m, max-file: 3)
- [ ] কন্টেইনার রিস্টার্ট পলিসি `unless-stopped` সেট করা হয়েছে
- [ ] `.env` `.gitignore`-এ যোগ করা হয়েছে
- [ ] ভলিউম ব্যাকআপ স্ট্র্যাটেজি আছে
- [ ] মনিটরিং/অ্যালার্টিং সেটআপ করা হয়েছে (Telegram অথবা Discord)
- [ ] ডিস্ক স্পেস মনিটরিং এনাবল আছে (`CHECK_DISK_BEFORE_UPLOAD = True`)
- [ ] অরফান ক্লিনআপ এনাবল আছে (`ENABLE_ORPHAN_CLEANUP = True`)

---

## Backup & Restore

### 💾 ভলিউম ব্যাকআপ

```bash
#!/bin/bash
# Backup স্ক্রিপ্ট
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

tar -czf $BACKUP_DIR/videos_$TIMESTAMP.tar.gz ./videos
tar -czf $BACKUP_DIR/archive_$TIMESTAMP.tar.gz ./archive
tar -czf $BACKUP_DIR/logs_$TIMESTAMP.tar.gz ./logs

echo "Backup completed: $BACKUP_DIR"
```

### ♻️ ব্যাকআপ থেকে রিস্টোর

```bash
# রিস্টোর করুন
tar -xzf backups/videos_YYYYMMDD_HHMMSS.tar.gz -C ./
tar -xzf backups/archive_YYYYMMDD_HHMMSS.tar.gz -C ./
tar -xzf backups/logs_YYYYMMDD_HHMMSS.tar.gz -C ./
```

---

## Future Roadmap

- [ ] Docker প্রোডাকশন অপ্টিমাইজেশন (multi-stage builds, health checks)
- [ ] আপলোড ও স্ট্যাটিস্টিকস মনিটরিংয়ের জন্য Web dashboard
- [ ] React/Next.js ফ্রন্টএন্ড অ্যাপ্লিকেশন
- [ ] অটোমেটিক সাবটাইটেল ডাউনলোড (OpenSubtitles API)
- [ ] কোয়ালিটি-ভিত্তিক আপলোড প্রায়োরিটি (সর্বোচ্চ কোয়ালিটি আগে)
- [ ] মাল্টি-সার্ভার ডিস্ট্রিবিউশন ও লোড ব্যালেন্সিং
- [ ] অ্যাডভান্সড রেকমেন্ডেশন ইঞ্জিন (`media_tags` ব্যবহার করে)
- [ ] ক্রস-ল্যাংগুয়েজ ইউজার ওয়াচ হিস্ট্রি সিংক
- [ ] এক্সটার্নাল ইন্টিগ্রেশনের জন্য REST API এন্ডপয়েন্ট
- [ ] রিয়েল-টাইম স্ট্যাটাস আপডেটের জন্য WebSocket
- [ ] ব্যর্থ আপলোডের ব্যাচ রি-প্রসেসিং
- [ ] কাস্টম আপলোড টার্গেটের জন্য প্লাগইন সিস্টেম

---

## License & Contributing

### 📄 License

MIT License — ব্যবহার, পরিবর্তন, এবং বিতরণ সম্পূর্ণ ফ্রি।

### 🤝 Contributing

Contributions স্বাগতম! অনুগ্রহ করে:
1. রিপোজিটরি ফর্ক করুন
2. ফিচার ব্রাঞ্চ তৈরি করুন (`git checkout -b feature/amazing-feature`)
3. পরিবর্তন commit করুন (`git commit -m 'Add amazing feature'`)
4. ব্রাঞ্চে push করুন (`git push origin feature/amazing-feature`)
5. Pull Request খুলুন

### 📧 Support

প্রশ্ন, বাগ রিপোর্ট, বা ফিচার রিকোয়েস্টের জন্য GitHub-এ issue খুলুন।

---

**Happy Uploading! 🎬✨**
