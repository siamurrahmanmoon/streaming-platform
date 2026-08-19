import re
from pathlib import Path
from typing import Dict, Optional


def parse_video_filename(filename: str) -> Optional[Dict]:
    stem = Path(filename).stem
    stem = stem.replace("5B", "[").replace("5D", "]")
    stem = stem.replace("_", " ").strip()

    # TV Series Regex
    tv_match = re.search(
        r"^(?P<title>.*?)\s*(?:\((?P<year>\d{4})\))?\s*(?:\[(?P<language>[^\]]+)\])?\s*[-]\s*S(?P<season>\d+)E(?P<episode>\d+)\s*[-]\s*(?P<quality>\d{3,4}[Pp])$",
        stem,
        re.IGNORECASE,
    )
    if tv_match:
        return _build_metadata_dict(tv_match, "TV Series")

    # Movie Regex
    movie_match = re.search(
        r"^(?P<title>.*?)\s*(?:\((?P<year>\d{4})\))?\s*(?:\[(?P<language>[^\]]+)\])?\s*[-]?\s*(?P<quality>\d{3,4}[Pp])$",
        stem,
        re.IGNORECASE,
    )
    if movie_match:
        return _build_metadata_dict(movie_match, "Movie")

    return None


def _build_metadata_dict(match, media_type: str) -> Dict:
    title = match.group("title").strip()
    year_str = match.groupdict().get("year")

    if not year_str:
        year_match = re.search(r"\b(19|20)\d{2}\b", title)
        if year_match:
            year_str = year_match.group(0)
            title = re.sub(r"\s*\b" + year_str + r"\b\s*", " ", title).strip()

    lang_str = match.group("language")
    season_str = match.groupdict().get("season")
    episode_str = match.groupdict().get("episode")
    langs = ["Original"]
    if lang_str:
        langs = [
            l.strip().title() for l in re.split(r"\s*[|/&,-]\s*", lang_str) if l.strip()
        ]

    return {
        "media_type": media_type,
        "title": title,
        "year": int(year_str) if year_str else None,
        "season": int(season_str) if season_str else None,
        "episode": int(episode_str) if episode_str else None,
        "episode_number": f"S{season_str}E{episode_str}" if season_str else None,
        "languages": langs,
        "language_tag": lang_str.strip() if lang_str else "original",
        "quality": (match.group("quality") or "unknown").upper(),
    }
