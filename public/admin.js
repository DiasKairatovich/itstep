/* =========================================
   Coffee Point — админка базы знаний
   Список документов, загрузка, переиндексация, удаление.
   ========================================= */
'use strict';

(function () {
  const MAX_DOC_BYTES = 1024 * 1024;

  const screenAuth = document.getElementById('screen-auth');
  const screenDocs = document.getElementById('screen-docs');
  const authForm = document.getElementById('auth-form');
  const authError = document.getElementById('auth-error');
  const authSubmit = document.getElementById('auth-submit');
  const uploadForm = document.getElementById('upload-form');
  const uploadFile = document.getElementById('upload-file');
  const uploadBtn = document.getElementById('upload-btn');
  const uploadStatus = document.getElementById('upload-status');
  const docsBody = document.getElementById('docs-body');
  const threshold = document.getElementById('threshold');

  /* ---------- запросы ---------- */

  async function request(path, options = {}) {
    const res = await fetch('/api' + path, {
      method: options.method || 'GET',
      headers: options.body ? { 'Content-Type': 'application/json' } : {},
      body: options.body ? JSON.stringify(options.body) : undefined,
      credentials: 'same-origin',
    });
    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      /* сервер отдал не JSON */
    }
    return { ok: res.ok, data };
  }

  function notify(text, failed) {
    uploadStatus.textContent = text;
    uploadStatus.dataset.state = failed ? 'off' : 'on';
    setTimeout(() => {
      uploadStatus.textContent = '';
    }, 6000);
  }

  /* ---------- вход ---------- */

  authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authSubmit.disabled = true;
    try {
      const { value: login } = document.getElementById('auth-login');
      const { value: password } = document.getElementById('auth-password');
      const { ok, data } = await Auth.login(login, password);
      if (!ok) {
        authError.textContent = data?.message || 'Не получилось войти.';
        authError.hidden = false;
        return;
      }
      if (data.user.role !== 'admin') {
        authError.textContent = 'Документы загружает только администратор.';
        authError.hidden = false;
        return;
      }
      showDocs();
    } finally {
      authSubmit.disabled = false;
    }
  });

  function showDocs() {
    screenAuth.hidden = true;
    screenDocs.hidden = false;
    return refresh();
  }

  /* ---------- список ---------- */

  function row(doc) {
    const tr = document.createElement('tr');

    const title = document.createElement('td');
    title.textContent = doc.title;

    const chunks = document.createElement('td');
    chunks.textContent = doc.chunks;

    const created = document.createElement('td');
    created.textContent = new Date(doc.created_at).toLocaleString('ru');

    const actions = document.createElement('td');
    const reindex = button('Переиндексировать', () => act(`/documents/${doc.id}/reindex`, doc.title));
    const remove = button('Удалить', () => act(`/documents/${doc.id}`, doc.title, 'DELETE'));
    reindex.className = 'rag-link';
    remove.className = 'rag-link rag-link-danger';
    actions.append(reindex, remove);

    tr.append(title, chunks, created, actions);
    return tr;
  }

  function button(text, onClick) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = text;
    b.addEventListener('click', onClick);
    return b;
  }

  async function refresh() {
    const { ok, data } = await request('/documents');
    if (!ok) {
      screenDocs.hidden = true;
      screenAuth.hidden = false;
      return;
    }

    docsBody.textContent = '';
    if (!data.documents.length) {
      docsBody.innerHTML = '<tr><td colspan="4" class="rag-empty">Документов пока нет.</td></tr>';
    } else {
      docsBody.append(...data.documents.map(row));
    }

    threshold.textContent =
      `Бот отвечает, если лучшее сходство ≥ ${data.threshold}; в промпт попадает ${data.top} ближайших фрагмента.`;
  }

  async function act(path, title, method) {
    if (method === 'DELETE' && !confirm(`Удалить «${title}» и его фрагменты?`)) return;

    notify('…');
    const { ok, data } = await request(path, method ? { method } : { method: 'POST' });
    if (!ok) return notify(data?.message || 'Сервер не ответил.', true);
    notify(method === 'DELETE' ? 'Удалено.' : 'Готово.');
    await refresh();
  }

  /* ---------- загрузка ---------- */

  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const file = uploadFile.files[0];
    if (!file) return notify('Выберите файл.', true);
    if (!/\.(txt|md)$/i.test(file.name)) return notify('Подходят только .txt и .md.', true);
    if (file.size > MAX_DOC_BYTES) return notify('Файл больше 1 МБ.', true);

    uploadBtn.disabled = true;
    notify('Читаю и индексирую…');

    try {
      const content = await file.text();
      const { ok, data } = await request('/documents', {
        method: 'POST',
        body: { filename: file.name, content },
      });
      if (!ok) return notify(data?.message || 'Сервер не ответил.', true);
      notify(`Загружено: ${data.document.chunks} фрагментов.`);
      uploadForm.reset();
      await refresh();
    } catch (err) {
      notify('Не удалось загрузить файл.', true);
    } finally {
      uploadBtn.disabled = false;
    }
  });

  /* ---------- старт ---------- */

  (async () => {
    const { ok, data } = await Auth.me();
    if (ok && data.user && data.user.role === 'admin') return showDocs();
    screenAuth.hidden = false;
  })();
})();
