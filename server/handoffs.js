'use strict';

/**
 * Очередь обращений «нужен человек» (Практика №2б: менеджер в кабинете).
 *
 * Telegram-бот находит вопрос, который сам не может закрыть, и записывает
 * сюда строку. Менеджер видит список в кабинете администратора и отвечает.
 * Ответ забирает бот (claimOutgoing) и сам отправляет его клиенту, — в
 * Telegram менеджеру заходить не нужно.
 *
 * Хранилище — своя таблица в SQLite: файл маленький, держим отдельно от
 * базы знаний, чтобы чистка RAG не задела журнал менеджера.
 */

const path = require('path');
const fs = require('fs');
const { DatabaseSync } = require('node:sqlite');

const DATA_DIR = path.join(__dirname, '..', 'data');
const DB_FILE = path.join(DATA_DIR, 'handoffs.db');

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS handoffs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    channel      TEXT NOT NULL,
    question     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'new',
    reply        TEXT,
    created_at   TEXT NOT NULL,
    replied_at   TEXT,
    delivered_at TEXT
  );

  CREATE INDEX IF NOT EXISTS handoffs_status ON handoffs(status);
`;

let db = null;

function handle() {
  if (db) return db;
  fs.mkdirSync(DATA_DIR, { recursive: true });
  db = new DatabaseSync(DB_FILE);
  db.exec(SCHEMA);
  return db;
}

const now = () => new Date().toISOString();

/** Новое обращение. Статус new: менеджер ещё не видел, бот ждёт ответа. */
function create({ session_id, channel = 'telegram', question }) {
  if (!session_id || !question) return null;
  const res = handle()
    .prepare('INSERT INTO handoffs (session_id, channel, question, created_at) VALUES (?, ?, ?, ?)')
    .run(String(session_id), String(channel), String(question), now());
  return get(Number(res.lastInsertRowid));
}

function get(id) {
  return handle().prepare('SELECT * FROM handoffs WHERE id = ?').get(id) || null;
}

/** Последние обращения: новые сверху, чтобы менеджер не листал. */
function list({ limit = 50 } = {}) {
  return handle()
    .prepare('SELECT * FROM handoffs ORDER BY id DESC LIMIT ?')
    .all(Number(limit) || 50);
}

/** Менеджер ответил. Ждём, пока бот заберёт (delivered_at пустой). */
function setReply(id, reply) {
  const text = String(reply || '').trim();
  if (!text) return null;
  const res = handle()
    .prepare('UPDATE handoffs SET reply = ?, replied_at = ?, status = ? WHERE id = ?')
    .run(text, now(), 'answered', Number(id));
  return res.changes > 0 ? get(Number(id)) : null;
}

/**
 * Ответы, которые бот ещё не отправил. Метка delivered_at ставится сразу:
 * если отправка сорвётся, менеджер увидит, что ответ ушёл, — копейка ради
 * переспамить клиенту хуже, чем один раз потерять ответ.
 */
function claimOutgoing() {
  const rows = handle()
    .prepare("SELECT * FROM handoffs WHERE status = 'answered' AND delivered_at IS NULL ORDER BY id")
    .all();
  const stamp = now();
  const mark = handle().prepare('UPDATE handoffs SET delivered_at = ? WHERE id = ?');
  for (const row of rows) mark.run(stamp, row.id);
  return rows;
}

module.exports = { create, get, list, setReply, claimOutgoing };
