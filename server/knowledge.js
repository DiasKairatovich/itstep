'use strict';

/**
 * База знаний, которая обслуживает чат-бота.
 *
 * Значения по умолчанию живут в context.js. Админ может переопределить их
 * из личного кабинета — тогда в data/knowledge.json кладётся переопределение,
 * и каждое сообщение бота перечитывает его (файл маленький, кэш не нужен).
 */

const fs = require('fs');
const path = require('path');
const { DEFAULT_SECTIONS, RULES } = require('./context');

const FILE = path.join(__dirname, '..', 'data', 'knowledge.json');

function normalize(sections) {
  const out = {};
  for (const key of Object.keys(DEFAULT_SECTIONS)) {
    const v = sections?.[key];
    out[key] = typeof v === 'string' ? v.trim().slice(0, 20000) : DEFAULT_SECTIONS[key];
  }
  return out;
}

function load() {
  try {
    return normalize({ ...DEFAULT_SECTIONS, ...JSON.parse(fs.readFileSync(FILE, 'utf8')) });
  } catch (err) {
    if (err.code !== 'ENOENT') console.warn(`[knowledge] ${err.message} — беру значений из кода`);
    return { ...DEFAULT_SECTIONS };
  }
}

function save(sections) {
  const data = normalize(sections);
  fs.mkdirSync(path.dirname(FILE), { recursive: true });
  fs.writeFileSync(FILE, JSON.stringify(data, null, 2));
  return data;
}

function sizeBytes() {
  try {
    return fs.statSync(FILE).size;
  } catch {
    return 0; // 0 = «изменений не сохраняли», в UI это «по умолчанию»
  }
}

function buildSystemPrompt(sections) {
  const s = sections || load();
  const section = (title) => `=== ${title} ===\n${s[title]}`;
  return [
    section('О кофейне'),
    '',
    section('Меню и цены'),
    '',
    section('Контакты'),
    '',
    '=== Правила ===',
    RULES,
  ].join('\n');
}

module.exports = { load, save, sizeBytes, buildSystemPrompt, DEFAULT_SECTIONS };
