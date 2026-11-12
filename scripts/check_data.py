"""Проверка загруженных данных analytics.db (только чтение, is_test=0).

    python scripts/check_data.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics import db  # noqa: E402


def rows(conn, sql, *args):
    return conn.execute(sql, args).fetchall()


def section(title: str) -> None:
    print(f"\n== {title}")


def main() -> None:
    path = db.db_path()
    if not path.exists():
        sys.exit(f"{path} не найден")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

    n_conv = rows(conn, "SELECT COUNT(*) FROM conversations WHERE is_test = 0")[0][0]
    n_msg = rows(
        conn,
        "SELECT COUNT(*) FROM messages m JOIN conversations c ON c.id = m.conversation_id WHERE c.is_test = 0",
    )[0][0]
    section("Объём")
    print(f"диалогов: {n_conv}; сообщений: {n_msg}; в среднем {n_msg / n_conv:.1f} сообщ./диалог" if n_conv else "данных нет")
    if not n_conv:
        return

    section("Каналы")
    for ch, n in rows(conn, "SELECT channel, COUNT(*) FROM conversations WHERE is_test = 0 GROUP BY channel"):
        print(f"{ch:10} {n:4} ({n / n_conv:.0%})")

    section("Диалоги по дням (min / max / дней с данными)")
    per_day = rows(
        conn,
        "SELECT substr(started_at, 1, 10) d, COUNT(*) FROM conversations WHERE is_test = 0 GROUP BY d ORDER BY d",
    )
    counts = [n for _, n in per_day]
    print(f"{per_day[0][0]} … {per_day[-1][0]}; дней: {len(per_day)}; в день: min {min(counts)}, max {max(counts)}, среднее {sum(counts) / len(counts):.1f}")

    section("Fallback (ответ бота «нет в базе»)")
    fb_msgs, bot_msgs = rows(
        conn,
        """SELECT SUM(m.is_fallback), COUNT(*) FROM messages m JOIN conversations c ON c.id = m.conversation_id
           WHERE c.is_test = 0 AND m.role = 'assistant'""",
    )[0]
    fb_conv = rows(
        conn,
        """SELECT COUNT(DISTINCT c.id) FROM conversations c JOIN messages m ON m.conversation_id = c.id
           WHERE c.is_test = 0 AND m.is_fallback = 1""",
    )[0][0]
    print(f"доля ответов-fallback: {fb_msgs}/{bot_msgs} = {fb_msgs / bot_msgs:.1%}")
    print(f"доля диалогов с fallback: {fb_conv}/{n_conv} = {fb_conv / n_conv:.1%}")

    section("События")
    mgr, lead, rated = rows(
        conn,
        """SELECT SUM(handed_to_manager), SUM(lead_created), SUM(rating IS NOT NULL)
           FROM conversations WHERE is_test = 0""",
    )[0]
    print(f"передано менеджеру: {mgr} ({mgr / n_conv:.1%}); заявок: {lead} ({lead / n_conv:.1%}); с оценкой: {rated} ({rated / n_conv:.1%})")
    print("оценки:", dict(rows(conn, "SELECT rating, COUNT(*) FROM conversations WHERE rating IS NOT NULL AND is_test = 0 GROUP BY rating")))

    section("Токены и стоимость (у gen_* — оценка, не замер)")
    t_in, t_out, cost, priced = rows(
        conn,
        """SELECT SUM(tokens_in), SUM(tokens_out), SUM(cost_usd), SUM(cost_usd IS NOT NULL)
           FROM messages m JOIN conversations c ON c.id = m.conversation_id WHERE c.is_test = 0""",
    )[0]
    print(f"токенов вход/выход: {t_in}/{t_out}; сообщений со стоимостью: {priced}; сумма: {cost if cost is not None else 'цены не заданы в prices.json'}")

    section("Пустые поля и аномалии")
    problems = {
        "сообщения с пустым текстом": "SELECT COUNT(*) FROM messages WHERE trim(text) = ''",
        "диалоги без сообщений": "SELECT COUNT(*) FROM conversations c WHERE NOT EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id)",
        "диалоги без реплики клиента": "SELECT COUNT(*) FROM conversations c WHERE NOT EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user')",
        "служебные метки [[...]] в тексте": "SELECT COUNT(*) FROM messages WHERE text LIKE '%[[%'",
        "fallback у реплики клиента": "SELECT COUNT(*) FROM messages WHERE role = 'user' AND is_fallback = 1",
        "оценка вне 1..5": "SELECT COUNT(*) FROM conversations WHERE rating IS NOT NULL AND rating NOT BETWEEN 1 AND 5",
    }
    for name, sql in problems.items():
        print(f"{name}: {rows(conn, sql)[0][0]}")

    section("Дубликаты")
    dup_first = rows(
        conn,
        """SELECT lower(trim(text)), COUNT(*) FROM messages m JOIN conversations c ON c.id = m.conversation_id
           WHERE c.is_test = 0 AND m.id = (SELECT MIN(id) FROM messages WHERE conversation_id = c.id)
           GROUP BY 1 HAVING COUNT(*) > 1 ORDER BY 2 DESC LIMIT 5""",
    )
    print(f"повторяющиеся первые реплики клиента: {len(dup_first)}")
    for text, n in dup_first:
        print(f"  {n}× {text[:70]}")
    dup_sess = rows(conn, "SELECT COUNT(*) FROM (SELECT session_id FROM conversations GROUP BY session_id, is_test HAVING COUNT(*) > 1)")[0][0]
    print(f"session_id с несколькими диалогами (реальные сессии >30 мин): {dup_sess}")


if __name__ == "__main__":
    main()
