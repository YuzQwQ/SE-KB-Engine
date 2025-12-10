/**
 * 知识库构建系统 - 前端脚本
 */

// DOM 元素
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

// 状态
let isRunning = false;
let pollInterval = null;
let lastLogCount = 0;

// 状态映射
const statusMap = {
    'idle': { text: '等待中', class: '' },
    'running': { text: '运行中', class: 'running' },
    'completed': { text: '已完成', class: 'completed' },
    'error': { text: '出错', class: 'error' }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 绑定事件
    searchBtn.addEventListener('click', startTask);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') startTask();
    });
    clearBtn.addEventListener('click', clearLogs);
    
    // 初始状态检查
    checkStatus();
});

// 开始任务
async function startTask() {
    const query = searchInput.value.trim();
    if (!query) {
        alert('请输入搜索内容');
        searchInput.focus();
        return;
    }
    
    if (isRunning) {
        alert('已有任务正在运行');
        return;
    }
    
    const limit = parseInt(limitSelect.value);
    const type = typeSelect.value;
    const types = type ? [type] : [];
    
    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, limit, types })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            alert(data.error || '启动失败');
            return;
        }
        
        // 开始轮询状态
        isRunning = true;
        lastLogCount = 0;
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">运行中...</span>';
        
        // 清空旧日志
        logContainer.innerHTML = '';
        resultList.innerHTML = '';
        resultSection.classList.remove('visible');
        
        startPolling();
        
    } catch (error) {
        console.error('Error:', error);
        alert('请求失败: ' + error.message);
    }
}

// 开始轮询
function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(checkStatus, 500);
}

// 停止轮询
function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// 检查状态
async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        updateUI(data);
        
        // 任务结束
        if (data.status === 'completed' || data.status === 'error') {
            isRunning = false;
            stopPolling();
            searchBtn.disabled = false;
            searchBtn.innerHTML = '<span class="btn-icon">🚀</span><span class="btn-text">开始构建</span>';
        }
        
    } catch (error) {
        console.error('Status check error:', error);
    }
}

// 更新 UI
function updateUI(data) {
    // 更新状态徽章
    const status = statusMap[data.status] || statusMap.idle;
    statusBadge.textContent = status.text;
    statusBadge.className = 'status-badge ' + status.class;
    
    // 更新进度
    progressText.textContent = data.progress + '%';
    progressFill.style.width = data.progress + '%';
    
    // 更新日志（只添加新的）
    if (data.logs && data.logs.length > lastLogCount) {
        const newLogs = data.logs.slice(lastLogCount);
        newLogs.forEach(log => addLogEntry(log));
        lastLogCount = data.logs.length;
        
        // 滚动到底部
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    // 更新结果
    if (data.results && data.results.length > 0) {
        updateResults(data.results);
    }
}

// 添加日志条目
function addLogEntry(log) {
    // 移除占位符
    const placeholder = logContainer.querySelector('.log-placeholder');
    if (placeholder) placeholder.remove();
    
    const entry = document.createElement('div');
    entry.className = 'log-entry ' + log.level;
    
    entry.innerHTML = `
        <span class="log-time">[${log.time}]</span>
        <span class="log-message">${escapeHtml(log.message)}</span>
    `;
    
    logContainer.appendChild(entry);
}

// 更新结果
function updateResults(results) {
    resultSection.classList.add('visible');
    resultList.innerHTML = '';
    
    results.forEach(result => {
        const item = document.createElement('div');
        item.className = 'result-item';
        
        const types = result.types ? result.types.join(', ') : '未知';
        const tokens = result.tokens || 0;
        
        item.innerHTML = `
            <div>
                <div class="result-title">${escapeHtml(result.title || '未命名')}</div>
                <div class="result-types">📁 ${types}</div>
            </div>
            <div class="result-tokens">${tokens} tokens</div>
        `;
        
        resultList.appendChild(item);
    });
}

// 清空日志
function clearLogs() {
    logContainer.innerHTML = '<div class="log-placeholder">等待任务开始...</div>';
    lastLogCount = 0;
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


