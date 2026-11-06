---
name: telegram-bot-resilience
description: >-
  Expert architect and engineer for production-grade Telegram bots (aiogram, python-telegram-bot, telethon).
  Use when the user requests to:
  (1) design, build, debug, or refactor Telegram bots (e.g. ad_manager_bot, sale-bot, tg-transcribe-bot, telegram_notification),
  (2) decouple Telegram notification dispatchers from trading autopilots or background computation loops,
  (3) fix polling crashes, connection drops (TelegramNetworkError), rate limits (FloodWait / RetryAfter), and unhandled update exceptions,
  (4) implement voice-to-text / Whisper transcription pipelines without freezing update handlers,
  (5) configure Docker supervision, systemd daemonization, and graceful restarts for Telegram bots.
  Trigger words: "telegram bot", "телеграм бот", "aiogram", "telethon", "краш бота", "транскрибация",
  "polling error", "bot notification", "bot supervisor".
license: Apache-2.0
metadata:
  version: v1
  publisher: antigravity
  category: Chatbots & Automation
---

# Production Telegram Bot Resilience (`telegram-bot-resilience`)

This skill provides architectural patterns, crash resilience runbooks, and decoupling strategies for production Telegram bots.

---

## 🧭 Core Principles

1. **Non-Blocking Handler Execution**:
   - Update handlers must return immediately (within milliseconds). Heavy computations (audio transcription, DB queries, trading calculations) must be dispatched to background workers via `asyncio.create_task` or a message queue.
2. **Resilient Polling & Reconnection**:
   - Wrap long-polling in self-healing loops catching `TelegramNetworkError`, connection resets, and SSL handshake drops.
3. **Throttled Outbox & Flood Control**:
   - Respect Telegram's limit (max 30 messages/sec globally, 1 message/sec per chat). Queue outgoing broadcasts with rate-limiting token buckets.
4. **Decoupled Notification Architecture**:
   - Keep notification bots strictly as clients. A failure in Telegram API connectivity must never crash or block the trading autopilot or core service.

---

## 🛠 Operational Workflows

*Consult patterns: [references/telegram-patterns.md](./references/telegram-patterns.md)*

### 1. Diagnose Bot Crashes
- Inspect logs for unhandled update exceptions.
- Check if long-running synchronous code blocked the `asyncio` event loop.
- Verify that `allowed_updates` is explicitly configured to prevent backlog overload.

### 2. Audio & Media Processing (Whisper / Transcription)
- Store temporary audio in RAM or tempfiles with guaranteed deletion in `finally:` blocks.
- Offload transcription inference (`model.transcribe()`) to a dedicated thread pool (`asyncio.to_thread` or `run_in_executor`) so the bot remains responsive to other users.

### 3. Containerized Deployment & Health Monitoring
- Configure `restart: unless-stopped` in Docker Compose.
- Implement a healthcheck endpoint (e.g. lightweight aiohttp or socket probe) verifying that polling is actively processing ticks.
