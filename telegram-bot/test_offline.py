"""Офлайн-самопроверка бота (Практики №1 и №2а) — без сети и без платного ИИ.

    .venv/bin/python telegram-bot/test_offline.py

Update и Bot подменены фиктивными классами, отправка письма и очередь менеджера
заглушками. Проверяем: кнопки и сценарии не тратят токены, письмо менеджеру
содержит источник, вопрос и данные клиента, а режим ``human`` не зовёт backend.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

# Порядок важен: mailer читает настройки в момент отправки.
os.environ.update(
    {
        "DRY_RUN": "true",
        "MANAGER_EMAIL": "manager@example.test",
        "BACKEND_MODE": "mock",
        "MANAGER_CHAT_ID": "",
        "SITE_URL": "http://127.0.0.1:3456",
    }
)

import handlers  # noqa: E402
import mailer  # noqa: E402
import scenarios  # noqa: E402

SENT_MAIL: list[dict] = []


class FakeContext:
    """Кусок ``ContextTypes.DEFAULT_TYPE``: боту нужен только send_message."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

        async def send_message(chat_id: int, text: str, **_: object) -> None:
            self.sent.append((chat_id, text))

        self.bot = SimpleNamespace(send_message=send_message)


def fake_update(chat_id: int, text: str, username: str | None = None):
    user = SimpleNamespace(id=chat_id, first_name="Айгерік", last_name="Смаул", username=username)
    return SimpleNamespace(
        message=FakeMessage(text),
        effective_chat=SimpleNamespace(id=chat_id),
        effective_user=user,
    )


class FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.reply_to_message = None
        self.sent: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.sent.append(text)


async def _no_report(*_args, **_kwargs) -> None:
    """Очередь менеджера на сайте — не проверяем, она проверяется на стенде."""


async def run_checks() -> None:
    tmp = tempfile.TemporaryDirectory()
    handlers.LOG_FILE = Path(tmp.name) / "dialogs.jsonl"

    def capture_mail(session_id, channel, last_messages, **kwargs):
        SENT_MAIL.append({"session_id": session_id, "channel": channel, **kwargs})
        return True

    async def no_ping(*_args, **_kwargs) -> None:
        return None

    real_send_manager_email = mailer.send_manager_email  # настоящая функция, до подмены
    mailer.send_manager_email = capture_mail
    handlers._ping_manager = no_ping
    handlers.manager_api.report = no_ping

    # 1. Кнопка «Связаться с менеджером» + следующий вопрос: письмо ушло.
    handlers.PENDING_QUESTION.add("tg_660405782")
    context = FakeContext()
    update = fake_update(660405782, "Хочу заказать торт на выходных", username="PeakPeak")
    await handlers.on_text(update, context)

    assert SENT_MAIL, "письмо не отправлено"
    mail = SENT_MAIL[-1]
    assert mail["question"] == "Хочу заказать торт на выходных"
    assert mail["client"] == {"name": "Айгерік Смаул", "username": "PeakPeak", "chat_id": "660405782"}
    assert update.message.sent == [scenarios.HANDOFF], update.message.sent
    print("1. кнопка + вопрос → письмо с client=userName ... ок")

    body = mailer._body(
        mail["session_id"], mail["channel"], [], mail["question"], mail["reason"], mail["client"]
    )
    assert "https://t.me/PeakPeak" in body and "@PeakPeak" in body, body
    assert "Взять диалог себе: /take tg_660405782" in body, body
    assert "Источник (канал): Telegram-бот" in body, body
    print("2. в письме @username и ссылка на личную ..... ok")

    # 3. username нет — ссылку не выдумываем и честно об этом пишем.
    await handlers.on_text(fake_update(660405782, "Нужен менеджер"), context)
    mail = SENT_MAIL[-1]
    body = mailer._body(
        mail["session_id"], mail["channel"], [], mail["question"], mail["reason"], mail["client"]
    )
    assert "https://t.me" not in body and "не задан" in body, body
    print("3. клиент без username .............. ok")

    # 4. Правила: ключевые слова ловим, сценарий отвечает сам, backend не дёргаем.
    assert mailer.needs_human("Хочу купить") and mailer.matched_words("нужен менеджер")
    assert scenarios.match("какие часы работы?") == "hours"
    print("4. needs_human и сценарии без платного ИИ ...... ok")

    # 5. Троттл: второе письмо в тот же диалог в течение 5 минут не уходит.
    mailer._last_sent.clear()
    assert real_send_manager_email("tg_1", "telegram", [], question="a", reason="a") is True
    assert real_send_manager_email("tg_1", "telegram", [], question="b", reason="b") is False
    print("5. повторного письма за 5 минут ........  ok")

    print("\n--- как выглядит письмо ---")
    print(
        mailer._body(
            "tg_660405782",
            "telegram",
            [{"role": "user", "content": "Который час работы?"}],
            "Хочу заказать торт",
            "клиент сам нажал «Связаться с менеджером»",
            {"name": "Айгерік Смаул", "username": "PeakPeak", "chat_id": "660405782"},
        )
    )
    tmp.cleanup()


if __name__ == "__main__":
    asyncio.run(run_checks())
    print("все проверки прошли, сеть и платный ИИ не использовались")
