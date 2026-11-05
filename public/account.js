/* =========================================
   Coffee Point — логика личного кабинета
   ========================================= */
'use strict';

(async function () {
  const screenAuth = document.getElementById('screen-auth');
  const screenApp = document.getElementById('screen-app');

  const tabLogin = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');
  const authForm = document.getElementById('auth-form');
  const authLogin = document.getElementById('auth-login');
  const authPassword = document.getElementById('auth-password');
  const authError = document.getElementById('auth-error');
  const authSubmit = document.getElementById('auth-submit');
  const authHint = document.getElementById('auth-hint');
  const authEye = document.getElementById('auth-password-eye');

  const tabProfile = document.getElementById('tab-profile');
  const tabKnowledge = document.getElementById('tab-knowledge');
  const tabCases = document.getElementById('tab-cases');
  const paneProfile = document.getElementById('pane-profile');
  const paneKnowledge = document.getElementById('pane-knowledge');
  const paneCases = document.getElementById('pane-cases');
  const casesList = document.getElementById('cases-list');
  const casesStatus = document.getElementById('cases-status');
  const profileLogin = document.getElementById('profile-login');
  const profileRole = document.getElementById('profile-role');
  const profileRoleDetail = document.getElementById('profile-role-detail');
  const btnLogout = document.getElementById('btn-logout');

  let mode = 'login';

  async function refresh() {
    const { ok, data } = await Auth.me();
    const user = ok && data.user ? data.user : null;

    if (!user) {
      screenApp.hidden = true;
      screenAuth.hidden = false;
      return;
    }

    const role = user.role === 'admin' ? 'Администратор' : 'Клиент';
    profileLogin.textContent = user.login;
    profileRole.textContent = role;
    profileRoleDetail.textContent = role;
    tabKnowledge.hidden = user.role !== 'admin';
    tabCases.hidden = user.role !== 'admin';
    if (user.role !== 'admin') showPane('profile');

    if (user.role === 'admin' && !kbSectionsBuilt) await buildKbEditor();

    screenAuth.hidden = true;
    screenApp.hidden = false;
  }

  /* ---------- вход / регистрация ---------- */

  function setMode(next) {
    mode = next;
    const login = mode === 'login';
    tabLogin.classList.toggle('active', login);
    tabRegister.classList.toggle('active', !login);
    authSubmit.textContent = login ? 'Войти' : 'Создать кабинет';
    authHint.innerHTML = login
      ? 'Новый клиент кофейни? <a href="#register">Зарегистрируйтесь</a>'
      : 'Уже есть кабинет? <a href="#login">Войдите</a>';
    authPassword.autocomplete = login ? 'current-password' : 'new-password';
    authError.hidden = true;
  }

  /* ---------- «глазик» показа пароля ---------- */

  function setPasswordVisible(visible) {
    const shown = Boolean(visible);
    authPassword.type = shown ? 'text' : 'password';

    authEye.querySelector('.acc-eye-open').hidden = shown;
    authEye.querySelector('.acc-eye-off').hidden = !shown;

    const label = shown ? 'Скрыть пароль' : 'Показать пароль';
    authEye.setAttribute('aria-label', label);
    authEye.setAttribute('aria-pressed', String(shown));
    authEye.title = label;
  }

  authEye.addEventListener('click', () => {
    setPasswordVisible(authPassword.type === 'password');
    // курсор — в конец, иначе после переключения типа он прыгает в начало
    const end = authPassword.value.length;
    authPassword.focus();
    try {
      authPassword.setSelectionRange(end, end);
    } catch (_) {
      /* браузеры, не дающие работать с password-полем, просто не двигают курсор */
    }
  });

  document.getElementById('tab-login').addEventListener('click', () => setMode('login'));
  document.getElementById('tab-register').addEventListener('click', () => setMode('register'));
  authHint.addEventListener('click', (e) => {
    if (e.target.tagName === 'A') {
      e.preventDefault();
      setMode(mode === 'login' ? 'register' : 'login');
    }
  });

  authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const { value: login } = authLogin;
    const { value: password } = authPassword;
    const run = mode === 'login' ? Auth.login : Auth.register;

    authSubmit.disabled = true;
    try {
      const { ok, data } = await run(login, password);
      if (!ok) {
        authError.textContent = data?.message || 'Не удалось. Попробуйте ещё раз.';
        authError.hidden = false;
        return;
      }
      await refresh();
    } catch (_) {
      authError.textContent = 'Сервер недоступен.';
      authError.hidden = false;
    } finally {
      authSubmit.disabled = false;
    }
  });

  /* ---------- вкладки ---------- */

  function showPane(which) {
    tabProfile.classList.toggle('active', which === 'profile');
    tabKnowledge.classList.toggle('active', which === 'knowledge');
    tabCases.classList.toggle('active', which === 'cases');
    paneProfile.hidden = which !== 'profile';
    paneKnowledge.hidden = which !== 'knowledge';
    paneCases.hidden = which !== 'cases';
    if (which === 'cases') refreshCases();
  }

  tabProfile.addEventListener('click', () => showPane('profile'));
  tabKnowledge.addEventListener('click', () => showPane('knowledge'));
  tabCases.addEventListener('click', () => showPane('cases'));

  btnLogout.addEventListener('click', async () => {
    await Auth.logout();
    location.reload();
  });

  /* ---------- база знаний ---------- */

  let kbSectionsBuilt = false;

  async function buildKbEditor() {
    if (kbSectionsBuilt) return;
    const { ok, data } = await fetchJSON('/api/knowledge');
    if (!ok) return;

    const host = document.getElementById('kb-sections');
    for (const [name, text] of Object.entries(data.sections)) {
      const label = document.createElement('label');
      label.className = 'kb-field';
      label.innerHTML = `<span>${name}</span><textarea rows="7"></textarea>`;
      label.querySelector('textarea').value = text;
      label.querySelector('textarea').dataset.section = name;
      host.appendChild(label);
    }
    kbSectionsBuilt = true;
  }

  document.getElementById('kb-save').addEventListener('click', async () => {
    const statusEl = document.getElementById('kb-status');
    const sections = {};
    document.querySelectorAll('#kb-sections textarea').forEach((ta) => {
      sections[ta.dataset.section] = ta.value;
    });

    const { ok, data } = await fetchJSON('/api/knowledge', sections);
    statusEl.textContent = ok
      ? 'Сохранено — бот отвечает по новым данным.'
      : `Ошибка: ${data?.message || 'сервер недоступен'}`;
    setTimeout(() => { statusEl.textContent = ''; }, 4000);
  });

  async function fetchJSON(path, sections) {
    const res = await fetch('/api' + path, {
      method: sections ? 'PUT' : 'GET',
      headers: sections ? { 'Content-Type': 'application/json' } : {},
      body: sections ? JSON.stringify({ sections }) : undefined,
      credentials: 'same-origin',
    });
    let data = null;
    try { data = await res.json(); } catch (_) { /* ignore */ }
    return { ok: res.ok, data };
  }

  /* ---------- обращения: нужен человек (Практика №2б) ---------- */

  const CASE_STATUS = { new: 'ждёт ответа', answered: 'ответ уйдёт клиенту' };

  // Черновики ответов: список перечитывается каждые 10 секунд, и без этого
  // незапечатанный текст в textarea исчезал бы на глазах у менеджера.
  const drafts = new Map();

  async function postJSON(path, body) {
    const res = await fetch('/api' + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      credentials: 'same-origin',
    });
    let data = null;
    try { data = await res.json(); } catch (_) { /* ignore */ }
    return { ok: res.ok, data };
  }

  function casesSay(text) {
    casesStatus.textContent = text;
    setTimeout(() => { casesStatus.textContent = ''; }, 5000);
  }

  function caseCard(item) {
    const card = document.createElement('article');
    card.className = item.reply ? 'case case--done' : 'case';

    const meta = document.createElement('p');
    meta.className = 'case-meta';
    meta.textContent = `${new Date(item.created_at).toLocaleString('ru')} · ${item.session_id} · ${CASE_STATUS[item.status] || item.status}`;

    const question = document.createElement('p');
    question.className = 'case-q';
    question.textContent = item.question;

    card.append(meta, question);

    if (item.reply) {
      const answer = document.createElement('p');
      answer.className = 'case-a';
      answer.textContent = `Ответ: ${item.reply}`;
      card.append(answer);
      return card;
    }

    const form = document.createElement('form');
    form.className = 'case-form';
    const input = document.createElement('textarea');
    input.rows = 3;
    input.placeholder = 'Ответ клиенту — он придёт ему в Telegram';
    input.value = drafts.get(item.id) || '';
    input.addEventListener('input', () => {
      if (input.value.trim()) drafts.set(item.id, input.value);
      else drafts.delete(item.id);
    });
    const btn = document.createElement('button');
    btn.className = 'btn btn-primary btn-sm';
    btn.type = 'submit';
    btn.textContent = 'Ответить';
    form.append(input, btn);

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const reply = input.value.trim();
      if (!reply) return;
      input.disabled = true;
      const { ok, data } = await postJSON(`/handoffs/${item.id}/reply`, { reply });
      input.disabled = false;
      if (!ok) return casesSay(data?.message || 'Сервер не ответил.');
      drafts.delete(item.id);
      casesSay('Ответ отправлен, бот отнесёт его клиенту.');
      await refreshCases();
    });

    card.append(form);
    return card;
  }

  async function refreshCases() {
    const { ok, data } = await fetchJSON('/handoffs');
    if (!ok) return;

    casesList.textContent = '';
    const waiting = data.handoffs.filter((item) => item.status === 'new').length;
    tabCases.textContent = waiting ? `Обращения: ${waiting}` : 'Обращения';

    if (!data.handoffs.length) {
      casesList.textContent = 'Пока пусто: бот никого не звал.';
      return;
    }
    casesList.append(...data.handoffs.map(caseCard));
  }

  // Менеджер держит вкладку открытой — подтягиваем новые обращения сами.
  setInterval(() => {
    if (!paneCases.hidden) refreshCases();
  }, 10000);

  await refresh();
})();
