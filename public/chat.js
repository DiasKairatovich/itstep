/* =========================================
   Coffee Point — клиент чата с ассистентом
   ========================================= */

(function () {
  'use strict';

  const ENDPOINT = '/api/chat';
  const HISTORY_LIMIT = 12; // сколько последних реплик отправляем на сервер
  const STORAGE_KEY = 'cp_chat_history';

  const log = document.getElementById('chat-log');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const resetBtn = document.getElementById('chat-reset');
  const statusEl = document.getElementById('chat-status');
  const chips = document.querySelectorAll('.chat-chip');
  const fab = document.getElementById('fab-chat');
  const widget = document.getElementById('chat-widget');

  if (!log || !form || !input) return;

  let history = load();
  let busy = false;

  /* ---------- Хранилище ---------- */

  function load() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed)
        ? parsed.filter((m) => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
        : [];
    } catch (_) {
      return [];
    }
  }

  function save() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(-HISTORY_LIMIT * 2)));
    } catch (_) {
      /* приватный режим — просто продолжаем без персиста */
    }
  }

  /* ---------- DOM ---------- */

  function bubble(role, text) {
    const el = document.createElement('div');
    el.className = `chat-msg chat-msg-${role}`;
    el.textContent = text; // textContent: ответ модели не может инжектить HTML
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  /** Подпись под ответом: из каких документов собран ответ. */
  function sources(list) {
    if (!Array.isArray(list) || !list.length) return;
    const el = document.createElement('div');
    el.className = 'chat-msg chat-msg-sources';
    el.textContent = `Источники: ${list.join(', ')}`;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
  }

  function typing() {
    const el = document.createElement('div');
    el.className = 'chat-msg chat-msg-bot chat-msg-typing';
    el.innerHTML = '<span></span><span></span><span></span>';
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function setStatus(text, off) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.dataset.state = off ? 'off' : 'on';
  }

  function setBusy(state) {
    busy = state;
    [sendBtn, ...chips].forEach((el) => el && (el.disabled = state));
    if (state) {
      input.setAttribute('readonly', 'readonly');
    } else {
      input.removeAttribute('readonly');
    }
  }

  function autosize() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
  }

  function renderHistory() {
    log.querySelectorAll('.chat-msg').forEach((n) => n.remove());
    history.forEach((m) => bubble(m.role === 'user' ? 'user' : 'bot', m.content));
    if (!history.length) {
      bubble('bot', 'Привет! Я ассистент Coffee Point. Спросите про меню, цены, адрес или часы работы — с радостью помогу.');
    }
  }

  /* ---------- Сеть ---------- */

  async function ask(question) {
    const payload = { messages: history.slice(-HISTORY_LIMIT * 2) };

    const res = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      /* не-JSON: обработаем ниже */
    }

    if (!res.ok || !data || typeof data.reply !== 'string') {
      const err = new Error((data && data.message) || `HTTP ${res.status}`);
      err.transient = res.status === 429 || res.status >= 500;
      throw err;
    }

    return data;
  }

  async function submit(text) {
    const question = (text || '').trim();
    if (!question || busy) return;

    history.push({ role: 'user', content: question });
    bubble('user', question);
    input.value = '';
    autosize();
    save();

    setBusy(true);
    setStatus('думает…');
    const spinner = typing();

    try {
      const data = await ask(question);
      spinner.remove();
      history.push({ role: 'assistant', content: data.reply });
      bubble('bot', data.reply);
      sources(data.sources);
      save();
      setStatus(data.degraded ? 'работает в упрощённом режиме' : 'онлайн', Boolean(data.degraded));
    } catch (err) {
      spinner.remove();

      // Возвратим вопрос в поле ввода и уберём его из истории — иначе
      // при ретраеп он попадёт в контекст дважды.
      history.pop();
      save();
      input.value = question;
      autosize();

      setStatus('нет связи с сервером', true);
      const note = bubble('error', `Не получилось спросить: ${err.message || 'ошибка связи'}.`);
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.className = 'chat-chip';
      retry.textContent = '↻ Повторить';
      retry.addEventListener('click', () => {
        note.remove();
        submit(question);
      }, { once: true });
      note.appendChild(retry);
    } finally {
      setBusy(false);
    }
  }

  /* ---------- События ---------- */

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    submit(input.value);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(input.value);
    }
  });

  input.addEventListener('input', autosize);

  chips.forEach((chip) =>
    chip.addEventListener('click', () => submit(chip.dataset.question))
  );

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      history = [];
      save();
      renderHistory();
      setStatus('онлайн');
    });
  }

  if (fab && widget) {
    fab.addEventListener('click', () => {
      widget.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => input.focus(), 400);
    });
  }

  renderHistory();
  setStatus('онлайн');
})();
