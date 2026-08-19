import json
import os
import re
import time
from typing import Optional
from urllib.parse import quote

import requests
from tqdm import tqdm

import config
from utils.logger import get_logger
from utils.retry import retry_with_backoff

log = get_logger("uploaders")


class UploadProgress(requests.adapters.HTTPAdapter):
    """Simple progress tracking for requests."""

    def __init__(self, total_size, pbar):
        super().__init__()
        self.total_size = total_size
        self.pbar = pbar

    def send(
        self,
        request,
        stream=False,
        timeout=None,
        verify=True,
        cert=None,
        proxies=None,
    ):
        response = super().send(request, stream, timeout, verify, cert, proxies)
        response._content_consumed = False
        return response


class ProgressFile:
    def __init__(self, file_obj, pbar):
        self.file_obj = file_obj
        self.pbar = pbar

    def read(self, size=-1):
        chunk = self.file_obj.read(size)
        if chunk:
            self.pbar.update(len(chunk))
        return chunk

    def __getattr__(self, name):
        return getattr(self.file_obj, name)


@retry_with_backoff()
def upload_to_doodstream_api(
    file_path: str, api_key: str, progress_id: int = 0
) -> Optional[str]:
    if not config.ENABLE_DOODSTREAM or not api_key:
        if not api_key:
            log.error("DOODSTREAM_API_KEY is missing!")
        return None

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    try:
        response = requests.get(
            f"https://doodapi.co/api/upload/server?key={api_key}",
            timeout=config.TIMEOUT_PER_FILE,
        )
        server_data = response.json()
        if server_data.get("status") != 200:
            raise Exception(f"Failed to get upload server: {server_data.get('msg')}")

        upload_url = server_data["result"]
        with open(file_path, "rb") as file_obj, tqdm(
            total=file_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=f"Dood: {file_name[:35]}",
            position=progress_id,
            ncols=100,
        ) as pbar:
            files = {
                "api_key": (None, api_key),
                "file": (
                    file_name,
                    ProgressFile(file_obj, pbar),
                    "application/octet-stream",
                ),
            }
            response = requests.post(
                f"{upload_url}?{api_key}",
                files=files,
                timeout=config.TIMEOUT_PER_FILE,
            )

        if "application/json" not in response.headers.get("Content-Type", ""):
            raise Exception(
                f"Server returned non-JSON (Status {response.status_code}). "
                f"Response: {response.text[:300]}"
            )
        result = response.json()
        if result.get("status") == 200 and result.get("result"):
            file_info = result["result"][0]
            download_url = file_info.get("download_url")
            log.info(f"DoodStream upload succeeded: {download_url}")
            return download_url
        raise Exception(f"API Upload Failed: {result.get('msg', 'Unknown error')}")
    except Exception as error:
        if "429" in str(error) or "Too Many Requests" in str(error):
            time.sleep(5)
        log.error(f"DoodStream API Error: {error}")
        raise


def upload_to_mixdrop(
    file_path: str, email: str, key: str, api_url: str, progress_id: int = 0
) -> Optional[str]:
    if not config.ENABLE_MIXDROP or not email:
        return None

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    try:
        with open(file_path, "rb") as file_obj, tqdm(
            total=file_size,
            unit="B",
            unit_scale=True,
            desc=f"Mix: {file_name[:30]}",
            position=progress_id,
            ncols=100,
        ) as pbar:
            files = {
                "email": (None, email),
                "key": (None, key),
                "file": (
                    file_name,
                    ProgressFile(file_obj, pbar),
                    "application/octet-stream",
                ),
            }
            response = requests.post(
                api_url, files=files, timeout=config.TIMEOUT_PER_FILE
            )
        result = response.json()
        if result.get("success"):
            return result["result"].get("url") or (
                f"https://mixdrop.ag/f/{result['result'].get('fileref', '')}"
            )
        raise Exception(result.get("message", "Unknown API Error"))
    except Exception as error:
        log.error(f"MixDrop Error: {error}")
        raise


def upload_to_streamtape(
    file_path: str, login: str, password: str, progress_id: int = 0
) -> Optional[str]:
    if not config.ENABLE_STREAMTAPE or not login:
        return None

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    try:
        response = requests.get(
            config.STREAMTAPE_API_URL,
            params={"login": login, "key": password},
            timeout=config.TIMEOUT_PER_FILE,
        )
        result = response.json()
        if result.get("status") != 200:
            raise Exception(result.get("msg", "Unknown"))

        with open(file_path, "rb") as file_obj, tqdm(
            total=file_size,
            unit="B",
            unit_scale=True,
            desc=f"ST: {file_name[:30]}",
            position=progress_id,
            ncols=100,
        ) as pbar:
            files = {
                "file1": (
                    file_name,
                    ProgressFile(file_obj, pbar),
                    "application/octet-stream",
                )
            }
            response = requests.post(
                result["result"]["url"],
                files=files,
                timeout=config.TIMEOUT_PER_FILE,
            )

        text = response.text
        try:
            upload_result = json.loads(text)
        except json.JSONDecodeError:
            upload_result = {}
        if upload_result.get("status") not in (None, 200):
            raise Exception(upload_result.get("msg", "Upload failed"))

        upload_data = upload_result.get("result", {})
        if isinstance(upload_data, dict):
            public_url = upload_data.get("link") or upload_data.get("video_link")
            if public_url:
                return public_url
            file_id = (
                upload_data.get("id")
                or upload_data.get("file")
                or upload_data.get("linkid")
            )
            if file_id:
                return f"https://streamtape.com/v/{file_id}/{quote(file_name)}"

        match = re.search(
            r'(https://(?:streamtape\.com|tapecontent\.net)/[^\s"<>]+)', text
        )
        if match:
            return match.group(1)
        raise Exception("Upload completed but no StreamTape file link was returned")
    except Exception as error:
        log.error(f"StreamTape Error: {error}")
        raise
