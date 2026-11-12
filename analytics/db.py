"""Аналитика диалогов: SQLite (стандартный sqlite3, без ORM).

Схема общая с Node (analytics/schema.sql). Любая ошибка записи гасится
и логируется: аналитика не должна ломать ответы бота.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("analytics")

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = Path(__file__).with_name("schema.sql")
PRICES_FILE = Path(__file__).with_name("prices.json")

# Реплика в течение этого окна продолжает прежний диалог сессии, позже — новый.
SESSION_GAP = timedelta(minutes=30)


def db_path() -> Path:
    return Path(os.environ.get("ANALYTICS_DB") or ROOT / "data" / "analytics.db")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # Node и Python пишут в один файл
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))


def cost_usd(model: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
    """Стоимость по prices.json; None, если цена не заполнена."""
    try:
        price = json.loads(PRICES_FILE.read_text(encoding="utf-8")).get(model) or {}
        p_in, p_out = price.get("input_per_1m_usd"), price.get("output_per_1m_usd")
        if p_in is None or p_out is None or tokens_in is None or tokens_out is None:
            return None
        return (tokens_in * p_in + tokens_out * p_out) / 1_000_000
    except Exception:  # noqa: BLE001
        log.exception("не удалось прочитать цены")
        return None


def _conversation_id(conn: sqlite3.Connection, session_id: str, channel: str, is_test: bool) -> int:
    row = conn.execute(
        """SELECT c.id, COALESCE(MAX(m.created_at), c.started_at) AS last_at
           FROM conversations c LEFT JOIN messages m ON m.conversation_id = c.id
           WHERE c.session_id = ? AND c.is_test = ?
           GROUP BY c.id ORDER BY c.id DESC LIMIT 1""",
        (session_id, int(is_test)),
    ).fetchone()
    if row:
        last = datetime.fromisoformat(row["last_at"])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last < SESSION_GAP:
            return row["id"]
    cur = conn.execute(
        "INSERT INTO conversations (session_id, channel, started_at, is_test) VALUES (?, ?, ?, ?)",
        (session_id, channel, _now(), int(is_test)),
    )
    return int(cur.lastrowid)


def log_exchange(
    session_id: str,
    channel: str,
    user_text: str = "",
    bot_text: str = "",
    *,
    is_fallback: bool = False,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    cost: float | None = None,
    is_test: bool = False,
    handed_to_manager: bool = False,
    lead_created: bool = False,
) -> int | None:
    """Записать реплику клиента и/или ответ бота. Возвращает id диалога или None при сбое."""
    try:
        with connect() as conn:
            conv = _conversation_id(conn, session_id, channel, is_test)
            if user_text:
                conn.execute(
                    "INSERT INTO messages (conversation_id, role, text, created_at) VALUES (?, 'user', ?, ?)",
                    (conv, user_text, _now()),
                )
            if bot_text:
                conn.execute(
                    """INSERT INTO messages (conversation_id, role, text, created_at, is_fallback,
                                             tokens_in, tokens_out, cost_usd)
                       VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?)""",
                    (conv, bot_text, _now(), int(is_fallback), tokens_in, tokens_out, cost),
                )
            if handed_to_manager:
                conn.execute("UPDATE conversations SET handed_to_manager = 1 WHERE id = ?", (conv,))
            if lead_created:
                conn.execute("UPDATE conversations SET lead_created = 1 WHERE id = ?", (conv,))
            return conv
    except Exception:  # noqa: BLE001
        log.exception("аналитика: не удалось записать обмен")
        return None


def _latest_conversation(conn: sqlite3.Connection, session_id: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM conversations WHERE session_id = ? AND is_test = 0 ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    return row["id"] if row else None


def set_rating(session_id: str, rating: int) -> None:
    """ЗАГЛУШКА-ХУК: оценки ответа в проекте пока нет.

    Вызвать там, где появится кнопка 1–5: в Telegram — обработчик нажатия
    inline-кнопки; на сайте — новый эндпоинт, например POST /api/rating.
    """
    try:
        if not 1 <= int(rating) <= 5:
            return
        with connect() as conn:
            conv = _latest_conversation(conn, session_id)
            if conv:
                conn.execute("UPDATE conversations SET rating = ? WHERE id = ?", (int(rating), conv))
    except Exception:  # noqa: BLE001
        log.exception("аналитика: не удалось записать оценку")
