import os
import aiohttp
import asyncio
from typing import Optional, Dict
from tqdm import tqdm
import sys
from datetime import datetime
from pathlib import Path
from supabase import Client

sys.path.append(str(Path(__file__).parent.parent))
import config
from utils.image_uploader import upload_image_to_supabase
from utils.omdb_fetcher import OMDbMetadataFetcher

_metadata_locks = {}


class TMDBMetadataFetcher:
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY")
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_tv(
        self, title: str, season: int, year: Optional[int] = None
    ) -> Optional[Dict]:
        if not self.api_key:
            return None
        try:
            params = {"api_key": self.api_key, "query": title, "language": "en-US"}
            if year:
                params["first_air_date_year"] = str(year)

            async with self.session.get(
                f"{self.base_url}/search/tv", params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("results"):
                        for result in data["results"]:
                            if result.get("name", "").lower() == title.lower():
                                return await self.get_tv_details(result["id"], season)
                        return await self.get_tv_details(
                            data["results"][0]["id"], season
                        )
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB TV search error: {e}")
            return None

    async def search_movie(
        self, title: str, year: Optional[int] = None
    ) -> Optional[Dict]:
        if not self.api_key:
            return None
        try:
            params = {"api_key": self.api_key, "query": title, "language": "en-US"}
            if year:
                params["primary_release_year"] = str(year)

            async with self.session.get(
                f"{self.base_url}/search/movie", params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("results"):
                        for result in data["results"]:
                            if result.get("title", "").lower() == title.lower():
                                return await self.get_movie_details(result["id"])
                        return await self.get_movie_details(data["results"][0]["id"])
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB Movie search error: {e}")
            return None

    async def get_tv_details(self, tv_id: int, season: int) -> Optional[Dict]:
        try:
            async with self.session.get(
                f"{self.base_url}/tv/{tv_id}",
                params={"api_key": self.api_key, "language": "en-US"},
            ) as response:
                if response.status == 200:
                    tv_data = await response.json()
                    release_date_str = tv_data.get("first_air_date", "")
                    return {
                        "tmdb_id": tv_id,
                        "media_type": "TV Series",
                        "release_year": (
                            int(release_date_str.split("-")[0])
                            if release_date_str
                            else 0
                        ),
                        "tmdb_status": tv_data.get("status", ""),
                        "total_seasons": tv_data.get("number_of_seasons", 0),
                        "total_episodes": tv_data.get("number_of_episodes", 0),
                        "original_language": tv_data.get("original_language", ""),
                        "networks": [n["name"] for n in tv_data.get("networks", [])],
                        "creators": [c["name"] for c in tv_data.get("created_by", [])],
                        "overview": tv_data.get("overview", ""),
                        "genres": [
                            {"name": g["name"]} for g in tv_data.get("genres", [])
                        ],
                        "vote_average": float(tv_data.get("vote_average", 0.0)),
                        "poster_path": tv_data.get("poster_path"),
                        "backdrop_path": tv_data.get("backdrop_path"),
                    }
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB TV details error: {e}")
            return None

    async def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        try:
            async with self.session.get(
                f"{self.base_url}/movie/{movie_id}",
                params={"api_key": self.api_key, "language": "en-US"},
            ) as response:
                if response.status == 200:
                    m_data = await response.json()
                    release_date_str = m_data.get("release_date", "")
                    return {
                        "tmdb_id": movie_id,
                        "media_type": "Movie",
                        "release_year": (
                            int(release_date_str.split("-")[0])
                            if release_date_str
                            else 0
                        ),
                        "tmdb_status": m_data.get("status", ""),
                        "total_seasons": 0,
                        "total_episodes": 0,
                        "original_language": m_data.get("original_language", ""),
                        "networks": [
                            n["name"] for n in m_data.get("production_companies", [])
                        ],
                        "creators": [],
                        "overview": m_data.get("overview", ""),
                        "genres": [
                            {"name": g["name"]} for g in m_data.get("genres", [])
                        ],
                        "vote_average": float(m_data.get("vote_average", 0.0)),
                        "poster_path": m_data.get("poster_path"),
                        "backdrop_path": m_data.get("backdrop_path"),
                    }
            return None
        except Exception as e:
            tqdm.write(f"❌ TMDB Movie details error: {e}")
            return None

    async def fetch_image_bytes(self, image_path: str) -> Optional[bytes]:
        if not image_path:
            return None
        try:
            async with self.session.get(
                f"{self.image_base_url}{image_path}"
            ) as response:
                if response.status == 200:
                    return await response.read()
            return None
        except Exception as e:
            tqdm.write(f"❌ Image fetch error: {e}")
            return None


async def fetch_and_process_metadata(
    supabase_client: Client,
    supabase_storage_client: Client,
    title: str,
    media_type: str,
    season: int = None,
    year: int = None,
) -> Optional[Dict]:
    lock_key = f"{title}_{media_type}_{season or 'movie'}_{year or 'no_year'}"
    if lock_key not in _metadata_locks:
        _metadata_locks[lock_key] = asyncio.Lock()

    async with _metadata_locks[lock_key]:
        # 1. Check DB
        try:
            db_media_type = "tv_series" if media_type == "TV Series" else "movie"
            query = (
                supabase_client.table("media")
                .select(
                    "title, media_type, tmdb_id, release_year, overview, "
                    "poster_url, backdrop_url, original_language, total_episodes, "
                    "popularity_score"
                )
                .eq("title", title)
                .eq("media_type", db_media_type)
            )
            if year is not None:
                query = query.eq("release_year", year)

            result = query.not_.is_("poster_url", None).limit(1).execute()

            if (
                result.data
                and len(result.data) > 0
                and result.data[0].get("poster_url")
            ):
                tqdm.write(
                    f"✅ {media_type} '{title}' ({year}) metadata found in DB. Reusing..."
                )
                cached_metadata = result.data[0]
                cached_metadata["media_type"] = media_type
                cached_metadata["banner_url"] = cached_metadata.pop("backdrop_url", "")
                cached_metadata["vote_average"] = (
                    cached_metadata.get("popularity_score", 0.0) or 0.0
                ) / 10
                return cached_metadata
            elif year is not None:
                tqdm.write(
                    f"ℹ️ No matching metadata for '{title}' ({year}) in DB. Fetching fresh..."
                )
        except Exception as e:
            tqdm.write(f"⚠️ DB check failed: {e}")

        # 2. Try TMDB first, then fall back to OMDb.
        tqdm.write(
            f"\n🎨 Fetching metadata for: {title} ({media_type}) {'(' + str(year) + ')' if year else ''}..."
        )
        metadata = None
        async with TMDBMetadataFetcher() as tmdb:
            if media_type == "Movie":
                metadata = await tmdb.search_movie(title, year)
            else:
                metadata = await tmdb.search_tv(title, season, year)

            if metadata:
                tqdm.write(
                    f"✅ TMDB Matched: {title} ({metadata.get('release_year')}) | Type: {metadata.get('media_type')}"
                )
            else:
                tqdm.write("⚠️ TMDB not found. Trying OMDb...")
                omdb = OMDbMetadataFetcher()
                omdb_result = await omdb.search(title, year, media_type)
                if omdb_result and omdb_result.get("imdbID"):
                    metadata = await omdb.get_details(omdb_result["imdbID"])
                    if metadata:
                        tqdm.write(
                            f"✅ OMDb Matched: {metadata.get('title')} ({metadata.get('release_year')})"
                        )

            if not metadata:
                tqdm.write(f"⚠️ No metadata found in TMDB or OMDb for: {title}")
                return None

            tqdm.write(
                f"📅 Final Match: {title} ({metadata.get('release_year')}) | Type: {metadata.get('media_type')} | Status: {metadata.get('tmdb_status', 'N/A')}"
            )

            tmdb_id = metadata.get("tmdb_id")
            image_urls = {"poster_url": "", "banner_url": "", "thumbnail_url": ""}

            # 3. Upload TMDB or direct OMDb images.
            poster_path = metadata.get("poster_path") or metadata.get("poster_url")
            if poster_path:
                poster_fallback_url = (
                    poster_path
                    if poster_path.startswith("http")
                    else f"{tmdb.image_base_url}{poster_path}"
                )
                image_urls["poster_url"] = poster_fallback_url
                if poster_path.startswith("http"):
                    img_bytes = await _fetch_image_from_url(poster_path)
                else:
                    img_bytes = await tmdb.fetch_image_bytes(poster_path)

                if img_bytes:
                    url = await upload_image_to_supabase(
                        supabase_storage_client,
                        img_bytes,
                        "poster",
                        tmdb_id or 0,
                        season or 1,
                    )
                    if url:
                        image_urls["poster_url"] = url
                await asyncio.sleep(0.5)

            if metadata.get("backdrop_path"):
                img_bytes = await tmdb.fetch_image_bytes(metadata["backdrop_path"])
                if img_bytes:
                    url = await upload_image_to_supabase(
                        supabase_storage_client,
                        img_bytes,
                        "banner",
                        tmdb_id or 0,
                        season or 1,
                    )
                    if url:
                        image_urls["banner_url"] = url

                    url = await upload_image_to_supabase(
                        supabase_storage_client,
                        img_bytes,
                        "thumbnail",
                        tmdb_id or 0,
                        season or 1,
                    )
                    if url:
                        image_urls["thumbnail_url"] = url
                await asyncio.sleep(0.5)

        # 4. Update DB when an image was found or uploaded.
        if any(image_urls.values()) or metadata.get("poster_url"):
            full_meta = {**metadata, **image_urls}
            try:
                db_media_type = "tv_series" if media_type == "TV Series" else "movie"
                query = (
                    supabase_client.table("media")
                    .select("id")
                    .eq("title", title)
                    .eq("media_type", db_media_type)
                )
                if year is not None:
                    query = query.eq("release_year", year)

                res = query.execute()
                for row in res.data:
                    supabase_client.table("media").update(
                        {
                            "tmdb_id": full_meta.get("tmdb_id"),
                            "release_year": full_meta.get("release_year"),
                            "total_episodes": full_meta.get("total_episodes"),
                            "original_language": full_meta.get("original_language"),
                            "overview": full_meta.get("overview"),
                            "poster_url": full_meta.get("poster_url"),
                            "backdrop_url": full_meta.get("banner_url"),
                            "popularity_score": (full_meta.get("vote_average") or 0.0)
                            * 10,
                        }
                    ).eq("id", row["id"]).execute()

                count = len(res.data)
                if count == 0:
                    tqdm.write(
                        "ℹ️ Metadata fetched. Will be saved when current file saves to DB."
                    )
                else:
                    tqdm.write(f"✅ Metadata updated in DB for {count} existing files!")
            except Exception as e:
                tqdm.write(f"❌ Error saving metadata to DB: {e}")

            return full_meta

        return metadata


async def _fetch_image_from_url(url: str) -> Optional[bytes]:
    """Fetch image from a direct URL, such as an OMDb poster URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
        return None
    except Exception as e:
        tqdm.write(f"❌ Image fetch error: {e}")
        return None
