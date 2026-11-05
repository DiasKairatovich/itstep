"""Практика №2а: узнаём, что клиенту нужен человек, и зовём менеджера письмом.

Параметры SMTP читаются из .env. Пока DRY_RUN=true (по умолчанию) письмо
только печатается в консоль: на реальные адреса ничего не уходит.
"""

from __future__ import annotations

import logging
import os
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage

log = logging.getLogger(__name__)

# Намерение, которое бот должен передать человеку. Слова-фрагменты: «сотруднич»
# ловит «сотрудничество», «партнер» — «партнерство» (с «ё» тоже добавим).
HUMAN_WORDS = [
    "заказать", "оформить", "купить", "менеджер", "позвоните",
    "сотруднич", "партнер", "партнёр", "взаимовыгод",
]

THROTTLE_SECONDS = 5 * 60  # одно письмо на диалог, далее — только через 5 минут
_last_sent: dict[str, float] = {}


def dry_run() -> bool:
    """DRY_RUN=false включать осознанно, когда SMTP-настройки проверены."""
    return os.environ.get("DRY_RUN", "true").strip().lower() != "false"


def needs_human(message: str, backend_response: dict | None = None) -> bool:
    """Нужен ли человек: ключевые слова клиента или флаг от backend."""
    if backend_response and backend_response.get("needs_human"):
        return True
    lowered = message.lower()
    return any(word in lowered for word in HUMAN_WORDS)


def matched_words(message: str) -> list[str]:
    """Какие именно слова клиента потянули на человека — для письма менеджеру."""
    lowered = message.lower()
    return [word for word in HUMAN_WORDS if word in lowered]


def _throttled(session_id: str) -> bool:
    sent_at = _last_sent.get(session_id)
    return sent_at is not None and time.monotonic() - sent_at < THROTTLE_SECONDS


def _site_root() -> str:
    """Корень сайта: ссылка на очередь менеджера в письме.

    BACKEND_URL у нас может быть указан и как корень, и с путём /api/chat —
    режем путь. SITE_URL позволяет приточке письмо к другому стенду.
    """
    base = os.environ.get("SITE_URL") or os.environ.get("BACKEND_URL") or "http://localhost:3456"
    base = base.strip().rstrip("/")
    return base[: -len("/api/chat")] if base.endswith("/api/chat") else base


def _describe_client(client: dict) -> list[str]:
    """Кого зовём: имя и @username клиента — их бот получает в каждом апдейте."""
    lines = []
    name = (client.get("name") or "").strip()
    username = (client.get("username") or "").strip()
    if name:
        lines.append(f"Имя в Telegram: {name}")
    if username:
        lines.append(f"Ник: @{username}")
    else:
        lines.append("Ник (username) у клиента не задан — искать его придётся по chat_id ниже")
    if client.get("phone"):
        lines.append(f"Телефон клиента: {client['phone']}")
    return lines


def _contact_hints(session_id: str, channel: str, client: dict | None = None) -> list[str]:
    """Как менеджеру выйти на клиента. Без этих строк письмо бесполезно."""
    client = client or {}
    queue = f"{_site_root()}/account"
    hints = [
        f"Ответить в очереди менеджера: {queue} (раздел «Обращения») — "
        "для Telegram-клиентов бот сам доставит ответ в чат.",
    ]
    if channel == "telegram":
        hints += [
            f"Telegram chat_id клиента: {session_id.removeprefix('tg_') or session_id}",
            f"Взять диалог себе: /take {session_id} (в чате менеджера), "
            f"вернуть боту: /release {session_id}",
        ]
        # Ссылка-ник работает, только если клиент сам задал username в Telegram.
        if client.get("username"):
            hints.append(f"Написать в личную: https://t.me/{client['username']}")
    else:
        hints.append(f"Сессия клиента в чате на сайте: {session_id}")
    return hints


def _body(
    session_id: str,
    channel: str,
    last_messages: list[dict[str, str]],
    question: str = "",
    reason: str = "",
    client: dict | None = None,
) -> str:
    """Письмо: кто просит, откуда, как с ним связаться, о чём он спросил."""
    source = {"telegram": "Telegram-бот", "site": "чат на сайте"}.get(channel, channel or "неизвестно")
    tail = "\n".join(
        f"  {'клиент' if m['role'] == 'user' else 'бот'}: {m['content']}"
        for m in last_messages[-5:]
    ) or "  (диалог пуст)"

    return (
        "Coffee Point: клиент запросил менеджера.\n\n"
        f"Источник (канал): {source}\n"
        f"Диалог: {session_id}\n"
        f"Время обращения: {datetime.now().astimezone().strftime('%d.%m.%Y %H:%M')}\n"
        f"Основание: {reason or 'клиент попросил человека'}\n\n"
        "Клиент:\n"
        + "\n".join(f"  - {line}" for line in _describe_client(client or {}))
        + f"\n\nВопрос клиента:\n  {question.strip()[:500] or '(вопрос не задан)'}\n\n"
        "Как выйти на клиента:\n"
        + "\n".join(f"  - {line}" for line in _contact_hints(session_id, channel, client))
        + f"\n\nПоследние реплики:\n{tail}\n"
    )


def send_manager_email(
    session_id: str,
    channel: str,
    last_messages: list[dict[str, str]],
    question: str = "",
    reason: str = "",
    client: dict | None = None,
) -> bool:
    """Письмо менеджеру: «клиент запросил человека» + как до него добраться.

    ``question`` и ``reason`` попадают в тело письма, ``client`` — имя, @username
    и телефон клиента (то, что бот получил от Telegram). True — письмо отправлено
    (или напечатано), False — подавлено или не отправлено.
    Не чаще одного раза в THROTTLE_SECONDS на диалог: защита от спама.
    """
    if _throttled(session_id):
        log.info("[%s] письмо менеджеру уже уходило недавно — пропускаем", session_id)
        return False

    manager = os.environ.get("MANAGER_EMAIL", "").strip()
    body = _body(session_id, channel, last_messages, question, reason, client)
    subject = f"[Coffee Point] Клиент запросил менеджера: {session_id}"

    if dry_run():
        print(f"\n===== DRY_RUN: письмо менеджеру =====\n"
              f"Кому: {manager or '<MANAGER_EMAIL не задан>'}\n"
              f"Тема: {subject}\n{body}\n{'=' * 38}\n")
        _last_sent[session_id] = time.monotonic()
        return True

    if not manager:
        log.error("MANAGER_EMAIL не задан — писать некому")
        return False

    # FROM = SMTP_USER: Gmail/Яндекс разрешают писать только «from себя»,
    # поэтому второе значение в .env просить лишнее.
    sender = os.environ.get("FROM_EMAIL", "").strip() or os.environ.get("SMTP_USER", "").strip()
    if not sender:
        log.error("FROM_EMAIL/SMTP_USER не заданы — непонятно, от кого письмо")
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = manager
    message["Subject"] = subject
    message.set_content(body)

    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        # Иначе KeyError внутри обработчика уронил бы ответ клиенту.
        log.error("SMTP_HOST не задан — письмо менеджеру не отправить")
        return False

    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        log.error("SMTP_PORT должен быть числом, а не %r", os.environ.get("SMTP_PORT"))
        return False

    # SMTP_SSL=true (или порт 465) — implicit TLS вместо STARTTLS.
    use_ssl = os.environ.get("SMTP_SSL", "").strip().lower() in ("1", "true", "yes") or port == 465

    try:
        connection = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with connection(host, port, timeout=20) as smtp:
            if not use_ssl:
                smtp.starttls()  # Gmail/Яндекс/Mail.ru на 587: STARTTLS

            user, password = os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASSWORD", "")
            if user:
                smtp.login(user, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        # В лог идёт только тип ошибки: пароль и SMTP-ключ туда попадают невольно.
        log.error("письмо менеджеру не отправлено: %s: %s", type(exc).__name__, exc)
        return False

    _last_sent[session_id] = time.monotonic()
    log.info("[%s] письмо менеджеру отправлено", session_id)
    return True
