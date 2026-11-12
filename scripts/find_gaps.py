"""Поиск и группировка топ-10 пробелов базы знаний по диалогам с is_fallback=1 или not_resolved=1.

Режимы:
  # 1) Оценка стоимости (без платных запросов):
  .venv/bin/python scripts/find_gaps.py

  # 2) Запуск группировки через OpenAI и сохранение топ-10 пробелов:
  .venv/bin/python scripts/find_gaps.py --run
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analytics import db  # noqa: E402

MODEL = os.environ.get("GAPS_MODEL", "gpt-4o-mini")
GAPS_JSON = ROOT / "data" / "top_gaps.json"


class GapItem(BaseModel):
    rank: int = Field(description="Место в рейтинге от 1 до 10 по убыванию частоты.")
    formulation: str = Field(
        description="Чёткая обобщённая формулировка пробела в базе знаний (о чём спрашивают клиенты)."
    )
    count: int = Field(
        description="Количество вопросов/диалогов из входного списка, относящихся к этой группе."
    )
    example_1: str = Field(description="Первый дословный пример вопроса клиента из списка.")
    example_2: str = Field(description="Второй дословный пример вопроса клиента из списка.")


class TopGapsResponse(BaseModel):
    gaps: list[GapItem] = Field(
        description="Ровно 10 главных смысловых групп пробелов базы знаний, отсортированных по убыванию count."
    )


SYSTEM_PROMPT = """Ты — продуктовый аналитик базы знаний RAG-чат-бота кофейни «Coffee Point».
Тебе передан список реплик клиентов из диалогов, где бот не нашёл ответа в базе знаний (`is_fallback=1`) или не смог решить вопрос клиента (`not_resolved=1`).

Твоя задача:
1. Сгруппировать эти вопросы по смыслу в **топ-10 пробелов базы знаний** — тем и вопросов, по которым боту не хватает справочной информации или чёткого регламента ответа (например: альтернативное/безлактозное молоко и добавки/сиропы; десерты без сахара/глютена и расширенный ассортимент выпечки; регламент при задержке заказа/доставки и холодном напитке; состав, КБЖУ и сроки хранения; заказ навынос и способы оплаты картой; напитки без кофеина и чай; торты на заказ и их вкусы/ассортимент; актуальные акции и скидки; вопросы о вакансиях и др.).
2. Для каждой из 10 групп указать:
   - `rank`: порядковый номер 1..10 (по убыванию `count`);
   - `formulation`: краткая и понятная формулировка пробела;
   - `count`: сколько элементов входного списка относится к этой группе;
   - `example_1` и `example_2`: 2 реальных (дословных) примера вопросов клиентов из входного списка.
3. Не выдумывай примеры, которых нет во входном списке."""


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def collect_problem_questions(conn: sqlite3.Connection) -> list[dict]:
    """Собирает реплики клиентов из диалогов с is_fallback=1 или not_resolved=1 (is_test=0)."""
    sql = """
        SELECT
            c.id AS conv_id,
            COALESCE(ca.topic, '') AS topic,
            COALESCE(ca.intent, '') AS intent,
            COALESCE(ca.not_resolved, 0) AS not_resolved,
            MAX(CASE WHEN m.role = 'assistant' THEN m.is_fallback ELSE 0 END) AS has_fallback,
            GROUP_CONCAT(CASE WHEN m.role = 'user' THEN m.text END, ' // ') AS user_text
        FROM conversations c
        JOIN messages m ON m.conversation_id = c.id
        LEFT JOIN conversation_analysis ca ON ca.conversation_id = c.id
        WHERE c.is_test = 0
        GROUP BY c.id
        HAVING has_fallback = 1 OR COALESCE(ca.not_resolved, 0) = 1
        ORDER BY c.id
    """
    rows = conn.execute(sql).fetchall()
    return [
        {
            "conv_id": r["conv_id"],
            "topic": r["topic"],
            "fallback": bool(r["has_fallback"]),
            "not_resolved": bool(r["not_resolved"]),
            "questions": r["user_text"],
        }
        for r in rows
        if r["user_text"]
    ]


def save_gaps(conn: sqlite3.Connection, gaps: list[GapItem]) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute("DELETE FROM knowledge_gaps")
        for g in gaps:
            conn.execute(
                """INSERT INTO knowledge_gaps (rank, gap_title, count, example_1, example_2, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (g.rank, g.formulation, g.count, g.example_1, g.example_2, now),
            )
    GAPS_JSON.parent.mkdir(parents=True, exist_ok=True)
    GAPS_JSON.write_text(
        json.dumps([g.model_dump() for g in gaps], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="выполнить платный запрос к OpenAI")
    ap.add_argument("--model", default=MODEL, help="модель OpenAI")
    args = ap.parse_args()

    load_env()
    db.init_db()
    conn = db.connect()

    items = collect_problem_questions(conn)
    payload_text = "\n".join(
        f"[{it['conv_id']}] (topic={it['topic']}, fb={int(it['fallback'])}, nr={int(it['not_resolved'])}): {it['questions']}"
        for it in items
    )

    est_in = 700 + len(payload_text) // 2
    est_out = 900
    est_cost = db.cost_usd(args.model, est_in, est_out)
    prices = json.loads((ROOT / "analytics" / "prices.json").read_text(encoding="utf-8")).get(args.model, {})

    print(f"Найдено проблемных диалогов (is_fallback=1 или not_resolved=1): {len(items)}")
    print(f"Модель: {args.model}; запросов к OpenAI: 1")
    print(f"Оценка токенов: вход ~{est_in:,}, выход ~{est_out:,}")
    if est_cost is not None:
        print(f"Оценка стоимости: ~${est_cost:.5f}")
    else:
        print(
            f"Оценка стоимости: цены не заданы в analytics/prices.json ({prices}); "
            "формула = вход/1e6 * цена_вх + выход/1e6 * цена_вых"
        )

    if not args.run:
        print("\nРежим оценки: запросов к OpenAI НЕ было. Для запуска добавьте --run")
        return

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY не задан в .env")

    from openai import OpenAI

    client = OpenAI()
    completion = client.chat.completions.parse(
        model=args.model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Список вопросов из проблемных диалогов ({len(items)} шт.):\n\n{payload_text}"},
        ],
        response_format=TopGapsResponse,
    )
    parsed = completion.choices[0].message.parsed
    if not parsed or not parsed.gaps:
        sys.exit("Модель не вернула список пробелов")

    t_in = completion.usage.prompt_tokens if completion.usage else 0
    t_out = completion.usage.completion_tokens if completion.usage else 0
    cost = db.cost_usd(args.model, t_in, t_out)

    save_gaps(conn, parsed.gaps)

    print(f"\nФактический расход: вход {t_in:,}, выход {t_out:,} токенов; "
          + (f"стоимость: ${cost:.5f}" if cost is not None else "стоимость: цены в prices.json не заданы (null)"))
    print("\n=== ТОП-10 ПРОБЕЛОВ БАЗЫ ЗНАНИЙ ===\n")
    print("| # | Формулировка пробела | Кол-во | Пример 1 | Пример 2 |")
    print("|---:|---|---:|---|---|")
    for g in parsed.gaps:
        print(f"| {g.rank} | {g.formulation} | {g.count} | {g.example_1} | {g.example_2} |")


if __name__ == "__main__":
    main()
