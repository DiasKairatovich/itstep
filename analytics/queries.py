"""SQL-запросы аналитики для дашборда (только чтение, исключая is_test=1).

Все функции принимают параметры фильтрации:
  - date_from: начальная дата YYYY-MM-DD (включительно) или None
  - date_to:   конечная дата YYYY-MM-DD (включительно) или None
  - channel:   'website', 'telegram' или None / 'all' (все каналы)
и возвращают pandas.DataFrame.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from analytics import db

# Демо-заглушки коэффициентов (USD за 1M токенов) на случай, если в analytics/prices.json
# стоят null, чтобы карточка и график «Средняя стоимость диалога» отображали данные.
DEMO_INPUT_PER_1M = 1.0
DEMO_OUTPUT_PER_1M = 1.0


def _ro_connect() -> sqlite3.Connection:
    path = db.db_path()
    if not path.exists():
        raise FileNotFoundError(f"База данных {path} ещё не создана.")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def price_rates(model: str = "gpt-4o-mini") -> tuple[float, float, bool]:
    """Возвращает (in_rate_per_1m, out_rate_per_1m, is_placeholder).

    Если пользователь заполнил analytics/prices.json — берём его числа.
    Если там null — используем демо-заглушку, чтобы дашборд показывал метрику стоимости.
    """
    try:
        raw = json.loads(db.PRICES_FILE.read_text(encoding="utf-8")).get(model) or {}
        p_in, p_out = raw.get("input_per_1m_usd"), raw.get("output_per_1m_usd")
        if p_in is not None and p_out is not None:
            return float(p_in), float(p_out), False
    except Exception:  # noqa: BLE001
        pass
    return DEMO_INPUT_PER_1M, DEMO_OUTPUT_PER_1M, True


def _where_clause(
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
    alias: str = "c",
) -> tuple[str, list[object]]:
    conds = [f"{alias}.is_test = 0"]
    params: list[object] = []
    if date_from:
        conds.append(f"substr({alias}.started_at, 1, 10) >= ?")
        params.append(str(date_from)[:10])
    if date_to:
        conds.append(f"substr({alias}.started_at, 1, 10) <= ?")
        params.append(str(date_to)[:10])
    if channel and channel not in ("all", "Все"):
        conds.append(f"{alias}.channel = ?")
        params.append(channel)
    return " AND ".join(conds), params


def get_date_bounds() -> tuple[str | None, str | None]:
    """Минимальная и максимальная даты диалогов (is_test=0)."""
    try:
        with _ro_connect() as conn:
            row = conn.execute(
                "SELECT MIN(substr(started_at, 1, 10)), MAX(substr(started_at, 1, 10)) "
                "FROM conversations WHERE is_test = 0"
            ).fetchone()
            return (row[0], row[1]) if row else (None, None)
    except Exception:  # noqa: BLE001
        return None, None


def get_kpis(
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
) -> pd.DataFrame:
    """Сводные метрики для верхних карточек дашборда (1 строка DataFrame)."""
    where, params = _where_clause(date_from, date_to, channel, alias="c")
    p_in, p_out, is_placeholder = price_rates()
    sql = f"""
        WITH conv_stats AS (
            SELECT
                c.id,
                c.lead_created,
                ca.not_resolved,
                COALESCE(MAX(CASE WHEN m.role = 'assistant' THEN m.is_fallback ELSE 0 END), 0) AS has_fallback,
                SUM(
                    COALESCE(
                        m.cost_usd,
                        (COALESCE(m.tokens_in, 0) * ? + COALESCE(m.tokens_out, 0) * ?) / 1000000.0
                    )
                ) AS msg_cost_usd,
                COALESCE(
                    ca.cost_usd,
                    (COALESCE(ca.tokens_in, 0) * ? + COALESCE(ca.tokens_out, 0) * ?) / 1000000.0
                ) AS analysis_cost_usd
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            LEFT JOIN conversation_analysis ca ON ca.conversation_id = c.id
            WHERE {where}
            GROUP BY c.id
        )
        SELECT
            COUNT(*) AS total_dialogs,
            AVG(CASE WHEN not_resolved IS NOT NULL THEN (1.0 - not_resolved) END) AS resolved_share,
            AVG(CAST(has_fallback AS REAL)) AS fallback_share,
            AVG(CAST(lead_created AS REAL)) AS lead_conversion,
            AVG(COALESCE(msg_cost_usd, 0.0) + COALESCE(analysis_cost_usd, 0.0)) AS avg_dialog_cost_usd
        FROM conv_stats
    """
    full_params = [p_in, p_out, p_in, p_out, *params]
    with _ro_connect() as conn:
        df = pd.read_sql_query(sql, conn, params=full_params)
    df["is_price_placeholder"] = is_placeholder
    return df


def get_top_topics(
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
) -> pd.DataFrame:
    """Топ тем диалогов из conversation_analysis."""
    where, params = _where_clause(date_from, date_to, channel, alias="c")
    sql = f"""
        SELECT
            COALESCE(ca.topic, 'не размечено') AS topic,
            COUNT(*) AS dialogs,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct,
            SUM(CASE WHEN ca.not_resolved = 1 THEN 1 ELSE 0 END) AS unresolved_dialogs
        FROM conversations c
        LEFT JOIN conversation_analysis ca ON ca.conversation_id = c.id
        WHERE {where}
        GROUP BY COALESCE(ca.topic, 'не размечено')
        ORDER BY dialogs DESC
    """
    with _ro_connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_dialogs_by_day(
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
) -> pd.DataFrame:
    """Динамика числа диалогов по дням."""
    where, params = _where_clause(date_from, date_to, channel, alias="c")
    sql = f"""
        SELECT
            substr(c.started_at, 1, 10) AS day,
            COUNT(*) AS dialogs,
            SUM(CASE WHEN c.channel = 'website' THEN 1 ELSE 0 END) AS website_dialogs,
            SUM(CASE WHEN c.channel = 'telegram' THEN 1 ELSE 0 END) AS telegram_dialogs
        FROM conversations c
        WHERE {where}
        GROUP BY day
        ORDER BY day
    """
    with _ro_connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_unresolved_and_fallback_by_day(
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
) -> pd.DataFrame:
    """Доля fallback и доля not_resolved по дням (в процентах 0..100)."""
    where, params = _where_clause(date_from, date_to, channel, alias="c")
    sql = f"""
        WITH per_conv AS (
            SELECT
                c.id,
                substr(c.started_at, 1, 10) AS day,
                COALESCE(MAX(CASE WHEN m.role = 'assistant' THEN m.is_fallback ELSE 0 END), 0) AS has_fallback,
                ca.not_resolved AS not_resolved
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            LEFT JOIN conversation_analysis ca ON ca.conversation_id = c.id
            WHERE {where}
            GROUP BY c.id
        )
        SELECT
            day,
            COUNT(*) AS dialogs,
            ROUND(100.0 * AVG(CAST(has_fallback AS REAL)), 1) AS fallback_pct,
            ROUND(100.0 * AVG(CAST(not_resolved AS REAL)), 1) AS not_resolved_pct
        FROM per_conv
        GROUP BY day
        ORDER BY day
    """
    with _ro_connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_funnel(
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
) -> pd.DataFrame:
    """Воронка: все диалоги → ready_to_buy → lead_created=1."""
    where, params = _where_clause(date_from, date_to, channel, alias="c")
    sql = f"""
        SELECT
            COUNT(*) AS all_dialogs,
            SUM(CASE WHEN ca.intent = 'ready_to_buy' OR c.lead_created = 1 THEN 1 ELSE 0 END) AS ready_to_buy,
            SUM(CASE WHEN c.lead_created = 1 THEN 1 ELSE 0 END) AS lead_created
        FROM conversations c
        LEFT JOIN conversation_analysis ca ON ca.conversation_id = c.id
        WHERE {where}
    """
    with _ro_connect() as conn:
        row = conn.execute(sql, params).fetchone()
    total = int(row["all_dialogs"] or 0) if row else 0
    ready = int(row["ready_to_buy"] or 0) if row else 0
    leads = int(row["lead_created"] or 0) if row else 0
    stages = [
        {"stage": "1. Все диалоги", "dialogs": total, "share_pct": 100.0 if total else 0.0},
        {
            "stage": "2. Готовы купить (ready_to_buy)",
            "dialogs": ready,
            "share_pct": round(100.0 * ready / total, 1) if total else 0.0,
        },
        {
            "stage": "3. Оставили заявку (lead_created=1)",
            "dialogs": leads,
            "share_pct": round(100.0 * leads / total, 1) if total else 0.0,
        },
    ]
    return pd.DataFrame(stages)


def get_avg_cost_by_day(
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
) -> pd.DataFrame:
    """Средняя стоимость диалога (и среднее число токенов) по дням."""
    where, params = _where_clause(date_from, date_to, channel, alias="c")
    p_in, p_out, _ = price_rates()
    sql = f"""
        WITH per_conv AS (
            SELECT
                c.id,
                substr(c.started_at, 1, 10) AS day,
                c.channel,
                COALESCE(SUM(m.tokens_in), 0) + COALESCE(ca.tokens_in, 0) AS tokens_in,
                COALESCE(SUM(m.tokens_out), 0) + COALESCE(ca.tokens_out, 0) AS tokens_out,
                SUM(
                    COALESCE(
                        m.cost_usd,
                        (COALESCE(m.tokens_in, 0) * ? + COALESCE(m.tokens_out, 0) * ?) / 1000000.0
                    )
                ) + COALESCE(
                    ca.cost_usd,
                    (COALESCE(ca.tokens_in, 0) * ? + COALESCE(ca.tokens_out, 0) * ?) / 1000000.0
                ) AS dialog_cost_usd
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            LEFT JOIN conversation_analysis ca ON ca.conversation_id = c.id
            WHERE {where}
            GROUP BY c.id
        )
        SELECT
            day,
            COUNT(*) AS dialogs,
            ROUND(AVG(dialog_cost_usd), 5) AS avg_cost_usd,
            ROUND(AVG(tokens_in + tokens_out), 0) AS avg_tokens
        FROM per_conv
        GROUP BY day
        ORDER BY day
    """
    full_params = [p_in, p_out, p_in, p_out, *params]
    with _ro_connect() as conn:
        return pd.read_sql_query(sql, conn, params=full_params)


def get_top_gaps() -> pd.DataFrame:
    """Топ-10 пробелов базы знаний, сохранённых скриптом scripts/find_gaps.py."""
    try:
        with _ro_connect() as conn:
            return pd.read_sql_query(
                "SELECT rank, gap_title, count, example_1, example_2 FROM knowledge_gaps ORDER BY rank",
                conn,
            )
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["rank", "gap_title", "count", "example_1", "example_2"])

