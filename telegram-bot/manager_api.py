"""Очередь «нужен человек» на сайте (Практика №2б).

Бот докладывает сюда вопрос, который не смог закрыть сам, и забирает ответы
менеджера. Менеджер при этом работает в кабинете администратора
(http://localhost:3456/admin), а не в Telegram, — Telegram остаётся каналом
клиента.

Хранилище и экраны — на стороне сайта (server/handoffs.js).
"""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _root() -> str:
    """BACKEND_URL — корень сайта или путь к /api/chat; нам нужен корень."""
    base = os.environ.get("BACKEND_URL", "http://127.0.0.1:3456").strip().rstrip("/")
    if base.endswith("/api/chat"):
        return base[: -len("/api/chat")].rstrip("/")
    return base


async def report(session_id: str, channel: str, question: str) -> None:
    """Записать обращение в очередь менеджера.

    Не удалось — только пишем в лог: клиенту ответ и письмо важны, а очередь
    это подсказка менеджеру, терять из-за неё весь обмен нельзя.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            await client.post(
                f"{_root()}/api/handoffs",
                json={"session_id": session_id, "channel": channel, "question": question},
            )
    except httpx.HTTPError as exc:
        log.warning("обращение %s не записано в очередь: %s", session_id, exc)


async def claim_replies() -> list[dict]:
    """Ответы менеджера, которые ещё не ушли клиенту.

    Сайт помечает полученные ответы отправленными, так что повтор не ждёт.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.get(f"{_root()}/api/handoffs/outgoing")
            res.raise_for_status()
            return list(res.json().get("replies") or [])
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("ответы менеджера не забраны: %s", exc)
        return []
