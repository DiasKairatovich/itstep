#!/usr/bin/env node
'use strict';

/**
 * Проверка RAG: гоняет вопросы из eval/questions.json через бота и печатает
 * вопрос, ответ и источники.
 *
 *   node eval/run.js
 *
 * Сервер поднимается в этом же процессе на случайном порту — поднимать
 * `npm start` отдельно не нужно. Требуется OPENAI_API_KEY: он идёт и на
 * эмбеддинги, и на ответы.
 */

const fs = require('fs');
const path = require('path');

// .env может лежать не там, где запущен скрипт, поэтому указываем путь явно.
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const { app, NO_ANSWER } = require('../server/index.js');
const rag = require('../server/rag.js');

const SAMPLES = path.join(__dirname, '..', 'sample_docs');
const QUESTIONS = path.join(__dirname, '..', 'eval', 'questions.json');

/** Файлы из sample_docs/, которых ещё нет в базе. */
async function ensureDocuments() {
  const known = new Set(rag.listDocuments().map((d) => d.title));

  for (const file of fs.readdirSync(SAMPLES)) {
    if (!/\.(txt|md)$/i.test(file)) continue;
    const title = rag.sanitizeTitle(file);
    if (known.has(title)) {
      console.log(`документ уже в базе: ${title}`);
      continue;
    }
    const content = fs.readFileSync(path.join(SAMPLES, file), 'utf8');
    const doc = await rag.addDocument(file, content);
    console.log(`индексация: ${doc.title} (${doc.chunks} фрагм.)`);
  }
}

async function ask(baseUrl, question) {
  const res = await fetch(`${baseUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: [{ role: 'user', content: question }] }),
  });
  if (!res.ok) throw new Error(`/api/chat ответил ${res.status}`);
  return res.json();
}

(async () => {
  const questions = JSON.parse(fs.readFileSync(QUESTIONS, 'utf8'));

  await ensureDocuments();

  const server = app.listen(0);
  await new Promise((resolve) => server.once('listening', resolve));
  const baseUrl = `http://127.0.0.1:${server.address().port}`;
  console.log(`сервер на ${baseUrl}, порог сходства ${rag.MIN_SIMILARITY}\n`);

  let failures = 0;

  for (const [i, item] of questions.entries()) {
    const { reply, sources = [] } = await ask(baseUrl, item.question);
    const known = sources.length > 0 && reply !== NO_ANSWER;

    // Ловушка обязана остаться без ответа; обычный вопрос обязан сослаться
    // на ожидаемый документ.
    const ok = item.trap ? !known : known && sources.includes(item.expect);
    if (!ok) failures += 1;

    console.log('─'.repeat(72));
    console.log(`${i + 1}. ${item.question}${item.trap ? '  [ловушка]' : ''}`);
    console.log(`   ответ:     ${reply}`);
    console.log(`   источники: ${sources.length ? sources.join(', ') : '—'}`);
    console.log(`   ${ok ? 'ok' : 'ОШИБКА'}${item.expect ? `: ожидался «${item.expect}»` : ''}`);
  }

  server.close();
  console.log(`\n${'='.repeat(72)}\nуспешно: ${questions.length - failures} из ${questions.length}`);
  process.exit(failures ? 1 : 0);
})().catch((err) => {
  console.error('проверка упала:', err?.message ?? err);
  process.exit(1);
});
