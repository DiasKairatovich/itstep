"""ИИ-разметка диалогов из analytics.db (таблица conversation_analysis).

Режимы:
  # 1) Оценка стоимости на 20 случайных диалогах (без платных запросов):
  .venv/bin/python scripts/analyze_all.py --sample-20

  # 2) Прогон на 20 случайных диалогах и вывод таблицы «диалог | разметка»:
  .venv/bin/python scripts/analyze_all.py --sample-20 --run

  # 3) Оценка стоимости полной разметки всех неразмеченных диалогов (is_test=0):
  .venv/bin/python scripts/analyze_all.py

  # 4) Полная разметка (с записью в conversation_analysis, пропуском уже размеченных):
  .venv/bin/python scripts/analyze_all.py --run [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analytics import classifier, db  # noqa: E402

SAMPLE_IDS_FILE = ROOT / "data" / "sample_20_ids.json"
# Оценка по фактическому пробному прогону на 20 диалогах: ~2380 вх. и ~42 вых. токенов на диалог
EST_SYS_TOKENS = 2300
EST_OUT_TOKENS = 42
SEED = 42


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def fetch_messages(conn: sqlite3.Connection, conv_id: int) -> list[dict[str, str]]:
    rows = conn.execute(
        "SELECT role, text FROM messages WHERE conversation_id = ? ORDER BY id",
        (conv_id,),
    ).fetchall()
    return [{"role": r["role"], "text": r["text"]} for r in rows]


def get_sample_20_ids(conn: sqlite3.Connection, reset_sample: bool = False) -> list[int]:
    """Возвращает фиксированный список из 20 случайных conversation_id (is_test=0),
    чтобы после правок промпта повторный прогон шёл на ТЕХ ЖЕ 20 диалогах.
    """
    if SAMPLE_IDS_FILE.exists() and not reset_sample:
        ids = json.loads(SAMPLE_IDS_FILE.read_text(encoding="utf-8"))
        if isinstance(ids, list) and len(ids) == 20:
            return [int(x) for x in ids]

    all_ids = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM conversations WHERE is_test = 0 ORDER BY id"
        ).fetchall()
    ]
    rng = random.Random(SEED)
    chosen = sorted(rng.sample(all_ids, min(20, len(all_ids))))
    SAMPLE_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_IDS_FILE.write_text(json.dumps(chosen), encoding="utf-8")
    return chosen


def get_unlabeled_ids(conn: sqlite3.Connection, limit: int | None) -> list[int]:
    sql = """
        SELECT c.id
        FROM conversations c
        LEFT JOIN conversation_analysis ca ON ca.conversation_id = c.id
        WHERE c.is_test = 0 AND ca.conversation_id IS NULL
        ORDER BY c.id
    """
    if limit is not None and limit > 0:
        sql += f" LIMIT {int(limit)}"
    return [r[0] for r in conn.execute(sql).fetchall()]


def estimate_cost(conn: sqlite3.Connection, conv_ids: list[int], model: str) -> tuple[int, int, float | None]:
    total_chars = 0
    for cid in conv_ids:
        for m in fetch_messages(conn, cid):
            total_chars += len(m["text"])
    est_in = len(conv_ids) * EST_SYS_TOKENS + max(1, total_chars // 2)
    est_out = len(conv_ids) * EST_OUT_TOKENS
    return est_in, est_out, db.cost_usd(model, est_in, est_out)


def classify_with_retry(
    client,
    messages: list[dict[str, str]],
    model: str,
    retries: int = 3,
):
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return classifier.classify_conversation(messages, client=client, model=model)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                wait = 2 * attempt
                print(f"  [повтор {attempt}/{retries} через {wait}с: {type(exc).__name__}: {exc}]", flush=True)
                time.sleep(wait)
    raise RuntimeError(f"Не удалось классифицировать после {retries} попыток: {last_exc}")


def save_analysis(
    conn: sqlite3.Connection,
    conv_id: int,
    res: classifier.ConversationAnalysis,
    model: str,
    t_in: int,
    t_out: int,
    cost: float | None,
) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO conversation_analysis
           (conversation_id, topic, intent, sentiment, not_resolved, short_reason,
            model, tokens_in, tokens_out, cost_usd, analyzed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(conversation_id) DO UPDATE SET
             topic = excluded.topic,
             intent = excluded.intent,
             sentiment = excluded.sentiment,
             not_resolved = excluded.not_resolved,
             short_reason = excluded.short_reason,
             model = excluded.model,
             tokens_in = excluded.tokens_in,
             tokens_out = excluded.tokens_out,
             cost_usd = excluded.cost_usd,
             analyzed_at = excluded.analyzed_at
        """,
        (
            conv_id,
            res.topic,
            res.intent,
            res.sentiment,
            int(res.not_resolved),
            res.short_reason,
            model,
            t_in,
            t_out,
            cost,
            now,
        ),
    )


def short_dialog_preview(messages: list[dict[str, str]], max_len: int = 180) -> str:
    parts = []
    for m in messages:
        prefix = "К:" if m["role"] == "user" else "Б:"
        txt = m["text"].replace("\n", " ").strip()
        if len(txt) > 80:
            txt = txt[:77] + "…"
        parts.append(f"{prefix} {txt}")
    joined = " / ".join(parts)
    return (joined[: max_len - 1] + "…") if len(joined) > max_len else joined


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-20", action="store_true", help="прогон/оценка на 20 случайных диалогах с таблицей")
    ap.add_argument("--reset-sample", action="store_true", help="перевыбрать 20 случайных диалогов")
    ap.add_argument("--limit", type=int, default=None, help="максимум диалогов для разметки")
    ap.add_argument("--run", action="store_true", help="выполнить платные запросы к OpenAI")
    ap.add_argument("--model", default=classifier.MODEL, help="модель OpenAI")
    args = ap.parse_args()

    load_env()
    db.init_db()
    conn = db.connect()

    if args.sample_20:
        target_ids = get_sample_20_ids(conn, reset_sample=args.reset_sample)
        mode_title = "Пробная разметка 20 случайных диалогов (--sample-20)"
    else:
        target_ids = get_unlabeled_ids(conn, args.limit)
        mode_title = f"Разметка неразмеченных диалогов (is_test=0, limit={args.limit or 'все'})"

    est_in, est_out, est_cost = estimate_cost(conn, target_ids, args.model)
    prices = json.loads((ROOT / "analytics" / "prices.json").read_text(encoding="utf-8")).get(args.model, {})

    print(f"Режим: {mode_title}")
    print(f"Модель: {args.model}; диалогов (запросов к API): {len(target_ids)}")
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

    if not target_ids:
        print("Нет диалогов для обработки.")
        return

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY не задан в .env")

    from openai import OpenAI

    client = OpenAI()
    processed = errors = tok_in = tok_out = 0
    table_rows: list[tuple[int, str, classifier.ConversationAnalysis]] = []

    for idx, cid in enumerate(target_ids, 1):
        msgs = fetch_messages(conn, cid)
        try:
            res, tin, tout, cost = classify_with_retry(client, msgs, args.model)
            tok_in += tin
            tok_out += tout
            processed += 1
            with conn:
                save_analysis(conn, cid, res, args.model, tin, tout, cost)
            if args.sample_20:
                table_rows.append((cid, short_dialog_preview(msgs), res))
            print(
                f"[{idx}/{len(target_ids)}] id={cid}: topic={res.topic}, intent={res.intent}, "
                f"sentiment={res.sentiment}, not_resolved={res.not_resolved} ({tin}+{tout} tok)",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"[{idx}/{len(target_ids)}] id={cid}: ОШИБКА — {exc}", flush=True)

    total_cost = db.cost_usd(args.model, tok_in, tok_out)
    print("\n=== ИТОГ ===")
    print(f"Обработано: {processed}; ошибок: {errors}")
    print(
        f"Токены: вход {tok_in:,}, выход {tok_out:,}; "
        + (f"стоимость: ${total_cost:.5f}" if total_cost is not None else "стоимость: цены в prices.json не заданы (null)")
    )

    if args.sample_20 and table_rows:
        print("\n=== ТАБЛИЦА «ДИАЛОГ | РАЗМЕТКА» (20 случайных диалогов) ===\n")
        print("| ID | Диалог | Разметка |")
        print("|---:|---|---|")
        for cid, preview, r in table_rows:
            preview_esc = preview.replace("|", "\\|")
            label = (
                f"**topic**: `{r.topic}`<br>"
                f"**intent**: `{r.intent}`<br>"
                f"**sentiment**: `{r.sentiment}`<br>"
                f"**not_resolved**: `{r.not_resolved}`<br>"
                f"*{r.short_reason}*"
            ).replace("|", "\\|")
            print(f"| {cid} | {preview_esc} | {label} |")


if __name__ == "__main__":
    main()
