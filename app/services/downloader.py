import asyncio
import os
import tempfile
from urllib.parse import urlparse
import imageio_ffmpeg
import yt_dlp
from sqlalchemy.orm import Session
from app.models import DownloadAnalytics


class ProgressHookWrapper:
    """Wraps a WebSocket to send live progress updates along with streaming metadata."""

    def __init__(self, websocket, loop):
        self.websocket = websocket
        self.loop = loop

    def __call__(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0

            progress_percent = (downloaded / total * 100) if total > 0 else 0

            payload = {
                "status": "downloading",
                "progress": round(progress_percent, 2),
                "speed": (
                    f"{speed / (1024 * 1024):.2f} MB/s" if speed else "Processing..."
                ),
                "eta": f"{eta}s" if eta else "Unknown",
            }
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json(payload), self.loop
            )

        elif d["status"] == "finished":
            payload = {
                "status": "processing",
                "message": "Finalizing media asset streams...",
            }
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json(payload), self.loop
            )


def run_yt_dlp_download(video_url: str, db: Session, hook_fn) -> dict:
    """Downloads files intelligently to global OS temporary cache with metadata extraction."""
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    download_dir = os.path.join(tempfile.gettempdir(), "nexusgrab_cache")
    os.makedirs(download_dir, exist_ok=True)

    # 🚀 Feature 1: Automatic Audio-Only vs Video+Audio stream detection
    parsed_url = urlparse(video_url).netloc.lower()
    is_audio_platform = any(
        domain in parsed_url
        for domain in ["soundcloud", "spotify", "bandcamp", "audiomack"]
    )

    if is_audio_platform:
        format_selector = "bestaudio/best"
        out_template = os.path.join(download_dir, "%(title)s.mp3")
    else:
        format_selector = "bestvideo+bestaudio/best"
        out_template = os.path.join(download_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": format_selector,
        "outtmpl": out_template,
        "ffmpeg_location": ffmpeg_path,
        "noplaylist": True,
        "progress_hooks": [hook_fn],
        "extractor_args": {
            "youtube": {"player_client": ["android", "web"], "skip": ["dash", "hls"]}
        },
        "http_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    }

    # If it's an audio platform, configure postprocessors to output pristine MP3
    if is_audio_platform:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Pre-extract metadata non-destructively to grab title and thumbnail early
        info = ydl.extract_info(video_url, download=True) or {}
        title = info.get("title") or "Unknown Title"
        thumbnail = (
            info.get("thumbnail")
            or "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400"
        )

        full_disk_path = ydl.prepare_filename(info)
        # Handle extension updates caused by audio post-processing rules
        if is_audio_platform and not full_disk_path.endswith(".mp3"):
            full_disk_path = os.path.splitext(full_disk_path)[0] + ".mp3"

        final_filename = os.path.basename(full_disk_path)

        if os.path.exists(full_disk_path):
            file_size_mb = round(os.path.getsize(full_disk_path) / (1024 * 1024), 2)
        else:
            file_size_mb = None

        domain = urlparse(video_url).netloc.replace("www.", "")
        analytics_entry = DownloadAnalytics(
            title=title,
            url=video_url,
            domain=domain,
            duration=info.get("duration"),
            file_size=file_size_mb,
        )
        db.add(analytics_entry)
        db.commit()

        return {
            "title": title,
            "filename": final_filename,
            "full_path": full_disk_path,
            "thumbnail": thumbnail,
            "is_audio": is_audio_platform,
        }
