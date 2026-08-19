# utils/db_manager.py

import sys
from pathlib import Path
from typing import Optional, Dict, List
from supabase import Client
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent))
import config


class DatabaseManager:
    """Handles all normalized database operations for the uploader."""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def _generate_slug(self, title: str, year: int = None) -> str:
        """Generates a URL-friendly slug."""
        import re

        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-_")
        if year:
            slug += f"-{year}"
        return slug

    def ensure_media_exists(
        self,
        title: str,
        media_type: str,
        language_tag: str,
        year: int = None,
        metadata: Dict = None,
    ) -> Optional[str]:
        """Creates or fetches the Media row. Handles Original vs Dubbed logic."""

        # Determine language code and version type
        lang_code = "en"
        version_type = "original"
        if language_tag.lower() != "original":
            lang_code = language_tag.lower()  # e.g., 'hi', 'bn'
            version_type = "dubbed"

        # Map media_type to schema enum
        db_media_type = "tv_series" if media_type == "TV Series" else "movie"
        slug = self._generate_slug(title, year)

        # 1. Check if media already exists
        query = (
            self.supabase.table("media")
            .select("id")
            .eq("title", title)
            .eq("media_type", db_media_type)
        )
        if year:
            query = query.eq("release_year", year)
        query = query.eq("language_code", lang_code).limit(1)

        result = query.execute()
        if result.data:
            return result.data[0]["id"]

        # 2. If Dubbed, find the Original parent_media_id
        parent_id = None
        if version_type == "dubbed":
            parent_query = (
                self.supabase.table("media")
                .select("id")
                .eq("title", title)
                .eq("version_type", "original")
                .limit(1)
            )
            if year:
                parent_query = parent_query.eq("release_year", year)
            parent_res = parent_query.execute()
            if parent_res.data:
                parent_id = parent_res.data[0]["id"]

        # 3. Insert new media
        media_data = {
            "title": title,
            "slug": slug,
            "media_type": db_media_type,
            "language_code": lang_code,
            "version_type": version_type,
            "release_year": year,
            "parent_media_id": parent_id,
        }

        # Add TMDB metadata if available
        if metadata:
            media_data.update(
                {
                    "overview": metadata.get("overview"),
                    "poster_url": metadata.get("poster_url"),
                    "backdrop_url": metadata.get("banner_url"),
                    "tmdb_id": metadata.get("tmdb_id"),
                    "original_language": metadata.get("original_language"),
                    "total_episodes": metadata.get("total_episodes", 0),
                    "popularity_score": (metadata.get("vote_average") or 0.0) * 10,
                }
            )

        insert_res = self.supabase.table("media").insert(media_data).execute()
        if insert_res.data:
            return insert_res.data[0]["id"]

        logger.error(f"Failed to insert media: {title}")
        return None

    def ensure_season_exists(self, media_id: str, season_number: int) -> Optional[str]:
        """Creates or fetches a Season."""
        if not season_number:
            return None  # Movies don't have seasons

        query = (
            self.supabase.table("seasons")
            .select("id")
            .eq("media_id", media_id)
            .eq("season_number", season_number)
            .limit(1)
        )
        result = query.execute()

        if result.data:
            return result.data[0]["id"]

        insert_res = (
            self.supabase.table("seasons")
            .insert(
                {
                    "media_id": media_id,
                    "season_number": season_number,
                    "title": f"Season {season_number}",
                }
            )
            .execute()
        )

        return insert_res.data[0]["id"] if insert_res.data else None

    def ensure_episode_exists(
        self, season_id: str, episode_number: int, title: str
    ) -> Optional[str]:
        """Creates or fetches an Episode."""
        query = (
            self.supabase.table("episodes")
            .select("id")
            .eq("season_id", season_id)
            .eq("episode_number", episode_number)
            .limit(1)
        )
        result = query.execute()

        if result.data:
            return result.data[0]["id"]

        insert_res = (
            self.supabase.table("episodes")
            .insert(
                {
                    "season_id": season_id,
                    "episode_number": episode_number,
                    "title": title or f"Episode {episode_number}",
                }
            )
            .execute()
        )

        return insert_res.data[0]["id"] if insert_res.data else None

    def save_video_sources(self, episode_id: str, media_id: str, sources: List[Dict]):
        """Upserts video sources (DoodStream, MixDrop, etc.)."""
        for source in sources:
            if not source.get("video_url"):
                continue

            data = {
                "server_name": source["server_name"],
                "quality": source["quality"],
                "video_url": source["video_url"],
                "is_default": source.get("is_default", False),
            }

            # Link to episode if it's a series, otherwise link to media (movie)
            if episode_id:
                data["episode_id"] = episode_id
            else:
                data["media_id"] = media_id

            try:
                # Using upsert to avoid duplicate errors
                self.supabase.table("video_sources").upsert(
                    data,
                    on_conflict=(
                        "episode_id,server_name,quality"
                        if episode_id
                        else "media_id,server_name,quality"
                    ),
                ).execute()
            except Exception as e:
                logger.error(f"Error saving video source {source['server_name']}: {e}")

    def save_genres(self, media_id: str, genres: List[Dict]):
        """Links genres to media."""
        if not genres:
            return

        for genre in genres:
            genre_name = genre.get("name") if isinstance(genre, dict) else genre
            if not genre_name:
                continue

            # Ensure genre exists
            genre_res = (
                self.supabase.table("genres")
                .select("id")
                .eq("name", genre_name)
                .limit(1)
                .execute()
            )
            if not genre_res.data:
                slug = genre_name.lower().replace(" ", "-")
                genre_res = (
                    self.supabase.table("genres")
                    .insert({"name": genre_name, "slug": slug})
                    .execute()
                )

            genre_id = genre_res.data[0]["id"]

            # Link media and genre
            try:
                self.supabase.table("media_genres").upsert(
                    {"media_id": media_id, "genre_id": genre_id},
                    on_conflict="media_id,genre_id",
                ).execute()
            except Exception as e:
                logger.error(f"Error linking genre {genre_name}: {e}")


# Global instance helper
def get_db_manager(supabase_client: Client) -> DatabaseManager:
    return DatabaseManager(supabase_client)
