<div align="center">

<img src="./assets/avatar.png" width="160" height="160" alt="Relay Logo" style="border-radius: 50%; box-shadow: 0 10px 30px rgba(0,0,0,0.4);" />

# ⚡ Relay

**High-Performance Asynchronous Media Interceptor & Downloader for Telegram**  
*Високопродуктивний асинхронний бот для перехоплення та завантаження медіа без втрати якості та звуку*

[![CI](https://github.com/vbazavliuk/Relay/actions/workflows/ci.yml/badge.svg)](https://github.com/vbazavliuk/Relay/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-Latest-red?style=flat-square&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Enabled-007808?style=flat-square&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square)](https://github.com/astral-sh/ruff)

---

### 🌐 Select Language / Оберіть мову
[**🇺🇦 Українська**](#-українська) &nbsp;|&nbsp; [**🇬🇧 English**](#-english)

---

</div>

> [!WARNING]
> **DO NOT RUN LOCALLY ON MACOS. THIS STACK IS HOSTED ON REMOTE LINUX:**
> `valentin@192.168.1.110` in `/opt/stacks/relay/`

<br/>

<a id="-українська"></a>
## 🇺🇦 Українська

**Relay** — це сучасний, мінімалістичний та високопродуктивний Telegram-бот для автоматичного перехоплення посилань і миттєвого завантаження відео в чат безпосередньо з **YouTube (Shorts / Reels / Відео)**, **TikTok**, **Instagram**, **X (Twitter)** та **Facebook**.

Проєкт розроблено з акцентом на **збереження оригінальних пропорцій відео** (вирішення проблеми «квадратних» та сплюснутих роликів у Telegram), **100% гарантію наявності звуку**, **пакетну обробку декількох посилань одночасно** та **розумний стелс-режим для групових чатів**.

---

### ✨ Ключові можливості

* 🚀 **Пакетна обробка посилань (Multi-Link Batch Processing)**: якщо користувач надсилає два або більше посилань поспіль (в одному повідомленні або окремими повідомленнями), бот автоматично розпізнає та паралельно завантажує відео за кожним із них без пропусків.
* 🧹 **Стелс-режим / Очищення групових чатів (Clean Chat Mode)**: у групах та каналах, де боту надано права адміністратора на видалення повідомлень (`Delete Messages`), бот автоматично видаляє вихідне повідомлення з посиланнями після успішної доставки відео. У чаті залишається лише чисте відео без спаму посиланнями. Якщо прав немає — бот спокійно надсилає відео, не ламаючи роботу чату.
* 🔒 **Конфіденційність в особистих повідомленнях**: в особистому діалозі 1-на-1 із ботом повідомлення користувача **ніколи не видаляються**.
* 📐 **Ідеальні пропорції (Aspect Ratio Retention)**: завдяки аналізу метаданих через `ffprobe` (облік SAR та тегів орієнтації камери `rotate` 90°/270°) ролики не стискаються до співвідношення 1:1 та не розтягуються.
* 🔊 **100% гарантія звуку**: зведення роздільних потоків відео (H.264/AVC) та аудіо (AAC) у сумісний контейнер MP4 з прапорцем `+faststart` для моментального перегляду в режимі стримінгу.
* ⚡ **Блискавичний LRU-кеш**: раніше завантажені відео миттєво відправляються іншим користувачам за мілісекунди через Telegram `file_id` без повторного завантаження з інтернету.
* 🛡 **Контроль навантаження**: асинхронний семафор (`asyncio.Semaphore`) обмежує кількість важких завантажень, захищаючи процесор і пам'ять VPS від перевантаження.

---

### 🚀 Підтримувані платформи та формати

| Платформа | Підтримувані формати | Метод завантаження & Особливості |
| :--- | :--- | :--- |
| **▶️ YouTube** | `shorts/...`, `youtu.be/...`, `watch?v=...` | До 1080p, об'єднання відео + аудіо в MP4, фільтрація прямих трансляцій `!is_live` |
| **🎵 TikTok** | `tiktok.com`, `vm.tiktok.com`, `vt.tiktok.com` | Пряме завантаження без водяних знаків (TikWM API) + fallback на `yt-dlp` |
| **📸 Instagram** | `instagram.com/reel/...`, `/reels/...`, `/p/...`, `/tv/...`, share-лінки | Reels, відеопости, IGTV; підтримка сесій через `cookies.txt` |
| **🐦 X (Twitter)** | `x.com/...`, `twitter.com/...`, `fixupx.com/...` | Надшвидкий стрім MP4 через FxTwitter API v2 + резерв через `yt-dlp` |
| **🔷 Facebook** | `facebook.com/reel/...`, `fb.watch/...`, share-лінки | Reels, Watch, публічні відео; автоматичний резолв редиректів коротких посилань |

---

### 📐 Технічний опис: збереження пропорцій та гарантія звуку

#### 1. Усунення «квадратних» та сплюснутих відео
* **ffprobe аналіз**: перед надсиланням бот детально інспектує відеофайл, витягуючи фізичні габарити, Sample Aspect Ratio (SAR) та метадані обертання камери (`rotate` 90°/270° зі смартфонів).
* **Специфікація Telegram API**: у виклику `send_video` бот обов'язково вказує обчислені `width`, `height`, `duration` та прапорець `supports_streaming=True`.
* **Пропорційний thumbnail**: генерується індивідуальне JPEG-прев'ю (довша сторона до 320px), що точно відповідає геометрії відео, позбавляючи Telegram-клієнти від чорних смуг (letterboxing/pillarboxing).

#### 2. Гарантія звуку та миттєвий початок відтворення
* **Автоматичний муксинг потоків**: конфігурація `yt-dlp` пріоритезує відеопотік **H.264 (AVC)** та аудіопотік **AAC (MP4A)**, зводячи їх через `ffmpeg` у єдиний файл MP4.
* **Fast-Start оптимізація**: прапорець `-movflags +faststart` переміщує заголовок `moov` atom на початок файлу, дозволяючи користувачеві дивитися відео одразу під час завантаження в Telegram.

---

### 📊 Графічні схеми архітектури

#### Схема 1: Загальний життєвий цикл повідомлення та фільтрація
```mermaid
flowchart TD
    A["📨 Вхідне повідомлення (текст / підпис до медіа)"] --> B{"⚡ Fast-Path перевірка піддоменів"}
    B -- "Немає підтримуваних доменів" --> C["⏹ Швидкий вихід (0% CPU / без RegEx)"]
    B -- "Виявлено медіа-домени" --> D["🔍 extract_media_links(): нормалізація та санітизація"]
    D --> E{"Знайдено валідні URL?"}
    E -- "Ні" --> C
    E -- "Так (1-5 посилань)" --> F["⚡ Паралельний запуск обробки через asyncio.gather()"]
    F --> G["Конвеєр завантаження кожного посилання"]
    G --> H["🏁 Перевірка результатів та очищення чату"]
```

#### Схема 2: Конвеєр обробки та завантаження окремого медіа-посилання
```mermaid
flowchart TD
    A["🔗 Окреме посилання"] --> B{"Перевірка в LRU-кеші"}
    B -- "Хіт у кеші (Hit)" --> C["⚡ Миттєва відправка file_id з точними розмірами"]
    B -- "Промах (Miss)" --> D["Очікування слота в asyncio.Semaphore"]
    D --> E["Запуск фонового chat_action_sender (UPLOAD_VIDEO)"]
    E --> F{"Платформа"}
    F -- "TikTok" --> G["TikWM API (чисте відео) / yt-dlp"]
    F -- "X / Twitter" --> H["FxTwitter API v2 / yt-dlp"]
    F -- "YouTube / Instagram / Facebook" --> I["yt-dlp + селектори потоків"]
    G & H & I --> J{"Успішне завантаження?"}
    J -- "Ні (помилка / >50MB)" --> K["❌ Повернення False"]
    J -- "Так" --> L["ffprobe: отримання width, height, duration, SAR, rotate"]
    L --> M["ffmpeg: генерація пропорційного 320px thumbnail"]
    M --> N["Telegram send_video (supports_streaming=True)"]
    N --> O["Збереження file_id та габаритів у LRU-кеш"]
    O --> P["🧹 Видалення тимчасового файлу та прев'ю"]
    P --> Q["✅ Повернення True"]
```

#### Схема 3: Матриця рішень: Стелс-видалення посилань у групах
```mermaid
flowchart TD
    A["🏁 Завершення обробки всіх посилань у повідомленні"] --> B{"Тип Telegram-чату"}
    B -- "Приватний діалог (1-на-1)" --> C["🔒 Повідомлення користувача залишається недоторканим"]
    B -- "Група / Супергрупа / Канал" --> D{"Чи надіслано хоча б одне відео?"}
    D -- "Ні (всі завантаження зазнали невдачі)" --> E["⚠️ Повідомлення з посиланнями зберігається в чаті"]
    D -- "Так (мінімум одне відео успішно надіслано)" --> F{"Чи має бот права адміністратора 'Delete Messages'?"}
    F -- "Так (права надано)" --> G["🗑 Автоматичне видалення вихідного повідомлення з лінками"]
    G --> H["✨ У груповому чаті залишається лише чисте відео"]
    F -- "Ні (прав недостатньо)" --> I["ℹ️ М'який fallback (відео надіслано, повідомлення залишається)"]
```

#### Схема 4: Послідовність взаємодії компонентів у часі (Sequence Diagram)
```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Користувач
    participant TG as 📱 Telegram Cloud
    participant Bot as ⚡ Relay Bot
    participant Cache as 🧠 LRU Cache
    participant Downloader as 📥 Downloader (API / yt-dlp)
    participant FFmpeg as 🎞 FFmpeg & FFprobe

    User->>TG: Надсилає повідомлення (наприклад, 2 посилання)
    TG->>Bot: Подія Update (Message)
    Bot->>Bot: extract_media_links(): нормалізація 2 посилань
    
    par Паралельна обробка Посилання 1
        Bot->>Cache: Перевірка Посилання 1
        alt Знайдено в кеші
            Cache-->>Bot: file_id + ширина/висота
            Bot->>TG: reply_video(file_id)
        else Немає в кеші
            Bot->>TG: send_chat_action(UPLOAD_VIDEO)
            Bot->>Downloader: Завантаження медіафайлу
            Downloader-->>Bot: Локальний MP4 файл
            Bot->>FFmpeg: probe_video_metadata + thumbnail
            FFmpeg-->>Bot: Точні розміри та прев'ю
            Bot->>TG: reply_video(файл, прев'ю, розміри)
            Bot->>Cache: Збереження в кеш
        end
    and Паралельна обробка Посилання 2
        Bot->>Cache: Перевірка Посилання 2
        Bot->>TG: send_chat_action(UPLOAD_VIDEO)
        Bot->>Downloader: Завантаження медіафайлу
        Downloader-->>Bot: Локальний MP4 файл
        Bot->>FFmpeg: probe_video_metadata + thumbnail
        FFmpeg-->>Bot: Точні розміри та прев'ю
        Bot->>TG: reply_video(файл, прев'ю, розміри)
        Bot->>Cache: Збереження в кеш
    end

    TG-->>User: Відео 1 та Відео 2 доставлені в чат
    opt Якщо це група і надано дозвіл Delete Messages
        Bot->>TG: delete_message(message_id)
        TG-->>User: Вихідне повідомлення з лінками видалено
    end
```

---

### ⚙️ Налаштування оточення (`.env`)

Створіть файл конфігурації `.env` на основі `.env.example`:

```bash
cp .env.example .env
```

| Змінна | Опис | За замовчуванням |
| :--- | :--- | :--- |
| `BOT_TOKEN` | Токен Telegram-бота, отриманий у [@BotFather](https://t.me/BotFather) | *Обов'язково* |
| `MAX_CONCURRENT_DOWNLOADS` | Ліміт одночасних важких завантажень через `yt-dlp` | `3` |
| `COOKIES_FILE` | Шлях до файлу cookies для обходу блокувань Instagram / X | `cookies.txt` |

---

### 📦 Встановлення та запуск

#### Варіант 1: Запуск через Docker Compose (Рекомендовано)

```bash
# Збірка образу та фоновий запуск
docker compose up -d --build

# Перегляд живого журналу логів
docker compose logs -f

# Зупинка контейнера
docker compose down
```

#### Варіант 2: Локальний запуск через Python

```bash
# 1. Створення та активація віртуального середовища
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# venv\Scripts\activate   # Windows

# 2. Встановлення залежностей
pip install -r requirements.txt

# 3. Запуск бота
python bot.py
```

---

### 💡 Налаштування для груп (BotFather)

#### 1. Увімкнення читання посилань без слеш-команд
За замовчуванням Telegram обмежує видимість повідомлень у групах:
1. Відкрийте [@BotFather](https://t.me/BotFather) і надішліть команду `/mybots`.
2. Оберіть вашого бота → **Bot Settings** → **Group Privacy**.
3. Натисніть **Turn off**.
4. Якщо бот уже був у чаті, видаліть його та додайте знову.

#### 2. Увімкнення режиму чистого чату (Стелс-видалення посилань)
Щоб бот автоматично видаляв повідомлення з посиланнями та залишав тільки чисті відео:
1. Додайте бота до вашої групи як адміністратора.
2. Увімкніть дозвіл **Delete Messages** (Видалення повідомлень).
3. Готово! Тепер при надсиланні посилання бот завантажить відео, надішле його в чат і безслідно видалить вихідне повідомлення з лінком.

---

<br/>

<a id="-english"></a>
## 🇬🇧 English

**Relay** is a state-of-the-art, minimalist, and high-performance Telegram bot engineered for automated link interception and seamless video downloads directly into your chat from **YouTube (Shorts / Reels / Videos)**, **TikTok**, **Instagram**, **X (Twitter)**, and **Facebook**.

Specifically engineered to eliminate the infamous **Telegram square/squished video distortion**, guarantee **100% audio retention**, process **multiple consecutive links concurrently**, and provide **smart stealth cleanup in group chats**.

---

### ✨ Key Features

* 🚀 **Multi-Link Batch Processing**: if a user posts two or more links back-to-back (in a single message or consecutive messages), Relay automatically identifies and processes each link concurrently without skipping any media.
* 🧹 **Clean Chat / Stealth Mode in Groups**: in group chats and channels where Relay is granted administrator privileges with the `Delete Messages` permission, the bot automatically removes the original message containing the links once video delivery succeeds. Only the clean video remains in the chat! If permissions are missing, Relay falls back gracefully and sends the video normally.
* 🔒 **Direct Chat Privacy**: in 1-on-1 private conversations with the bot, user messages are **never deleted**.
* 📐 **Zero Aspect Ratio Distortion**: deep video inspection via `ffprobe` (accounting for Sample Aspect Ratio and smartphone `rotate` 90°/270° orientation tags) guarantees videos are never compressed into 1:1 boxes or stretched unnaturally.
* 🔊 **100% Sound Guarantee**: automatic stream muxing of video (H.264/AVC) and audio (AAC) streams into MP4 containers with `-movflags +faststart` for immediate streaming in Telegram clients.
* ⚡ **Ultra-Fast LRU Memory Cache**: previously downloaded videos are re-sent to any user within milliseconds using cached Telegram `file_id` references, saving bandwidth and VPS CPU.
* 🛡 **Concurrency Throttling**: an asynchronous semaphore (`asyncio.Semaphore`) prevents server overloads by strictly capping simultaneous heavy downloads.

---

### 🚀 Supported Platforms & Formats

| Platform | Supported Formats | Engine & Highlights |
| :--- | :--- | :--- |
| **▶️ YouTube** | `shorts/...`, `youtu.be/...`, `watch?v=...` | Up to 1080p, stream muxing (video + audio in MP4), live stream filter `!is_live` |
| **🎵 TikTok** | `tiktok.com`, `vm.tiktok.com`, `vt.tiktok.com` | Watermark-free downloads via TikWM API + resilient fallback to `yt-dlp` |
| **📸 Instagram** | `instagram.com/reel/...`, `/reels/...`, `/p/...`, `/tv/...`, share links | Reels, posts, IGTV; session auth support via `cookies.txt` |
| **🐦 X (Twitter)** | `x.com/...`, `twitter.com/...`, `fixupx.com/...` | Lightning-fast MP4 stream via FxTwitter API v2 + fallback to `yt-dlp` |
| **🔷 Facebook** | `facebook.com/reel/...`, `fb.watch/...`, share links | Reels, Watch, public videos; automatic short URL unshortening & redirect resolution |

---

### 📐 Technical Deep-Dive: Proportions & Audio Guarantees

#### 1. Eliminating Squished & Letterboxed Videos
* **ffprobe diagnostics**: before transmission, the bot parses video streams for exact pixel dimensions, non-square pixel ratios (SAR), and camera rotation metadata (`rotate` 90°/270° from vertical smartphone captures).
* **Telegram API parameters**: Relay explicitly provides calculated `width`, `height`, `duration`, and `supports_streaming=True` in every upload.
* **Proportional custom thumbnail**: an optimized JPEG thumbnail (longest side capped at 320px) is generated on-the-fly to ensure correct aspect ratios across Telegram Desktop, iOS, and Android.

#### 2. Sound Guarantee & Progressive Playback
* **Automated stream muxing**: the download engine prioritizes **H.264 (AVC)** video with **AAC** audio, remuxing them without quality loss into **MP4** containers.
* **Fast-Start progressive streaming**: `-movflags +faststart` relocates the container metadata (`moov` atom) to the beginning of the file, allowing instant playback without waiting for the full 50MB file to finish downloading.

---

### 📊 Graphic Architecture Diagrams

#### Diagram 1: Message Ingestion & Routing Pipeline
```mermaid
flowchart TD
    A["📨 Incoming Message (Text or Caption)"] --> B{"⚡ Fast-Path Substring Check"}
    B -- "No supported domains" --> C["⏹ Fast exit (0% CPU / No RegEx)"]
    B -- "Media domains detected" --> D["🔍 extract_media_links(): URL extraction & cleanup"]
    D --> E{"Valid URLs found?"}
    E -- "None" --> C
    E -- "1 to 5 links found" --> F["⚡ Concurrent execution via asyncio.gather()"]
    F --> G["Platform Media Download Pipeline"]
    G --> H["🏁 Evaluation & Group Chat Cleanup"]
```

#### Diagram 2: Single Media Link Download Pipeline
```mermaid
flowchart TD
    A["🔗 Single Media Link"] --> B{"Check LRU Cache"}
    B -- "Cache Hit" --> C["⚡ Instant reply with file_id & dimensions"]
    B -- "Cache Miss" --> D["Wait for slot in asyncio.Semaphore"]
    D --> E["Start background chat_action_sender (UPLOAD_VIDEO)"]
    E --> F{"Platform Selection"}
    F -- "TikTok" --> G["TikWM API (clean) / yt-dlp"]
    F -- "X / Twitter" --> H["FxTwitter API v2 / yt-dlp"]
    F -- "YouTube / Instagram / Facebook" --> I["yt-dlp + stream selectors"]
    G & H & I --> J{"Download successful?"}
    J -- "No (Error / >50MB)" --> K["❌ Return False"]
    J -- "Yes" --> L["ffprobe: extract width, height, duration, SAR, rotate"]
    L --> M["ffmpeg: generate proportional 320px thumbnail"]
    M --> N["Telegram send_video (supports_streaming=True)"]
    N --> O["Cache file_id & dimensions in LRU memory"]
    O --> P["🧹 Remove temporary files & thumbnail"]
    P --> Q["✅ Return True"]
```

#### Diagram 3: Decision Matrix: Stealth Link Cleanup in Group Chats
```mermaid
flowchart TD
    A["🏁 Media processing completed for message"] --> B{"Telegram Chat Type"}
    B -- "Private 1-on-1 Chat" --> C["🔒 User message is strictly preserved"]
    B -- "Group / Supergroup / Channel" --> D{"Was at least one video sent?"}
    D -- "No (all downloads failed)" --> E["⚠️ Keep original message with links"]
    D -- "Yes (at least one video sent)" --> F{"Does bot have 'Delete Messages' admin right?"}
    F -- "Yes (permission granted)" --> G["🗑 Delete user's message containing link(s)"]
    G --> H["✨ Chat displays only the clean video"]
    F -- "No (insufficient rights)" --> I["ℹ️ Graceful fallback (video delivered, message kept)"]
```

#### Diagram 4: End-to-End Sequence Diagram
```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant TG as 📱 Telegram Cloud
    participant Bot as ⚡ Relay Bot
    participant Cache as 🧠 LRU Cache
    participant Downloader as 📥 Downloader (API / yt-dlp)
    participant FFmpeg as 🎞 FFmpeg & FFprobe

    User->>TG: Sends message with 2 video links
    TG->>Bot: Message Update event
    Bot->>Bot: extract_media_links(): parse & sanitize 2 URLs
    
    par Concurrent Link 1 Processing
        Bot->>Cache: Query Link 1
        alt Cache Hit
            Cache-->>Bot: file_id + dimensions
            Bot->>TG: reply_video(file_id)
        else Cache Miss
            Bot->>TG: send_chat_action(UPLOAD_VIDEO)
            Bot->>Downloader: Download streams
            Downloader-->>Bot: Local MP4 file
            Bot->>FFmpeg: probe_video_metadata + thumbnail
            FFmpeg-->>Bot: Dimensions & thumbnail
            Bot->>TG: reply_video(file, thumbnail, dimensions)
            Bot->>Cache: Save file_id to LRU cache
        end
    and Concurrent Link 2 Processing
        Bot->>Cache: Query Link 2
        Bot->>TG: send_chat_action(UPLOAD_VIDEO)
        Bot->>Downloader: Download streams
        Downloader-->>Bot: Local MP4 file
        Bot->>FFmpeg: probe_video_metadata + thumbnail
        FFmpeg-->>Bot: Dimensions & thumbnail
        Bot->>TG: reply_video(file, thumbnail, dimensions)
        Bot->>Cache: Save file_id to LRU cache
    end

    TG-->>User: Both Video 1 and Video 2 appear in chat
    opt If Group Chat and Delete Messages Permission Granted
        Bot->>TG: delete_message(message_id)
        TG-->>User: Original link message disappears from chat
    end
```

---

### ⚙️ Configuration (`.env`)

Create your `.env` configuration file from the template:

```bash
cp .env.example .env
```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `BOT_TOKEN` | Telegram Bot Token obtained from [@BotFather](https://t.me/BotFather) | *Required* |
| `MAX_CONCURRENT_DOWNLOADS` | Maximum concurrent `yt-dlp` download jobs | `3` |
| `COOKIES_FILE` | Path to cookies file for bypassing platform limits | `cookies.txt` |

---

### 📦 Installation & Quickstart

#### Option 1: Docker Compose (Recommended)

```bash
# Build image and start in background
docker compose up -d --build

# Inspect live logs
docker compose logs -f

# Stop container
docker compose down
```

#### Option 2: Local Python Execution

```bash
# 1. Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# venv\Scripts\activate   # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start bot
python bot.py
```

---

### 💡 Group Chat Configuration (BotFather)

#### 1. Enabling Automatic Link Reading
By default, Telegram restricts bot visibility in groups:
1. Open [@BotFather](https://t.me/BotFather) and type `/mybots`.
2. Select your bot → **Bot Settings** → **Group Privacy**.
3. Choose **Turn off**.
4. If the bot is already in your group, remove and re-add it.

#### 2. Enabling Clean Chat Mode (Stealth Link Deletion)
To let Relay automatically delete the link message after delivering the video:
1. Promote Relay to **Administrator** in your group.
2. Grant the **Delete Messages** permission.
3. Done! When someone posts a video link, Relay will deliver the video and immediately clean up the link message.

---

### 📄 License

This project is open-sourced under the [MIT License](LICENSE).
