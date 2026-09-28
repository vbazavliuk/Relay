# Contributing to Relay / Внесок у розвиток Relay

[**🇬🇧 English**](#-english) &nbsp;|&nbsp; [**🇺🇦 Українська**](#-українська)

---

<a id="-english"></a>
## 🇬🇧 English

Thank you for your interest in contributing to **Relay**! We welcome bug reports, feature proposals, and pull requests.

### 🛠 Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/vbazavliuk/Relay.git
   cd Relay
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux / macOS
   # venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install ruff
   ```

4. **Set up `.env`**:
   ```bash
   cp .env.example .env
   # Add your test bot token from @BotFather
   ```

### 📐 Code Style & Architecture Guidelines

- **PEP 8 & Formatting**: Follow modern Python conventions. Run `ruff check .` before submitting a PR.
- **Async First**: All network requests and Telegram interactions must be asynchronous (`aiohttp`, `asyncio`). Heavy blocking CPU/IO operations (such as `yt-dlp` extraction or `ffmpeg`/`ffprobe` subprocesses) must be wrapped with `asyncio.to_thread`.
- **Multi-Link Support**: Ensure any link parsing methods support multiple links in a single message or consecutive messages without discarding subsequent items.
- **Smart Group Chat Cleanup**: Maintain graceful permission handling: in group chats where the bot is an admin with `can_delete_messages`, delete the link message after sending video; in private chats, never delete user messages.
- **Preserve Clean Aspect Ratios**: Always extract metadata via `probe_video_metadata` and pass `width`, `height`, `duration`, and proportional `thumbnail` to `reply_video` with `supports_streaming=True`.
- **Type Hints & Docstrings**: Keep functions cleanly typed and documented.

### 🚀 Submitting a Pull Request

1. Create a feature branch (`git checkout -b feature/amazing-feature`).
2. Verify code syntax and style:
   ```bash
   python -m py_compile bot.py
   ruff check .
   ```
3. Commit your changes (`git commit -m 'Add feature: ...'`).
4. Push to your branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request on GitHub.

---

<a id="-українська"></a>
## 🇺🇦 Українська

Дякуємо за ваш інтерес до розвитку проєкту **Relay**! Ми вітаємо звіти про помилки, пропозиції нових функцій та pull request'и.

### 🛠 Налаштування середовища розробки

1. **Створіть форк та клонуйте репозиторій**:
   ```bash
   git clone https://github.com/vbazavliuk/Relay.git
   cd Relay
   ```

2. **Створіть віртуальне оточення**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux / macOS
   # venv\Scripts\activate   # Windows
   ```

3. **Встановіть залежності**:
   ```bash
   pip install -r requirements.txt
   pip install ruff
   ```

4. **Налаштуйте файл `.env`**:
   ```bash
   cp .env.example .env
   # Вкажіть тестовий токен бота з @BotFather
   ```

### 📐 Стандарти коду та архітектурні принципи

- **Форматування та лінтинг**: Дотримуйтесь стандартів Python. Запускайте `ruff check .` перед створенням PR.
- **Асинхронність насамперед**: Усі мережеві запити та виклики Telegram Bot API мають бути асинхронними (`aiohttp`, `asyncio`). Важкі блокуючі операції (`yt-dlp`, виклики `ffmpeg`/`ffprobe`) обов'язково загортаються в `asyncio.to_thread`.
- **Пакетна обробка посилань**: Нові функції повинні підтримувати обробку кількох посилань поспіль або в одному повідомленні без втрати наступних URL.
- **Стелс-очищення чатів**: Дотримуйтесь логіки безпечного видалення: у групах із правами `can_delete_messages` видаляйте вихідне повідомлення після доставки відео; у приватних 1-на-1 діалогах повідомлення користувача ніколи не видаляються.
- **Збереження геометрії відео**: Завжди отримуйте метадані через `probe_video_metadata` та передавайте `width`, `height`, `duration`, прапорець `supports_streaming=True` та пропорційний `thumbnail`.

### 🚀 Створення Pull Request

1. Створіть окрему гілку (`git checkout -b feature/amazing-feature`).
2. Перевірте синтаксис та стиль коду:
   ```bash
   python -m py_compile bot.py
   ruff check .
   ```
3. Збережіть зміни у коміт (`git commit -m 'Додано підтримку: ...'`).
4. Надішліть гілку на GitHub (`git push origin feature/amazing-feature`).
5. Відкрийте Pull Request.
