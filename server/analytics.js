'use strict';

/**
 * Аналитика диалогов сайта: пишет в data/analytics.db (схема общая с Python:
 * analytics/schema.sql). Любая ошибка гасится и логируется — ответы бота
 * от аналитики не зависят.
 */

const fs = require('fs');
const path = require('path');
const { DatabaseSync } = require('node:sqlite');

const ROOT = path.join(__dirname, '..');
const DB_FILE = process.env.ANALYTICS_DB || path.join(ROOT, 'data', 'analytics.db');
const SCHEMA_FILE = path.join(ROOT, 'analytics', 'schema.sql');
const PRICES_FILE = path.join(ROOT, 'analytics', 'prices.json');

/** Реплика в течение этого окна продолжает диалог сессии, позже — новый диалог. */
const SESSION_GAP_MS = 30 * 60 * 1000;

let db = null;

function handle() {
  if (db) return db;
  fs.mkdirSync(path.dirname(DB_FILE), { recursive: true });
  const d = new DatabaseSync(DB_FILE);
  d.exec('PRAGMA busy_timeout = 5000;'); // Python-бот пишет в тот же файл
  d.exec('PRAGMA journal_mode = WAL;');
  d.exec('PRAGMA foreign_keys = ON;');
  d.exec(fs.readFileSync(SCHEMA_FILE, 'utf8'));
  db = d;
  return db;
}

/** Создать базу и таблицы заранее (вызывается при старте сервера). */
function initDb() {
  try {
    handle();
  } catch (err) {
    console.error('[analytics] init:', err?.message ?? err);
  }
}

const now = () => new Date().toISOString();

/** Стоимость по prices.json; null, если цена не заполнена. */
function costUsd(model, tokensIn, tokensOut) {
  try {
    const price = JSON.parse(fs.readFileSync(PRICES_FILE, 'utf8'))[model] || {};
    const pin = price.input_per_1m_usd;
    const pout = price.output_per_1m_usd;
    if (pin == null || pout == null || tokensIn == null || tokensOut == null) return null;
    return (tokensIn * pin + tokensOut * pout) / 1e6;
  } catch (err) {
    console.error('[analytics] цены:', err?.message ?? err);
    return null;
  }
}

/** session_id приходит от клиента: только короткая безопасная строка. */
function cleanSessionId(value) {
  const s = typeof value === 'string' ? value.trim() : '';
  return /^[\w:.-]{4,64}$/.test(s) ? s : null;
}

function cleanChannel(value) {
  return value === 'telegram' ? 'telegram' : 'website';
}

function conversationId(d, sessionId, channel, isTest) {
  const row = d
    .prepare(
      `SELECT c.id AS id, COALESCE(MAX(m.created_at), c.started_at) AS last_at
         FROM conversations c LEFT JOIN messages m ON m.conversation_id = c.id
        WHERE c.session_id = ? AND c.is_test = ?
        GROUP BY c.id ORDER BY c.id DESC LIMIT 1`
    )
    .get(sessionId, isTest ? 1 : 0);

  if (row && Date.now() - Date.parse(row.last_at) < SESSION_GAP_MS) return Number(row.id);

  const res = d
    .prepare('INSERT INTO conversations (session_id, channel, started_at, is_test) VALUES (?, ?, ?, ?)')
    .run(sessionId, channel, now(), isTest ? 1 : 0);
  return Number(res.lastInsertRowid);
}

/** Записать вопрос клиента и ответ бота. Возвращает id диалога или null при сбое. */
function logExchange({
  sessionId,
  channel = 'website',
  userText = '',
  botText = '',
  isFallback = false,
  tokensIn = null,
  tokensOut = null,
  cost = null,
  isTest = false,
  handedToManager = false,
  leadCreated = false,
}) {
  try {
    const d = handle();
    const conv = conversationId(d, sessionId, channel, isTest);

    if (userText) {
      d.prepare("INSERT INTO messages (conversation_id, role, text, created_at) VALUES (?, 'user', ?, ?)").run(
        conv,
        userText,
        now()
      );
    }
    if (botText) {
      d.prepare(
        `INSERT INTO messages (conversation_id, role, text, created_at, is_fallback, tokens_in, tokens_out, cost_usd)
         VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?)`
      ).run(conv, botText, now(), isFallback ? 1 : 0, tokensIn, tokensOut, cost);
    }
    if (handedToManager) d.prepare('UPDATE conversations SET handed_to_manager = 1 WHERE id = ?').run(conv);
    if (leadCreated) d.prepare('UPDATE conversations SET lead_created = 1 WHERE id = ?').run(conv);
    return conv;
  } catch (err) {
    console.error('[analytics] запись обмена:', err?.message ?? err);
    return null;
  }
}

/**
 * ЗАГЛУШКА-ХУК: оценки ответа в проекте пока нет. Вызвать из нового эндпоинта
 * (например, POST /api/rating {session_id, rating}) после кнопок 1–5 в chat.js.
 */
function setRating(sessionId, rating) {
  try {
    const n = Number(rating);
    if (!Number.isInteger(n) || n < 1 || n > 5) return;
    handle()
      .prepare(
        `UPDATE conversations SET rating = ?
          WHERE id = (SELECT id FROM conversations WHERE session_id = ? AND is_test = 0 ORDER BY id DESC LIMIT 1)`
      )
      .run(n, sessionId);
  } catch (err) {
    console.error('[analytics] оценка:', err?.message ?? err);
  }
}

module.exports = { initDb, costUsd, cleanSessionId, cleanChannel, logExchange, setRating };
