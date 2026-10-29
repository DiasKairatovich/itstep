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

  const tabProfile = document.getElementById('tab-profile');
  const tabKnowledge = document.getElementById('tab-knowledge');
  const paneProfile = document.getElementById('pane-profile');
  const paneKnowledge = document.getElementById('pane-knowledge');
  const profileLogin = document.getElementById('profile-login');
  const profileRole = document.getElementById('profile-role');
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

    profileLogin.textContent = user.login;
    profileRole.textContent = user.role === 'admin' ? 'Администратор' : 'Клиент';
    tabKnowledge.hidden = user.role !== 'admin';

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
    const knowledge = which === 'knowledge';
    tabProfile.classList.toggle('active', !knowledge);
    tabKnowledge.classList.toggle('active', knowledge);
    paneProfile.hidden = knowledge;
    paneKnowledge.hidden = !knowledge;
  }

  tabProfile.addEventListener('click', () => showPane('profile'));
  tabKnowledge.addEventListener('click', () => showPane('knowledge'));

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

  await refresh();
})();
