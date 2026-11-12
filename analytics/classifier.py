"""ИИ-разметка диалогов через Structured Outputs (OpenAI SDK >= 1.40 / 3.x).

Использует актуальный метод ``client.chat.completions.parse`` (не устаревший ``beta``).
"""

from __future__ import annotations

import os
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from analytics import db

MODEL = os.environ.get("CLASSIFY_MODEL", "gpt-4o-mini")

TopicType = Literal[
    "menu_prices",
    "hours_location",
    "delivery",
    "loyalty_promos",
    "preorders_events",
    "complaints_refunds",
    "unknown_product_info",
    "smalltalk_other",
]

IntentType = Literal[
    "price",
    "delivery",
    "complaint",
    "ready_to_buy",
    "info",
    "other",
]

SentimentType = Literal[
    "negative",
    "neutral",
    "positive",
]


class ConversationAnalysis(BaseModel):
    """Pydantic-схема результата ИИ-разметки одного диалога."""

    topic: TopicType = Field(
        description="Главная тема диалога из утверждённого списка."
    )
    intent: IntentType = Field(
        description="Основное намерение (интент) клиента в диалоге."
    )
    sentiment: SentimentType = Field(
        description="Эмоциональная тональность клиента в диалоге."
    )
    not_resolved: bool = Field(
        description="True, если вопрос или проблема клиента НЕ были решены ботом в рамках диалога."
    )
    short_reason: str = Field(
        description="Одно короткое предложение на русском языке, объясняющее выбранную разметку и статус решения."
    )


SYSTEM_PROMPT = """Ты — аналитик качества диалогов чат-бота кофейни «Coffee Point».
Твоя задача — классифицировать диалог между клиентом (user) и ботом (assistant) по строгой схеме.

### 1. Определения тем (topic):
- `menu_prices`: вопросы про текущее меню, цены, объём и базовый состав имеющихся в меню напитков и блюд (эспрессо, капучино, флэт уайт, мокко, колд брю, айс латте, матча латте, фраппе с ягодами, круассан, маффин, чизкейк, сэндвич с авокадо).
- `hours_location`: часы работы кофейни, адрес, как добраться, телефон и контакты.
- `delivery`: условия доставки (зоны, сроки, стоимость доставки, порог бесплатной доставки, часы работы доставки).
- `loyalty_promos`: программа лояльности, карта гостя, отметки/бонусы, скидка в день рождения, акция «Счастливые часы» и прочие акции/скидки.
- `preorders_events`: торты на заказ, крупные предварительные заказы, кейтеринг, проведение мероприятий, бронирование столиков.
- `complaints_refunds`: жалобы на задержку заказа, перепутанный заказ, плохое качество напитка/еды, грубость, требование возврата денег или обмена.
- `unknown_product_info`: вопросы о характеристиках, услугах или товарах кофейни, которых НЕТ в стандартной базе знаний и на которые бот не смог дать ответ по существу (например: аллергены, безглютеновая выпечка, десерты без сахара, выбор ягод/сиропов/добавок, калорийность/КБЖУ, оплата картой/QR, заказ навынос, наличие чая/какао/рафа, вакансии, франшиза, парковка, Wi-Fi и т.п.).
- `smalltalk_other`: приветствия, благодарности, общие комплименты без вопроса, проверка связи или вопросы, вообще не связанные с работой кофейни.

### 2. Определения намерений клиента (intent):
- `price`: клиент спрашивает стоимость напитка, еды, доставки или условия получения скидки/акции в деньгах.
- `delivery`: клиент интересуется возможностью, сроками, зонами или правилами доставки (если главный вопрос не о цене).
- `complaint`: клиент выражает недовольство, жалуется на проблему с заказом/обслуживанием или требует возврата.
- `ready_to_buy`: клиент явно выражает готовность сделать заказ, купить, забронировать столик, оформить торт на заказ или просит связать с менеджером для оформления заказа.
- `info`: клиент запрашивает справочную информацию (меню, состав, график работы, адрес, правила бонусной карты, наличие позиций).
- `other`: светская беседа (приветствие, отзыв без вопроса) или нерелевантный запрос.

### 3. Тональность клиента (sentiment):
- `negative`: раздражение, злость, разочарование, претензия, упрёк боту («вы даже не можете ответить», «неприемлемо»).
- `neutral`: обычные деловые или вежливые вопросы без ярких эмоций.
- `positive`: тёплая благодарность, похвала кофейне или боту.

### 4. Статус решения (not_resolved):
- `true`:
  1) бот ответил шаблонным отказом («К сожалению, я не владею такой информацией...», «Я умею отвечать только про Coffee Point...»);
  2) бот не дал конкретного ответа по существу фактического вопроса клиента;
  3) клиент обратился с реальной жалобой на инцидент (опоздание курьера, перепутанный заказ, очередь, возврат денег), где проблема требует вмешательства человека и в чате осталась нерешённой.
- `false`:
  1) бот дал точный и полный ответ на вопрос клиента по базе знаний;
  2) клиент хочет оформить заказ / предзаказ / торт / бронь (`ready_to_buy`), и бот корректно объяснил, как это сделать (принял заявку, передал менеджеру или дал контактный телефон/Telegram для оформления);
  3) клиент задал оценочный вопрос («Почему цены такие высокие?»), и бот вежливо аргументировал ответ (зерно прямой обжарки, specialty-качество).

### 5. Правила для спорных случаев:
1. Если в диалоге несколько вопросов, выбирай `topic` и `intent` по ГЛАВНОЙ цели клиента. Если один из вопросов остался без ответа (fallback), приоритет отдавай именно нерешённому вопросу.
2. Если клиент спрашивает про цену доставки («Сколько стоит доставка?»), ставь `topic="delivery"` и `intent="price"`.
3. Если клиент спрашивает про наличие позиции/опции (сиропы, без сахара, на вынос, оплата картой), а бот отвечает «К сожалению, я не владею такой информацией», ставь `topic="unknown_product_info"` и `not_resolved=true` (даже если вопрос звучал как вопрос о меню).
4. Но если клиент явно задал базовый вопрос про адрес, часы работы или цену известной позиции, а бот ошибочно ответил отказом — сохраняй тематическую рубрику (`hours_location` или `menu_prices`), но обязательно ставь `not_resolved=true`.
5. Если клиент начинает с вопроса о цене/меню, а затем прямо говорит «Хочу заказать / Оформите заказ», ставь `intent="ready_to_buy"`.
6. Если клиент выражает недовольство высокими ценами («Почему у вас так дорого?»), ставь `topic="menu_prices"` и `intent="complaint"`; если бот вежливо объяснил причины ценообразования — ставь `not_resolved=false`.
"""


def format_dialog(messages: list[dict[str, str]]) -> str:
    """Форматирует список сообщений [{'role': ..., 'text'|'content': ...}] в читаемый диалог."""
    lines: list[str] = []
    for m in messages:
        role = "Клиент" if m.get("role") == "user" else "Бот"
        text = (m.get("text") or m.get("content") or "").strip()
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


def classify_conversation(
    messages: list[dict[str, str]],
    *,
    client: OpenAI | None = None,
    model: str = MODEL,
) -> tuple[ConversationAnalysis, int, int, float | None]:
    """Классифицирует диалог через OpenAI Structured Outputs (`chat.completions.parse`).

    Возвращает кортеж: `(parsed_analysis, tokens_in, tokens_out, cost_usd)`.
    """
    if client is None:
        client = OpenAI()

    dialog_text = format_dialog(messages)
    completion = client.chat.completions.parse(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Разметь диалог:\n\n{dialog_text}"},
        ],
        response_format=ConversationAnalysis,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError(f"Модель не вернула structured output: {completion.choices[0].message.refusal}")

    t_in = completion.usage.prompt_tokens if completion.usage else 0
    t_out = completion.usage.completion_tokens if completion.usage else 0
    cost = db.cost_usd(model, t_in, t_out)
    return parsed, t_in, t_out, cost
