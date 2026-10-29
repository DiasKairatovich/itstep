/* =========================================
   Coffee Point — клиент аутентификации
   Общая для всех страниц: fetch-обёртки + ссылка «Кабинет» в навбаре
   ========================================= */
'use strict';

const Auth = (() => {
  async function request(path, options) {
    const res = await fetch('/api/auth/' + path, {
      method: options.method || 'GET',
      headers: options.body ? { 'Content-Type': 'application/json' } : {},
      body: options.body ? JSON.stringify(options.body) : undefined,
      credentials: 'same-origin',
    });
    let data = null;
    try {
      data = await res.json();
    } catch (_) { /* страница отдала не JSON */ }
    return { ok: res.ok, status: res.status, data };
  }

  return {
    me: () => request('me', {}),
    login: (login, password) => request('login', { method: 'POST', body: { login, password } }),
    register: (login, password) => request('register', { method: 'POST', body: { login, password } }),
    logout: () => request('logout', { method: 'POST' }),
  };
})();

// Пункт «Кабинет» в навбаре: показать имя вошедшего.
document.addEventListener('DOMContentLoaded', async () => {
  const link = document.getElementById('nav-account');
  if (!link) return;
  try {
    const { ok, data } = await Auth.me();
    if (ok && data.user) {
      link.textContent = data.user.login;
      link.title = data.user.role === 'admin' ? 'Администратор' : 'Клиент';
    }
  } catch (_) {
    /* сервер не отвечает — оставляем ссылку как есть */
  }
});
