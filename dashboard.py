"""Дашборд аналитики RAG-чат-бота кофейни Coffee Point (Streamlit).

Запуск:
    .venv/bin/streamlit run dashboard.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from analytics import queries

st.set_page_config(
    page_title="Coffee Point — Аналитика RAG-бота",
    page_icon="☕",
    layout="wide",
)

TOPIC_LABELS = {
    "menu_prices": "Меню и цены (menu_prices)",
    "hours_location": "Часы работы и адрес (hours_location)",
    "delivery": "Доставка (delivery)",
    "loyalty_promos": "Лояльность и акции (loyalty_promos)",
    "preorders_events": "Предзаказы и бронь (preorders_events)",
    "complaints_refunds": "Жалобы и возвраты (complaints_refunds)",
    "unknown_product_info": "Пробелы БЗ (unknown_product_info)",
    "smalltalk_other": "Разговорное / прочее (smalltalk_other)",
    "не размечено": "Не размечено",
}


@st.cache_data(ttl=15)
def load_bounds() -> tuple[str | None, str | None]:
    return queries.get_date_bounds()


@st.cache_data(ttl=15)
def load_dashboard_data(
    date_from: str | None,
    date_to: str | None,
    channel: str | None,
) -> dict[str, pd.DataFrame]:
    return {
        "kpis": queries.get_kpis(date_from, date_to, channel),
        "topics": queries.get_top_topics(date_from, date_to, channel),
        "by_day": queries.get_dialogs_by_day(date_from, date_to, channel),
        "quality_by_day": queries.get_unresolved_and_fallback_by_day(date_from, date_to, channel),
        "funnel": queries.get_funnel(date_from, date_to, channel),
        "cost_by_day": queries.get_avg_cost_by_day(date_from, date_to, channel),
        "gaps": queries.get_top_gaps(),
        "eval_summary": queries.get_eval_summary(),
        "eval_changes": queries.get_eval_changes(),
    }


def main() -> None:
    st.title("☕ Coffee Point — Аналитика диалогов RAG-бота")
    st.caption("Данные из `data/analytics.db` (только чтение, тестовые прогоны `is_test=1` исключены).")

    min_d, max_d = load_bounds()
    if not min_d or not max_d:
        st.warning("В базе данных `data/analytics.db` пока нет нетестовых диалогов (`is_test=0`).")
        return

    # ---------------- Боковая панель фильтров ----------------
    with st.sidebar:
        st.header("Фильтры")
        d_min = date.fromisoformat(min_d)
        d_max = date.fromisoformat(max_d)
        date_range = st.date_input(
            "Период (started_at)",
            value=(d_min, d_max),
            min_value=d_min,
            max_value=d_max,
        )
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            date_from, date_to = date_range[0].isoformat(), date_range[1].isoformat()
        elif isinstance(date_range, (tuple, list)) and len(date_range) == 1:
            date_from = date_to = date_range[0].isoformat()
        else:
            date_from = date_to = str(date_range)

        channel_opt = st.selectbox(
            "Канал",
            options=["all", "website", "telegram"],
            format_func=lambda x: {"all": "Все каналы", "website": "Сайт (website)", "telegram": "Telegram"}[x],
        )

    data = load_dashboard_data(date_from, date_to, channel_opt)
    kpis = data["kpis"]
    total_dialogs = int(kpis["total_dialogs"].iloc[0] or 0) if not kpis.empty else 0

    if total_dialogs == 0:
        st.info("За выбранный период и канал диалогов не найдено. Измените фильтры в боковой панели.")
        return

    resolved_share = kpis["resolved_share"].iloc[0]
    fallback_share = float(kpis["fallback_share"].iloc[0] or 0.0)
    lead_conv = float(kpis["lead_conversion"].iloc[0] or 0.0)
    avg_cost = float(kpis["avg_dialog_cost_usd"].iloc[0] or 0.0)
    is_placeholder = bool(kpis["is_price_placeholder"].iloc[0])

    # ---------------- 5 карточек KPI сверху ----------------
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Всего диалогов", f"{total_dialogs}")
    c2.metric(
        "Доля решённых",
        f"{resolved_share * 100:.1f}%" if pd.notna(resolved_share) else "н/д",
    )
    c3.metric("Доля fallback", f"{fallback_share * 100:.1f}%")
    c4.metric("Конверсия в заявку", f"{lead_conv * 100:.1f}%")
    c5.metric(
        "Средняя стоимость диалога",
        f"${avg_cost:.4f}" + (" *" if is_placeholder else ""),
        help="Считается по токенам сообщений и разметки. * — если в analytics/prices.json стоят null, используется демо-тариф $1 / 1M токенов.",
    )
    if is_placeholder:
        st.caption("* В `analytics/prices.json` цены пока оставлены как `null`-заглушки — для наглядности стоимость на графиках рассчитана по условному демо-коэффициенту `$1.00 / 1M токенов`.")

    st.divider()

    # ---------------- 5 виджетов аналитики ----------------
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("1. Топ тем обращений")
        topics_df = data["topics"].copy()
        topics_df["Тема"] = topics_df["topic"].map(lambda t: TOPIC_LABELS.get(t, t))
        st.bar_chart(topics_df.set_index("Тема")["dialogs"], horizontal=True)
        st.dataframe(
            topics_df[["Тема", "dialogs", "share_pct", "unresolved_dialogs"]].rename(
                columns={
                    "dialogs": "Диалогов",
                    "share_pct": "Доля, %",
                    "unresolved_dialogs": "Не решено (not_resolved)",
                }
            ),
            width="stretch",
            hide_index=True,
        )

    with col_right:
        st.subheader("2. Динамика числа диалогов по дням")
        by_day_df = data["by_day"].copy()
        if channel_opt == "all":
            st.bar_chart(
                by_day_df.set_index("day")[["website_dialogs", "telegram_dialogs"]].rename(
                    columns={"website_dialogs": "Website", "telegram_dialogs": "Telegram"}
                )
            )
        else:
            st.bar_chart(by_day_df.set_index("day")[["dialogs"]].rename(columns={"dialogs": "Диалогов"}))

    col_q, col_f = st.columns(2)

    with col_q:
        st.subheader("3. Доля fallback и доля not_resolved по дням (%)")
        q_df = data["quality_by_day"].copy()
        st.line_chart(
            q_df.set_index("day")[["fallback_pct", "not_resolved_pct"]].rename(
                columns={"fallback_pct": "Fallback, %", "not_resolved_pct": "Not resolved, %"}
            )
        )

    with col_f:
        st.subheader("4. Воронка конверсии")
        funnel_df = data["funnel"].copy()
        st.bar_chart(funnel_df.set_index("stage")["dialogs"])
        st.dataframe(
            funnel_df.rename(columns={"stage": "Этап", "dialogs": "Диалогов", "share_pct": "Конверсия от всех, %"}),
            width="stretch",
            hide_index=True,
        )

    st.subheader("5. Средняя стоимость диалога и расход токенов по дням")
    cost_df = data["cost_by_day"].copy()
    c_cost1, c_cost2 = st.columns(2)
    with c_cost1:
        st.line_chart(
            cost_df.set_index("day")[["avg_cost_usd"]].rename(columns={"avg_cost_usd": "Средняя стоимость, USD"})
        )
    with c_cost2:
        st.bar_chart(
            cost_df.set_index("day")[["avg_tokens"]].rename(columns={"avg_tokens": "Среднее число токенов на диалог"})
        )

    st.divider()
    st.subheader("6. Топ пробелов базы знаний (is_fallback=1 / not_resolved=1)")
    gaps_df = data["gaps"].copy()
    if gaps_df.empty:
        st.info("Топ пробелов ещё не сформирован. Запустите `python scripts/find_gaps.py --run`.")
    else:
        st.dataframe(
            gaps_df.rename(
                columns={
                    "rank": "#",
                    "gap_title": "Формулировка пробела",
                    "count": "Количество",
                    "example_1": "Пример 1",
                    "example_2": "Пример 2",
                }
            ),
            width="stretch",
            hide_index=True,
        )

    st.divider()
    st.subheader("7. Сравнение качества бота «До / После» (eval_results)")
    eval_sum = data["eval_summary"].copy()
    eval_chg = data["eval_changes"].copy()
    if eval_sum.empty:
        st.info("Замеры `before` / `after` ещё не проведены. Запустите `scripts/run_eval.py`.")
    else:
        c_ev1, c_ev2 = st.columns(2)
        with c_ev1:
            st.markdown("**Доли `ok` / `partial` / `fail` по группам (%)**")
            st.dataframe(
                eval_sum.rename(
                    columns={
                        "run_label": "Замер",
                        "scope": "Выборка",
                        "n": "N",
                        "ok_cnt": "ok",
                        "ok_pct": "ok, %",
                        "partial_cnt": "partial",
                        "partial_pct": "partial, %",
                        "fail_cnt": "fail",
                        "fail_pct": "fail, %",
                    }
                ),
                width="stretch",
                hide_index=True,
            )
        with c_ev2:
            st.markdown("**Рост доли `ok` (%) До vs После**")
            piv = eval_sum.pivot(index="scope", columns="run_label", values="ok_pct")
            cols_order = [c for c in ("before", "after") if c in piv.columns]
            st.bar_chart(piv[cols_order])

        if not eval_chg.empty:
            better = eval_chg[eval_chg["status"] == "Стало лучше"]
            worse = eval_chg[eval_chg["status"] == "Стало хуже"]
            st.markdown(
                f"**Изменения по вопросам:** стало лучше — **{len(better)}**, "
                f"стало хуже — **{len(worse)}**, без изменений — **{len(eval_chg) - len(better) - len(worse)}**."
            )
            st.dataframe(
                eval_chg.rename(
                    columns={
                        "question_id": "ID",
                        "grp": "Группа",
                        "question": "Вопрос",
                        "verdict_before": "До (before)",
                        "verdict_after": "После (after)",
                        "status": "Динамика",
                        "reason_after": "Комментарий судьи (after)",
                    }
                ),
                width="stretch",
                hide_index=True,
            )


if __name__ == "__main__":
    main()
