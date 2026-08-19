from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class VideoMetadata:
    file_path: str
    file_name: str
    file_size: int
    title: str
    media_type: str = "TV Series"
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_number: Optional[str] = None
    languages: List[str] = field(default_factory=lambda: ['Original'])
    language_tag: str = "original"
    quality: str = "unknown"
    upload_date: str = ""
    doodstream_url: str = ""
    mixdrop_url: str = ""
    streamtape_url: str = ""
    status: str = "pending"
    release_year: int = 0
    total_seasons: int = 0
    total_episodes: int = 0
    tmdb_status: str = ""
    original_language: str = ""
    networks: List[str] = field(default_factory=list)
    creators: List[str] = field(default_factory=list)
    tmdb_id: int = 0
    overview: str = ""
    genres: List[Dict[str, str]] = field(default_factory=list)
    vote_average: float = 0.0
    poster_url: str = ""
    banner_url: str = ""
    thumbnail_url: str = ""