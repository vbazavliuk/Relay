# Contributing to Relay

Thank you for your interest in contributing to **Relay**! We welcome bug reports, feature proposals, and pull requests.

---

## 🛠 Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/vbazavliuk/Relay.git
   cd Relay
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux / macOS
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

---

## 📐 Code Style & Guidelines

- **PEP 8 & Formatting**: Follow standard Python conventions. Run `ruff check .` before submitting a PR.
- **Async First**: All network requests and Telegram interactions must be asynchronous (`aiohttp`, `asyncio`). Heavy CPU operations (like `yt-dlp` extraction) must be wrapped with `asyncio.to_thread`.
- **Preserve Clean Aspect Ratios**: Always extract metadata via `probe_video_metadata` and pass `width`, `height`, `duration`, and `thumbnail` to `reply_video`.
- **Type Hints & Docstrings**: Keep functions documented and typed where applicable.

---

## 🚀 Submitting a Pull Request

1. Create a feature branch (`git checkout -b feature/amazing-feature`).
2. Verify code syntax and style:
   ```bash
   python -m py_compile bot.py
   ruff check .
   ```
3. Commit your changes (`git commit -m 'Add support for Platform XYZ'`).
4. Push to your branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request on GitHub.
