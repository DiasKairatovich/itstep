"""Оценка качества ответов RAG-бота по тестовому набору tests/test_questions.csv.

Режимы:
  # 1) Оценка стоимости прогона (без платных запросов):
  .venv/bin/python scripts/run_eval.py --label before

  # 2) Реальный запуск замера (вызов бота с is_test=1 + судья OpenAI temperature=0):
  .venv/bin/python scripts/run_eval.py --label before --run
  .venv/bin/python scripts/run_eval.py --label after --run
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analytics import db  # noqa: E402

QUESTIONS_CSV = ROOT / "tests" / "test_questions.csv"
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "gpt-4o-mini")
BOT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
EVAL_PORT = 3499


class JudgeResult(BaseModel):
    verdict: Literal["ok", "partial", "fail"] = Field(
        description=(
            "ok — ответ бота точный, содержит все ключевые факты из expected_points и не выдумывает лишнего; "
            "partial — ответ верный лишь частично (часть фактов упущена или размыта); "
            "fail — бот отказался отвечать («не владею информацией»), дал неверный ответ или противоречит expected_points."
        )
    )
    reason: str = Field(
        description="Одно короткое предложение на русском языке: почему выставлен такой вердикт."
    )


JUDGE_SYSTEM_PROMPT = """Ты — строгий и объективный судья качества ответов RAG-чат-бота кофейни «Coffee Point».
Тебе даны:
1. Вопрос клиента (`question`)
2. Ожидаемые ключевые тезисы ответа (`expected_points`)
3. Фактический ответ бота (`answer`)

Правила оценки (`verdict`):
- `ok`: бот ответил по существу и верно передал все ключевые факты из `expected_points`.
- `partial`: бот дал частично верный ответ по теме, но упустил часть важных деталей из `expected_points`.
- `fail`: бот ответил заглушкой («К сожалению, я не владею такой информацией...», «Я умею отвечать только про Coffee Point...»), ушёл от ответа или назвал факты/цифры, противоречащие `expected_points`.
Поясни решение в `reason` одним коротким предложением."""


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def load_questions() -> list[dict[str, str]]:
    if not QUESTIONS_CSV.exists():
        sys.exit(f"Файл {QUESTIONS_CSV} не найден")
    with QUESTIONS_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def start_eval_server() -> subprocess.Popen:
    env = os.environ.copy()
    env["PORT"] = str(EVAL_PORT)
    env["RPS_LIMIT"] = "500"
    proc = subprocess.Popen(
        ["node", "server/index.js"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    url = f"http://127.0.0.1:{EVAL_PORT}/api/health"
    for _ in range(30):
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code == 200:
                return proc
        except Exception:  # noqa: BLE001
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError("Не удалось поднять локальный сервер бота для eval")


def ask_bot(client: httpx.Client, qid: str, question: str, label: str) -> tuple[str, int, int]:
    res = client.post(
        f"http://127.0.0.1:{EVAL_PORT}/api/chat",
        json={
            "messages": [{"role": "user", "content": question}],
            "session_id": f"eval_{label}_{qid}",
            "channel": "website",
            "is_test": True,
        },
        timeout=30.0,
    )
    res.raise_for_status()
    data = res.json()
    meta = data.get("meta") or {}
    return data["reply"], int(meta.get("tokens_in") or 0), int(meta.get("tokens_out") or 0)


def judge_answer(openai_client, question: str, expected: str, answer: str, model: str) -> tuple[JudgeResult, int, int]:
    user_msg = (
        f"Вопрос клиента: {question}\n"
        f"Ожидаемые тезисы (expected_points): {expected}\n"
        f"Ответ бота: {answer}"
    )
    completion = openai_client.chat.completions.parse(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format=JudgeResult,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Судья не вернул вердикт")
    tin = completion.usage.prompt_tokens if completion.usage else 0
    tout = completion.usage.completion_tokens if completion.usage else 0
    return parsed, tin, tout


def print_summary(conn: sqlite3.Connection, label: str, sample_random: int = 10) -> None:
    rows = conn.execute(
        'SELECT question_id, "group" AS grp, answer, verdict, reason FROM eval_results WHERE run_label = ? ORDER BY question_id',
        (label,),
    ).fetchall()
    if not rows:
        print(f"Нет результатов для метки {label!r}")
        return

    print(f"\n=== ИТОГОВЫЕ ДОЛИ (run_label = {label!r}, всего = {len(rows)}) ===")
    for grp_title, grp_filter in [("Все вопросы", None), ("group = known", "known"), ("group = gap", "gap")]:
        subset = [r for r in rows if grp_filter is None or r["grp"] == grp_filter]
        n = len(subset)
        if not n:
            continue
        ok = sum(1 for r in subset if r["verdict"] == "ok")
        part = sum(1 for r in subset if r["verdict"] == "partial")
        fail = sum(1 for r in subset if r["verdict"] == "fail")
        print(
            f"  {grp_title:15}: N={n:2d} | "
            f"ok={ok:2d} ({ok / n:5.1%}) | partial={part:2d} ({part / n:5.1%}) | fail={fail:2d} ({fail / n:5.1%})"
        )

    q_by_id = {int(q["id"]): q for q in load_questions()}
    rng = random.Random(42)
    sample = rng.sample(list(rows), min(sample_random, len(rows)))
    print(f"\n=== {len(sample)} СЛУЧАЙНЫХ ВЕРДИКТОВ ДЛЯ РУЧНОЙ ПРОВЕРКИ ({label}) ===\n")
    print("| ID | Group | Вопрос | Ответ бота | Вердикт | Причина |")
    print("|---:|---|---|---|---|---|")
    for r in sorted(sample, key=lambda x: x["question_id"]):
        qid = int(r["question_id"])
        q_txt = q_by_id.get(qid, {}).get("question", "").replace("|", "\\|")
        ans_short = r["answer"].replace("\n", " ").strip()
        if len(ans_short) > 110:
            ans_short = ans_short[:107] + "…"
        ans_short = ans_short.replace("|", "\\|")
        reason = r["reason"].replace("|", "\\|")
        print(f"| {qid} | `{r['grp']}` | {q_txt} | {ans_short} | **{r['verdict']}** | {reason} |")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, choices=["before", "after"], help="метка замера: before или after")
    ap.add_argument("--run", action="store_true", help="выполнить платный прогон")
    ap.add_argument("--model", default=JUDGE_MODEL, help="модель судьи")
    args = ap.parse_args()

    load_env()
    db.init_db()
    questions = load_questions()
    n = len(questions)

    unfilled = [q["id"] for q in questions if "[УТОЧНИТЬ" in q.get("expected_points", "")]
    est_bot_in = n * 2100
    est_bot_out = n * 90
    est_judge_in = n * 420
    est_judge_out = n * 45
    est_in = est_bot_in + est_judge_in
    est_out = est_bot_out + est_judge_out
    est_cost = db.cost_usd(args.model, est_in, est_out)
    prices = json.loads((ROOT / "analytics" / "prices.json").read_text(encoding="utf-8")).get(args.model, {})

    print(f"Метка замера: {args.label}; вопросов в {QUESTIONS_CSV.name}: {n}")
    if unfilled:
        print(
            f"[!] Внимание: в {len(unfilled)} вопросах в expected_points ещё осталась метка [УТОЧНИТЬ] "
            f"(ID: {', '.join(unfilled[:10])}{'…' if len(unfilled) > 10 else ''})"
        )
    print(f"Запросов к OpenAI: до {n * 3} ({n} эмбеддингов поиска + до {n} ответов бота + {n} вызовов судьи)")
    print(f"Оценка токенов ({args.model}): вход ~{est_in:,}, выход ~{est_out:,}")
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

    openai_client = OpenAI()
    conn = db.connect()
    with conn:
        conn.execute("DELETE FROM eval_results WHERE run_label = ?", (args.label,))

    server_proc = start_eval_server()
    tok_in = tok_out = 0
    try:
        with httpx.Client() as http_client:
            for idx, q in enumerate(questions, 1):
                qid = int(q["id"])
                grp = q["group"].strip()
                q_text = q["question"].strip()
                expected = q["expected_points"].strip()

                ans, b_in, b_out = ask_bot(http_client, str(qid), q_text, args.label)
                j_res, j_in, j_out = judge_answer(openai_client, q_text, expected, ans, args.model)
                tok_in += b_in + j_in
                tok_out += b_out + j_out

                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                with conn:
                    conn.execute(
                        """INSERT INTO eval_results
                           (run_label, question_id, "group", answer, verdict, reason, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (args.label, qid, grp, ans, j_res.verdict, j_res.reason, now),
                    )
                print(f"[{idx:2d}/{n}] id={qid:2d} ({grp:5s}) -> {j_res.verdict:7s} | {j_res.reason}", flush=True)
    finally:
        server_proc.terminate()
        server_proc.wait(timeout=5)

    cost = db.cost_usd(args.model, tok_in, tok_out)
    print(f"\nФактический расход токенов (бот + судья): вход {tok_in:,}, выход {tok_out:,}; "
          + (f"стоимость: ${cost:.5f}" if cost is not None else "стоимость: цены в prices.json не заданы (null)"))
    print_summary(conn, args.label)


if __name__ == "__main__":
    main()
