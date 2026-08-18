import os
import hashlib
from pathlib import Path

def check_file_integrity(file_path: str, expected_size: int = None) -> bool:
    """Check if file exists, is readable, has size > 0, and matches expected size."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return False
    if path.stat().st_size == 0:
        return False
    if expected_size is not None and path.stat().st_size != expected_size:
        return False
    return True

def calculate_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """Calculate MD5 hash for deep integrity verification (Optional use)."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()