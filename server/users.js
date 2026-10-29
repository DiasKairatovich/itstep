'use strict';

/**
 * Хранилище пользователей и сессий.
 *
 * Пароли нигде не хранятся в открытом виде: только scrypt-хеш с солью.
 * Сессии — случайные токены в HTTP-only cookie, клиент не может подделать
 * роль: она всегда берётся из серверной записи пользователя.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DATA_DIR = path.join(__dirname, '..', 'data');
const FILE = path.join(DATA_DIR, 'users.json');

const LOGIN_RE = /^[\wа-яА-ЯёЁ-]{3,24}$/;
const PASSWORD_MIN = 6;
const PASSWORD_MAX = 72;
const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000; // месяц

function hashPassword(password, saltHex) {
  const salt = saltHex || crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return { salt, hash };
}

function verifyPassword(password, salt, expectedHex) {
  const { hash } = hashPassword(password, salt);
  return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), Buffer.from(expectedHex, 'hex'));
}

/* ------------------------- users.json ------------------------- */

function read() {
  try {
    return JSON.parse(fs.readFileSync(FILE, 'utf8'));
  } catch (err) {
    if (err.code !== 'ENOENT') console.warn(`[auth] не удалось прочитать users.json: ${err.message}`);
    return [];
  }
}

function write(users) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(FILE, JSON.stringify(users, null, 2));
}

/**
 * Создаёт администратора из ADMIN_LOGIN/ADMIN_PASSWORD, если в хранилище
 * ещё нет ни одного админа.
 */
function ensureAdmin() {
  const users = read();
  if (users.some((u) => u.role === 'admin')) return;

  const login = (process.env.ADMIN_LOGIN || 'admin').trim().toLowerCase();
  const password = process.env.ADMIN_PASSWORD || 'admin123';

  const { salt, hash } = hashPassword(password);
  users.push({ login, salt, hash, role: 'admin', createdAt: new Date().toISOString() });
  write(users);

  if (!process.env.ADMIN_PASSWORD) {
    console.warn(
      `[auth] создан администратор «${login}» с паролем по умолчанию — смените его (ADMIN_PASSWORD в .env).`
    );
  }
}

const sanitize = (u) => ({ login: u.login, role: u.role });

function findByLogin(login) {
  return read().find((u) => u.login === String(login).trim().toLowerCase()) || null;
}

function validate(login, password) {
  const errs = [];
  if (typeof login !== 'string' || !LOGIN_RE.test(login)) {
    errs.push('Логин — 3–24 символов: буквы, цифры, «_», «-»');
  }
  if (typeof password !== 'string' || password.length < PASSWORD_MIN || password.length > PASSWORD_MAX) {
    errs.push(`Пароль — от ${PASSWORD_MIN} символов`);
  }
  return errs;
}

function register(login, password) {
  const errs = validate(login, password);
  if (errs.length) return { error: errs.join('. ') };

  login = login.trim().toLowerCase();
  const users = read();
  if (users.some((u) => u.login === login)) return { error: 'Такой логин уже занят' };

  const { salt, hash } = hashPassword(password);
  users.push({ login, salt, hash, role: 'client', createdAt: new Date().toISOString() });
  write(users);
  return { user: { login, role: 'client' } };
}

function verify(login, password) {
  const user = findByLogin(login);
  if (!user) return null;
  return verifyPassword(password, user.salt, user.hash) ? sanitize(user) : null;
}

/* ------------------------- sessions ------------------------- */

const sessions = new Map();

function createSession(user) {
  const token = crypto.randomBytes(32).toString('hex');
  sessions.set(token, { login: user.login, expires: Date.now() + SESSION_TTL_MS });
  return token;
}

function resolveSession(token) {
  const s = sessions.get(token);
  if (!s) return null;
  if (s.expires < Date.now()) {
    sessions.delete(token);
    return null;
  }
  const user = findByLogin(s.login);
  return user ? sanitize(user) : null;
}

function destroySession(token) {
  sessions.delete(token);
}

function startSessionCleanup() {
  const timer = setInterval(() => {
    const now = Date.now();
    for (const [token, s] of sessions) {
      if (s.expires < now) sessions.delete(token);
    }
  }, 60 * 1000);
  timer.unref?.();
}

module.exports = {
  ensureAdmin,
  register,
  verify,
  findByLogin,
  sanitize,
  createSession,
  resolveSession,
  destroySession,
  startSessionCleanup,
  validate,
};
