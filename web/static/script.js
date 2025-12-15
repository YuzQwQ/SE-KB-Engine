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
// 爬取功能
// ============================================================

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
        newLogs.forEach(log => addLogEntry(log, logContainer));
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
function addLogEntry(log, container) {
    // 移除占位符
    const placeholder = container.querySelector('.log-placeholder');
    if (placeholder) placeholder.remove();
    
    const entry = document.createElement('div');
    entry.className = 'log-entry ' + (log.level || 'info');
    
    entry.innerHTML = `
        <span class="log-time">[${log.time}]</span>
        <span class="log-message">${escapeHtml(log.message)}</span>
    `;
    
    container.appendChild(entry);
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

// ============================================================
// 精炼功能
// ============================================================

// 加载 artifacts 日期列表
async function loadArtifactsDates() {
    try {
        const response = await fetch('/api/artifacts/list');
        const data = await response.json();
        
        refineDateSelect.innerHTML = '<option value="">全部日期</option>';
        
        if (data.dates && data.dates.length > 0) {
            data.dates.forEach(item => {
                const option = document.createElement('option');
                option.value = item.date;
                const totalFiles = item.times.reduce((sum, t) => sum + t.file_count, 0);
                option.textContent = `${item.date} (${totalFiles} 文件)`;
                option.dataset.times = JSON.stringify(item.times);
                refineDateSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('加载日期列表失败:', error);
    }
}

// 日期选择变化
function onDateChange() {
    const selected = refineDateSelect.selectedOptions[0];
    refineTimeSelect.innerHTML = '<option value="">全部时间</option>';
    
    if (selected && selected.dataset.times) {
        const times = JSON.parse(selected.dataset.times);
        times.forEach(t => {
            const option = document.createElement('option');
            option.value = t.time;
            option.textContent = `${t.time.replace('_', ':')} (${t.file_count} 文件)`;
            refineTimeSelect.appendChild(option);
        });
    }
}

// 预览精炼
async function previewRefine() {
    const date = refineDateSelect.value;
    const time = refineTimeSelect.value;
    
    previewBtn.disabled = true;
    previewBtn.innerHTML = '⏳ 分析中...';
    
    try {
        const response = await fetch('/api/refine/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, time })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            alert(data.error || '预览失败');
            return;
        }
        
        // 显示预览结果
        displayPreview(data);
        
    } catch (error) {
        console.error('预览失败:', error);
        alert('预览请求失败: ' + error.message);
    } finally {
        previewBtn.disabled = false;
        previewBtn.innerHTML = '<span>👁️ 预览分析</span>';
    }
}

// 显示预览结果
function displayPreview(data) {
    previewResult.style.display = 'block';
    
    let html = `<div><strong>总 artifact 数:</strong> ${data.total_artifacts}</div>`;
    
    // 按类型分布
    if (data.by_type && Object.keys(data.by_type).length > 0) {
        html += '<div style="margin-top: 12px;"><strong>按类型分布:</strong></div>';
        for (const [type, info] of Object.entries(data.by_type)) {
            html += `
                <div class="preview-type-item">
                    <span class="preview-type-name">${type}</span>
                    <span class="preview-type-count">待处理: ${info.artifact_count}, 已有: ${info.existing_count}</span>
                </div>
            `;
        }
    }
    
    // 潜在重复
    if (data.potential_duplicates && Object.keys(data.potential_duplicates).length > 0) {
        html += '<div class="preview-duplicate"><div class="preview-duplicate-title">⚠️ 潜在重复:</div>';
        for (const [type, items] of Object.entries(data.potential_duplicates)) {
            html += `<div style="margin-top: 8px;"><strong>${type}:</strong></div>`;
            items.forEach(item => {
                const status = item.has_increment ? '📝 有增量' : '🔄 纯重复';
                html += `
                    <div class="preview-duplicate-item">
                        • ${item.file} (相似度: ${(item.similarity * 100).toFixed(0)}%) ${status}
                    </div>
                `;
            });
        }
        html += '</div>';
    } else {
        html += '<div style="margin-top: 12px; color: var(--accent-green);">✅ 未发现明显重复</div>';
    }
    
    previewContent.innerHTML = html;
}

// 开始精炼
async function startRefine() {
    if (isRefining) {
        alert('精炼任务正在运行');
        return;
    }
    
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
        
        if (!response.ok) {
            alert(data.error || '启动失败');
            return;
        }
        
        // 开始轮询
        isRefining = true;
        lastRefineLogCount = 0;
        refineBtn.disabled = true;
        refineBtn.innerHTML = '⏳ 精炼中...';
        previewBtn.disabled = true;
        
        // 清空旧内容
        refineLogContainer.innerHTML = '';
        refineProgressSection.style.display = 'block';
        refineStatsSection.style.display = 'none';
        
        startRefinePoll();
        
    } catch (error) {
        console.error('启动精炼失败:', error);
        alert('请求失败: ' + error.message);
    }
}

// 开始精炼轮询
function startRefinePoll() {
    if (refinePollInterval) clearInterval(refinePollInterval);
    refinePollInterval = setInterval(checkRefineStatus, 500);
}

// 停止精炼轮询
function stopRefinePoll() {
    if (refinePollInterval) {
        clearInterval(refinePollInterval);
        refinePollInterval = null;
    }
}

// 检查精炼状态
async function checkRefineStatus() {
    try {
        const response = await fetch('/api/refine/status');
        const data = await response.json();
        
        updateRefineUI(data);
        
        // 任务结束
        if (data.status === 'completed' || data.status === 'error') {
            isRefining = false;
            stopRefinePoll();
            refineBtn.disabled = false;
            refineBtn.innerHTML = '<span>✨ 开始精炼</span>';
            previewBtn.disabled = false;
            
            // 显示统计
            if (data.stats && Object.keys(data.stats).length > 0) {
                displayRefineStats(data.stats);
            }
            
            // 刷新日期列表
            loadArtifactsDates();
        }
        
    } catch (error) {
        console.error('检查精炼状态失败:', error);
    }
}

// 更新精炼 UI
function updateRefineUI(data) {
    // 更新状态徽章
    const status = statusMap[data.status] || statusMap.idle;
    refineStatusBadge.textContent = status.text;
    refineStatusBadge.className = 'status-badge ' + status.class;
    
    // 更新进度
    refineProgressText.textContent = data.progress + '%';
    refineProgressFill.style.width = data.progress + '%';
    
    // 更新日志
    if (data.logs && data.logs.length > lastRefineLogCount) {
        const newLogs = data.logs.slice(lastRefineLogCount);
        newLogs.forEach(log => addLogEntry(log, refineLogContainer));
        lastRefineLogCount = data.logs.length;
        
        refineLogContainer.scrollTop = refineLogContainer.scrollHeight;
    }
}

// 显示精炼统计
function displayRefineStats(stats) {
    refineStatsSection.style.display = 'block';
    
    refineStatsGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.total_artifacts || 0}</div>
            <div class="stat-label">总 artifact 数</div>
        </div>
        <div class="stat-card warning">
            <div class="stat-value">${stats.duplicates_found || 0}</div>
            <div class="stat-label">发现重复</div>
        </div>
        <div class="stat-card success">
            <div class="stat-value">${stats.merged_count || 0}</div>
            <div class="stat-label">执行融合</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.skipped_count || 0}</div>
            <div class="stat-label">纯重复跳过</div>
        </div>
        <div class="stat-card success">
            <div class="stat-value">${stats.new_count || 0}</div>
            <div class="stat-label">新增内容</div>
        </div>
    `;
}

// 清空精炼日志
function clearRefineLogs() {
    refineLogContainer.innerHTML = '<div class="log-placeholder">选择日期后点击"预览分析"或"开始精炼"...</div>';
    lastRefineLogCount = 0;
    refineStatsSection.style.display = 'none';
    previewResult.style.display = 'none';
}

// ============================================================
// 工具函数
// ============================================================

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
