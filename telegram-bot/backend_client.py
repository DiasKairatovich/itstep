"""Адаптер бота к RAG-backend сайта — единственная дверь к платному ИИ.

Формат нашего backend (он же обслуживает чат на сайте), server/index.js:

    POST {BACKEND_URL}/api/chat
    {"messages": [{"role": "user", "content": "..."}, ...]}
    -> {"reply": "Капучино — 650 ₸ ...", "sources": ["Меню.md"], "degraded": false}

Поэтому:
  * `session_id` backend не знает — контекст он ждёт в теле запроса, исторю
    передаёт бот (аргумент `history`);
  * `answer` — это поле `reply`;
  * признака `needs_human` у backend нет, подставляем False (решит Практика №2а).

Ключи только из .env; в код их не пишем.
"""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)

# Столько же, сколько принимает server/index.js (MAX_MESSAGES / MAX_INPUT_CHARS).
MAX_MESSAGES = 20
MAX_CHARS = 2000

TIMEOUT = httpx.Timeout(30.0, connect=5.0)


class BackendError(Exception):
    """Backend недоступен, ответил ошибкой или прислал неизвестный формат."""


def _endpoint() -> str:
    """BACKEND_URL принимает и корень сайта, и полный путь к /api/chat."""
    base = os.environ.get("BACKEND_URL", "http://127.0.0.1:3456").strip().rstrip("/")
    return base if base.endswith("/api/chat") else f"{base}/api/chat"


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    # У нашего backend авторизации на /api/chat нет; на случай другого backend
    # оставляем BACKEND_TOKEN — он же позволит сменить API без правок кода.
    token = os.environ.get("BACKEND_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def ask_backend(
    session_id: str,
    message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Спросить backend и вернуть ``{"answer": str, "needs_human": bool}``.

    ``history`` — реплики диалога ``[{"role", "content"}, ...]`` без текущего
    вопроса: backend историю не хранит, окно на 20 реплик собираем заново.
    ``session_id`` в запрос не кладём (backend его не понимает), он нужен боту
    для журнала диалогов.

    ``BackendError`` — бот обязан ответить вежливую заготовку, не падать.
    """
    if os.environ.get("BACKEND_MODE", "real").strip().lower() == "mock":
        # Заглушка из «Тест без трат»: проверка цепочек бота без токенов.
        return {"answer": f"[mock] Вопрос получен: {message[:80]}", "needs_human": False}

    messages = list(history or [])
    messages = (messages + [{"role": "user", "content": message.strip()[:MAX_CHARS]}])[-MAX_MESSAGES:]

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.post(_endpoint(), json={"messages": messages}, headers=_headers())
    except httpx.HTTPError as exc:
        raise BackendError(f"backend не ответил: {exc}") from exc

    if res.status_code == 429:
        raise BackendError("backend ограничил частоту запросов (429)")
    if res.status_code >= 400:
        # Текст ошибки backend может содержать служебные детали — в лог id ответа.
        raise BackendError(f"backend ответил {res.status_code}")

    try:
        data = res.json()
    except ValueError as exc:
        raise BackendError("ожидали JSON с полем reply, получили другой ответ") from exc

    answer = data.get("reply")
    if not isinstance(answer, str) or not answer.strip():
        raise BackendError(f"в ответе backend нет строкового поля reply: {sorted(data)!r}")

    if data.get("degraded"):
        # Ответ-заготовка: платный ИИ не сработал, но пользователю отвечаем.
        log.warning("[%s] backend ответил degraded", session_id)

    needs_human = data.get("needs_human")
    return {"answer": answer.strip(), "needs_human": bool(needs_human)}
