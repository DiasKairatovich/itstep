'use strict';

require('dotenv').config();

const path = require('path');
const express = require('express');
const OpenAI = require('openai');
const auth = require('./users');
const knowledge = require('./knowledge');
const rag = require('./rag');

const PUBLIC_DIR = path.join(__dirname, '..', 'public');

const PORT = Number(process.env.PORT) || 3456;
const MODEL = process.env.OPENAI_MODEL || 'gpt-4o-mini';
const MAX_MESSAGES = Number(process.env.MAX_MESSAGES) || 20;
const MAX_INPUT_CHARS = 2000;
const SESSION_COOKIE = 'cp_session';

/** Ответ, когда вопрос вне темы кофейни, либо OpenAI недоступен. */
const DEFAULT_ANSWER =
  'Я умею отвечать только про Coffee Point: меню, цены, состав напитков, адрес и часы работы. ' +
  'Спросите о напитках или позвоните нам — +7 700 123-45-67';

const OUT_OF_SCOPE = '[[OUT_OF_SCOPE]]';

/**
 * Ответ, когда похожих фрагментов в базе не нашлось. Формулировка для
 * посетителя: он не в курсе, что у нас база знаний и RAG, — говорим простыми
 * словами, что таких данных у бота нет.
 */
const NO_ANSWER =
  'К сожалению, я не владею такой информацией. ' +
  'Попробуйте спросить про меню, цены, адрес и часы работы — с радостью отвечу.';

const MAX_DOC_BYTES = 1024 * 1024; // 1 МБ — верхняя планка загружаемого файла

const app = express();
app.disable('x-powered-by');

// Лимиты по телу: 128 КБ с запасом покрывают окно чата (20 реплик по
// 2000 знаков), админские секции базы знаний длиннее, документы приходят
// целыми файлами — для них отдельный парсер на маршруте.
const jsonSmall = express.json({ limit: '128kb' });
const jsonSections = express.json({ limit: '256kb' });

app.use((req, res, next) => {
  if (req.path.startsWith('/api/documents')) return next();
  if (req.path.startsWith('/api/knowledge')) return jsonSections(req, res, next);
  return jsonSmall(req, res, next);
});

const apiKey = process.env.OPENAI_API_KEY;
const openai = apiKey ? new OpenAI({ apiKey }) : null;

if (!openai) {
  console.warn(
    '[coffee-point] OPENAI_API_KEY не задан — /api/chat будет отвечать заготовкой. ' +
    'Скопируйте .env.example в .env и укажите ключ.'
  );
}

/* ------------------------------------------------------------------ *
 *  Простейший rate limit по IP: не более N запросов в минуту.
 * ------------------------------------------------------------------ */
const WINDOW_MS = 60 * 1000;
const LIMIT = Number(process.env.RPS_LIMIT) || 20;
const hits = new Map();

function rateLimit(req, res, next) {
  const now = Date.now();
  const key = req.ip || 'unknown';
  const entry = hits.get(key);
  if (!entry || now - entry.started > WINDOW_MS) {
    hits.set(key, { started: now, count: 1 });
    return next();
  }
  entry.count += 1;
  if (entry.count > LIMIT) {
    res.setHeader('Retry-After', Math.ceil((WINDOW_MS - (now - entry.started)) / 1000));
    return res.status(429).json({ error: 'too_many_requests', message: 'Слишком много запросов. Попробуйте позже.' });
  }
  next();
}

// Периодически чистим карту, чтобы она не росла бесконечно.
setInterval(() => {
  const now = Date.now();
  for (const [ip, entry] of hits) {
    if (now - entry.started > WINDOW_MS * 2) hits.delete(ip);
  }
}, WINDOW_MS).unref();

/* ------------------------------------------------------------------ *
 *  Нормализация истории сообщений: только user/assistant,
 *  только строки, с обрезкой по длине и по размеру окна.
 * ------------------------------------------------------------------ */
function normalizeMessages(body) {
  const raw = Array.isArray(body?.messages) ? body.messages : [];

  const cleaned = raw
    .filter(
      (m) =>
        m &&
        (m.role === 'user' || m.role === 'assistant') &&
        typeof m.content === 'string' &&
        m.content.trim().length > 0
    )
    .map((m) => ({ role: m.role, content: m.content.trim().slice(0, MAX_INPUT_CHARS) }))
    .slice(-MAX_MESSAGES);

  // История должна заканчиваться вопросом пользователя.
  while (cleaned.length && cleaned[cleaned.length - 1].role !== 'user') cleaned.pop();

  return cleaned;
}

/**
 * Вызов OpenAI. Возвращает текст-заготовку, если ключа нет или API
 * недоступен — чтобы сайт никогда не падал с 500.
 */
async function askOpenAI(messages, ragContext = '') {
  if (!openai) return DEFAULT_ANSWER;

  const res = await openai.chat.completions.create({
    model: MODEL,
    temperature: 0.3,
    max_tokens: 400,
    messages: [{ role: 'system', content: knowledge.buildSystemPrompt() + ragContext }, ...messages],
  });

  const text = res.choices?.[0]?.message?.content?.trim();
  if (!text) return DEFAULT_ANSWER;
  if (text.includes(OUT_OF_SCOPE)) return DEFAULT_ANSWER;
  return text;
}

/* ------------------------------------------------------------------ *
 *  Аутентификация
 * ------------------------------------------------------------------ */

const COOKIE_OPTS = {
  httpOnly: true,
  sameSite: 'lax',
  path: '/',
  maxAge: 30 * 24 * 60 * 60 * 1000,
};

function readSessionToken(req) {
  const match = (req.headers.cookie || '').match(/(?:^|;\s*)cp_session=([^;\s]+)/);
  return match ? match[1] : null;
}

function currentUser(req) {
  const token = readSessionToken(req);
  return token ? auth.resolveSession(token) : null;
}

function requireUser(req, res, next) {
  const user = currentUser(req);
  if (!user) return res.status(401).json({ error: 'unauthorized', message: 'Нужно войти в кабинет.' });
  req.user = user;
  next();
}

function requireAdmin(req, res, next) {
  const user = currentUser(req);
  if (!user) return res.status(401).json({ error: 'unauthorized', message: 'Нужно войти в кабинет.' });
  if (user.role !== 'admin') return res.status(403).json({ error: 'forbidden', message: 'Только для администратора.' });
  next();
}

function loginVia(req, res, user) {
  const token = auth.createSession(user);
  res.cookie(SESSION_COOKIE, token, COOKIE_OPTS);
  res.json({ user });
}

app.post('/api/auth/login', rateLimit, (req, res) => {
  const { login, password } = req.body || {};
  const errs = auth.validate(login, password);
  if (errs.length) return res.status(400).json({ error: 'bad_request', message: errs.join('. ') });

  const user = auth.verify(login, password);
  if (!user) return res.status(401).json({ error: 'unauthorized', message: 'Неверный логин или пароль.' });

  loginVia(req, res, user);
});

app.post('/api/auth/register', rateLimit, (req, res) => {
  const { login, password } = req.body || {};
  const errs = auth.validate(login, password);
  if (errs.length) return res.status(400).json({ error: 'bad_request', message: errs.join('. ') });

  const result = auth.register(login, password);
  if (result.error) return res.status(409).json({ error: 'conflict', message: result.error });

  loginVia(req, res, result.user);
});

app.post('/api/auth/logout', (req, res) => {
  const token = readSessionToken(req);
  if (token) auth.destroySession(token);
  res.clearCookie(SESSION_COOKIE, { path: '/' });
  res.json({ ok: true });
});

app.get('/api/auth/me', (req, res) => {
  res.json({ user: currentUser(req) });
});

/* ------------------------------------------------------------------ *
 *  База знаний (только администратор)
 * ------------------------------------------------------------------ */
app.get('/api/knowledge', requireAdmin, (_req, res) => {
  res.json({ sections: knowledge.load(), bytes: knowledge.sizeBytes() });
});

app.put('/api/knowledge', requireAdmin, (req, res) => {
  const sections = knowledge.save(req.body?.sections);
  res.json({ sections, bytes: knowledge.sizeBytes() });
});

/* ------------------------------------------------------------------ *
 *  Маршруты
 * ------------------------------------------------------------------ */
app.get('/api/health', (_req, res) => {
  res.json({ ok: true, model: MODEL, aiEnabled: Boolean(openai) });
});

app.post('/api/chat', rateLimit, async (req, res) => {
  const messages = normalizeMessages(req.body);

  if (!messages.length) {
    return res.status(400).json({ error: 'bad_request', message: 'Нужно сообщение с содержимым.' });
  }

  // 1. Ищем вопрос в базе знаний. Пока документов не загружено, база пуста и
  //    бот работает как раньше — по системным подсказкам из knowledge.js.
  let ragContext = '';
  let sources = [];

  if (!rag.isEmpty()) {
    const question = messages[messages.length - 1].content;

    let found;
    try {
      found = await rag.search(question);
    } catch (err) {
      // Эмбеддинг вопроса — тот же OpenAI, что и ответ: при его недоступности
      // модель всё равно не ответит, так что деградируем как при сбое chat.
      console.error('[/api/chat] поиск по базе знаний:', err?.message ?? err);
      return res.json({ reply: DEFAULT_ANSWER, sources: [], degraded: true });
    }

    // 2. Слишком далёкие фрагменты — не выдумываем, а зовём на помощь админа.
    if (found.best < rag.MIN_SIMILARITY) {
      return res.json({ reply: NO_ANSWER, sources: [] });
    }

    // 3. Ответим по найденным фрагментам, а их названия покажем пользователю.
    ragContext = rag.buildPrompt(found.top);
    sources = [...new Set(found.top.map((c) => c.title))];
  }

  try {
    const reply = await askOpenAI(messages, ragContext);
    // Ответ-заготовка к базовому знанию не относится — не ищем в нём источник.
    res.json({ reply, sources: reply === DEFAULT_ANSWER ? [] : sources });
  } catch (err) {
    const status = err?.status ?? err?.response?.status;
    console.error(`[/api/chat] ${status ?? ''} ${err?.message ?? err}`);

    // Остальные сбои OpenAI (таймаут, лимит-тайр) не должны ломать чат:
    // отдаём дефолтный ответ и помечаем его как degraded.
    if (status === 401 || status === 403) {
      return res.status(502).json({ error: 'ai_auth', message: 'Проверьте OPENAI_API_KEY на сервере.' });
    }
    res.json({ reply: DEFAULT_ANSWER, sources: [], degraded: true });
  }
});

/* ------------------------------------------------------------------ *
 *  Документы базы знаний (только администратор)
 *
 *  Файл читается в браузере как текст и приходит JSON'ом: .txt и .md —
 *  это текст, multipart-парсер ради этого не нужен.
 * ------------------------------------------------------------------ */
const jsonDoc = express.json({ limit: '3mb' });

app.get('/api/documents', requireAdmin, (_req, res) => {
  res.json({ documents: rag.listDocuments(), threshold: rag.MIN_SIMILARITY, top: rag.TOP_K });
});

app.post('/api/documents', requireAdmin, rateLimit, jsonDoc, async (req, res) => {
  const { filename, content } = req.body || {};

  if (!rag.allowedExtension(filename)) {
    return res.status(400).json({ error: 'bad_request', message: 'Принимаются файлы .txt и .md' });
  }
  if (typeof content !== 'string' || !content.trim()) {
    return res.status(400).json({ error: 'bad_request', message: 'В файле нет текста' });
  }
  if (Buffer.byteLength(content, 'utf8') > MAX_DOC_BYTES) {
    return res.status(413).json({ error: 'too_large', message: 'Файл больше 1 МБ' });
  }

  try {
    const doc = await rag.addDocument(filename, content);
    // Содержимое документа в лог не пишем — только заголовок и размеры.
    console.log(`[rag] ${doc.title}: фрагментов ${doc.chunks}`);
    return res.json({ document: doc });
  } catch (err) {
    console.error('[rag] индексация:', err?.message ?? err);
    return res.status(502).json({ error: 'index_failed', message: 'Документ не проиндексирован' });
  }
});

app.post('/api/documents/:id/reindex', requireAdmin, rateLimit, async (req, res) => {
  const doc = await rag.reindexDocument(Number(req.params.id) || 0);
  if (!doc) return res.status(404).json({ error: 'not_found', message: 'Документ не найден' });
  console.log(`[rag] переиндексация ${doc.title}: фрагментов ${doc.chunks}`);
  res.json({ document: doc });
});

app.delete('/api/documents/:id', requireAdmin, (req, res) => {
  if (!rag.removeDocument(Number(req.params.id) || 0)) {
    return res.status(404).json({ error: 'not_found', message: 'Документ не найден' });
  }
  res.json({ ok: true });
});

// Статика — в самый конец, чтобы /api/* имела приоритет.
app.use(
  express.static(PUBLIC_DIR, {
    extensions: ['html'],
    setHeaders(res, filePath) {
      if (filePath.endsWith('.html')) res.setHeader('Cache-Control', 'no-cache');
    },
  })
);

// Кабинет — чистый URL вместо account.html.
app.get('/account', (_req, res) => res.sendFile(path.join(PUBLIC_DIR, 'account.html')));

// Админка базы данных — вместо admin.html.
app.get('/admin', (_req, res) => res.sendFile(path.join(PUBLIC_DIR, 'admin.html')));

// Фолбэк для несуществующих путей — на index, как у SPA-подобных лендингов.
app.get(/^(?!\/api\/|\/account).*/, (_req, res) => res.redirect('/'));

module.exports = { app, normalizeMessages, DEFAULT_ANSWER, NO_ANSWER };

// Слушатель поднимаем только при прямом запуске — чтобы модуль можно было
// импортировать в тестах, не занимая порт.
if (require.main === module) {
  auth.ensureAdmin();
  auth.startSessionCleanup();

  const server = app.listen(PORT, () => {
    console.log(`☕ Coffee Point → http://localhost:${PORT}`);
  });

  process.on('SIGTERM', () => server.close());
}
