"""Обработчики бота: /start, кнопки, гибрид сценарий/AI, журнал диалогов.

Текстовое сообщение сначала пытается ответить сценарий из scenarios.py (0
токенов), и только если тема не распознана — уходит платный запрос в backend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import backend_client
import mailer
import manager_api
import scenarios

log = logging.getLogger(__name__)

# Журнал диалога в памяти: session_id -> [{"role": "user", "content": ...}, ...]
# Перезапуск бота историю обнуляет — для анализа она в dialogs.jsonl.
DIALOGS: dict[str, list[dict[str, str]]] = {}

# Нажали «Связаться с менеджером», но вопрос ещё не задали. Ждём реплику:
# только с ней есть смысл звать менеджера (письмо + очередь в кабинете).
PENDING_QUESTION: set[str] = set()

MAX_STORED = 20  # backend принимает окно в 20 реплик, больше всё равно не отправим
TELEGRAM_TEXT_LIMIT = 4000  # Telegram режет сообщения длиннее 4096 знаков

# Как часто заглядывать в очередь менеджера (секунд).
REPLY_POLL_SECONDS = 5

LOG_FILE = Path(__file__).with_name("dialogs.jsonl")


def _session_id(chat_id: int) -> str:
    return f"tg_{chat_id}"


def _history(session_id: str) -> list[dict[str, str]]:
    return DIALOGS.get(session_id, [])[-MAX_STORED:]


def _remember(session_id: str, role: str, content: str) -> None:
    DIALOGS.setdefault(session_id, []).append({"role": role, "content": content})
    del DIALOGS[session_id][:-MAX_STORED]


def _log_exchange(session_id: str, message: str, answer: str, needs_human: bool, route: str) -> None:
    """Одна строка JSON на обмен: понадобится Практике №2а и №4.

    ``route`` — ``scenario`` (без затрат) или ``backend`` (платный ИИ).
    """
    row = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": session_id,
        "channel": "telegram",
        "message": message,
        "answer": answer,
        "needs_human": needs_human,
        "route": route,
    }
    try:
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        log.exception("не удалось дописать в %s", LOG_FILE)


def _menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"menu:{key}") for label, key in row]
        for row in scenarios.MENU_BUTTONS
    ]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    DIALOGS.setdefault(_session_id(update.effective_chat.id), [])
    await update.message.reply_text(scenarios.WELCOME, reply_markup=_menu())


async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Нажатие кнопки: готовый текст, backend не вызываем (0 токенов)."""
    query = update.callback_query
    if query is None:
        return
    key = query.data.split(":", 1)[1]
    text = scenarios.answer_for(key)

    try:
        # answer() лишь гасит «часики» на кнопке. Если бот был выключен и апдейт
        # задержался, Telegram отвечает «Query is too old» — это не повод молчать.
        await query.answer(None if text else "Такой кнопки нет", show_alert=not text)
    except TelegramError as exc:
        log.debug("callback %s не подтвердить: %s", query.id, exc)

    if text is None:
        return

    # Кнопка «Связаться с менеджером»: сам клик ещё не вопрос. Просим клиента
    # описать проблему, а письмо и очередь отправит on_text на следующем сообщении.
    if key == "manager":
        PENDING_QUESTION.add(_session_id(update.effective_chat.id))
        text = f"{text}\n\nОпишите ваш вопрос обычным сообщением — я передам его менеджеру."

    try:
        await query.edit_message_text(text, reply_markup=_menu())
    except TelegramError:
        # Старое сообщение недоступно (бот пробыл в простое) — шлём новое.
        await context.bot.send_message(update.effective_chat.id, text, reply_markup=_menu())


def _hybrid_enabled() -> bool:
    """HYBRID_ROUTING=false в .env — и все вопросы, кроме кнопок, уходят в AI."""
    return os.environ.get("HYBRID_ROUTING", "true").strip().lower() != "false"


# --------------------------------------------------------------------------- #
#  Практика №2б: менеджер подключается к диалогу
# --------------------------------------------------------------------------- #

# Режимы живут в памяти: session_id -> "bot" | "human".
# human = бот молчит, реплика уходит менеджеру, клиенту отвечает менеджер.
MODES: dict[str, str] = {}

# message_id пересланной реплики в чате менеджера -> session_id.
# По нему находим диалог, когда менеджер отвечает на пересланное сообщение.
TAKEN: dict[int, str] = {}


def set_mode(session_id: str, mode: str) -> None:
    MODES[session_id] = mode


def get_mode(session_id: str) -> str:
    return MODES.get(session_id, "bot")


def _manager_chat() -> int | None:
    """MANAGER_CHAT_ID или None: команды менеджера принимаем только в этом чате."""
    raw = os.environ.get("MANAGER_CHAT_ID", "").strip()
    return int(raw) if raw else None


def _chat_of(session_id: str) -> int:
    """session_id 'tg_123' делали мы из chat_id -> возвращаем chat_id."""
    return int(session_id.removeprefix("tg_"))


async def _need_manager(update, context) -> bool:
    """/take, /release, /dialogs — команды менеджера, из другого чата игнорим."""
    if _from_manager(update):
        return True
    await update.message.reply_text(
        "Эта команда работает только в чате менеджера. Напишите /id в нём."
    )
    return False


def _from_manager(update) -> bool:
    manager = _manager_chat()
    return manager is not None and update.effective_chat.id == manager


async def cmd_take(update, context) -> None:
    """/take tg_123 — менеджер забирает диалог себе (режим human)."""
    if not await _need_manager(update, context):
        return
    if not context.args:
        await update.message.reply_text("Укажите диалог: /take tg_123456")
        return
    session_id = context.args[0]
    set_mode(session_id, "human")
    await update.message.reply_text("Вы говорите с клиентом")


async def cmd_release(update, context) -> None:
    """/release tg_123 — вернуть диалог боту."""
    if not await _need_manager(update, context):
        return
    session_id = context.args[0] if context.args else _session_id(update.effective_chat.id)
    set_mode(session_id, "bot")
    await update.message.reply_text("Вы снова сами")
    try:
        await context.bot.send_message(
            _chat_of(session_id), "Менеджер отключился, бот снова отвечает"
        )
    except Exception:  # клиент мог закрыть чат — не должны ронять ответ менеджеру
        log.warning("не удалось предупредить клиента %s", session_id)


async def cmd_id(update, context) -> None:
    """/id — chat_id этого чата; его и вписать в MANAGER_CHAT_ID."""
    await update.message.reply_text(f"chat_id этого чата: {update.effective_chat.id}")


async def cmd_dialogs(update, context) -> None:
    """/dialogs — активные диалоги: session_id, режим, последняя реплика."""
    if not await _need_manager(update, context):
        return
    rows = []
    for sid in sorted(DIALOGS):
        last = (DIALOGS.get(sid) or [{"content": ""}])[-1]["content"][:40]
        rows.append(f"{sid} [{get_mode(sid)}] {last}")
    await update.message.reply_text("\n".join(rows) if rows else "Активных диалогов нет")


async def _manager_answered(update, context, text: str) -> bool:
    """Ответ менеджера на пересланную реплику -> текст уходит клиенту."""
    reply = update.message.reply_to_message
    session_id = TAKEN.get(reply.id) if reply else None
    if not session_id or get_mode(session_id) != "human":
        return False

    await context.bot.send_message(_chat_of(session_id), text)
    _remember(session_id, "assistant", text)
    _log_exchange(session_id, text, text, True, "manager")
    log.info("[%s] ответил менеджер", session_id)
    return True


async def _forward_to_manager(update, context, text: str, session_id: str, manager: int) -> None:
    """Реплика клиента в режиме human: менеджеру, с by caption session_id."""
    sent = await context.bot.send_message(manager, f"[{session_id}] {text}")
    TAKEN[sent.id] = session_id
    _remember(session_id, "user", text)
    _log_exchange(session_id, text, "", False, "human")
    log.info("[%s] режим human: переслали менеджеру", session_id)
    await update.message.reply_text("Ваш вопрос передаю менеджеру")


def _client_profile(update) -> dict:
    """Кого нашёл менеджер: имя и @username клиент Telegram сам присылает в апдейте.

    ``username`` приходит, только если клиент сам задал его в настройках — у
    четверти людей его нет, и тогда ссылка на личную переписку невозможна.
    Телефон Telegram не отдаёт: его клиент обязан сам передать кнопкой.
    """
    user = getattr(update, "effective_user", None)
    if user is None:
        return {}
    return {
        "name": " ".join(part for part in (user.first_name, user.last_name) if part),
        "username": user.username or "",
        "chat_id": str(user.id),
    }


async def _call_manager(
    context,
    session_id: str,
    text: str,
    dialog,
    reason: str = "",
    client: dict | None = None,
) -> None:
    """Позвать менеджера: письмо, тост в Telegram и очередь в кабинете.

    Письмо — главный канал: в нём источник, вопрос клиента и инструкция, как
    менеджеру выйти на этого клиента.
    """
    mailer.send_manager_email(
        session_id,
        "telegram",
        list(dialog) + [{"role": "user", "content": text}],
        question=text,
        reason=reason,
        client=client,
    )
    await _ping_manager(context, session_id, text)
    await manager_api.report(session_id, "telegram", text)


async def _ping_manager(context, session_id: str, text: str) -> None:
    """Уведомление в чат менеджера: письмо могло и не настроить, а звать надо."""
    manager = _manager_chat()
    if not manager:
        return
    try:
        await context.bot.send_message(
            manager,
            f"Клиент ждёт менеджера: {text[:120]}\n"
            f"Диалог: {session_id}\nВозьмите: /take {session_id}",
        )
    except Exception:
        log.warning("не удалось позвать менеджера в %s", manager)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Текст клиента: сначала готовый сценарий (0 токенов), иначе — backend."""
    if update.message is None or not (text := (update.message.text or "").strip()):
        return

    session_id = _session_id(update.effective_chat.id)
    client = _client_profile(update)

    # ------------------------------------------------------------------ #
    #  Практика №2б: режим проверяем ДО обращения к платному backend.
    #  Из чата менеджера перехватываем только ответ на пересланную реплику:
    #  если MANAGER_CHAT_ID случайно совпал с рабочим чатом, остальной текст
    #  должен жить как у обычного клиента, а не глушить весь бот.
    # ------------------------------------------------------------------ #
    manager = _manager_chat()
    if manager and update.effective_chat.id == manager:
        if await _manager_answered(update, context, text):
            return

    if manager and get_mode(session_id) == "human":
        await _forward_to_manager(update, context, text, session_id, manager)
        return

    # Клиент раньше нажал «Связаться с менеджером» — эта реплика и есть вопрос.
    if session_id in PENDING_QUESTION:
        PENDING_QUESTION.discard(session_id)
        dialog = _history(session_id)
        await _call_manager(
            context, session_id, text, dialog,
            reason="клиент сам нажал «Связаться с менеджером»",
            client=client,
        )
        _remember(session_id, "user", text)
        _log_exchange(session_id, text, scenarios.HANDOFF, True, "handoff")
        await update.message.reply_text(scenarios.HANDOFF)
        return

    dialog = _history(session_id)
    scenario = scenarios.match(text) if _hybrid_enabled() else None
    handoff_reason = ""

    if mailer.needs_human(text):
        # Заказ/менеджер/сотрудничество: платный запрос не тратим, зовём человека.
        answer, needs_human, route = scenarios.HANDOFF, True, "handoff"
        words = ", ".join(mailer.matched_words(text)) or "ключевые слова"
        handoff_reason = f"в сообщении клиента прозвучала заявка: {words}"
    elif scenario:
        answer, needs_human, route = scenarios.ANSWERS[scenario], False, "scenario"
        log.info("[%s] ответил сценарий, backend не трогали: %s", session_id, scenario)
    else:
        route = "backend"
        try:
            result = await backend_client.ask_backend(session_id, text, history=dialog)
            answer, needs_human = str(result["answer"]), bool(result["needs_human"])
            if needs_human:  # backend сам попросил человека
                answer = f"{answer}\n\n{scenarios.HANDOFF}"
                handoff_reason = "backend ответил: нужен человек"
        except backend_client.BackendError as exc:
            log.error("[%s] %s", session_id, exc)
            answer, needs_human = scenarios.BACKEND_DOWN, False

    if needs_human:
        await _call_manager(
            context, session_id, text, dialog, reason=handoff_reason, client=client
        )

    _remember(session_id, "user", text)
    _remember(session_id, "assistant", answer)
    _log_exchange(session_id, text, answer, needs_human, route)

    await update.message.reply_text(answer[:TELEGRAM_TEXT_LIMIT])


async def manager_pump(application) -> None:
    """Ответы менеджера из кабинета -> клиенту. sites-очередь замечает их сам."""
    while True:
        await asyncio.sleep(REPLY_POLL_SECONDS)
        try:
            replies = await manager_api.claim_replies()
        except Exception as exc:  # сеть/сайт — ждём следующего интервала
            log.warning("очередь менеджера недоступна: %s", exc)
            continue
        for item in replies:
            session_id, text = item.get("session_id", ""), str(item.get("reply") or "").strip()
            if not session_id.startswith("tg_") or not text:
                continue
            try:
                await application.bot.send_message(_chat_of(session_id), text)
            except Exception as exc:
                log.warning("ответ менеджера до %s не дошёл: %s", session_id, exc)
                continue
            _remember(session_id, "assistant", text)
            _log_exchange(session_id, "", text, True, "manager")
            log.info("[%s] ответ менеджера из кабинета", session_id)


async def on_error(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Без обработчика PTB печатает «No error handlers are registered» и трейсбек."""
    log.error("обработчик %s упал: %s", type(context.error).__name__, context.error)


def register(application) -> None:
    """Повесить обработчики на ``telegram.ext.Application``.

    Аргументы команд PTB кладет в ``context.args`` сам, отдельно их не просят.
    """
    application.add_error_handler(on_error)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", cmd_id))
    application.add_handler(CommandHandler("take", cmd_take))
    application.add_handler(CommandHandler("release", cmd_release))
    application.add_handler(CommandHandler("dialogs", cmd_dialogs))
    application.add_handler(CallbackQueryHandler(on_menu, pattern=r"^menu:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
