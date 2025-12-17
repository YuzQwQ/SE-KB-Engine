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
const statusBadge = document.getElementById('statusBadge');
const progressText = document.getElementById('progressText');
const progressFill = document.getElementById('progressFill');
const logContainer = document.getElementById('logContainer');
const clearBtn = document.getElementById('clearBtn');
const resultSection = document.getElementById('resultSection');
const resultList = document.getElementById('resultList');

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

// ============================================================
// 状态
// ============================================================
let isRunning = false;
let isRefining = false;
let pollInterval = null;
let refinePollInterval = null;
let lastLogCount = 0;
let lastRefineLogCount = 0;

// 状态映射
const statusMap = {
    'idle': { text: '等待中', class: '' },
    'running': { text: '运行中', class: 'running' },
    'completed': { text: '已完成', class: 'completed' },
    'error': { text: '出错', class: 'error' }
};

// ============================================================
// 初始化
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // Tab 切换
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
    
    // 爬取功能事件
    searchBtn.addEventListener('click', startTask);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') startTask();
    });
    clearBtn.addEventListener('click', clearLogs);
    
    // 精炼功能事件
    previewBtn.addEventListener('click', previewRefine);
    refineBtn.addEventListener('click', startRefine);
    clearRefineLogBtn.addEventListener('click', clearRefineLogs);
    refineDateSelect.addEventListener('change', onDateChange);
    
    // 初始状态检查
    checkStatus();
    
    // 加载 artifacts 日期列表
    loadArtifactsDates();
    
    // 语义检索功能事件
    semanticSearchBtn.addEventListener('click', startSemanticSearch);
    semanticSearchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') startSemanticSearch();
    });
});

// ============================================================
// Tab 切换
// ============================================================
function switchTab(tabName) {
    // 更新 Tab 按钮状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // 更新 Tab 内容显示
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === tabName + '-tab');
    });
}

// ============================================================
// 爬取功能逻辑
// ============================================================
async function startTask() {
    if (isRunning) return;
    
    const query = searchInput.value.trim();
    if (!query) {
        alert('请输入搜索关键词');
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
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            appendLog('任务已启动...');
            pollStatus();
        } else {
            const errorMsg = data.error || data.message || '未知错误';
            appendLog(`启动失败: ${errorMsg}`, 'error');
            isRunning = false;
            updateUIState(false);
        }
    } catch (error) {
        appendLog(`请求失败: ${error.message}`, 'error');
        isRunning = false;
        updateUIState(false);
    }
}

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
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
            const response = await fetch('/api/status');
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
                updateUIState(false);
                
                if (data.status === 'completed') {
                    appendLog('任务完成！', 'success');
                    displayResults(data.results);
                } else if (data.status === 'error') {
                    appendLog(`任务出错: ${data.error}`, 'error');
                }
            }
        } catch (error) {
            console.error('轮询失败:', error);
        }
    }, 1000);
}

function updateUIState(running) {
    searchBtn.disabled = running;
    searchInput.disabled = running;
    limitSelect.disabled = running;
    typeSelect.disabled = running;
    
    if (running) {
        searchBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">运行中...</span>';
        statusBadge.className = 'status-badge running';
        statusBadge.textContent = '运行中';
    } else {
        searchBtn.innerHTML = '<span class="btn-icon">🚀</span><span class="btn-text">开始构建</span>';
        statusBadge.className = 'status-badge';
        statusBadge.textContent = '等待中';
    }
}

function updateProgress(percent) {
    progressText.textContent = `${percent}%`;
    progressFill.style.width = `${percent}%`;
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

    const div = document.createElement('div');
    div.className = `log-entry ${level}`;
    
    div.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
    
    logContainer.appendChild(div);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function clearLogs() {
    logContainer.innerHTML = '';
    lastLogCount = 0;
    resultSection.style.display = 'none';
    resultList.innerHTML = '';
}

function displayResults(results) {
    if (!results || results.length === 0) return;
    
    resultSection.style.display = 'block';
    resultList.innerHTML = '';
    
    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <div class="result-header">
                <span class="result-type">${item.type}</span>
                <span class="result-source">${item.source || '未知来源'}</span>
            </div>
            <div class="result-content">${formatContent(item.content)}</div>
        `;
        resultList.appendChild(div);
    });
}

function formatContent(content) {
    // 简单的 Markdown 格式化或转义
    return content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
}

// ============================================================
// 精炼功能逻辑
// ============================================================
async function loadArtifactsDates() {
    try {
        const response = await fetch('/api/artifacts/dates');
        const dates = await response.json();
        
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
        const response = await fetch(`/api/artifacts/times?date=${date}`);
        const times = await response.json();
        
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
    previewContent.innerHTML = '<div class="loading">正在分析...</div>';
    
    try {
        const response = await fetch('/api/refine/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, time })
        });
        
        const data = await response.json();
        if (data.error) {
            previewContent.innerHTML = `<div class="error">分析失败: ${data.error}</div>`;
        } else {
            previewContent.innerHTML = `
                <p>找到 <strong>${data.total_files}</strong> 个文件</p>
                <p>包含 <strong>${data.total_items}</strong> 条知识条目</p>
                <p>预计生成 <strong>${data.estimated_clusters}</strong> 个知识簇</p>
            `;
        }
    } catch (error) {
        previewContent.innerHTML = `<div class="error">请求失败: ${error.message}</div>`;
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, time, dry_run: dryRun })
        });
        
        const data = await response.json();
        if (response.ok) {
            appendRefineLog('精炼任务已启动...');
            pollRefineStatus();
        } else {
            const errorMsg = data.error || data.message || '未知错误';
            appendRefineLog(`启动失败: ${errorMsg}`, 'error');
            isRefining = false;
            updateRefineUIState(false);
        }
    } catch (error) {
        appendRefineLog(`请求失败: ${error.message}`, 'error');
        isRefining = false;
        updateRefineUIState(false);
    }
}

function pollRefineStatus() {
    if (refinePollInterval) clearInterval(refinePollInterval);
    
    refinePollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/refine/status');
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
                updateRefineUIState(false);
                
                if (data.status === 'completed') {
                    appendRefineLog('精炼任务完成！', 'success');
                    displayRefineStats(data.stats);
                } else if (data.status === 'error') {
                    appendRefineLog(`任务出错: ${data.error}`, 'error');
                }
            }
        } catch (error) {
            console.error('精炼轮询失败:', error);
        }
    }, 1000);
}

function updateRefineUIState(running) {
    refineBtn.disabled = running;
    previewBtn.disabled = running;
    refineDateSelect.disabled = running;
    refineTimeSelect.disabled = running;
    
    if (running) {
        refineBtn.innerHTML = '<span>⏳ 处理中...</span>';
        refineStatusBadge.className = 'status-badge running';
        refineStatusBadge.textContent = '运行中';
        refineProgressSection.style.display = 'block';
    } else {
        refineBtn.innerHTML = '<span>✨ 开始精炼</span>';
        refineStatusBadge.className = 'status-badge';
        refineStatusBadge.textContent = '等待中';
    }
}

function updateRefineProgress(percent) {
    refineProgressText.textContent = `${percent}%`;
    refineProgressFill.style.width = `${percent}%`;
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

    const div = document.createElement('div');
    div.className = `log-entry ${level}`;
    div.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
    refineLogContainer.appendChild(div);
    refineLogContainer.scrollTop = refineLogContainer.scrollHeight;
}

function clearRefineLogs() {
    refineLogContainer.innerHTML = '';
    lastRefineLogCount = 0;
    refineStatsSection.style.display = 'none';
}

function displayRefineStats(stats) {
    if (!stats) return;
    
    refineStatsSection.style.display = 'block';
    refineStatsGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.processed_files || 0}</div>
            <div class="stat-label">处理文件</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.generated_items || 0}</div>
            <div class="stat-label">生成条目</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.duplicates_removed || 0}</div>
            <div class="stat-label">去重数量</div>
        </div>
    `;
}

// ============================================================
// 语义检索功能逻辑
// ============================================================
async function startSemanticSearch() {
    const query = semanticSearchInput.value.trim();
    if (!query) {
        alert('请输入检索关键词');
        return;
    }
    
    // 更新 UI 状态
    semanticSearchBtn.disabled = true;
    semanticSearchInput.disabled = true;
    semanticSearchBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">检索中...</span>';
    semanticProgressSection.style.display = 'block';
    semanticResultSection.style.display = 'none';
    semanticResultList.innerHTML = '';
    semanticLogContainer.innerHTML = ''; // 清空旧日志
    
    appendSemanticLog(`开始检索: "${query}"`, 'info');
    
    try {
        const response = await fetch('/api/semantic-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                intent: semanticIntentSelect.value,
                top_k: semanticTopKSelect.value
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            appendSemanticLog(`检索失败: ${data.error}`, 'error');
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
        semanticSearchBtn.innerHTML = '<span class="btn-icon">🔍</span><span class="btn-text">开始检索</span>';
        semanticProgressSection.style.display = 'none';
    }
}

function appendSemanticLog(message, type = 'info') {
    const div = document.createElement('div');
    div.className = `log-entry ${type}`;
    div.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span> ${message}`;
    semanticLogContainer.appendChild(div);
    semanticLogContainer.scrollTop = semanticLogContainer.scrollHeight;
}

function displaySemanticResults(results) {
    if (!results || results.length === 0) {
        appendSemanticLog('未找到匹配的结果', 'warning');
        return;
    }
    
    semanticResultSection.style.display = 'block';
    
    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'result-item';
        
        // 匹配度颜色
        let scoreClass = 'score-low';
        if (item.score < 0.3) scoreClass = 'score-high';
        else if (item.score < 0.7) scoreClass = 'score-medium';
        
        div.innerHTML = `
            <div class="result-header">
                <span class="result-type">${item.type || '未知类型'}</span>
                <span class="result-score ${scoreClass}">距离: ${item.score}</span>
                <span class="result-source">${item.source || '未知来源'}</span>
            </div>
            <div class="result-content">${formatContent(item.content)}</div>
        `;
        semanticResultList.appendChild(div);
    });
}
