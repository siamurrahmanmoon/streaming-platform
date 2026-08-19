import os
import time
import shutil
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
import config
from tqdm import tqdm


def cleanup_orphaned_files(folder_path: str) -> int:
    """Moves files older than ORPHAN_DAYS_LIMIT to quarantine."""
    if not config.ENABLE_ORPHAN_CLEANUP:
        return 0

    quarantine_dir = Path(config.QUARANTINE_FOLDER)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    current_time = time.time()
    limit_seconds = config.ORPHAN_DAYS_LIMIT * 86400
    moved_count = 0
    video_extensions = set(ext.lower() for ext in config.SUPPORTED_EXTENSIONS)

    tqdm.write(
        f"🧹 Checking for orphaned files older than {config.ORPHAN_DAYS_LIMIT} days..."
    )

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if Path(file).suffix.lower() in video_extensions:
                file_path = Path(root) / file
                # Skip staging or archive folders
                if "_staging" in str(file_path) or "archive" in str(file_path):
                    continue

                file_age = current_time - file_path.stat().st_mtime

                if file_age > limit_seconds:
                    target_path = quarantine_dir / file.name
                    counter = 1
                    while target_path.exists():
                        target_path = (
                            quarantine_dir
                            / f"{file_path.stem}_{counter}{file_path.suffix}"
                        )
                        counter += 1

                    try:
                        shutil.move(str(file_path), str(target_path))
                        tqdm.write(f"🗑️ Quarantined orphaned file: {file}")
                        moved_count += 1
                    except Exception as e:
                        tqdm.write(f"⚠️ Failed to quarantine {file}: {e}")

    return moved_count
