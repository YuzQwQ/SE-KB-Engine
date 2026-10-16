(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const statuses = {stopped:'已停止', starting:'启动中', running:'运行中', stopping:'停止中', failed:'异常', timeout:'启动超时'};
  let api = null, cursor = 0, logs = [], source = 'all', state = null;
  let pending = false, connected = false, searching = null, toastTimer = null;
  const exitDialog = $('exitDialog');
  const output = $('logOutput');

  function notify(message) {
    $('toast').textContent = message;
    $('toast').hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { $('toast').hidden = true; }, 5500);
  }

  function updateControls() {
    const busy = pending || !connected || Boolean(state?.busy);
    document.querySelectorAll('[data-action]').forEach(button => {
      const {action, target} = button.dataset;
      const service = state?.services[target];
      button.disabled = busy || (action === 'start' && Boolean(service?.pid)) ||
        (action === 'stop' && target !== 'all' && !service?.pid);
    });
    document.querySelectorAll('[data-open]').forEach(button => {
      button.disabled = !connected || state?.services[button.dataset.open]?.status !== 'running';
    });
    for (const name of ['web','api']) {
      $(name+'Port').disabled = busy || Boolean(state?.services[name]?.pid);
    }
    $('confirmExit').disabled = pending || Boolean(state?.busy);
  }

  function renderState(next) {
    state = next;
    let running = 0;
    for (const [name, service] of Object.entries(next.services)) {
      const pill = $(name+'Status');
      pill.className = 'status-pill ' + service.status;
      pill.lastElementChild.textContent = statuses[service.status] || service.status;
      document.querySelector(`[data-service="${name}"]`).dataset.status = service.status;
      $(name+'Detail').textContent = service.detail;
      $(name+'Detail').title = service.detail;
      $(name+'Pid').textContent = 'PID ' + (service.pid || '—');
      if (service.pid) $(name+'Port').value = service.port;
      if (service.status === 'running') running++;
    }
    $('serviceSummary').textContent = `${running} / 2 服务运行中`;
    if (next.close_requested && !exitDialog.open) showExit();
    updateControls();
  }

  function showExit() {
    if (!exitDialog.open) exitDialog.showModal();
    $('cancelExit').focus();
  }

  function renderLogs() {
    const query = $('logSearch').value.toLocaleLowerCase();
    const level = $('logLevel').value;
    const filtered = logs.filter(row => (source === 'all' || row.source === source) &&
      (level === 'all' || row.level === level) && row.text.toLocaleLowerCase().includes(query));
    const scroll = output.scrollTop;
    const fragment = document.createDocumentFragment();
    if (filtered.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'empty-logs';
      const title = document.createElement('strong');
      title.textContent = logs.length ? '没有匹配的日志' : '一切就绪，等待你的第一次启动';
      const hint = document.createElement('span');
      hint.textContent = logs.length ? '试试调整来源、级别或搜索关键词。' : '服务的运行轨迹，将从这里开始。';
      empty.append(title,hint);
      fragment.append(empty);
    } else {
      for (const row of filtered) {
        const line = document.createElement('div');
        line.className = 'log-line ' + row.level;
        for (const [cls, text] of [['log-time',row.time],['log-source',row.source.toUpperCase()],
          ['log-level',row.level === 'warning' ? 'WARN' : row.level.toUpperCase()],['log-text',row.text]]) {
          const part = document.createElement('span');
          part.className = cls;
          part.textContent = text;
          line.append(part);
        }
        fragment.append(line);
      }
    }
    output.replaceChildren(fragment);
    $('logCount').textContent = logs.length;
    $('logSummary').textContent = logs.length ? `显示 ${filtered.length} 条 · 最多保留 2000 条` : '等待服务输出';
    output.scrollTop = $('autoFollow').checked ? output.scrollHeight : scroll;
  }

  async function call(method, ...args) {
    if (!api) { notify('桌面连接尚未建立，请从启动工作台入口打开。'); return null; }
    try {
      const result = await api[method](...args);
      if (result && !result.ok) notify(result.error || '操作未完成，请查看日志');
      return result;
    } catch (error) {
      notify('操作失败：' + String(error));
      return null;
    }
  }

  async function command(action, target) {
    if (pending || !connected || state?.busy) return;
    const ports = {web:$('webPort').value, api:$('apiPort').value};
    if (action !== 'stop') {
      for (const [name,value] of Object.entries(ports)) {
        if (!/^\d+$/.test(value) || Number(value) < 1024 || Number(value) > 65535) {
          notify('端口需为 1024–65535 之间的整数'); $(name+'Port').focus(); return;
        }
      }
      if (ports.web === ports.api) { notify('Web 和 API 必须使用不同端口'); return; }
    }
    pending = true; updateControls();
    try { await call('command',action,target,ports,$('debugMode').checked); }
    finally { pending = false; updateControls(); }
  }

  async function poll() {
    if (!api) return;
    try {
      const next = await api.poll(cursor);
      connected = true;
      $('connection').className = 'connection connected';
      $('connectionText').textContent = '桌面已连接';
      renderState(next);
      cursor = next.cursor;
      if (next.logs.length) {
        logs.push(...next.logs);
        logs = logs.slice(-2000);
        renderLogs();
      }
    } catch (error) {
      connected = false;
      $('connection').className = 'connection disconnected';
      $('connectionText').textContent = '连接中断，正在重试';
      updateControls();
    } finally { setTimeout(poll, 500); }
  }

  document.querySelectorAll('[data-action]').forEach(button => {
    button.addEventListener('click',() => command(button.dataset.action,button.dataset.target));
  });
  document.querySelectorAll('[data-open]').forEach(button => {
    button.addEventListener('click',() => call('open_service',button.dataset.open));
  });
  document.querySelectorAll('[data-source]').forEach(button => {
    button.addEventListener('click',() => {
      source = button.dataset.source;
      document.querySelectorAll('[data-source]').forEach(tab => {
        const active = tab === button;
        tab.classList.toggle('active',active);
        tab.setAttribute('aria-pressed',String(active));
      });
      renderLogs();
    });
  });
  $('logSearch').addEventListener('input',() => {
    clearTimeout(searching); searching = setTimeout(renderLogs,150);
  });
  $('logLevel').addEventListener('change',renderLogs);
  $('autoFollow').addEventListener('change',() => {
    if ($('autoFollow').checked) output.scrollTop = output.scrollHeight;
  });
  $('clearLogs').addEventListener('click',async () => {
    if ((await call('clear_logs'))?.ok) { logs = []; renderLogs(); }
  });
  $('exitButton').addEventListener('click',showExit);
  async function cancelExit() { exitDialog.close(); await call('cancel_exit'); }
  $('cancelExit').addEventListener('click',cancelExit);
  exitDialog.addEventListener('cancel',event => { event.preventDefault(); cancelExit(); });
  $('confirmExit').addEventListener('click',async () => {
    if (pending || state?.busy) return;
    pending = true; updateControls();
    try { await call('exit'); }
    finally { pending = false; updateControls(); }
  });
  $('logsNav').addEventListener('click',() => {
    document.querySelector('.terminal').scrollIntoView({behavior:'smooth'}); output.focus({preventScroll:true});
  });
  $('overviewNav').addEventListener('click',() => window.scrollTo({top:0,behavior:'smooth'}));
  // No anchors or user-controlled navigation are allowed in the privileged window.
  document.addEventListener('click',event => { if (event.target.closest('a')) event.preventDefault(); });
  document.addEventListener('dragover',event => event.preventDefault());
  document.addEventListener('drop',event => event.preventDefault());
  function connect() {
    if (api || !window.pywebview?.api) return;
    api = window.pywebview.api;
    poll();
  }
  window.addEventListener('pywebviewready',connect);
  updateControls(); connect();
  setTimeout(() => {
    if (!api) {
      $('connection').className = 'connection disconnected';
      $('connectionText').textContent = '界面预览 · 请从桌面入口启动';
    }
  },1800);
})();
