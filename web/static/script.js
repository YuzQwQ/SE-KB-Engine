/**
 * 知识库构建系统 - 前端脚本
 */

// ============================================================
// 爬取功能相关 DOM 元素
// ============================================================
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const limitSelect = document.getElementById('limitSelect');
const typeSelect = document.getElementById('typeSelect');
const manualUrlInput = document.getElementById('manualUrlInput');
const manualCrawlBtn = document.getElementById('manualCrawlBtn');
const statusBadge = document.getElementById('statusBadge');
const progressText = document.getElementById('progressText');
const progressFill = document.getElementById('progressFill');
const logContainer = document.getElementById('logContainer');
const clearBtn = document.getElementById('clearBtn');
const resultSection = document.getElementById('resultSection');
const resultList = document.getElementById('resultList');
const resultCount = document.getElementById('resultCount');

// ============================================================
// 精炼功能相关 DOM 元素
// ============================================================
const refineDateSelect = document.getElementById('refineDateSelect');
const refineTimeSelect = document.getElementById('refineTimeSelect');
const dryRunCheck = document.getElementById('dryRunCheck');
const previewBtn = document.getElementById('previewBtn');
const refineBtn = document.getElementById('refineBtn');
const previewResult = document.getElementById('previewResult');
const previewContent = document.getElementById('previewContent');
const refineProgressSection = document.getElementById('refineProgressSection');
const refineStatusBadge = document.getElementById('refineStatusBadge');
const refineProgressText = document.getElementById('refineProgressText');
const refineProgressFill = document.getElementById('refineProgressFill');
const refineLogContainer = document.getElementById('refineLogContainer');
const clearRefineLogBtn = document.getElementById('clearRefineLogBtn');
const refineStatsSection = document.getElementById('refineStatsSection');
const refineStatsGrid = document.getElementById('refineStatsGrid');

// ============================================================
// 语义检索功能相关 DOM 元素
// ============================================================
const semanticSearchInput = document.getElementById('semanticSearchInput');
const semanticIntentSelect = document.getElementById('semanticIntentSelect');
const semanticTopKSelect = document.getElementById('semanticTopKSelect');
const semanticSearchBtn = document.getElementById('semanticSearchBtn');
const semanticProgressSection = document.getElementById('semanticProgressSection');
const semanticStatusBadge = document.getElementById('semanticStatusBadge');
const semanticLogContainer = document.getElementById('semanticLogContainer');
const semanticResultSection = document.getElementById('semanticResultSection');
const semanticResultList = document.getElementById('semanticResultList');
const semanticResultCount = document.getElementById('semanticResultCount');
const serviceKeyInput = document.getElementById('serviceKeyInput');
const serviceKeyToggle = document.getElementById('serviceKeyToggle');
const keyStatus = document.getElementById('keyStatus');
const appNotice = document.getElementById('appNotice');

// ============================================================
// Obsidian Vault 与知识图谱
// ============================================================
const vaultRefreshBtn = document.getElementById('vaultRefreshBtn');
const vaultAvailability = document.getElementById('vaultAvailability');
const vaultName = document.getElementById('vaultName');
const vaultNoteCount = document.getElementById('vaultNoteCount');
const vaultLastExport = document.getElementById('vaultLastExport');
const vaultDiagnostic = document.getElementById('vaultDiagnostic');
const vaultSourceInput = document.getElementById('vaultSourceInput');
const vaultEntityKindsInput = document.getElementById('vaultEntityKindsInput');
const vaultQualityInput = document.getElementById('vaultQualityInput');
const vaultPreviewBtn = document.getElementById('vaultPreviewBtn');
const vaultExportBtn = document.getElementById('vaultExportBtn');
const vaultPlanSection = document.getElementById('vaultPlanSection');
const vaultPlanCount = document.getElementById('vaultPlanCount');
const vaultPlanSummary = document.getElementById('vaultPlanSummary');
const vaultPlanBody = document.getElementById('vaultPlanBody');
const vaultProgressSection = document.getElementById('vaultProgressSection');
const vaultCancelBtn = document.getElementById('vaultCancelBtn');
const vaultStatusBadge = document.getElementById('vaultStatusBadge');
const vaultProgressText = document.getElementById('vaultProgressText');
const vaultProgressFill = document.getElementById('vaultProgressFill');
const vaultLogContainer = document.getElementById('vaultLogContainer');
const vaultRelationKind = document.getElementById('vaultRelationKind');
const vaultGraphRefreshBtn = document.getElementById('vaultGraphRefreshBtn');
const vaultGraphStatus = document.getElementById('vaultGraphStatus');
const vaultGraph = document.getElementById('vaultGraph');
const vaultRelationshipBody = document.getElementById('vaultRelationshipBody');

// ============================================================
// 状态
// ============================================================
let isRunning = false;
let isRefining = false;
let pollInterval = null;
let refinePollInterval = null;
let lastLogCount = 0;
let lastRefineLogCount = 0;
let noticeTimer = null;
let vaultPollInterval = null;
let activeVaultJobId = null;

function cookieValue(name) {
    const item = document.cookie.split('; ').find(row => row.startsWith(`${name}=`));
    return item ? decodeURIComponent(item.split('=')[1]) : '';
}

function serviceHeaders(mutating = false) {
    const key = serviceKeyInput.value.trim();
    if (key) sessionStorage.setItem('kb_api_key', key);
    const token = key || sessionStorage.getItem('kb_api_key') || '';
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (mutating) headers['X-CSRF-Token'] = cookieValue('kb_csrf');
    return headers;
}

function updateCredentialStatus() {
    const hasKey = Boolean(serviceKeyInput.value.trim());
    keyStatus.textContent = hasKey ? '已设置 · 仅会话保存' : '未设置 · 仅会话保存';
    keyStatus.classList.toggle('ready', hasKey);
}

function showNotice(message, type = 'error') {
    if (noticeTimer) window.clearTimeout(noticeTimer);
    appNotice.textContent = message;
    appNotice.className = `app-notice ${type}`;
    appNotice.hidden = false;
    noticeTimer = window.setTimeout(() => {
        appNotice.hidden = true;
    }, 4500);
}

function setButtonContent(button, label, symbol = '') {
    const text = document.createElement('span');
    text.className = 'btn-text';
    text.textContent = label;
    button.replaceChildren(text);
    if (symbol) {
        const icon = document.createElement('span');
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = symbol;
        button.appendChild(icon);
    }
}

function apiErrorMessage(data, fallback = '请求失败') {
    if (typeof data?.error === 'string') return data.error;
    return data?.error?.message || data?.error?.code || data?.message || fallback;
}

// 状态映射
const statusMap = {
    'idle': { text: '等待中', class: '' },
    'running': { text: '运行中', class: 'running' },
    'completed': { text: '已完成', class: 'completed' },
    'error': { text: '出错', class: 'error' },
    'cancelled': { text: '已取消', class: 'error' },
    'interrupted': { text: '已中断', class: 'error' }
};

// ============================================================
// 初始化
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    serviceKeyInput.value = sessionStorage.getItem('kb_api_key') || '';
    updateCredentialStatus();
    serviceKeyInput.addEventListener('input', () => {
        const key = serviceKeyInput.value.trim();
        if (key) sessionStorage.setItem('kb_api_key', key);
        else sessionStorage.removeItem('kb_api_key');
        updateCredentialStatus();
    });
    serviceKeyInput.addEventListener('change', () => {
        if (serviceKeyInput.value.trim()) refreshAuthorizedData();
    });
    serviceKeyToggle.addEventListener('click', () => {
        const reveal = serviceKeyInput.type === 'password';
        serviceKeyInput.type = reveal ? 'text' : 'password';
        serviceKeyToggle.textContent = reveal ? '隐藏' : '显示';
        serviceKeyToggle.setAttribute('aria-label', reveal ? '隐藏服务密钥' : '显示服务密钥');
        serviceKeyToggle.setAttribute('aria-pressed', String(reveal));
    });

    // Tab 切换
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
        btn.addEventListener('keydown', onTabKeydown);
    });
    switchTab(sessionStorage.getItem('kb_active_tab') || 'crawl');
    
    // 爬取功能事件
    searchBtn.addEventListener('click', startTask);
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startTask();
    });
    manualCrawlBtn.addEventListener('click', startManualCrawl);
    manualUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startManualCrawl();
    });
    clearBtn.addEventListener('click', clearLogs);
    
    // 精炼功能事件
    previewBtn.addEventListener('click', previewRefine);
    refineBtn.addEventListener('click', startRefine);
    clearRefineLogBtn.addEventListener('click', clearRefineLogs);
    refineDateSelect.addEventListener('change', onDateChange);
    
    if (serviceKeyInput.value.trim()) refreshAuthorizedData();
    
    // 语义检索功能事件
    semanticSearchBtn.addEventListener('click', startSemanticSearch);
    semanticSearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startSemanticSearch();
    });

    vaultRefreshBtn.addEventListener('click', loadVaultStatus);
    vaultPreviewBtn.addEventListener('click', previewVaultExport);
    vaultExportBtn.addEventListener('click', startVaultExport);
    vaultCancelBtn.addEventListener('click', cancelVaultExport);
    vaultGraphRefreshBtn.addEventListener('click', loadVaultRelationships);
    vaultRelationKind.addEventListener('change', loadVaultRelationships);
});

function refreshAuthorizedData() {
    checkStatus();
    loadArtifactsDates();
    loadVaultStatus();
}

// ============================================================
// Tab 切换
// ============================================================
function switchTab(tabName) {
    const availableTabs = Array.from(document.querySelectorAll('.tab-btn'));
    if (!availableTabs.some(btn => btn.dataset.tab === tabName)) tabName = 'crawl';
    sessionStorage.setItem('kb_active_tab', tabName);

    // 更新 Tab 按钮状态
    availableTabs.forEach(btn => {
        const active = btn.dataset.tab === tabName;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-selected', String(active));
        btn.tabIndex = active ? 0 : -1;
    });
    
    // 更新 Tab 内容显示
    document.querySelectorAll('.tab-content').forEach(content => {
        const active = content.id === tabName + '-tab';
        content.classList.toggle('active', active);
        content.hidden = !active;
    });
    if (tabName === 'vault' && serviceKeyInput.value.trim()) loadVaultStatus();
}

function onTabKeydown(event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const tabs = Array.from(document.querySelectorAll('.tab-btn'));
    const current = tabs.indexOf(event.currentTarget);
    let next = current;
    if (event.key === 'ArrowRight') next = (current + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (current - 1 + tabs.length) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    switchTab(tabs[next].dataset.tab);
    tabs[next].focus();
}

// ============================================================
// 爬取功能逻辑
// ============================================================
async function startTask() {
    if (isRunning) return;
    
    const query = searchInput.value.trim();
    if (!query) {
        showNotice('请输入搜索关键词');
        searchInput.focus();
        return;
    }
    
    isRunning = true;
    updateUIState(true);
    clearLogs();
    
    try {
        const payload = {
            query: query,
            limit: parseInt(limitSelect.value)
        };
        
        if (typeSelect.value) {
            payload.types = [typeSelect.value];
        }

        const response = await fetch('/api/start', {
            method: 'POST',
            headers: serviceHeaders(true),
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            appendLog('任务已启动...');
            pollStatus();
        } else {
            const errorMsg = apiErrorMessage(data, '未知错误');
            appendLog(`启动失败: ${errorMsg}`, 'error');
            isRunning = false;
            updateUIState(false, 'error');
        }
    } catch (error) {
        appendLog(`请求失败: ${error.message}`, 'error');
        isRunning = false;
        updateUIState(false, 'error');
    }
}

async function startManualCrawl() {
    if (isRunning) return;
    
    let url = manualUrlInput.value.trim();
    if (!url) {
        showNotice('请输入要采集的 URL');
        manualUrlInput.focus();
        return;
    }
    
    if (!/^https?:\/\//i.test(url)) {
        url = `https://${url}`;
    }
    
    try {
        new URL(url);
    } catch (error) {
        showNotice('URL 格式不正确，请检查后重试');
        manualUrlInput.focus();
        return;
    }
    
    isRunning = true;
    updateUIState(true);
    clearLogs();
    
    try {
        const payload = {
            url: url
        };
        
        if (typeSelect.value) {
            payload.types = [typeSelect.value];
        }
        
        const response = await fetch('/api/crawl-url', {
            method: 'POST',
            headers: serviceHeaders(true),
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            appendLog('手动爬取任务已启动...');
            pollStatus();
        } else {
            const errorMsg = apiErrorMessage(data, '未知错误');
            appendLog(`启动失败: ${errorMsg}`, 'error');
            isRunning = false;
            updateUIState(false, 'error');
        }
    } catch (error) {
        appendLog(`请求失败: ${error.message}`, 'error');
        isRunning = false;
        updateUIState(false, 'error');
    }
}

async function checkStatus() {
    try {
        const response = await fetch('/api/status', { headers: serviceHeaders() });
        const data = await response.json();
        
        if (data.status === 'running') {
            isRunning = true;
            updateUIState(true);
            pollStatus();
        }
    } catch (error) {
        console.error('状态检查失败:', error);
    }
}

function pollStatus() {
    if (pollInterval) clearInterval(pollInterval);
    
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/status', { headers: serviceHeaders() });
            const data = await response.json();
            
            // 更新进度条
            updateProgress(data.progress);
            
            // 更新日志
            if (data.logs && data.logs.length > lastLogCount) {
                const newLogs = data.logs.slice(lastLogCount);
                newLogs.forEach(log => appendLog(log));
                lastLogCount = data.logs.length;
            }
            
            // 检查是否完成
            if (data.status !== 'running') {
                clearInterval(pollInterval);
                isRunning = false;
                
                if (data.status === 'completed') {
                    updateUIState(false, 'completed');
                    appendLog('任务完成！', 'success');
                    displayResults(data.results);
                } else if (data.status === 'error') {
                    updateUIState(false, 'error');
                    appendLog(`任务出错: ${data.error}`, 'error');
                } else {
                    updateUIState(false);
                }
            }
        } catch (error) {
            console.error('轮询失败:', error);
        }
    }, 1000);
}

function updateUIState(running, state = 'idle') {
    searchBtn.disabled = running;
    searchInput.disabled = running;
    limitSelect.disabled = running;
    typeSelect.disabled = running;
    manualUrlInput.disabled = running;
    manualCrawlBtn.disabled = running;
    
    if (running) {
        setButtonContent(searchBtn, '运行中…', '···');
        state = 'running';
    } else {
        setButtonContent(searchBtn, '开始构建', '→');
    }
    const status = statusMap[state] || statusMap.idle;
    statusBadge.className = `status-badge ${status.class}`.trim();
    statusBadge.textContent = status.text;
}

function updateProgress(percent) {
    const safePercent = Math.min(100, Math.max(0, Number(percent) || 0));
    progressText.textContent = `${safePercent}%`;
    progressFill.style.width = `${safePercent}%`;
    progressFill.parentElement.setAttribute('aria-valuenow', String(safePercent));
}

function appendLog(logEntry, type = 'info') {
    let message = logEntry;
    let time = new Date().toLocaleTimeString();
    let level = type;

    if (typeof logEntry === 'object' && logEntry !== null) {
        message = logEntry.message || JSON.stringify(logEntry);
        if (logEntry.time) time = logEntry.time;
        if (logEntry.level) level = logEntry.level;
    }

    if (logContainer.querySelector('.log-placeholder')) logContainer.replaceChildren();
    const div = document.createElement('div');
    div.className = `log-entry ${level}`;
    
    const timeSpan = document.createElement('span');
    timeSpan.className = 'log-time';
    timeSpan.textContent = `[${time}]`;
    div.append(timeSpan, document.createTextNode(` ${message}`));
    
    logContainer.appendChild(div);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function clearLogs() {
    logContainer.replaceChildren();
    lastLogCount = 0;
    resultSection.style.display = 'none';
    resultList.replaceChildren();
    resultCount.textContent = '';
    updateProgress(0);
}

function displayResults(results) {
    if (!results || results.length === 0) {
        showNotice('任务已完成，但没有生成可展示的抽取结果');
        return;
    }
    
    resultSection.style.display = 'block';
    resultList.replaceChildren();
    resultCount.textContent = `${results.length} 条`;
    
    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'result-item';
        const header = document.createElement('div');
        header.className = 'result-header';
        const type = document.createElement('span');
        type.className = 'result-type';
        type.textContent = item.type || '未知类型';
        const source = document.createElement('span');
        source.className = 'result-source';
        source.textContent = item.source || '未知来源';
        const content = document.createElement('div');
        content.className = 'result-content';
        content.textContent = item.content || '';
        header.append(type, source);
        div.append(header, content);
        resultList.appendChild(div);
    });
}

// ============================================================
// 精炼功能逻辑
// ============================================================
async function loadArtifactsDates() {
    try {
        const response = await fetch('/api/artifacts/dates', { headers: serviceHeaders() });
        const dates = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(dates));
        
        refineDateSelect.innerHTML = '<option value="">全部日期</option>';
        dates.forEach(date => {
            const option = document.createElement('option');
            option.value = date;
            option.textContent = date;
            refineDateSelect.appendChild(option);
        });
    } catch (error) {
        console.error('加载日期失败:', error);
    }
}

async function onDateChange() {
    const date = refineDateSelect.value;
    if (!date) {
        refineTimeSelect.innerHTML = '<option value="">全部时间</option>';
        return;
    }
    
    try {
        const response = await fetch(`/api/artifacts/times?date=${encodeURIComponent(date)}`, {
            headers: serviceHeaders()
        });
        const times = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(times));
        
        refineTimeSelect.innerHTML = '<option value="">全部时间</option>';
        times.forEach(item => {
            const option = document.createElement('option');
            // 兼容旧接口（直接返回字符串）和新接口（返回对象）
            if (typeof item === 'string') {
                option.value = item;
                option.textContent = item;
            } else {
                option.value = item.time;
                option.textContent = `${item.time} (${item.count} 文件)`;
            }
            refineTimeSelect.appendChild(option);
        });
    } catch (error) {
        console.error('加载时间失败:', error);
    }
}

async function previewRefine() {
    const date = refineDateSelect.value;
    const time = refineTimeSelect.value;
    
    previewResult.style.display = 'block';
    previewContent.replaceChildren();
    const loading = document.createElement('div');
    loading.className = 'loading';
    loading.textContent = '正在分析…';
    previewContent.appendChild(loading);
    
    try {
        const response = await fetch('/api/refine/preview', {
            method: 'POST',
            headers: serviceHeaders(true),
            body: JSON.stringify({ date, time })
        });
        
        const data = await response.json();
        if (!response.ok || data.error) {
            previewContent.textContent = `分析失败: ${apiErrorMessage(data)}`;
        } else {
            previewContent.replaceChildren();
            [
                `找到 ${data.total_files} 个文件`,
                `包含 ${data.total_items} 条知识条目`,
                `预计生成 ${data.estimated_clusters} 个知识簇`
            ].forEach(text => {
                const line = document.createElement('p');
                line.textContent = text;
                previewContent.appendChild(line);
            });
        }
    } catch (error) {
        previewContent.textContent = `请求失败: ${error.message}`;
    }
}

async function startRefine() {
    if (isRefining) return;
    
    isRefining = true;
    updateRefineUIState(true);
    clearRefineLogs();
    
    const date = refineDateSelect.value;
    const time = refineTimeSelect.value;
    const dryRun = dryRunCheck.checked;
    
    try {
        const response = await fetch('/api/refine/start', {
            method: 'POST',
            headers: serviceHeaders(true),
            body: JSON.stringify({ date, time, dry_run: dryRun })
        });
        
        const data = await response.json();
        if (response.ok) {
            appendRefineLog('精炼任务已启动...');
            pollRefineStatus();
        } else {
            const errorMsg = apiErrorMessage(data, '未知错误');
            appendRefineLog(`启动失败: ${errorMsg}`, 'error');
            isRefining = false;
            updateRefineUIState(false, 'error');
        }
    } catch (error) {
        appendRefineLog(`请求失败: ${error.message}`, 'error');
        isRefining = false;
        updateRefineUIState(false, 'error');
    }
}

function pollRefineStatus() {
    if (refinePollInterval) clearInterval(refinePollInterval);
    
    refinePollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/refine/status', { headers: serviceHeaders() });
            const data = await response.json();
            
            // 更新进度
            updateRefineProgress(data.progress);
            
            // 更新日志
            if (data.logs && data.logs.length > lastRefineLogCount) {
                const newLogs = data.logs.slice(lastRefineLogCount);
                newLogs.forEach(log => appendRefineLog(log));
                lastRefineLogCount = data.logs.length;
            }
            
            // 检查是否完成
            if (data.status !== 'running') {
                clearInterval(refinePollInterval);
                isRefining = false;
                
                if (data.status === 'completed') {
                    updateRefineUIState(false, 'completed');
                    appendRefineLog('精炼任务完成！', 'success');
                    displayRefineStats(data.stats);
                } else if (data.status === 'error') {
                    updateRefineUIState(false, 'error');
                    appendRefineLog(`任务出错: ${data.error}`, 'error');
                } else {
                    updateRefineUIState(false);
                }
            }
        } catch (error) {
            console.error('精炼轮询失败:', error);
        }
    }, 1000);
}

function updateRefineUIState(running, state = 'idle') {
    refineBtn.disabled = running;
    previewBtn.disabled = running;
    refineDateSelect.disabled = running;
    refineTimeSelect.disabled = running;
    
    if (running) {
        setButtonContent(refineBtn, '处理中…', '···');
        state = 'running';
        refineProgressSection.style.display = 'block';
    } else {
        setButtonContent(refineBtn, '开始精炼', '→');
    }
    const status = statusMap[state] || statusMap.idle;
    refineStatusBadge.className = `status-badge ${status.class}`.trim();
    refineStatusBadge.textContent = status.text;
}

function updateRefineProgress(percent) {
    const safePercent = Math.min(100, Math.max(0, Number(percent) || 0));
    refineProgressText.textContent = `${safePercent}%`;
    refineProgressFill.style.width = `${safePercent}%`;
    refineProgressFill.parentElement.setAttribute('aria-valuenow', String(safePercent));
}

function appendRefineLog(logEntry, type = 'info') {
    let message = logEntry;
    let time = new Date().toLocaleTimeString();
    let level = type;

    if (typeof logEntry === 'object' && logEntry !== null) {
        message = logEntry.message || JSON.stringify(logEntry);
        if (logEntry.time) time = logEntry.time;
        if (logEntry.level) level = logEntry.level;
    }

    if (refineLogContainer.querySelector('.log-placeholder')) refineLogContainer.replaceChildren();
    const div = document.createElement('div');
    div.className = `log-entry ${level}`;
    const timeSpan = document.createElement('span');
    timeSpan.className = 'log-time';
    timeSpan.textContent = `[${time}]`;
    div.append(timeSpan, document.createTextNode(` ${message}`));
    refineLogContainer.appendChild(div);
    refineLogContainer.scrollTop = refineLogContainer.scrollHeight;
}

function clearRefineLogs() {
    refineLogContainer.replaceChildren();
    lastRefineLogCount = 0;
    refineStatsSection.style.display = 'none';
    updateRefineProgress(0);
}

function displayRefineStats(stats) {
    if (!stats) return;
    
    refineStatsSection.style.display = 'block';
    refineStatsGrid.replaceChildren();
    [
        [stats.processed_files || 0, '处理文件'],
        [stats.generated_items || 0, '生成条目'],
        [stats.duplicates_removed || 0, '去重数量']
    ].forEach(([value, label]) => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        const number = document.createElement('div');
        number.className = 'stat-value';
        number.textContent = String(value);
        const caption = document.createElement('div');
        caption.className = 'stat-label';
        caption.textContent = label;
        card.append(number, caption);
        refineStatsGrid.appendChild(card);
    });
}

// ============================================================
// 语义检索功能逻辑
// ============================================================
async function startSemanticSearch() {
    const query = semanticSearchInput.value.trim();
    if (!query) {
        showNotice('请输入检索关键词');
        semanticSearchInput.focus();
        return;
    }
    
    // 更新 UI 状态
    semanticSearchBtn.disabled = true;
    semanticSearchInput.disabled = true;
    setButtonContent(semanticSearchBtn, '检索中…', '···');
    semanticProgressSection.style.display = 'block';
    semanticResultSection.style.display = 'none';
    semanticResultList.replaceChildren();
    semanticResultCount.textContent = '';
    semanticLogContainer.replaceChildren();
    
    appendSemanticLog(`开始检索: "${query}"`, 'info');
    
    try {
        const response = await fetch('/api/semantic-search', {
            method: 'POST',
            headers: serviceHeaders(),
            body: JSON.stringify({
                query: query,
                intent: semanticIntentSelect.value,
                top_k: parseInt(semanticTopKSelect.value, 10)
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || data.error) {
            appendSemanticLog(`检索失败: ${apiErrorMessage(data)}`, 'error');
        } else {
            appendSemanticLog(`检索完成，找到 ${data.total_found || 0} 条相关结果`, 'success');
            if (data.detected_intent) {
                appendSemanticLog(`识别意图: ${data.detected_intent}`, 'info');
            }
            displaySemanticResults(data.results);
        }
    } catch (error) {
        appendSemanticLog(`请求出错: ${error.message}`, 'error');
    } finally {
        // 恢复 UI 状态
        semanticSearchBtn.disabled = false;
        semanticSearchInput.disabled = false;
        setButtonContent(semanticSearchBtn, '开始检索', '→');
        semanticProgressSection.style.display = 'none';
    }
}

function appendSemanticLog(message, type = 'info') {
    if (semanticLogContainer.querySelector('.log-placeholder')) semanticLogContainer.replaceChildren();
    const div = document.createElement('div');
    div.className = `log-entry ${type}`;
    const timeSpan = document.createElement('span');
    timeSpan.className = 'log-time';
    timeSpan.textContent = `[${new Date().toLocaleTimeString()}]`;
    div.append(timeSpan, document.createTextNode(` ${message}`));
    semanticLogContainer.appendChild(div);
    semanticLogContainer.scrollTop = semanticLogContainer.scrollHeight;
}

function displaySemanticResults(results) {
    if (!results || results.length === 0) {
        appendSemanticLog('未找到匹配的结果', 'warning');
        return;
    }
    
    semanticResultSection.style.display = 'block';
    semanticResultCount.textContent = `${results.length} 条`;
    
    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'result-item';
        
        // 匹配度颜色
        let scoreClass = 'score-low';
        if (item.score < 0.3) scoreClass = 'score-high';
        else if (item.score < 0.7) scoreClass = 'score-medium';
        
        const header = document.createElement('div');
        header.className = 'result-header';
        const type = document.createElement('span');
        type.className = 'result-type';
        type.textContent = item.type || '未知类型';
        const score = document.createElement('span');
        score.className = `result-score ${scoreClass}`;
        score.textContent = `距离: ${item.score}`;
        const source = document.createElement('span');
        source.className = 'result-source';
        source.textContent = item.source || '未知来源';
        const content = document.createElement('div');
        content.className = 'result-content';
        content.textContent = item.content || '';
        header.append(type, score, source);
        div.append(header, content);
        semanticResultList.appendChild(div);
    });
}

// ============================================================
// Obsidian Vault 与知识图谱逻辑
// ============================================================
function vaultSelectionPayload() {
    const split = value => value.split(',').map(item => item.trim()).filter(Boolean);
    const quality = Number(vaultQualityInput.value);
    if (!Number.isFinite(quality) || quality < 0 || quality > 1) {
        showNotice('最低质量分必须在 0 到 1 之间');
        vaultQualityInput.focus();
        return null;
    }
    return {
        sources: split(vaultSourceInput.value),
        entity_kinds: split(vaultEntityKindsInput.value),
        minimum_quality: quality
    };
}

async function loadVaultStatus() {
    if (!serviceKeyInput.value.trim()) return;
    vaultRefreshBtn.disabled = true;
    try {
        const response = await fetch('/api/obsidian/status', { headers: serviceHeaders() });
        const data = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(data));
        const availabilityLabels = {
            ready: '可用',
            not_configured: '尚未配置',
            unavailable: '不可访问',
            read_only: '只读保护'
        };
        vaultAvailability.textContent = availabilityLabels[data.availability] || data.availability;
        vaultAvailability.className = data.available ? 'value-ready' : 'value-warning';
        vaultName.textContent = data.vault_name || '—';
        vaultNoteCount.textContent = String(data.managed_notes || 0);
        vaultLastExport.textContent = data.last_exported_at
            ? new Date(data.last_exported_at).toLocaleString()
            : '尚未导出';
        vaultDiagnostic.textContent = vaultDiagnosticText(data.diagnostic);
        vaultPreviewBtn.disabled = !data.available;
        vaultExportBtn.disabled = !data.available;
        vaultGraphRefreshBtn.disabled = !data.available;
    } catch (error) {
        vaultAvailability.textContent = '检查失败';
        vaultAvailability.className = 'value-warning';
        vaultDiagnostic.textContent = error.message;
        vaultPreviewBtn.disabled = true;
        vaultExportBtn.disabled = true;
        vaultGraphRefreshBtn.disabled = true;
    } finally {
        vaultRefreshBtn.disabled = false;
    }
}

function vaultDiagnosticText(code) {
    const labels = {
        vault_not_configured: '设置 OBSIDIAN_VAULT_ROOT 后即可启用安全投影。',
        vault_unavailable: '配置的 Vault 目录不存在或当前进程无法访问。',
        vault_unreadable: '当前进程无权读取该 Vault。',
        vault_read_only: 'Vault 当前只读，预览可用但不能发布。',
        export_state_corrupt: '导出状态损坏，已进入只读保护。',
        export_state_newer_version: '导出状态来自更高版本，已进入只读保护。',
        export_state_invalid: '导出状态无效，需要人工检查。'
    };
    return code ? (labels[code] || code) : '只管理 SE-KB 命名空间，不会改写用户笔记。';
}

async function previewVaultExport() {
    const payload = vaultSelectionPayload();
    if (!payload) return;
    vaultPreviewBtn.disabled = true;
    setButtonContent(vaultPreviewBtn, '生成中…');
    try {
        const response = await fetch('/api/obsidian/preview', {
            method: 'POST',
            headers: serviceHeaders(),
            body: JSON.stringify({ ...payload, offset: 0, limit: 100 })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(data));
        renderVaultPlan(data);
    } catch (error) {
        showNotice(`预览失败：${error.message}`);
    } finally {
        vaultPreviewBtn.disabled = false;
        setButtonContent(vaultPreviewBtn, '生成预览');
    }
}

function renderVaultPlan(plan) {
    vaultPlanSection.hidden = false;
    vaultPlanBody.replaceChildren();
    vaultPlanSummary.replaceChildren();
    vaultPlanCount.textContent = `${plan.total || 0} 项`;
    const labels = {
        create: '新增', update: '更新', rename: '重命名', unchanged: '未变化',
        conflict: '冲突', skipped: '跳过', stale: '已过期'
    };
    Object.entries(plan.counts || {}).forEach(([action, count]) => {
        const badge = document.createElement('span');
        badge.className = `plan-chip action-${action}`;
        badge.textContent = `${labels[action] || action} ${count}`;
        vaultPlanSummary.appendChild(badge);
    });
    (plan.items || []).forEach(item => {
        const row = document.createElement('tr');
        const action = document.createElement('td');
        const actionBadge = document.createElement('span');
        actionBadge.className = `plan-chip action-${item.action}`;
        actionBadge.textContent = labels[item.action] || item.action;
        action.appendChild(actionBadge);
        const kind = document.createElement('td');
        kind.textContent = item.kind || '—';
        const path = document.createElement('td');
        path.className = 'path-cell';
        path.textContent = item.logical_path;
        const reason = document.createElement('td');
        reason.textContent = item.reason;
        row.append(action, kind, path, reason);
        vaultPlanBody.appendChild(row);
    });
    if (plan.partial) {
        const note = document.createElement('p');
        note.className = 'partial-note';
        note.textContent = `当前仅显示前 ${plan.items.length} 项，完整计数已保留。`;
        vaultPlanSummary.appendChild(note);
    }
}

async function startVaultExport() {
    const payload = vaultSelectionPayload();
    if (!payload || activeVaultJobId) return;
    vaultExportBtn.disabled = true;
    setButtonContent(vaultExportBtn, '提交中…', '···');
    try {
        const response = await fetch('/api/obsidian/export', {
            method: 'POST',
            headers: serviceHeaders(true),
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(data));
        activeVaultJobId = data.job_id || response.headers.get('X-Job-ID');
        vaultProgressSection.hidden = false;
        vaultCancelBtn.hidden = false;
        updateVaultProgress(0, 'running');
        pollVaultJob(activeVaultJobId);
    } catch (error) {
        showNotice(`导出启动失败：${error.message}`);
        vaultExportBtn.disabled = false;
        setButtonContent(vaultExportBtn, '导出到 Vault', '→');
    }
}

function pollVaultJob(jobId) {
    if (vaultPollInterval) window.clearInterval(vaultPollInterval);
    const check = async () => {
        try {
            const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, { headers: serviceHeaders() });
            const data = await response.json();
            if (!response.ok) throw new Error(apiErrorMessage(data));
            updateVaultProgress(data.progress, data.status);
            renderVaultLogs(data.logs || []);
            if (!['queued', 'running'].includes(data.status)) {
                window.clearInterval(vaultPollInterval);
                vaultPollInterval = null;
                activeVaultJobId = null;
                vaultCancelBtn.hidden = true;
                vaultExportBtn.disabled = false;
                setButtonContent(vaultExportBtn, '导出到 Vault', '→');
                if (data.status === 'completed') {
                    showNotice('Vault 导出完成', 'success');
                    await loadVaultStatus();
                    await previewVaultExport();
                    await loadVaultRelationships();
                } else {
                    showNotice(`Vault 导出${statusMap[data.status]?.text || '未完成'}`);
                }
            }
        } catch (error) {
            window.clearInterval(vaultPollInterval);
            vaultPollInterval = null;
            activeVaultJobId = null;
            vaultExportBtn.disabled = false;
            vaultCancelBtn.hidden = true;
            setButtonContent(vaultExportBtn, '导出到 Vault', '→');
            updateVaultProgress(0, 'error');
            showNotice(`任务状态获取失败：${error.message}`);
        }
    };
    vaultPollInterval = window.setInterval(check, 900);
    check();
}

async function cancelVaultExport() {
    if (!activeVaultJobId) return;
    vaultCancelBtn.disabled = true;
    try {
        const response = await fetch(`/api/jobs/${encodeURIComponent(activeVaultJobId)}/cancel`, {
            method: 'POST',
            headers: serviceHeaders(true),
            body: '{}'
        });
        const data = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(data));
        updateVaultProgress(data.progress, data.status);
    } catch (error) {
        showNotice(`取消失败：${error.message}`);
    } finally {
        vaultCancelBtn.disabled = false;
    }
}

function updateVaultProgress(percent, state) {
    const safePercent = Math.min(100, Math.max(0, Number(percent) || 0));
    vaultProgressText.textContent = `${safePercent}%`;
    vaultProgressFill.style.width = `${safePercent}%`;
    vaultProgressFill.parentElement.setAttribute('aria-valuenow', String(safePercent));
    const display = statusMap[state] || statusMap.idle;
    vaultStatusBadge.className = `status-badge ${display.class}`.trim();
    vaultStatusBadge.textContent = display.text;
}

function renderVaultLogs(logs) {
    vaultLogContainer.replaceChildren();
    logs.forEach(log => {
        const entry = document.createElement('div');
        entry.className = `log-entry ${log.level || 'info'}`;
        const time = document.createElement('span');
        time.className = 'log-time';
        time.textContent = `[${log.time || ''}]`;
        entry.append(time, document.createTextNode(` ${log.message || ''}`));
        vaultLogContainer.appendChild(entry);
    });
}

async function loadVaultRelationships() {
    if (!serviceKeyInput.value.trim()) return;
    vaultGraphRefreshBtn.disabled = true;
    vaultGraphStatus.textContent = '正在加载关系数据…';
    try {
        const query = new URLSearchParams({ limit: '180' });
        if (vaultRelationKind.value) query.set('kind', vaultRelationKind.value);
        const response = await fetch(`/api/obsidian/relationships?${query}`, { headers: serviceHeaders() });
        const data = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(data));
        renderVaultGraph(data);
        renderRelationshipTable(data);
        vaultGraphStatus.textContent = data.partial
            ? `显示 ${data.edges.length} / ${data.total} 条关系；当前视图已按安全上限截断。`
            : `已加载 ${data.nodes.length} 个节点、${data.edges.length} 条关系。实线为显式关系，虚线为语义推荐。`;
    } catch (error) {
        vaultGraph.replaceChildren();
        vaultGraphStatus.textContent = `图谱加载失败：${error.message}`;
        vaultRelationshipBody.replaceChildren(tableMessageRow('关系数据不可用'));
    } finally {
        vaultGraphRefreshBtn.disabled = false;
    }
}

function renderVaultGraph(data) {
    const namespace = 'http://www.w3.org/2000/svg';
    vaultGraph.replaceChildren();
    const nodes = data.nodes || [];
    const edges = data.edges || [];
    if (nodes.length === 0) {
        const message = document.createElementNS(namespace, 'text');
        message.setAttribute('x', '480');
        message.setAttribute('y', '260');
        message.setAttribute('text-anchor', 'middle');
        message.setAttribute('class', 'graph-empty');
        message.textContent = '暂无可视化关系';
        vaultGraph.appendChild(message);
        return;
    }
    const centerX = 480;
    const centerY = 260;
    const radiusX = Math.min(370, 120 + nodes.length * 12);
    const radiusY = Math.min(205, 90 + nodes.length * 7);
    const positions = new Map();
    nodes.forEach((node, index) => {
        const angle = -Math.PI / 2 + (Math.PI * 2 * index / nodes.length);
        positions.set(node.id, {
            x: centerX + Math.cos(angle) * radiusX,
            y: centerY + Math.sin(angle) * radiusY
        });
    });
    edges.forEach(edge => {
        const source = positions.get(edge.source);
        const target = positions.get(edge.target);
        if (!source || !target) return;
        const line = document.createElementNS(namespace, 'line');
        line.setAttribute('x1', source.x);
        line.setAttribute('y1', source.y);
        line.setAttribute('x2', target.x);
        line.setAttribute('y2', target.y);
        line.setAttribute('class', `graph-edge ${edge.kind === 'semantic' ? 'semantic' : 'explicit'}`);
        vaultGraph.appendChild(line);
    });
    nodes.forEach(node => {
        const position = positions.get(node.id);
        const group = document.createElementNS(namespace, 'g');
        group.setAttribute('class', `graph-node node-${node.kind || 'unknown'}`);
        group.setAttribute('transform', `translate(${position.x} ${position.y})`);
        group.setAttribute('tabindex', '0');
        group.setAttribute('role', 'link');
        group.setAttribute('aria-label', `${node.title}，${node.kind || '未知类型'}，在 Obsidian 中打开`);
        const title = document.createElementNS(namespace, 'title');
        title.textContent = `${node.title} · ${node.kind || 'unknown'}`;
        const circle = document.createElementNS(namespace, 'circle');
        circle.setAttribute('r', node.kind === 'source' ? '25' : '20');
        const label = document.createElementNS(namespace, 'text');
        label.setAttribute('y', node.kind === 'source' ? '40' : '35');
        label.setAttribute('text-anchor', 'middle');
        label.textContent = shortenLabel(node.title, 13);
        const open = () => openVaultNote(node.id);
        group.addEventListener('click', open);
        group.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                open();
            }
        });
        group.append(title, circle, label);
        vaultGraph.appendChild(group);
    });
}

function renderRelationshipTable(data) {
    vaultRelationshipBody.replaceChildren();
    const nodes = new Map((data.nodes || []).map(node => [node.id, node]));
    if (!data.edges || data.edges.length === 0) {
        vaultRelationshipBody.appendChild(tableMessageRow('暂无关系数据'));
        return;
    }
    data.edges.forEach(edge => {
        const source = nodes.get(edge.source) || { id: edge.source, title: edge.source };
        const target = nodes.get(edge.target) || { id: edge.target, title: edge.target };
        const row = document.createElement('tr');
        const sourceCell = document.createElement('td');
        sourceCell.textContent = source.title;
        const relationCell = document.createElement('td');
        relationCell.textContent = edge.relation;
        const targetCell = document.createElement('td');
        targetCell.textContent = target.title;
        const provenanceCell = document.createElement('td');
        provenanceCell.textContent = edge.kind === 'semantic'
            ? `语义推荐 · ${Number(edge.score || 0).toFixed(3)} · ${edge.method || 'unknown'}`
            : '显式关系';
        const actionCell = document.createElement('td');
        actionCell.className = 'table-actions';
        actionCell.append(
            noteActionButton('打开', () => openVaultNote(target.id)),
            noteActionButton('复制路径', () => copyVaultPath(target))
        );
        row.append(sourceCell, relationCell, targetCell, provenanceCell, actionCell);
        vaultRelationshipBody.appendChild(row);
    });
}

function tableMessageRow(message) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.textContent = message;
    row.appendChild(cell);
    return row;
}

function noteActionButton(label, action) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn-small';
    button.textContent = label;
    button.addEventListener('click', action);
    return button;
}

async function openVaultNote(identifier) {
    try {
        const response = await fetch(`/api/obsidian/notes/${encodeURIComponent(identifier)}/location`, {
            headers: serviceHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(data));
        window.location.href = data.obsidian_uri;
    } catch (error) {
        showNotice(`无法打开笔记：${error.message}`);
    }
}

async function copyVaultPath(node) {
    try {
        let logicalPath = node.logical_path;
        if (!logicalPath) {
            const response = await fetch(`/api/obsidian/notes/${encodeURIComponent(node.id)}/location`, {
                headers: serviceHeaders()
            });
            const data = await response.json();
            if (!response.ok) throw new Error(apiErrorMessage(data));
            logicalPath = data.logical_path;
        }
        await navigator.clipboard.writeText(logicalPath);
        showNotice('Vault 相对路径已复制', 'success');
    } catch (error) {
        showNotice(`复制失败：${error.message}`);
    }
}

function shortenLabel(value, maximum) {
    const text = String(value || 'Untitled');
    return text.length > maximum ? `${text.slice(0, maximum - 1)}…` : text;
}
