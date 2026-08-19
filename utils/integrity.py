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
