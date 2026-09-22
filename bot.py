import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiohttp
import yt_dlp
from aiogram import Bot, Dispatcher
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, Message
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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Regular expressions for media links
TIKTOK_REGEX = re.compile(r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+")
INSTA_REGEX = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/[A-Za-z0-9_-]+[^\s]*"
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


# Global shared HTTP session for connection pooling
http_session: aiohttp.ClientSession | None = None

# Concurrency limit for heavy yt-dlp downloads to prevent CPU overload
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")


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

    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        logger.warning("Файл перевищує ліміт Telegram (50 MB): %d байт", file_size)
        try:
            await message.reply("⚠️ Розмір відео перевищує 50 МБ (ліміт Telegram для ботів).")
        except TelegramAPIError:
            pass
        return False

    # Extract video metadata
    meta = await asyncio.to_thread(probe_video_metadata, file_path)
    width = meta.get("width")
    height = meta.get("height")
    duration = meta.get("duration")

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

    return False


# --- TikTok Downloader (TikWM API with fallback to yt-dlp) ---
async def extract_tiktok_url(url: str) -> str | None:
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
                    return payload.get("data", {}).get("play")
    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        KeyError,
        ValueError,
        TypeError,
    ) as e:
        logger.error("Помилка парсингу TikTok через TikWM: %s", e)

    return None


async def process_and_send_tiktok(message: Message, url: str):
    # Cache lookup
    cached = await file_cache.get(url)
    if cached:
        try:
            await message.reply_video(
                video=cached.file_id,
                width=cached.width,
                height=cached.height,
                duration=cached.duration,
                supports_streaming=True,
            )
            return
        except TelegramAPIError:
            pass

    async with chat_action_sender(bot, message.chat.id):
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "tiktok.mp4")
        success = False

        # 1. Try TikWM API for fast watermark-free download
        direct_url = await extract_tiktok_url(url)
        if direct_url and http_session:
            try:
                async with http_session.get(direct_url, timeout=25) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(file_path, "wb") as f:
                            f.write(content)
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
                    await reply_with_video_file(message, url, ytdlp_file)
                finally:
                    try:
                        if os.path.exists(ytdlp_file):
                            os.remove(ytdlp_file)
                        p_dir = os.path.dirname(ytdlp_file)
                        if os.path.exists(p_dir):
                            os.rmdir(p_dir)
                    except OSError:
                        pass

        # Cleanup TikWM temporary directory
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except OSError:
            pass


# --- Universal yt-dlp Downloader with Guaranteed Audio & Aspect Ratio ---
def download_ytdlp_sync(
    url: str,
    extractor_args: dict | None = None,
    platform_name: str = "media",
) -> str | None:
    temp_dir = tempfile.mkdtemp()
    out_tmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")

    # Format selector:
    # 1. Prioritizes best video (up to 1080p, H.264/AVC) + best audio (AAC/M4A).
    # 2. Merges streams into MP4 container via ffmpeg, ensuring audio presence in Shorts/Reels.
    # 3. Adds +faststart (moov atom at file start) for instant Telegram streaming.
    ydl_opts = {
        "format": (
            "bestvideo[height<=1080][vcodec^=avc][ext=mp4]+bestaudio[acodec^=mp4a]/"
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080][ext=mp4]/"
            "best[height<=1080]/"
            "best"
        ),
        "merge_output_format": "mp4",
        "match_filter": yt_dlp.utils.match_filter_func("!is_live"),
        "postprocessor_args": {
            "merger": ["-movflags", "+faststart"],
            "videoconverter": ["-movflags", "+faststart"],
        },
        "outtmpl": out_tmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": 48 * 1024 * 1024,
        "socket_timeout": 15,
        "concurrent_fragment_downloads": 4,
    }

    if extractor_args:
        ydl_opts["extractor_args"] = extractor_args

    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None

            expected_path = ydl.prepare_filename(info)
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
    except (YoutubeDLError, OSError) as e:
        logger.error(
            "Помилка yt-dlp при завантаженні %s (%s): %s",
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


async def process_and_send_instagram(message: Message, url: str):
    # Cache lookup
    cached = await file_cache.get(url)
    if cached:
        try:
            await message.reply_video(
                video=cached.file_id,
                width=cached.width,
                height=cached.height,
                duration=cached.duration,
                supports_streaming=True,
            )
            return
        except TelegramAPIError:
            pass

    async with chat_action_sender(bot, message.chat.id):
        async with download_semaphore:
            file_path = await asyncio.to_thread(download_instagram_sync, url)

        if not file_path:
            return

        try:
            await reply_with_video_file(message, url, file_path)
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


async def process_and_send_twitter(message: Message, url: str, tweet_id: str):
    # Cache lookup
    cached = await file_cache.get(url)
    if cached:
        try:
            await message.reply_video(
                video=cached.file_id,
                width=cached.width,
                height=cached.height,
                duration=cached.duration,
                supports_streaming=True,
            )
            return
        except TelegramAPIError:
            pass

    async with chat_action_sender(bot, message.chat.id):
        # 1. Fast path via FxTwitter API
        direct_url = await extract_twitter_url(tweet_id)
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "twitter.mp4")
        success = False

        if direct_url and http_session:
            try:
                async with http_session.get(direct_url, timeout=25) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(file_path, "wb") as f:
                            f.write(content)
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
                    await reply_with_video_file(message, url, ytdlp_file)
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


# --- YouTube Downloader (Shorts / Reels / Clips) ---
def download_youtube_sync(url: str) -> str | None:
    return download_ytdlp_sync(url, platform_name="YouTube")


async def process_and_send_youtube(message: Message, url: str):
    # Cache lookup
    cached = await file_cache.get(url)
    if cached:
        try:
            await message.reply_video(
                video=cached.file_id,
                width=cached.width,
                height=cached.height,
                duration=cached.duration,
                supports_streaming=True,
            )
            return
        except TelegramAPIError:
            pass

    async with chat_action_sender(bot, message.chat.id):
        async with download_semaphore:
            file_path = await asyncio.to_thread(download_youtube_sync, url)

        if not file_path:
            return

        try:
            await reply_with_video_file(message, url, file_path)
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


async def process_and_send_facebook(message: Message, url: str):
    # 1. Cache lookup with raw URL
    cached = await file_cache.get(url)
    resolved_url = url
    if not cached:
        resolved_url = await resolve_facebook_url(url)
        if resolved_url != url:
            cached = await file_cache.get(resolved_url)

    if cached:
        try:
            await message.reply_video(
                video=cached.file_id,
                width=cached.width,
                height=cached.height,
                duration=cached.duration,
                supports_streaming=True,
            )
            return
        except TelegramAPIError:
            pass

    async with chat_action_sender(bot, message.chat.id):
        async with download_semaphore:
            target_url = resolved_url or url
            file_path = await asyncio.to_thread(download_facebook_sync, target_url)
            # If target_url failed and was different from original url, retry with original url
            if not file_path and target_url != url:
                file_path = await asyncio.to_thread(download_facebook_sync, url)

        if not file_path:
            return

        try:
            success = await reply_with_video_file(message, url, file_path)
            if success and resolved_url and resolved_url != url:
                cached_obj = await file_cache.get(url)
                if cached_obj:
                    await file_cache.set(resolved_url, cached_obj)
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                parent_dir = os.path.dirname(file_path)
                if os.path.exists(parent_dir):
                    os.rmdir(parent_dir)
            except OSError as e:
                logger.error("Помилка видалення тимчасового файлу Facebook: %s", e)


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
    await message.reply(welcome_text, parse_mode="HTML")


@dp.message(Command("help"))
async def handle_help(message: Message):
    help_text = (
        "📖 <b>Relay Help / Довідка</b>\n\n"
        "<b>How to use / Як користуватись:</b>\n"
        "1. Send any supported link (YouTube, TikTok, Instagram, X/Twitter, Facebook).\n"
        "2. Relay will process it and send back the clean video directly into the chat.\n\n"
        "<b>Group Chats / Для груп:</b>\n"
        "To allow Relay to read links automatically without slash commands:\n"
        "1. Open @BotFather → <code>/mybots</code> → select your bot.\n"
        "2. <b>Bot Settings</b> → <b>Group Privacy</b> → <b>Turn off</b>.\n\n"
        "⚠️ <i>Telegram Bot API limits maximum upload size to 50 MB.</i>"
    )
    await message.reply(help_text, parse_mode="HTML")


@dp.message(Command("ping"))
async def handle_ping(message: Message):
    await message.reply("🏓 <b>Pong!</b> Relay is online and ready.", parse_mode="HTML")


# --- Fast Message Handler (Fast-path filtering) ---
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

    if is_tiktok:
        match = TIKTOK_REGEX.search(text)
        if match:
            await process_and_send_tiktok(message, match.group(0))
            return

    if is_insta:
        match = INSTA_REGEX.search(text)
        if match:
            await process_and_send_instagram(message, match.group(0))
            return

    if is_twitter:
        match = TWITTER_REGEX.search(text)
        if match:
            await process_and_send_twitter(message, match.group(0), match.group(1))
            return

    if is_youtube:
        match = YOUTUBE_REGEX.search(text)
        if match:
            await process_and_send_youtube(message, match.group(0))
            return

    if is_facebook:
        match = FACEBOOK_REGEX.search(text)
        if match:
            await process_and_send_facebook(message, match.group(0))
            return



async def main():
    global http_session
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    # Initialize HTTP connection pool
    http_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        connector=aiohttp.TCPConnector(limit=50, keepalive_timeout=60),
    )

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message"],
            polling_timeout=20,
        )
    finally:
        if http_session and not http_session.closed:
            await http_session.close()


if __name__ == "__main__":
    asyncio.run(main())
