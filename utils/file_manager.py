import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Tuple
import sys
from tqdm import tqdm

# Ensure parent directory is in path for config import
sys.path.append(str(Path(__file__).parent.parent))
import config
from core.logger import get_logger

log = get_logger("file_manager")


def prepare_and_package(video_path: str) -> Tuple[str, List[str]]:
    """
    Moves video + subtitles/NFO to a temp staging folder, packages them into a ZIP,
    and returns (zip_path, list_of_staged_files).
    """
    path = Path(video_path)
    stem = path.stem
    parent = path.parent
    
    files_to_stage = [str(path)]
    for ext in config.SUBTITLE_EXTENSIONS | config.NFO_EXTENSIONS:
        rel_file = parent / f"{stem}{ext}"
        if rel_file.exists():
            files_to_stage.append(str(rel_file))
            
    staging_dir = parent / "_staging"
    staging_dir.mkdir(exist_ok=True)
    
    moved_files = []
    for f in files_to_stage:
        f_path = Path(f)
        dest = staging_dir / f_path.name
        shutil.move(str(f_path), str(dest))
        moved_files.append(str(dest))
        
    zip_path = staging_dir / f"{stem}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in moved_files:
            zipf.write(f, Path(f).name)
            
    return str(zip_path), moved_files


def safe_archive_files(file_paths: List[str], status: str):
    """
    Safely moves files to success or failed archive folders.
    If ENABLE_SAFE_ARCHIVE is False, files are simply deleted.
    """
    if not config.ENABLE_SAFE_ARCHIVE:
        for f in file_paths:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                log.warning(f"⚠️ Could not delete {f}: {e}")
        return

    target_folder = config.ARCHIVE_SUCCESS_FOLDER if status == "completed" else config.ARCHIVE_FAILED_FOLDER
    Path(target_folder).mkdir(parents=True, exist_ok=True)
    
    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            continue
            
        target_path = Path(target_folder) / path.name
        
        # Handle filename collisions
        counter = 1
        while target_path.exists():
            target_path = Path(target_folder) / f"{path.stem}_{counter}{path.suffix}"
            counter += 1
            
        try:
            shutil.move(str(path), str(target_path))
            tqdm.write(f"📁 Archived: {path.name} -> {status}")
        except Exception as e:
            tqdm.write(f"⚠️ Failed to archive {path.name}: {e}")
            log.error(f"Failed to archive {path.name}: {e}")


def move_to_unmatched(file_path: str, file_name: str):
    """
    Move a video without metadata to the manual-review folder.
    Handles filename collisions by appending a counter.
    """
    try:
        unmatched_folder = Path(config.UNMATCHED_VIDEOS_FOLDER)
        unmatched_folder.mkdir(parents=True, exist_ok=True)

        dest_path = unmatched_folder / file_name
        counter = 1
        while dest_path.exists():
            stem = Path(file_name).stem
            suffix = Path(file_name).suffix
            dest_path = unmatched_folder / f"{stem}_{counter}{suffix}"
            counter += 1

        shutil.move(file_path, str(dest_path))
        tqdm.write(f"📁 Moved to unmatched: {dest_path.name}")
        tqdm.write("💡 Tip: Rename the file to match TMDB/OMDb naming convention")
    except Exception as e:
        tqdm.write(f"❌ Failed to move to unmatched folder: {e}")
        log.error(f"Failed to move to unmatched folder: {e}")


def cleanup_temp_staging(staging_path: str):
    """
    Safely removes a temporary ZIP file and its parent staging directory 
    (only if the directory is empty).
    """
    try:
        path = Path(staging_path)
        if path.exists():
            path.unlink()
            
        staging_dir = path.parent
        if staging_dir.exists() and not any(staging_dir.iterdir()):
            staging_dir.rmdir()
    except Exception as e:
        tqdm.write(f"⚠️ Temp cleanup failed for {staging_path}: {e}")
        log.warning(f"Temp cleanup failed: {e}")