"""Запуск Telegram-бота (Практика №1) из корня проекта:

    .venv/bin/python telegram-bot/bot.py

Настройки берём из telegram-bot/.env, а отсутствующие ключи — из .env сайта
(то есть TELEGRAM_BOT_TOKEN и BACKEND_URL можно держать в одном .env проекта).

Бот работает в режиме polling — публичный адрес и вебхук не нужны, но backend
должен быть доступен: у локального сайта это та же машина, `npm start`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram.ext import Application

import backend_client
import handlers

ENV_FILE = Path(__file__).with_name(".env")  # telegram-bot/.env — настройки бота
ROOT_ENV = ENV_FILE.parent.parent / ".env"   # .env сайта: дополняем из него


def load_settings() -> None:
    """Свой .env важнее: значения из корневого файла его не перекрывают."""
    load_dotenv(ENV_FILE)
    load_dotenv(ROOT_ENV)  # override=False по умолчанию — не перезапишет заданное


PUMP_TASK: "asyncio.Task | None" = None


async def _start_manager_pump(application) -> None:
    """Ответы менеджера из админки приходят клиенту фоновой задачей.

    `Application.create_task` здесь ещё до start(), и PTB warns про «won't be
    awaited» — поэтому своя задача и явная отмена в post_shutdown.
    """
    global PUMP_TASK
    PUMP_TASK = asyncio.create_task(handlers.manager_pump(application), name="manager-pump")


async def _stop_manager_pump(_application) -> None:
    if PUMP_TASK:
        PUMP_TASK.cancel()


def main() -> None:
    # Ищем настройки сначала в telegram-bot/.env, затем в .env сайта.
    load_settings()

    logging.basicConfig(
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        level=logging.INFO,
    )
    # HTTP и Telegram в INFO забивают журнал бесполезными деталями запросов.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        sys.exit(
            f"TELEGRAM_BOT_TOKEN не найден. Скопируйте {ENV_FILE.name}.example "
            f"в {ENV_FILE.name} и впишите токен от @BotFather."
        )

    if os.environ.get("BACKEND_MODE", "real").strip().lower() == "mock":
        print("BACKEND_MODE=mock: ответы из заглушки, платный ИИ не вызывается.")
    print(f"Backend: {backend_client._endpoint()}")

    application = (
        Application.builder()
        .token(token)
        .post_init(_start_manager_pump)
        .post_shutdown(_stop_manager_pump)
        .build()
    )
    handlers.register(application)

    # drop_pending_updates=False: вопросы, накопившиеся за время простоя, не теряются.
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
