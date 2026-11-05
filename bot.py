import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import aiohttp
import yt_dlp
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import FSInputFile, Message, TelegramObject
from dotenv import load_dotenv
from yt_dlp.utils import YoutubeDLError

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize ffmpeg (uses static_ffmpeg if system binary is unavailable)
if not shutil.which("ffmpeg"):
    try:
        import static_ffmpeg

        static_ffmpeg.add_paths()
    except (ImportError, OSError) as e:
        logger.warning("Не вдалося ініціалізувати static_ffmpeg: %s", e)

# Suppress noisy aiogram.event logs for unhandled messages in group chats
logging.getLogger("aiogram.event").setLevel(logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Токен Telegram не знайдено! Перевірте файл .env")

# Local Telegram Bot API Server (supports uploading files up to 2000 MB)
TELEGRAM_API_SERVER = os.getenv("TELEGRAM_API_SERVER")
if TELEGRAM_API_SERVER:
    logger.info("Використовується локальний Telegram Bot API Server: %s", TELEGRAM_API_SERVER)
    bot = Bot(
        token=BOT_TOKEN,
        session=AiohttpSession(
            api=TelegramAPIServer.from_base(TELEGRAM_API_SERVER),
            timeout=300.0,
        ),
    )
else:
    bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

# Administrator configuration and maintenance mode
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: set[int] = {
    int(uid.strip())
    for uid in ADMIN_IDS_RAW.split(",")
    if uid.strip().lstrip("-").isdigit()
}

SETTINGS_FILE = os.getenv("SETTINGS_FILE", "settings.json")

# Chat administrators cache: chat_id -> (timestamp, set_of_admin_user_ids)
CHAT_ADMIN_CACHE_TTL = 300  # 5 minutes
chat_admin_cache: dict[int, tuple[float, set[int]]] = {}


def load_settings() -> dict[str, Any]:
    """Loads the persisted settings from disk if available."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Не вдалося зчитати %s: %s", SETTINGS_FILE, e)
    return {}


def save_settings(data: dict[str, Any]) -> None:
    """Persists settings to disk."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error("Не вдалося зберегти %s: %s", SETTINGS_FILE, e)


_initial_settings = load_settings()
admin_only_mode: bool = bool(_initial_settings.get("admin_only_mode", False))
admin_only_chats: set[int] = {
    int(cid) for cid in _initial_settings.get("admin_only_chats", [])
}


def save_admin_only_mode(enabled: bool) -> None:
    """Updates and persists global admin-only mode state."""
    global admin_only_mode
    admin_only_mode = enabled
    data = load_settings()
    data["admin_only_mode"] = enabled
    data["admin_only_chats"] = sorted(list(admin_only_chats))
    save_settings(data)


def is_chat_admin_only(chat_id: int) -> bool:
    """Checks if a group chat has admin-only mode enabled (/addon)."""
    return chat_id in admin_only_chats


def set_chat_admin_only(chat_id: int, enabled: bool) -> None:
    """Enables (/addon) or disables (/addoff) admin-only mode for a specific chat."""
    if enabled:
        admin_only_chats.add(chat_id)
    else:
        admin_only_chats.discard(chat_id)
    data = load_settings()
    data["admin_only_mode"] = admin_only_mode
    data["admin_only_chats"] = sorted(list(admin_only_chats))
    save_settings(data)


def is_admin(user_id: int | None) -> bool:
    """Returns True if the user ID is in the configured global ADMIN_IDS."""
    return bool(user_id and user_id in ADMIN_IDS)


async def get_chat_admin_ids(chat_id: int, force_refresh: bool = False) -> set[int]:
    """Retrieves and caches the set of administrator user IDs for a given chat."""
    now = time.time()
    if not force_refresh and chat_id in chat_admin_cache:
        cached_ts, cached_ids = chat_admin_cache[chat_id]
        if now - cached_ts < CHAT_ADMIN_CACHE_TTL:
            return cached_ids

    try:
        admins = await bot.get_chat_administrators(chat_id=chat_id)
        admin_ids = {m.user.id for m in admins if m.user}
        chat_admin_cache[chat_id] = (now, admin_ids)
        return admin_ids
    except TelegramAPIError as e:
        logger.warning("Не вдалося отримати адміністраторів чату %s: %s", chat_id, e)
        if chat_id in chat_admin_cache:
            return chat_admin_cache[chat_id][1]
        return set()
    except Exception as e:
        logger.error(
            "Несподівана помилка при отриманні адміністраторів чату %s: %s",
            chat_id,
            e,
        )
        return set()


async def is_user_chat_admin(
    chat_id: int,
    user_id: int | None,
    sender_chat_id: int | None = None,
    force_refresh: bool = False,
) -> bool:
    """
    Checks if a user is an administrator in the specified chat.
    Considers:
    1. Anonymous chat administrators (sender_chat == chat_id)
    2. Global bot administrators (from ADMIN_IDS)
    3. Chat administrators fetched from Telegram API (cached)
    """
    if sender_chat_id and sender_chat_id == chat_id:
        return True
    if user_id and is_admin(user_id):
        return True
    if not user_id:
        return False
    admin_ids = await get_chat_admin_ids(chat_id, force_refresh=force_refresh)
    return user_id in admin_ids



# Regular expressions for media links
TIKTOK_REGEX = re.compile(r"https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com/[^\s]+")
INSTA_REGEX = re.compile(
    r"https?://(?:www\.|m\.)?instagram\.com/(?:reels?|p|tv|share/reel|share)/([A-Za-z0-9_-]+)[^\s]*"
)
TWITTER_REGEX = re.compile(
    r"https?://(?:(?:www|mobile)\.)?(?:twitter\.com|x\.com|fxtwitter\.com|vxtwitter\.com|fixupx\.com)/[^\s/]+/status(?:es)?/(\d+)[^\s]*"
)
YOUTUBE_REGEX = re.compile(
    r"https?://(?:www\.|m\.)?(?:youtube\.com/(?:shorts/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})[^\s]*"
)
FACEBOOK_REGEX = re.compile(
    r"https?://(?:(?:www|m|web)\.)?(?:facebook\.com/(?:reel/|reels/|share/(?:[rv]/)?|watch/?\?(?:[^#\s]*&)?v=|[^\s/]+/videos/)|fb\.watch/)[^\s]+"
)

MEDIA_PATTERNS = [
    ("tiktok", TIKTOK_REGEX),
    ("instagram", INSTA_REGEX),
    ("twitter", TWITTER_REGEX),
    ("youtube", YOUTUBE_REGEX),
    ("facebook", FACEBOOK_REGEX),
]


def extract_media_links(text: str) -> list[tuple[str, str, str | None]]:
    """
    Extracts all supported media links from text in the order they appear.
    Strips trailing punctuation and avoids duplicate or overlapping URLs.
    Returns a list of tuples: (platform, clean_url, extra_id)
    """
    matches = []
    for platform, pattern in MEDIA_PATTERNS:
        for m in pattern.finditer(text):
            raw_url = m.group(0)
            clean_url = raw_url.rstrip(".,;:!?)]>'\"")
            extra = m.group(1) if m.re.groups >= 1 else None
            matches.append((m.start(), m.end(), platform, clean_url, extra))

    matches.sort(key=lambda x: x[0])

    filtered = []
    seen_urls = set()
    last_end = -1
    for start, end, platform, url, extra in matches:
        if start < last_end:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        filtered.append((platform, url, extra))
        last_end = end

    return filtered


# --- Admin-Only Mode Middleware ---
class AdminOnlyMiddleware(BaseMiddleware):
    """
    Guards incoming messages when admin-only mode is active.
    - Administrators always pass through unconditionally.
    - In private chats, non-admins receive a maintenance notice if sending commands or media links.
    - In group chats, non-admin messages are silently dropped to avoid spam.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        global admin_only_mode
        if not admin_only_mode:
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if is_admin(user_id):
            return await handler(event, data)

        # User is not an admin and admin_only_mode is active
        if event.chat.type == "private":
            text = event.text or event.caption or ""
            is_cmd = text.startswith("/")
            has_media = bool(extract_media_links(text)) if text else False
            if is_cmd or has_media:
                try:
                    await event.reply(
                        "🛠️ <b>Maintenance Mode / Технічні роботи</b>\n\n"
                        "The bot is temporarily available only to administrators. Please try again later!\n"
                        "<i>Бот тимчасово доступний лише для адміністраторів. Будь ласка, спробуйте пізніше!</i>",
                        parse_mode="HTML",
                        allow_sending_without_reply=True,
                    )
                except TelegramAPIError:
                    pass

        # In group chats or non-actionable private messages: drop silently
        return None


dp.message.outer_middleware(AdminOnlyMiddleware())


# Global shared HTTP session for connection pooling
http_session: aiohttp.ClientSession | None = None

# Concurrency limit for heavy yt-dlp downloads to prevent CPU overload
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")

# Video limits: 15 minutes duration, 400 MB direct file size, 650 MB max with auto-compression
MAX_VIDEO_DURATION_SECONDS = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", "900"))
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_MB", "400")) * 1024 * 1024
MAX_COMPRESS_SIZE_BYTES = int(os.getenv("MAX_COMPRESS_SIZE_MB", "650")) * 1024 * 1024


# --- Media Processing Exceptions ---
class MediaError(Exception):
    """Base exception for media processing errors with a user-facing explanation."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class VideoTooLongError(MediaError):
    """Raised when a video exceeds the maximum duration limit (15 minutes)."""

    pass


class VideoTooLargeError(MediaError):
    """Raised when a video exceeds the maximum file size limit (200 MB)."""

    pass


class RestrictedContentError(MediaError):
    """Raised when a video is age-restricted, private, or requires authentication."""

    pass


# --- Cached Video Data ---
@dataclass
class CachedVideo:
    file_id: str
    width: int | None = None
    height: int | None = None
    duration: int | None = None


# --- LRU Cache for Storing Telegram file_id and Video Metadata ---
class LRUFileCache:
    """URL-to-metadata LRU cache for instant re-sending of previously processed videos."""

    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, CachedVideo] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> CachedVideo | None:
        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    async def set(self, key: str, value: CachedVideo) -> None:
        async with self._lock:
            self._cache[key] = value
            self._cache.move_to_end(key)
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)


file_cache = LRUFileCache(maxsize=1000)


# --- Keep-Alive Background ChatAction Sender ---
@asynccontextmanager
async def chat_action_sender(
    bot_instance: Bot,
    chat_id: int,
    action: ChatAction = ChatAction.UPLOAD_VIDEO,
    interval: float = 4.5,
):
    """Periodically refreshes the Telegram upload video status to keep it active beyond 5s."""
    stop_event = asyncio.Event()

    async def _loop():
        while not stop_event.is_set():
            try:
                await bot_instance.send_chat_action(
                    chat_id=chat_id, action=action
                )
            except TelegramAPIError as e:
                logger.debug("Не вдалося надіслати chat action: %s", e)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    task = asyncio.create_task(_loop())
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# --- Media Helper Functions (ffprobe / ffmpeg) ---
def probe_video_metadata(file_path: str) -> dict:
    """
    Extracts precise width, height, duration, orientation (rotation), and audio presence using ffprobe.
    Prevents distorted 'square' videos by properly accounting for rotation tags and SAR/DAR.
    """
    meta: dict = {
        "width": None,
        "height": None,
        "duration": None,
        "has_audio": False,
    }
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=index,codec_type,codec_name,width,height,duration,sample_aspect_ratio:stream_side_data:stream_tags=rotate",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            file_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            for s in streams:
                if s.get("codec_type") == "audio":
                    meta["has_audio"] = True
                elif s.get("codec_type") == "video" and meta["width"] is None:
                    raw_w = s.get("width")
                    raw_h = s.get("height")
                    if raw_w and raw_h:
                        w = int(raw_w)
                        h = int(raw_h)

                        # Account for Sample Aspect Ratio (non-square pixels)
                        sar_str = s.get("sample_aspect_ratio")
                        if sar_str and ":" in sar_str:
                            parts = sar_str.split(":")
                            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                                sar_num, sar_den = float(parts[0]), float(parts[1])
                                if sar_den > 0 and sar_num > 0:
                                    sar = sar_num / sar_den
                                    if abs(sar - 1.0) > 0.01:
                                        w = int(round(w * sar))

                        # Check video rotation angle (mobile vertical recording)
                        rotation = 0
                        tags = s.get("tags") or {}
                        if "rotate" in tags:
                            try:
                                rotation = int(tags["rotate"])
                            except (ValueError, TypeError):
                                pass
                        for side in s.get("side_data_list") or []:
                            if "rotation" in side:
                                try:
                                    rotation = int(side["rotation"])
                                except (ValueError, TypeError):
                                    pass

                        if rotation in (90, 270, -90, -270):
                            w, h = h, w

                        # Ensure even dimensions for Telegram compatibility
                        if w % 2 != 0:
                            w += 1
                        if h % 2 != 0:
                            h += 1

                        meta["width"] = w
                        meta["height"] = h

            fmt = data.get("format") or {}
            dur = fmt.get("duration")
            if dur:
                try:
                    meta["duration"] = int(float(dur))
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        logger.warning("Помилка отримання метаданих через ffprobe (%s): %s", file_path, e)

    return meta


def generate_thumbnail(
    video_path: str,
    thumb_path: str,
    width: int | None = None,
    height: int | None = None,
) -> bool:
    """Generates an optimized JPEG thumbnail preserving correct aspect ratios."""
    try:
        # Scale thumbnail so the longer side does not exceed 320 pixels
        vf = "scale='if(gt(a,1),320,-2)':'if(gt(a,1),-2,320)'"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            "00:00:01",
            "-i",
            video_path,
            "-vframes",
            "1",
            "-vf",
            vf,
            "-q:v",
            "3",
            thumb_path,
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=10)
        if (
            res.returncode == 0
            and os.path.exists(thumb_path)
            and os.path.getsize(thumb_path) > 0
        ):
            return True

        # If video is very short (<1 sec), capture frame at 00:00:00
        cmd[2] = "00:00:00"
        res = subprocess.run(cmd, capture_output=True, timeout=10)
        return (
            res.returncode == 0
            and os.path.exists(thumb_path)
            and os.path.getsize(thumb_path) > 0
        )
    except Exception as e:
        logger.warning("Не вдалося згенерувати thumbnail (%s): %s", video_path, e)
        return False


def compress_video_to_target_size(
    input_path: str,
    output_path: str,
    duration: int,
    target_size_mb: int = 380,
) -> bool:
    """
    Compresses video to fit strictly under target_size_mb using ffmpeg single-pass with target bitrate.
    """
    try:
        target_total_bits = target_size_mb * 1024 * 1024 * 8
        total_bitrate = int(target_total_bits / max(duration, 1))

        # Audio bitrate: 96 kbps
        audio_bitrate_kb = 96
        audio_bitrate = audio_bitrate_kb * 1000

        # Video bitrate: total - audio (floor at 250 kbps)
        video_bitrate = max(total_bitrate - audio_bitrate, 250_000)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-c:v",
            "libx264",
            "-b:v",
            str(video_bitrate),
            "-maxrate",
            str(int(video_bitrate * 1.2)),
            "-bufsize",
            str(int(video_bitrate * 2)),
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-b:a",
            f"{audio_bitrate_kb}k",
            "-movflags",
            "+faststart",
            output_path,
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=240)
        return (
            res.returncode == 0
            and os.path.exists(output_path)
            and os.path.getsize(output_path) > 0
            and os.path.getsize(output_path) <= target_size_mb * 1024 * 1024 * 1.05
        )
    except Exception as e:
        logger.warning("Помилка стиснення відео через ffmpeg (%s): %s", input_path, e)
        return False


async def reply_with_video_file(
    message: Message,
    original_url: str,
    file_path: str,
) -> bool:
    """
    Sends video to chat with exact dimensions (width/height), duration,
    custom thumbnail, and supports_streaming=True flag.
    Prevents letterboxing, black borders, and square distortion in Telegram clients.
    """
    if not os.path.exists(file_path):
        return False

    # Extract video metadata first
    meta = await asyncio.to_thread(probe_video_metadata, file_path)
    width = meta.get("width")
    height = meta.get("height")
    duration = meta.get("duration")

    if not width or not height:
        logger.warning("Файл не містить відеопотоку (%s): %s", original_url, file_path)
        return False

    if duration and duration > MAX_VIDEO_DURATION_SECONDS:
        mins = int(duration // 60)
        secs = int(duration % 60)
        limit_mins = MAX_VIDEO_DURATION_SECONDS // 60
        logger.warning(
            "Відео перевищує ліміт тривалості (%d хв): %d хв %d сек",
            limit_mins,
            mins,
            secs,
        )
        try:
            await message.reply(
                f"⚠️ Відео занадто довге ({mins} хв {secs} с). "
                f"Максимальна дозволена тривалість — {limit_mins} хвилин.",
                allow_sending_without_reply=True,
            )
        except TelegramAPIError:
            pass
        return False

    file_size = os.path.getsize(file_path)
    compressed_path: str | None = None

    # If file exceeds 400 MB, try fast compression if under 650 MB and duration is known
    if file_size > MAX_FILE_SIZE_BYTES:
        mb = file_size / (1024 * 1024)
        limit_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        if (
            file_size <= MAX_COMPRESS_SIZE_BYTES
            and duration
            and duration <= MAX_VIDEO_DURATION_SECONDS
        ):
            logger.info(
                "Відео (%.1f МБ) перевищує ліміт %d МБ. Запуск оптимізаційного стиснення...",
                mb,
                limit_mb,
            )
            compressed_path = f"{file_path}_compressed.mp4"
            compressed = await asyncio.to_thread(
                compress_video_to_target_size,
                file_path,
                compressed_path,
                duration,
                380,
            )
            if compressed and os.path.exists(compressed_path):
                file_path = compressed_path
                file_size = os.path.getsize(file_path)
                logger.info(
                    "Відео успішно оптимізовано: %.1f МБ", file_size / (1024 * 1024)
                )
            else:
                logger.warning("Стиснення не вдалося, перевірка ліміту розміру...")

        if file_size > MAX_FILE_SIZE_BYTES:
            logger.warning("Файл перевищує ліміт (%d MB): %.1f MB", limit_mb, mb)
            try:
                await message.reply(
                    f"⚠️ Розмір відео ({mb:.1f} МБ) перевищує ліміт {limit_mb} МБ. Завантаження скасовано.",
                    allow_sending_without_reply=True,
                )
            except TelegramAPIError:
                pass
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except OSError:
                    pass
            return False

    # Generate thumbnail to guarantee proper aspect ratio in preview
    thumb_path = f"{file_path}_thumb.jpg"
    has_thumb = await asyncio.to_thread(
        generate_thumbnail, file_path, thumb_path, width, height
    )

    try:
        video_input = FSInputFile(file_path)
        thumb_input = FSInputFile(thumb_path) if has_thumb else None

        sent_msg = await message.reply_video(
            video=video_input,
            width=width,
            height=height,
            duration=duration,
            thumbnail=thumb_input,
            supports_streaming=True,
            allow_sending_without_reply=True,
        )

        if sent_msg and sent_msg.video:
            await file_cache.set(
                original_url,
                CachedVideo(
                    file_id=sent_msg.video.file_id,
                    width=sent_msg.video.width or width,
                    height=sent_msg.video.height or height,
                    duration=sent_msg.video.duration or duration,
                ),
            )
            return True
    except TelegramAPIError as e:
        logger.error("Помилка відправки відео в Telegram: %s", e)
        return False
    finally:
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass
        if compressed_path and os.path.exists(compressed_path):
            try:
                os.remove(compressed_path)
            except OSError:
                pass

    return False


async def send_cached_video(message: Message, cached: CachedVideo) -> bool:
    """Helper to send a cached video by file_id with original dimensions."""
    try:
        await message.reply_video(
            video=cached.file_id,
            width=cached.width,
            height=cached.height,
            duration=cached.duration,
            supports_streaming=True,
            allow_sending_without_reply=True,
        )
        return True
    except TelegramAPIError as e:
        logger.debug("Помилка відправки кешованого відео в Telegram: %s", e)
        return False


# --- TikTok Downloader (TikWM API with Slideshow Builder & fallback to yt-dlp) ---
def probe_image_dimensions(image_path: str) -> tuple[int, int]:
    """Returns (width, height) of an image using ffprobe, fallback to (1080, 1920)."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            image_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            parts = res.stdout.strip().split("\n")[0].split("x")
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 1080, 1920


def create_tiktok_slideshow_sync(
    image_paths: list[str],
    audio_path: str | None,
    output_path: str,
) -> bool:
    """
    Combines a list of static images and an optional audio track into an MP4 slideshow
    video with smooth scaling, black letterboxing, 25 fps, and audio fadeout.
    """
    if not image_paths:
        return False

    n = len(image_paths)
    if n == 1:
        slide_dur = 4.0
    elif n <= 6:
        slide_dur = 3.0
    elif n <= 12:
        slide_dur = 2.5
    else:
        slide_dur = 2.0

    total_duration = n * slide_dur

    w, h = probe_image_dimensions(image_paths[0])
    if w > h:
        canvas_w, canvas_h = 1920, 1080
    else:
        canvas_w, canvas_h = 1080, 1920

    inputs = []
    filters = []
    for i, img in enumerate(image_paths):
        inputs.extend(["-loop", "1", "-t", str(slide_dur), "-i", img])
        filters.append(
            f"[{i}:v]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,"
            f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=25[v{i}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(n))
    filters.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vout]")

    cmd = ["ffmpeg", "-y", *inputs]

    has_audio_file = bool(audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0)
    if has_audio_file:
        cmd.extend(["-stream_loop", "-1", "-i", audio_path])
        fade_st = max(total_duration - 0.5, 0.0)
        filters.append(f"[{n}:a]afade=t=out:st={fade_st:.2f}:d=0.5[aout]")
        audio_map = "[aout]"
    else:
        cmd.extend(["-f", "lavfi", "-t", f"{total_duration:.2f}", "-i", "anullsrc=r=44100:cl=stereo"])
        audio_map = f"{n}:a"

    filter_str = ";".join(filters)
    cmd.extend([
        "-filter_complex", filter_str,
        "-map", "[vout]",
        "-map", audio_map,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", f"{total_duration:.2f}",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return (
            res.returncode == 0
            and os.path.exists(output_path)
            and os.path.getsize(output_path) > 0
        )
    except Exception as e:
        logger.error("Помилка створення слайдшоу TikTok через ffmpeg: %s", e)
        return False


async def extract_tiktok_data(url: str) -> dict | None:
    if not http_session:
        return None

    api_endpoint = "https://www.tikwm.com/api/"
    params = {"url": url, "hd": 1}

    try:
        async with http_session.get(
            api_endpoint, params=params, timeout=12
        ) as response:
            if response.status == 200:
                payload = await response.json()
                if payload.get("code") == 0:
                    return payload.get("data")
    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        KeyError,
        ValueError,
        TypeError,
    ) as e:
        logger.error("Помилка парсингу TikTok через TikWM: %s", e)

    return None


async def extract_tiktok_url(url: str) -> str | None:
    data = await extract_tiktok_data(url)
    if data:
        return data.get("play")
    return None


async def process_and_send_tiktok(message: Message, url: str) -> bool:
    # Cache lookup
    cached = await file_cache.get(url)
    if cached and await send_cached_video(message, cached):
        return True

    async with chat_action_sender(bot, message.chat.id):
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "tiktok.mp4")
        success = False

        try:
            # 1. Try TikWM API for watermark-free download
            data = await extract_tiktok_data(url)
            if data and http_session:
                images = data.get("images")
                # Check if this is a photomode / slideshow post
                if images and isinstance(images, list) and len(images) > 0:
                    logger.info("Виявлено фото-слайдшоу TikTok (%d фото): %s", len(images), url)

                    async def fetch_image(img_url: str, idx: int) -> str | None:
                        img_path = os.path.join(temp_dir, f"slide_{idx:03d}.jpg")
                        try:
                            dl_timeout = aiohttp.ClientTimeout(total=45, connect=10, sock_read=30)
                            async with http_session.get(img_url, timeout=dl_timeout) as resp:
                                if resp.status == 200:
                                    with open(img_path, "wb") as f:
                                        async for chunk in resp.content.iter_chunked(64 * 1024):
                                            f.write(chunk)
                                    return img_path
                        except Exception as e:
                            logger.debug("Помилка завантаження фото слайду TikTok #%d: %s", idx, e)
                        return None

                    tasks = [fetch_image(img_url, i) for i, img_url in enumerate(images)]
                    results = await asyncio.gather(*tasks)
                    valid_images = [p for p in results if p and os.path.exists(p) and os.path.getsize(p) > 0]

                    audio_url = data.get("music") or data.get("play")
                    audio_path = None
                    if audio_url:
                        candidate_audio = os.path.join(temp_dir, "audio.mp4")
                        try:
                            dl_timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
                            async with http_session.get(audio_url, timeout=dl_timeout) as resp:
                                if resp.status == 200:
                                    with open(candidate_audio, "wb") as f:
                                        async for chunk in resp.content.iter_chunked(64 * 1024):
                                            f.write(chunk)
                                    if os.path.exists(candidate_audio) and os.path.getsize(candidate_audio) > 0:
                                        audio_path = candidate_audio
                        except Exception as e:
                            logger.debug("Помилка завантаження аудіо до слайдшоу TikTok: %s", e)

                    if valid_images:
                        slideshow_path = os.path.join(temp_dir, "tiktok_slideshow.mp4")
                        async with download_semaphore:
                            encoded = await asyncio.to_thread(
                                create_tiktok_slideshow_sync,
                                valid_images,
                                audio_path,
                                slideshow_path,
                            )
                        if encoded and os.path.exists(slideshow_path):
                            success = await reply_with_video_file(
                                message, url, slideshow_path
                            )

                # Regular video post
                elif data.get("play"):
                    direct_url = data.get("hdplay") or data.get("play")
                    try:
                        dl_timeout = aiohttp.ClientTimeout(total=180, connect=15, sock_read=60)
                        async with http_session.get(direct_url, timeout=dl_timeout) as resp:
                            if resp.status == 200:
                                with open(file_path, "wb") as f:
                                    async for chunk in resp.content.iter_chunked(128 * 1024):
                                        f.write(chunk)
                                success = await reply_with_video_file(
                                    message, url, file_path
                                )
                    except Exception as e:
                        logger.debug("Помилка скачування прямого відео TikTok: %s", e)

            # 2. If TikWM fails, fall back to yt-dlp
            if not success:
                async with download_semaphore:
                    ytdlp_file = await asyncio.to_thread(
                        download_ytdlp_sync, url, None, "TikTok"
                    )
                if ytdlp_file:
                    try:
                        success = await reply_with_video_file(message, url, ytdlp_file)
                    finally:
                        try:
                            if os.path.exists(ytdlp_file):
                                os.remove(ytdlp_file)
                            p_dir = os.path.dirname(ytdlp_file)
                            if os.path.exists(p_dir):
                                os.rmdir(p_dir)
                        except OSError:
                            pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return success


# --- Universal yt-dlp Downloader with Guaranteed Audio & Aspect Ratio ---
def check_restricted_content_error(e: Exception, platform_name: str) -> None:
    """Checks if a YoutubeDLError was caused by age restriction, login wall, or private content."""
    err_msg = str(e)
    err_msg_lower = err_msg.lower()

    if (
        "this content isn't available to everyone" in err_msg_lower
        or "can't be seen by certain audiences" in err_msg_lower
        or "sign in to confirm your age" in err_msg_lower
        or "age-restricted" in err_msg_lower
        or "age restricted" in err_msg_lower
        or "inappropriate for some users" in err_msg_lower
        or "restricted video" in err_msg_lower
        or "gating_type_thrift" in err_msg_lower
    ):
        raise RestrictedContentError(
            f"⚠️ Це відео має вікові обмеження (18+) або обмеження доступу в {platform_name}. "
            "Бот не може завантажити його без авторизації."
        )

    if (
        "login required" in err_msg_lower
        or "redirected to the login page" in err_msg_lower
        or "registered users who follow this account" in err_msg_lower
        or "this video is private" in err_msg_lower
        or "private video" in err_msg_lower
    ):
        raise RestrictedContentError(
            f"⚠️ Це відео або акаунт є приватним у {platform_name}. "
            "Бот не може завантажити його без авторизації."
        )


def probe_ytdlp_metadata(
    url: str,
    extractor_args: dict | None = None,
    platform_name: str = "media",
) -> dict | None:
    """Pre-fetches video metadata without downloading to check duration and size."""
    probe_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 15,
    }
    if os.path.exists(COOKIES_FILE):
        probe_opts["cookiefile"] = COOKIES_FILE
    if extractor_args:
        probe_opts["extractor_args"] = extractor_args

    try:
        with yt_dlp.YoutubeDL(probe_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except (VideoTooLongError, VideoTooLargeError, RestrictedContentError):
        raise
    except YoutubeDLError as e:
        check_restricted_content_error(e, platform_name)
        logger.debug("Попереднє отримання метаданих через yt-dlp завершилося з винятком: %s", e)
        return None
    except Exception as e:
        logger.debug("Попереднє отримання метаданих через yt-dlp завершилося з винятком: %s", e)
        return None


def download_ytdlp_sync(
    url: str,
    extractor_args: dict | None = None,
    platform_name: str = "media",
) -> str | None:
    # 1. Quick pre-check: verify duration and approximate size before downloading
    info = probe_ytdlp_metadata(url, extractor_args, platform_name)
    if info:
        dur = info.get("duration")
        if dur and dur > MAX_VIDEO_DURATION_SECONDS:
            mins = int(dur // 60)
            secs = int(dur % 60)
            limit_mins = MAX_VIDEO_DURATION_SECONDS // 60
            logger.info(
                "Відео %s (%s) занадто довге: %d хв %d сек (ліміт: %d хв)",
                platform_name,
                url,
                mins,
                secs,
                limit_mins,
            )
            raise VideoTooLongError(
                f"⚠️ Відео занадто довге ({mins} хв {secs} с). "
                f"Максимальна дозволена тривалість — {limit_mins} хвилин."
            )

        filesize = info.get("filesize") or info.get("filesize_approx")
        if filesize and filesize > MAX_COMPRESS_SIZE_BYTES:
            mb = int(filesize / (1024 * 1024))
            limit_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            logger.info(
                "Відео %s (%s) перевищує максимальний ліміт розміру: %d МБ (ліміт: %d МБ)",
                platform_name,
                url,
                mb,
                limit_mb,
            )
            raise VideoTooLargeError(
                f"⚠️ Очікуваний розмір відео ({mb} МБ) перевищує ліміт {limit_mb} МБ. Завантаження скасовано."
            )

    temp_dir = tempfile.mkdtemp()
    out_tmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")

    def match_filter_limits(info_dict, *, incomplete):
        if info_dict.get("is_live"):
            return "Live streams are not supported"
        dur_val = info_dict.get("duration")
        if dur_val and dur_val > MAX_VIDEO_DURATION_SECONDS:
            return "Video duration exceeds limit"
        return None

    # Format selector:
    # 1. Prioritizes best 1080p under 400 MB, falls back to 720p if 1080p is too heavy.
    # 2. Merges streams into MP4 container via ffmpeg, ensuring audio presence in Shorts/Reels.
    # 3. Adds +faststart (moov atom at file start) for instant Telegram streaming.
    ydl_opts = {
        "format": (
            "bestvideo[height<=1080][filesize_approx<=?400M][vcodec^=avc][ext=mp4]+bestaudio[acodec^=mp4a]/"
            "bestvideo[height<=1080][filesize_approx<=?400M][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=1080][filesize_approx<=?400M]+bestaudio/"
            "bestvideo[height<=720][filesize_approx<=?400M]+bestaudio/"
            "best[height<=1080][filesize_approx<=?400M][ext=mp4]/"
            "best[height<=1080][filesize_approx<=?400M]/"
            "best[filesize_approx<=?400M]/"
            "bestvideo[height<=720]+bestaudio/"
            "best[height<=720]/"
            "best"
        ),
        "merge_output_format": "mp4",
        "match_filter": match_filter_limits,
        "postprocessor_args": {
            "merger": ["-movflags", "+faststart"],
            "videoconverter": ["-movflags", "+faststart"],
        },
        "outtmpl": out_tmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": MAX_COMPRESS_SIZE_BYTES,
        "socket_timeout": 20,
        "concurrent_fragment_downloads": 4,
    }

    if extractor_args:
        ydl_opts["extractor_args"] = extractor_args

    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            download_info = ydl.extract_info(url, download=True)
            if not download_info:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None

            expected_path = ydl.prepare_filename(download_info)
            base, _ = os.path.splitext(expected_path)
            final_path = f"{base}.mp4"

            if os.path.exists(final_path):
                return final_path
            if os.path.exists(expected_path):
                return expected_path

            # Search for any downloaded mp4 file in temp_dir
            for f in os.listdir(temp_dir):
                full_p = os.path.join(temp_dir, f)
                if os.path.isfile(full_p) and full_p.endswith(".mp4"):
                    return full_p

            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
    except (VideoTooLongError, VideoTooLargeError, RestrictedContentError):
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except YoutubeDLError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        err_msg = str(e)
        if "Video duration exceeds limit" in err_msg:
            raise VideoTooLongError(
                f"⚠️ Відео довше {MAX_VIDEO_DURATION_SECONDS // 60} хвилин (ліміт бота). Завантаження скасовано."
            )
        if "File is larger than max-filesize" in err_msg or "max-filesize" in err_msg:
            raise VideoTooLargeError(
                f"⚠️ Розмір відео перевищує {MAX_FILE_SIZE_BYTES // (1024 * 1024)} МБ. Завантаження скасовано."
            )
        check_restricted_content_error(e, platform_name)
        logger.error(
            "Помилка yt-dlp при завантаженні %s (%s): %s",
            platform_name,
            url,
            e,
        )
        return None
    except OSError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.error(
            "Помилка ОС при завантаженні %s (%s): %s",
            platform_name,
            url,
            e,
        )
        return None


# --- Instagram Downloader (via yt-dlp) ---
def download_instagram_sync(url: str) -> str | None:
    return download_ytdlp_sync(
        url,
        extractor_args={"instagram": {"skip": ["comments"]}},
        platform_name="Instagram",
    )


async def process_and_send_instagram(message: Message, url: str) -> bool:
    # Cache lookup
    cached = await file_cache.get(url)
    if cached and await send_cached_video(message, cached):
        return True

    async with chat_action_sender(bot, message.chat.id):
        async with download_semaphore:
            file_path = await asyncio.to_thread(download_instagram_sync, url)

        if not file_path:
            return False

        try:
            return await reply_with_video_file(message, url, file_path)
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                parent_dir = os.path.dirname(file_path)
                if os.path.exists(parent_dir):
                    os.rmdir(parent_dir)
            except OSError as e:
                logger.error("Помилка видалення тимчасового файлу Instagram: %s", e)


# --- Twitter / X Downloader (FxTwitter API with fallback to yt-dlp) ---
def download_twitter_sync(url: str) -> str | None:
    return download_ytdlp_sync(url, platform_name="Twitter/X")


async def extract_twitter_url(tweet_id: str) -> str | None:
    if not http_session:
        return None

    api_endpoint = f"https://api.fxtwitter.com/2/status/{tweet_id}"
    headers = {"User-Agent": "telegram-media-bot/1.0"}

    try:
        async with http_session.get(
            api_endpoint, headers=headers, timeout=12
        ) as response:
            if response.status == 200:
                payload = await response.json()
                status = payload.get("status") or payload.get("tweet") or {}
                media = status.get("media") or {}
                videos = media.get("videos") or []
                if videos and isinstance(videos, list):
                    first_video = videos[0]
                    formats = first_video.get("formats") or []
                    best_format_url = None
                    best_bitrate = -1
                    for f in formats:
                        if f.get("container") == "mp4" and f.get("url"):
                            bitrate = f.get("bitrate") or 0
                            if bitrate > best_bitrate:
                                best_bitrate = bitrate
                                best_format_url = f.get("url")
                    return best_format_url or first_video.get("url")
    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        KeyError,
        ValueError,
        TypeError,
    ) as e:
        logger.error("Помилка парсингу Twitter/X через FxTwitter API: %s", e)

    return None


async def process_and_send_twitter(message: Message, url: str, tweet_id: str) -> bool:
    # Cache lookup
    cached = await file_cache.get(url)
    if cached and await send_cached_video(message, cached):
        return True

    async with chat_action_sender(bot, message.chat.id):
        # 1. Fast path via FxTwitter API
        direct_url = await extract_twitter_url(tweet_id) if tweet_id else None
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "twitter.mp4")
        success = False

        if direct_url and http_session:
            try:
                dl_timeout = aiohttp.ClientTimeout(total=180, connect=15, sock_read=60)
                async with http_session.get(direct_url, timeout=dl_timeout) as resp:
                    if resp.status == 200:
                        with open(file_path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(128 * 1024):
                                f.write(chunk)
                        success = await reply_with_video_file(
                            message, url, file_path
                        )
            except Exception as e:
                logger.debug("Помилка скачування прямого відео Twitter: %s", e)

        # 2. Fallback via yt-dlp
        if not success:
            async with download_semaphore:
                ytdlp_file = await asyncio.to_thread(download_twitter_sync, url)

            if ytdlp_file:
                try:
                    success = await reply_with_video_file(message, url, ytdlp_file)
                finally:
                    try:
                        if os.path.exists(ytdlp_file):
                            os.remove(ytdlp_file)
                        parent_dir = os.path.dirname(ytdlp_file)
                        if os.path.exists(parent_dir):
                            os.rmdir(parent_dir)
                    except OSError as e:
                        logger.error("Помилка видалення тимчасового файлу Twitter: %s", e)

        # Cleanup FxTwitter temporary directory
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except OSError:
            pass

        return success


# --- YouTube Downloader (Shorts / Reels / Clips) ---
def download_youtube_sync(url: str) -> str | None:
    return download_ytdlp_sync(url, platform_name="YouTube")


async def process_and_send_youtube(message: Message, url: str) -> bool:
    # Cache lookup
    cached = await file_cache.get(url)
    if cached and await send_cached_video(message, cached):
        return True

    async with chat_action_sender(bot, message.chat.id):
        async with download_semaphore:
            file_path = await asyncio.to_thread(download_youtube_sync, url)

        if not file_path:
            return False

        try:
            return await reply_with_video_file(message, url, file_path)
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                parent_dir = os.path.dirname(file_path)
                if os.path.exists(parent_dir):
                    os.rmdir(parent_dir)
            except OSError as e:
                logger.error("Помилка видалення тимчасового файлу YouTube: %s", e)


# --- Facebook Downloader (Reels / Watch / Videos via yt-dlp) ---
def download_facebook_sync(url: str) -> str | None:
    return download_ytdlp_sync(
        url,
        platform_name="Facebook",
    )


async def resolve_facebook_url(url: str) -> str:
    """Розкриває короткі посилання (fb.watch, facebook.com/share/...) до канонічного URL."""
    if not http_session:
        return url

    if "fb.watch" in url or "/share/" in url:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
            async with http_session.get(
                url,
                allow_redirects=True,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                if resp.url:
                    final_url = str(resp.url)
                    logger.debug("Facebook redirect: %s -> %s", url, final_url)
                    return final_url
        except Exception as e:
            logger.debug("Не вдалося розкрити редирект Facebook (%s): %s", url, e)

    return url


async def process_and_send_facebook(message: Message, url: str) -> bool:
    # 1. Cache lookup with raw URL
    cached = await file_cache.get(url)
    resolved_url = url
    if not cached:
        resolved_url = await resolve_facebook_url(url)
        if resolved_url != url:
            cached = await file_cache.get(resolved_url)

    if cached and await send_cached_video(message, cached):
        return True

    async with chat_action_sender(bot, message.chat.id):
        async with download_semaphore:
            target_url = resolved_url or url
            file_path = await asyncio.to_thread(download_facebook_sync, target_url)
            # If target_url failed and was different from original url, retry with original url
            if not file_path and target_url != url:
                file_path = await asyncio.to_thread(download_facebook_sync, url)

        if not file_path:
            return False

        try:
            success = await reply_with_video_file(message, url, file_path)
            if success and resolved_url and resolved_url != url:
                cached_obj = await file_cache.get(url)
                if cached_obj:
                    await file_cache.set(resolved_url, cached_obj)
            return success
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                parent_dir = os.path.dirname(file_path)
                if os.path.exists(parent_dir):
                    os.rmdir(parent_dir)
            except OSError as e:
                logger.error("Помилка видалення тимчасового файлу Facebook: %s", e)


# --- Media Dispatcher ---
async def process_media_item(
    message: Message,
    platform: str,
    url: str,
    extra: str | None = None,
) -> bool:
    """Dispatches a single media item to its platform-specific downloader."""
    try:
        if platform == "tiktok":
            return await process_and_send_tiktok(message, url)
        elif platform == "instagram":
            return await process_and_send_instagram(message, url)
        elif platform == "twitter":
            return await process_and_send_twitter(message, url, extra or "")
        elif platform == "youtube":
            return await process_and_send_youtube(message, url)
        elif platform == "facebook":
            return await process_and_send_facebook(message, url)
    except MediaError as e:
        logger.info("Скасовано обробку %s (%s): %s", platform, url, e.user_message)
        try:
            await message.reply(e.user_message, allow_sending_without_reply=True)
        except TelegramAPIError:
            pass
        return False
    except Exception as e:
        logger.error("Несподівана помилка при обробці %s (%s): %s", platform, url, e)
    return False


# --- Command Handlers ---
@dp.message(CommandStart())
async def handle_start(message: Message):
    welcome_text = (
        "⚡ <b>Welcome to Relay! / Вітаємо в Relay!</b>\n\n"
        "I automatically download videos in original quality with sound and correct aspect ratio.\n"
        "<i>Я автоматично завантажую відео у найвищій якості без втрати звуку та пропорцій.</i>\n\n"
        "<b>Supported platforms / Підтримувані платформи:</b>\n"
        "• 🔴 <b>YouTube:</b> Shorts, Reels, Videos\n"
        "• ⚫ <b>TikTok:</b> watermark-free / без водяних знаків\n"
        "• 🟣 <b>Instagram:</b> Reels, Posts, IGTV\n"
        "• 🔵 <b>X (Twitter):</b> video posts\n"
        "• 🔷 <b>Facebook:</b> Reels, Watch & Videos\n\n"
        "💡 <i>Just send any video link here or add me to your group chat!</i>\n"
        "<i>Просто надішліть посилання у цей чат або додайте мене до групи!</i>"
    )
    await message.reply(welcome_text, parse_mode="HTML", allow_sending_without_reply=True)


@dp.message(Command("help", ignore_case=True))
async def handle_help(message: Message):
    help_text = (
        "📖 <b>Relay Help / Довідка</b>\n\n"
        "<b>How to use / Як користуватись:</b>\n"
        "1. Send any supported link (YouTube, TikTok, Instagram, X/Twitter, Facebook).\n"
        "2. Relay will process it and send back the clean video directly into the chat.\n"
        "3. <b>Multi-link support:</b> Send multiple links at once (even in one message) — Relay downloads all of them!\n\n"
        "<b>Group Chats / Для груп:</b>\n"
        "• <b>Privacy:</b> Turn off Group Privacy in @BotFather to let Relay read links automatically.\n"
        "• <b>Clean chat mode:</b> If Relay has admin rights to delete messages, it will automatically delete the message containing the link, leaving only the clean video in the chat!\n"
        "• <b>Admin-only mode (/addon & /addoff):</b> Group admins can restrict Relay to process links exclusively from administrators.\n"
        "  - <code>/addon</code> (або <code>/add on</code>) — allow video downloads ONLY for group admins\n"
        "  - <code>/addoff</code> (або <code>/add off</code>) — open video downloads for ALL chat members\n"
        "  - <code>/addstatus</code> (або <code>/add status</code>) — check current mode in this chat\n"
        "• <b>Private chats:</b> In direct 1-on-1 chats, messages are never deleted.\n\n"
        f"⚠️ <i>Limits: Max duration {MAX_VIDEO_DURATION_SECONDS // 60} mins, "
        f"file size up to {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB (auto-compressed up to {MAX_COMPRESS_SIZE_BYTES // (1024 * 1024)} MB).</i>"
    )
    if is_admin(message.from_user.id if message.from_user else None):
        help_text += (
            "\n\n👑 <b>Global Admin Controls / Глобальне адміністрування:</b>\n"
            "• <code>/adminonly [on|off|status]</code> (або <code>/maintenance</code>) — увімкнути/вимкнути глобальний режим обслуговування."
        )
    await message.reply(help_text, parse_mode="HTML", allow_sending_without_reply=True)


@dp.message(Command("ping", ignore_case=True))
async def handle_ping(message: Message):
    user_id = message.from_user.id if message.from_user else "unknown"
    status_suffix = ""
    if is_admin(message.from_user.id if message.from_user else None):
        mode_str = "🔒 ON (Admin-only)" if admin_only_mode else "🔓 OFF (Public)"
        status_suffix = f"\n👑 <b>Role:</b> Bot Admin | <b>Global Mode:</b> {mode_str}"
    if message.chat.type in ("group", "supergroup"):
        group_mode = (
            "🔒 ON (/addon - only admins)"
            if is_chat_admin_only(message.chat.id)
            else "🔓 OFF (/addoff - all members)"
        )
        status_suffix += f"\n👥 <b>Group Mode:</b> {group_mode}"
    await message.reply(
        f"🏓 <b>Pong!</b> Relay is online and ready.\n"
        f"👤 <b>Your ID:</b> <code>{user_id}</code>{status_suffix}",
        parse_mode="HTML",
        allow_sending_without_reply=True,
    )


@dp.message(Command("addon", "adminon", "add_on", "admin_on", ignore_case=True))
async def handle_addon(message: Message):
    if message.chat.type == "private":
        await message.reply(
            "ℹ️ Команда <code>/addon</code> призначена для групових чатів.\n"
            "<i>Вона вмикає режим, за якого бот завантажує відео лише за посиланнями від адміністраторів групи.</i>",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )
        return

    sender_chat_id = message.sender_chat.id if message.sender_chat else None
    user_id = message.from_user.id if message.from_user else None
    user_name = message.from_user.username if message.from_user else "unknown"

    is_adm = await is_user_chat_admin(
        message.chat.id, user_id, sender_chat_id, force_refresh=True
    )
    logger.info(
        "Команда /addon у чаті %s від користувача %s (@%s), is_adm=%s",
        message.chat.id,
        user_id,
        user_name,
        is_adm,
    )
    if not is_adm:
        await message.reply(
            "⛔ <b>Ця команда доступна лише адміністраторам цієї групи.</b>",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )
        return

    set_chat_admin_only(message.chat.id, True)
    logger.info("Успішно увімкнено /addon для чату %s", message.chat.id)
    await message.reply(
        "🔒 <b>Режим «Тільки для адмінів» УВІМКНЕНО для цієї групи (/addon)!</b>\n\n"
        "Тепер бот завантажуватиме медіа <b>лише за посиланнями від адміністраторів</b> цієї групи.\n"
        "Посилання від інших учасників будуть ігноруватися.\n\n"
        "💡 <i>Вимкнути та відкрити для всіх: <code>/addoff</code></i>",
        parse_mode="HTML",
        allow_sending_without_reply=True,
    )


@dp.message(Command("addoff", "adminoff", "add_off", "admin_off", ignore_case=True))
async def handle_addoff(message: Message):
    if message.chat.type == "private":
        await message.reply(
            "ℹ️ Команда <code>/addoff</code> призначена для групових чатів.",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )
        return

    sender_chat_id = message.sender_chat.id if message.sender_chat else None
    user_id = message.from_user.id if message.from_user else None
    user_name = message.from_user.username if message.from_user else "unknown"

    is_adm = await is_user_chat_admin(
        message.chat.id, user_id, sender_chat_id, force_refresh=True
    )
    logger.info(
        "Команда /addoff у чаті %s від користувача %s (@%s), is_adm=%s",
        message.chat.id,
        user_id,
        user_name,
        is_adm,
    )
    if not is_adm:
        await message.reply(
            "⛔ <b>Ця команда доступна лише адміністраторам цієї групи.</b>",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )
        return

    set_chat_admin_only(message.chat.id, False)
    logger.info("Успішно вимкнено /addon для чату %s", message.chat.id)
    await message.reply(
        "🔓 <b>Режим «Тільки для адмінів» ВИМКНЕНО для цієї групи (/addoff)!</b>\n\n"
        "Тепер бот завантажує медіа за посиланнями <b>від усіх учасників</b> цієї групи.\n\n"
        "💡 <i>Увімкнути знову: <code>/addon</code></i>",
        parse_mode="HTML",
        allow_sending_without_reply=True,
    )


@dp.message(Command("addstatus", "adminstatus", "add_status", "admin_status", ignore_case=True))
async def handle_addstatus(message: Message):
    if message.chat.type == "private":
        await message.reply(
            "ℹ️ Команда <code>/addstatus</code> призначена для групових чатів.",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )
        return

    is_on = is_chat_admin_only(message.chat.id)
    state_text = (
        "🔒 <b>УВІМКНЕНО (/addon)</b> — бот завантажує відео лише за лінками від адмінів"
        if is_on
        else "🔓 <b>ВИМКНЕНО (/addoff)</b> — бот завантажує відео для всіх учасників"
    )
    await message.reply(
        f"ℹ️ <b>Статус режиму в цій групі:</b>\n\n"
        f"• Стан: {state_text}\n\n"
        f"💡 <i>Керування: <code>/addon</code> (лише адміни) або <code>/addoff</code> (для всіх).</i>",
        parse_mode="HTML",
        allow_sending_without_reply=True,
    )


@dp.message(Command("add", ignore_case=True))
async def handle_add_cmd(message: Message, command: CommandObject):
    arg = (command.args or "").strip().lower()
    if arg in ("on", "enable", "1", "true"):
        return await handle_addon(message)
    elif arg in ("off", "disable", "0", "false"):
        return await handle_addoff(message)
    elif arg in ("status", "state"):
        return await handle_addstatus(message)
    else:
        # Toggle current mode
        if is_chat_admin_only(message.chat.id):
            return await handle_addoff(message)
        else:
            return await handle_addon(message)


@dp.message(Command("adminonly", "maintenance", ignore_case=True))
async def handle_admin_only(message: Message, command: CommandObject):
    user_id = message.from_user.id if message.from_user else None

    if not ADMIN_IDS:
        if message.chat.type == "private":
            await message.reply(
                f"⚠️ <b>ADMIN_IDS не налаштовано в .env!</b>\n\n"
                f"Ваш Telegram User ID: <code>{user_id or 'unknown'}</code>\n\n"
                f"Щоб керувати ботом, додайте ваш ID у файл <code>.env</code>:\n"
                f"<code>ADMIN_IDS={user_id or 12345678}</code>\n"
                f"та перезапустіть бота на сервері.",
                parse_mode="HTML",
                allow_sending_without_reply=True,
            )
        return

    if not is_admin(user_id):
        if message.chat.type == "private":
            await message.reply(
                "⛔ <b>Access denied / Доступ заборонено</b>",
                parse_mode="HTML",
                allow_sending_without_reply=True,
            )
        return

    global admin_only_mode
    action = (command.args or "").strip().lower()

    if action in ("on", "enable", "1", "true"):
        admin_only_mode = True
        save_admin_only_mode(True)
        await message.reply(
            "🔒 <b>Admin-Only Mode: ENABLED / УВІМКНЕНО</b>\n\n"
            "The bot is now restricted. Regular users cannot use Relay.\n"
            "Only bot administrators can download media and send commands.\n\n"
            "<i>Бот переведено в режим обмеженого доступу. Роботу для звичайних користувачів призупинено.\n"
            "Бот реагує виключно на команди та посилання від адміністраторів.</i>\n\n"
            "💡 <i>Disable anytime with: <code>/adminonly off</code></i>",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )
    elif action in ("off", "disable", "0", "false"):
        admin_only_mode = False
        save_admin_only_mode(False)
        await message.reply(
            "🔓 <b>Admin-Only Mode: DISABLED / ВИМКНЕНО</b>\n\n"
            "The bot is now available for all users and group chats.\n\n"
            "<i>Режим обмеження вимкнено. Relay знову доступний для всіх користувачів та груп.</i>\n\n"
            "💡 <i>Enable anytime with: <code>/adminonly on</code></i>",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )
    elif action == "status":
        state_text = (
            "🔒 <b>ENABLED (Тільки для адмінів)</b>"
            if admin_only_mode
            else "🔓 <b>DISABLED (Доступний усім)</b>"
        )
        admin_list = (
            ", ".join(f"<code>{uid}</code>" for uid in sorted(ADMIN_IDS))
            if ADMIN_IDS
            else "<i>не налаштовано</i>"
        )
        await message.reply(
            f"ℹ️ <b>Admin-Only Mode Status / Стан режиму:</b>\n\n"
            f"• Режим: {state_text}\n"
            f"• Адміністратори ({len(ADMIN_IDS)}): {admin_list}\n\n"
            f"💡 <i>Використання: <code>/adminonly [on|off|status]</code> або просто <code>/adminonly</code> для перемикання.</i>",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )
    elif not action or action == "toggle":
        admin_only_mode = not admin_only_mode
        save_admin_only_mode(admin_only_mode)
        if admin_only_mode:
            await message.reply(
                "🔒 <b>Admin-Only Mode: ENABLED / УВІМКНЕНО</b>\n\n"
                "The bot is now restricted to administrators only.\n"
                "<i>Бот переведено в режим «Тільки для адмінів».</i>\n\n"
                "💡 <i>Use <code>/adminonly off</code> to reopen for all users.</i>",
                parse_mode="HTML",
                allow_sending_without_reply=True,
            )
        else:
            await message.reply(
                "🔓 <b>Admin-Only Mode: DISABLED / ВИМКНЕНО</b>\n\n"
                "The bot is now available for all users.\n"
                "<i>Бот доступний для всіх користувачів.</i>\n\n"
                "💡 <i>Use <code>/adminonly on</code> to restrict to admins only.</i>",
                parse_mode="HTML",
                allow_sending_without_reply=True,
            )
    else:
        await message.reply(
            "⚠️ <b>Невідомий параметр!</b>\n\n"
            "Використовуйте:\n"
            "• <code>/adminonly on</code> — увімкнути режим тільки для адмінів\n"
            "• <code>/adminonly off</code> — вимкнути (відкрити для всіх)\n"
            "• <code>/adminonly status</code> — перевірити поточний стан\n"
            "• <code>/adminonly</code> — перемкнути стан (toggle)",
            parse_mode="HTML",
            allow_sending_without_reply=True,
        )


# --- Fast Message Handler (Fast-path filtering & Batch Processing) ---
@dp.message()
async def handle_message(message: Message):
    text = message.text or message.caption
    if not text:
        return

    # Fast substring check (instant return for 99% of chat messages without RegEx evaluation)
    is_tiktok = "tiktok.com" in text
    is_insta = "instagram.com" in text
    is_twitter = (
        "twitter.com" in text
        or "x.com/" in text
        or "fixupx.com" in text
        or "vxtwitter.com" in text
        or "fxtwitter.com" in text
    )
    is_youtube = (
        "youtube.com" in text
        or "youtu.be" in text
    )
    is_facebook = (
        "facebook.com" in text
        or "fb.watch" in text
    )

    if not (is_tiktok or is_insta or is_twitter or is_youtube or is_facebook):
        return

    media_items = extract_media_links(text)
    if not media_items:
        return

    # Check per-group admin-only mode (/addon)
    if message.chat.type in ("group", "supergroup"):
        is_restricted = is_chat_admin_only(message.chat.id)
        sender_chat_id = message.sender_chat.id if message.sender_chat else None
        user_id = message.from_user.id if message.from_user else None
        user_name = message.from_user.username if message.from_user else "unknown"

        if is_restricted:
            is_adm = await is_user_chat_admin(message.chat.id, user_id, sender_chat_id)
            if not is_adm:
                logger.info(
                    "⛔ [/addon] Ігноруємо посилання в чаті %s від не-адміна %s (@%s)",
                    message.chat.id,
                    user_id,
                    user_name,
                )
                return
            else:
                logger.info(
                    "✅ [/addon] Обробляємо посилання в чаті %s від адміна %s (@%s)",
                    message.chat.id,
                    user_id,
                    user_name,
                )

    # Cap to avoid overload from a single message (process up to 5 links)
    media_items = media_items[:5]

    # Process all links concurrently
    tasks = [
        process_media_item(message, platform, url, extra)
        for platform, url, extra in media_items
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    any_success = any(res is True for res in results)

    # In group/supergroup/channel chats where the bot is permitted,
    # delete the original message with links so only the clean video remains.
    # In direct 1-on-1 private chats, user messages are never deleted.
    if message.chat.type != "private" and any_success:
        try:
            logger.info(
                "Спроба видалити повідомлення з посиланням у чаті %s (msg_id=%s)",
                message.chat.id,
                message.message_id,
            )
            await message.delete()
            logger.info("Повідомлення %s успішно видалено", message.message_id)
        except TelegramAPIError as e:
            logger.warning(
                "Не вдалося видалити повідомлення %s у чаті %s: %s",
                message.message_id,
                message.chat.id,
                e,
            )
        except Exception as e:
            logger.warning(
                "Несподівана помилка при видаленні повідомлення %s у чаті %s: %s",
                message.message_id,
                message.chat.id,
                e,
            )



async def periodic_temp_cleaner():
    """Periodically purges orphaned temporary files in /tmp older than 30 minutes."""
    while True:
        try:
            await asyncio.sleep(1800)  # Every 30 minutes
            now = time.time()
            temp_dir = tempfile.gettempdir()
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isdir(item_path) and item.startswith("tmp"):
                        if now - os.path.getmtime(item_path) > 1800:
                            shutil.rmtree(item_path, ignore_errors=True)
                    elif os.path.isfile(item_path) and (
                        item.endswith(".mp4")
                        or item.endswith(".jpg")
                        or item.endswith(".part")
                        or item.endswith(".ytdl")
                    ):
                        if now - os.path.getmtime(item_path) > 1800:
                            os.remove(item_path)
                except OSError:
                    pass
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug("Помилка фонового очищення temp: %s", e)


async def main():
    global http_session
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    if ADMIN_IDS:
        logger.info(
            "Завантажено %d адміністратор(ів) у список ADMIN_IDS: %s",
            len(ADMIN_IDS),
            list(ADMIN_IDS),
        )
    else:
        logger.warning(
            "ADMIN_IDS не налаштовано в .env. Адміністративні команди будуть недоступні."
        )

    if admin_only_mode:
        logger.warning(
            "УВАГА: Бот запущено в режимі 'Тільки для адмінів' (admin_only_mode=True)!"
        )

    if admin_only_chats:
        logger.info(
            "Завантажено %d груп з увімкненим режимом /addon: %s",
            len(admin_only_chats),
            list(admin_only_chats),
        )

    # Initialize HTTP connection pool
    http_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        connector=aiohttp.TCPConnector(limit=50, keepalive_timeout=60),
    )

    cleaner_task = asyncio.create_task(periodic_temp_cleaner())

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message"],
            polling_timeout=20,
        )
    finally:
        cleaner_task.cancel()
        if http_session and not http_session.closed:
            await http_session.close()


if __name__ == "__main__":
    asyncio.run(main())
