"""Генерация синтетических диалогов клиентов в analytics.db (is_test=0).

Режимы:
  python scripts/generate_dialogs.py            # ТОЛЬКО план и оценка стоимости, запросов к OpenAI нет
  python scripts/generate_dialogs.py --run      # реальная генерация (платно!)
  python scripts/generate_dialogs.py --run --limit 15   # пробный прогон на одном батче

Диалоги пишутся «целиком» (реплики клиента и бота): так дешевле, чем гонять
реплики через настоящего бота. Ответы бота модель пишет только по базе знаний
(knowledge + документы из data/rag.db), поэтому цен и сроков не выдумывает.
Для «ответа нет в базе» скрипт сам подставляет настоящую фразу NO_ANSWER.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analytics import db  # noqa: E402

# ---------------------------------------------------------------- настройки
TOTAL = 250
BATCH = 15
MODEL = os.environ.get("GEN_MODEL", "gpt-4o-mini")
SEED = 42
DAYS = 30

MIX = {"normal": 0.60, "no_answer": 0.20, "complaint": 0.10, "lead": 0.10}
STYLES = ["короткие реплики", "с опечатками", "вежливый", "раздражённый", "разговорный", "деловой"]
CHANNEL_SHARE_TELEGRAM = 0.4
RATING_SHARE = 0.35          # доля диалогов с оценкой
COMPLAINT_HANDOFF = 0.5      # доля жалоб, переданных менеджеру
MAX_USER_TURNS = 3           # 1..3 реплики клиента => 2..6 сообщений в диалоге

# Токены/стоимость синтетических ответов бота — ОЦЕНКА (бот не вызывался).
CHAT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # модель, цену которой применяем
FALLBACK_PROMPT_TOKENS = 1850  # замер tokens_in реального ответа бота в Фазе 1
CHARS_PER_TOKEN = 3            # грубо для русского текста с разметкой

# Оценка токенов для режима без --run (грубая, по выводу сессии с реальным ботом)
EST_PROMPT_OVERHEAD = 1000   # инструкция + спецификация батча, токенов
EST_OUT_PER_DIALOG = 200

# Фраза «в базе нет» — как в server/index.js (константа NO_ANSWER).
NO_ANSWER = (
    "К сожалению, я не владею такой информацией. "
    "Попробуйте спросить про меню, цены, адрес и часы работы — с радостью отвечу."
)


# ---------------------------------------------------------------- окружение
def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def knowledge_text() -> str:
    """Что бот реально знает: системная база (Node) + документы из rag.db."""
    parts: list[str] = []
    try:
        out = subprocess.run(
            ["node", "-e", "process.stdout.write(require('./server/knowledge').buildSystemPrompt())"],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=True,
        )
        # Служебные правила бота не нужны, нужны факты: берём как есть, модель разберётся.
        parts.append(out.stdout)
    except Exception as exc:  # noqa: BLE001
        print(f"[!] не удалось получить knowledge.js: {exc}")
    rag = ROOT / "data" / "rag.db"
    if rag.exists():
        conn = sqlite3.connect(f"file:{rag}?mode=ro", uri=True)
        for title, text in conn.execute("SELECT title, text FROM documents ORDER BY id"):
            parts.append(f"## Документ: {title}\n{text}")
        conn.close()
    return "\n\n".join(parts)


# ---------------------------------------------------------------- план
def build_plan(total: int, rng: random.Random) -> list[dict]:
    cats: list[str] = []
    for name, share in MIX.items():
        cats += [name] * round(total * share)
    while len(cats) < total:
        cats.append("normal")
    cats = cats[:total]
    rng.shuffle(cats)
    return [
        {
            "i": n + 1,
            "category": c,
            "style": rng.choice(STYLES),
            "user_turns": rng.randint(1, MAX_USER_TURNS),
        }
        for n, c in enumerate(cats)
    ]


SYSTEM = """Ты генерируешь тестовые диалоги клиентов кофейни Coffee Point с чат-ботом.
Ниже БАЗА ЗНАНИЙ бота. Это единственный источник фактов.

{kb}

Правила:
- Для каждого элемента спецификации напиши диалог: реплики клиента (user) и бота (assistant) строго по очереди, начиная с клиента. Число реплик клиента задано в user_turns, после каждой идёт ответ бота.
- Категории:
  normal — обычные вопросы про меню, цены, часы работы, доставку, сроки, лояльность; бот отвечает кратко (1-3 предложения) ТОЛЬКО по базе знаний.
  no_answer — клиент спрашивает то, чего в базе знаний НЕТ (например состав добавок, франшиза, вакансии, аллергены, парковка, оплата картой, меню на вынос и т.п.; проверяй по базе!). Ответ бота на такой вопрос — ровно строка [[NO_ANSWER]]. Остальные реплики такого диалога могут быть обычными.
  complaint — клиент недоволен (задержка, качество, ошибка заказа); бот извиняется, предлагает позвонить по телефону из базы, не обещает компенсаций.
  lead — клиент готов купить или оставить заявку (заказ, торт на заказ, мероприятие); бот предлагает позвонить или оформить через менеджера.
- Не выдумывай цены, сроки, акции и условия: бери только из базы. Если нужного факта нет, это ответ [[NO_ANSWER]].
- Стиль клиента задан в style. Пиши по-русски, реалистично, разнообразно, без повторов формулировок между диалогами.
- Ответ строго JSON: {{"dialogs":[{{"i":<номер из спецификации>,"messages":[{{"role":"user","text":"..."}},{{"role":"assistant","text":"..."}}]}}]}}"""


# ---------------------------------------------------------------- валидация
def valid(dialog: dict, spec: dict) -> bool:
    msgs = dialog.get("messages")
    if not isinstance(msgs, list) or not 2 <= len(msgs) <= MAX_USER_TURNS * 2:
        return False
    for k, m in enumerate(msgs):
        if m.get("role") != ("user" if k % 2 == 0 else "assistant"):
            return False
        if not isinstance(m.get("text"), str) or not m["text"].strip():
            return False
    if msgs[-1]["role"] != "assistant":
        return False
    # Служебные метки, кроме нашей [[NO_ANSWER]], в тексте недопустимы (модель любит вставлять [[OUT_OF_SCOPE]]).
    if any("[[" in m["text"].replace("[[NO_ANSWER]]", "") for m in msgs):
        return False
    has_gap = any("[[NO_ANSWER]]" in m["text"] for m in msgs)
    return has_gap if spec["category"] == "no_answer" else not has_gap


def ask_batch(client, kb: str, specs: list[dict]) -> tuple[list[dict], int, int]:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            res = client.chat.completions.create(
                model=MODEL,
                temperature=0.9,
                max_tokens=6000,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM.format(kb=kb)},
                    {"role": "user", "content": "Спецификация:\n" + json.dumps(specs, ensure_ascii=False)},
                ],
            )
            data = json.loads(res.choices[0].message.content)
            return data.get("dialogs", []), res.usage.prompt_tokens, res.usage.completion_tokens
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            print(f"    повтор {attempt + 1}/3: {type(exc).__name__}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"батч не удался: {last_exc}")


# ---------------------------------------------------------------- запись
def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def real_prompt_base(conn: sqlite3.Connection) -> int:
    """Медиана tokens_in у настоящих ответов бота; иначе значение, замеренное вручную в Фазе 1."""
    rows = [r[0] for r in conn.execute(
        "SELECT m.tokens_in FROM messages m JOIN conversations c ON c.id = m.conversation_id "
        "WHERE m.tokens_in IS NOT NULL AND c.session_id NOT LIKE 'gen\\_%' ESCAPE '\\' ORDER BY m.tokens_in"
    )]
    return rows[len(rows) // 2] if rows else FALLBACK_PROMPT_TOKENS


def save(conn: sqlite3.Connection, spec: dict, dialog: dict, rng: random.Random, now: datetime, base_in: int) -> None:
    started = now - timedelta(seconds=rng.randint(0, DAYS * 86400))
    cat = spec["category"]
    channel = "telegram" if rng.random() < CHANNEL_SHARE_TELEGRAM else "website"
    lead = cat == "lead"
    handed = lead or (cat == "complaint" and rng.random() < COMPLAINT_HANDOFF)
    rating = None
    if rng.random() < RATING_SHARE:
        rating = rng.randint(1, 3) if cat == "complaint" else rng.randint(3, 5) if cat == "no_answer" else rng.randint(4, 5)
    cur = conn.execute(
        """INSERT INTO conversations (session_id, channel, started_at, rating, handed_to_manager, lead_created, is_test)
           VALUES (?, ?, ?, ?, ?, ?, 0)""",
        (f"gen_{channel[:2]}_{spec['i']:04d}", channel, iso(started), rating, int(handed), int(lead)),
    )
    t = started
    history_chars = 0
    for m in dialog["messages"]:
        t += timedelta(seconds=rng.randint(5, 90))
        fallback = m["role"] == "assistant" and "[[NO_ANSWER]]" in m["text"]
        text = NO_ANSWER if fallback else m["text"].strip()
        t_in = t_out = c = None
        if m["role"] == "assistant" and not fallback:
            # ОЦЕНКА, не замер: бота реально не вызывали. Вход = типичный промпт бота
            # + история диалога, выход = длина ответа. Fallback по порогу модель не вызывает.
            t_in = base_in + history_chars // CHARS_PER_TOKEN
            t_out = max(1, len(text) // CHARS_PER_TOKEN)
            c = db.cost_usd(CHAT_MODEL, t_in, t_out)
        history_chars += len(text)
        conn.execute(
            """INSERT INTO messages (conversation_id, role, text, created_at, is_fallback,
                                     tokens_in, tokens_out, cost_usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cur.lastrowid, m["role"], text, iso(t), int(fallback), t_in, t_out, c),
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="выполнить генерацию (платные запросы)")
    ap.add_argument("--limit", type=int, default=TOTAL, help="сколько диалогов сгенерировать")
    ap.add_argument("--reset", action="store_true", help="удалить ранее сгенерированные (gen_*) и начать заново")
    args = ap.parse_args()

    load_env()
    rng = random.Random(SEED)
    plan = build_plan(args.limit, rng)
    batches = [plan[k : k + BATCH] for k in range(0, len(plan), BATCH)]
    kb = knowledge_text()
    kb_tokens = len(kb) // 2  # грубо: ~2 знака кириллицы на токен

    est_in = len(batches) * (kb_tokens + EST_PROMPT_OVERHEAD)
    est_out = len(plan) * EST_OUT_PER_DIALOG
    prices = json.loads((ROOT / "analytics" / "prices.json").read_text(encoding="utf-8")).get(MODEL, {})
    est_cost = db.cost_usd(MODEL, est_in, est_out)

    print(f"Модель: {MODEL}; диалогов: {len(plan)}; запросов: {len(batches)} (батч по {BATCH})")
    print(f"База знаний в промпте: ~{kb_tokens} токенов")
    print(f"Оценка: вход ~{est_in:,} токенов, выход ~{est_out:,} токенов (+30% на повторы)")
    print("Оценка стоимости: " + (f"~${est_cost:.4f}" if est_cost is not None else
          f"цены не заданы в analytics/prices.json ({prices}); стоимость = вход/1e6*цена_вх + выход/1e6*цена_вых"))
    if not args.run:
        print("\nРежим оценки: запросов к OpenAI НЕ было. Для запуска добавьте --run")
        return

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY не задан в .env")
    from openai import OpenAI  # импорт здесь: для режима оценки пакет не нужен

    client = OpenAI()
    db.init_db()
    conn = db.connect()
    existing = conn.execute("SELECT COUNT(*) FROM conversations WHERE session_id LIKE 'gen\\_%' ESCAPE '\\'").fetchone()[0]
    if existing and not args.reset:
        sys.exit(f"В базе уже {existing} сгенерированных диалогов. Запустите с --reset, чтобы заменить.")
    if args.reset:
        conn.execute("DELETE FROM conversations WHERE session_id LIKE 'gen\\_%' ESCAPE '\\'")
        conn.commit()

    now = datetime.now(timezone.utc)
    base_in = real_prompt_base(conn)
    print(f"Оценочный промпт бота для токенов синтетики: {base_in}")
    seen: set[str] = set()
    saved = rejected = tok_in = tok_out = 0
    for n, specs in enumerate(batches, 1):
        print(f"батч {n}/{len(batches)}…", flush=True)
        by_i = {s["i"]: s for s in specs}
        dialogs, t_in, t_out = ask_batch(client, kb, specs)
        tok_in, tok_out = tok_in + t_in, tok_out + t_out
        with conn:
            for d in dialogs:
                spec = by_i.get(d.get("i"))
                first = (d.get("messages") or [{}])[0].get("text", "").strip().lower()
                if not spec or not valid(d, spec) or first in seen:
                    rejected += 1
                    continue
                seen.add(first)
                save(conn, spec, d, rng, now, base_in)
                saved += 1
                by_i.pop(d["i"])
    cost = db.cost_usd(MODEL, tok_in, tok_out)
    print(f"\nГотово: записано {saved}, отбраковано {rejected}, не получено {len(plan) - saved - rejected}")
    print(f"Токены: вход {tok_in:,}, выход {tok_out:,}; стоимость: " + (f"${cost:.4f}" if cost is not None else "цены не заданы"))
    print("Дополнить недостающие: scripts/check_data.py покажет итог (его я напишу после загрузки).")


if __name__ == "__main__":
    main()
