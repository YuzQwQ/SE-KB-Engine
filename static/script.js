class CrawlerInterface {
    constructor() {
        // 获取DOM元素
        this.topicSelect = document.getElementById('topicSelect');
        this.searchInput = document.getElementById('searchInput');
        this.crawlButton = document.getElementById('startCrawlBtn');
        this.resultsStatus = document.getElementById('resultsStatus');
        this.resultsContent = document.getElementById('resultsContent');
        
        // 日志相关元素
        this.logPanel = document.getElementById('logPanel');
        this.logContent = document.getElementById('logContent');
        this.clearLogsBtn = document.getElementById('clearLogs');
        this.toggleLogsBtn = document.getElementById('toggleLogs');
        
        // 初始化功能
        this.init();
    }
    
    init() {
        this.initEventListeners();
        this.initLogFeature();
        this.initWebSocket();
        
        // 初始化状态
        this.updateStatus('ready', '准备就绪');
        this.addLog('系统已启动，等待选择主题和搜索内容...', 'system');
    }
    
    initEventListeners() {
        // 爬取按钮点击事件
        this.crawlButton.addEventListener('click', () => {
            this.startCrawling();
        });
        
        // 搜索输入框回车事件
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.startCrawling();
            }
        });
        
        // 输入验证
        this.searchInput.addEventListener('input', () => {
            this.validateInput();
        });
        
        this.topicSelect.addEventListener('change', () => {
            this.validateInput();
        });
    }
    
    validateInput() {
        const topic = this.topicSelect.value;
        const searchText = this.searchInput.value.trim();
        
        this.crawlButton.disabled = !topic || !searchText;
    }
    
    async startCrawling() {
        const topic = this.topicSelect.value;
        const searchText = this.searchInput.value.trim();
        
        if (!topic || !searchText) {
            this.addLog('请选择主题并输入搜索内容', 'error');
            return;
        }
        
        try {
            this.updateStatus('loading', topic === 'semantic_search' ? '正在检索知识库...' : '正在爬取中...');
            this.crawlButton.disabled = true;
            this.addLog(`开始任务 - 类型: ${this.getTopicName(topic)}, 内容: ${searchText}`, 'info');
            
            // 清空之前的结果
            this.resultsContent.innerHTML = '';
            
            let response;
            let data;
            
            if (topic === 'semantic_search') {
                // 调用语义搜索 API
                response = await fetch('/api/semantic-search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: searchText,
                        top_k: 10
                    })
                });
                
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                data = await response.json();
                
                if (data.error) throw new Error(data.error);
                
                this.addLog(`检索完成，意图识别: ${data.detected_intent}, 找到 ${data.total_found} 条结果`, 'success');
                this.displaySemanticResults(data);
                this.updateStatus('success', `成功检索到 ${data.results.length} 条相关知识`);
                
            } else {
                // 原有的爬取逻辑
                response = await fetch('/api/crawl', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        theme: topic,
                        search_content: searchText
                    })
                });
                
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                data = await response.json();
                
                this.addLog('爬取完成，正在处理结果...', 'system');
                
                if (data.success) {
                    const results = data.knowledge_bases || []; // 注意：这里可能需要根据实际返回结构调整
                    this.displayResults(results);
                    this.updateStatus('success', `成功爬取 ${results.length} 条结果`);
                    this.addLog(`爬取成功，获得 ${results.length} 条结果`, 'success');
                } else {
                    throw new Error(data.error || '爬取失败');
                }
            }
            
        } catch (error) {
            console.error('任务失败:', error);
            this.addLog(`任务失败: ${error.message}`, 'error');
            this.updateStatus('error', '任务失败');
            this.resultsContent.innerHTML = `<div class="error-message">❌ ${error.message}</div>`;
        } finally {
            this.crawlButton.disabled = false;
        }
    }
    
    getTopicName(topic) {
        const topicNames = {
            'general': '通用内容分析',
            'requirement_analysis': '需求分析',
            'dfd_expert': '数据流图(DFD)',
            'requirement_to_dfd': '需求生成DFD',
            'system_design': '系统设计',
            'universal_knowledge': '通用知识库',
            'semantic_search': '🔍 语义检索'
        };
        return topicNames[topic] || topic;
    }

    displaySemanticResults(data) {
        if (!data.results || data.results.length === 0) {
            this.resultsContent.innerHTML = `
                <div class="welcome-message">
                    <h4>未找到相关知识</h4>
                    <p>尝试更换关键词，或者知识库中尚未录入相关内容。</p>
                    <p>检测到的意图: <strong>${data.detected_intent}</strong></p>
                </div>
            `;
            return;
        }

        const resultsHtml = data.results.map((result, index) => {
            const scorePercent = Math.round(result.score * 100);
            const scoreClass = scorePercent > 80 ? 'high-score' : (scorePercent > 60 ? 'medium-score' : 'low-score');
            
            return `
                <div class="crawl-result semantic-result">
                    <div class="result-header">
                        <div class="result-title">
                            <span class="badge ${result.type}">${result.type}</span>
                            相关度: <span class="${scoreClass}">${scorePercent}%</span>
                        </div>
                        <div class="result-meta">来源: ${result.collection}</div>
                    </div>
                    <div class="result-content">
                        <div class="markdown-body">${this.escapeHtml(result.content)}</div>
                        ${result.source ? `<div class="result-source">File: ${result.source}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        this.resultsContent.innerHTML = `
            <div class="search-meta">
                <p>查询: <strong>${this.escapeHtml(data.query)}</strong> | 意图: <code>${data.detected_intent}</code></p>
            </div>
            ${resultsHtml}
        `;
    }
    
    updateStatus(type, message) {
        this.resultsStatus.className = `results-status ${type}`;
        this.resultsStatus.textContent = message;
    }
    
    displayResults(results) {
        console.log('displayResults 被调用，参数:', results);
        console.log('results 类型:', typeof results);
        console.log('results 是否为数组:', Array.isArray(results));
        
        if (!results || results.length === 0) {
            console.log('没有结果或结果为空');
            this.resultsContent.innerHTML = `
                <div class="welcome-message">
                    <h4>没有找到结果</h4>
                    <p>请尝试使用不同的搜索关键词或选择其他主题。</p>
                </div>
            `;
            return;
        }
        
        const resultsHtml = results.map((result, index) => {
            return `
                <div class="crawl-result">
                    <div class="result-header">
                        <div class="result-title">结果 ${index + 1}</div>
                        <div class="result-meta">${new Date().toLocaleString('zh-CN')}</div>
                    </div>
                    <div class="result-content">
                        ${this.formatResultContent(result)}
                    </div>
                </div>
            `;
        }).join('');
        
        this.resultsContent.innerHTML = resultsHtml;
    }
    
    formatResultContent(result) {
        if (typeof result === 'string') {
            return `<p>${this.escapeHtml(result)}</p>`;
        }
        
        if (typeof result === 'object') {
            let html = '';
            
            // 显示提取状态
            const status = result.extraction_success ? '✅ 提取成功' : '❌ 提取失败';
            html += `<div class="extraction-status"><strong>状态:</strong> ${status}</div>`;
            
            // 显示标题
            if (result.title) {
                html += `<h5>${this.escapeHtml(result.title)}</h5>`;
            }
            
            // 显示摘要
            if (result.snippet) {
                html += `<div class="result-snippet"><strong>摘要:</strong> ${this.escapeHtml(result.snippet)}</div>`;
            }
            
            // 显示知识库内容
            if (result.knowledge_base) {
                html += `
                    <div class="knowledge-base">
                        <strong>知识库内容:</strong>
                        <div class="knowledge-content">${this.escapeHtml(JSON.stringify(result.knowledge_base, null, 2))}</div>
                    </div>
                `;
            }
            
            // 显示来源URL
            if (result.url) {
                html += `<p><strong>来源:</strong> <a href="${result.url}" target="_blank">${this.escapeHtml(result.url)}</a></p>`;
            }
            
            return html || `<p>${this.escapeHtml(JSON.stringify(result))}</p>`;
        }
        
        return `<p>${this.escapeHtml(String(result))}</p>`;
    }
    
    displayError(errorMessage) {
        this.resultsContent.innerHTML = `
            <div class="crawl-result">
                <div class="result-header">
                    <div class="result-title" style="color: #dc2626;">错误</div>
                    <div class="result-meta">${new Date().toLocaleString('zh-CN')}</div>
                </div>
                <div class="result-content">
                    <p style="color: #dc2626;">${this.escapeHtml(errorMessage)}</p>
                    <p>请检查网络连接或稍后重试。</p>
                </div>
            </div>
        `;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    

    
    // 日志功能
    initLogFeature() {
        // 清空日志按钮
        if (this.clearLogsBtn) {
            this.clearLogsBtn.addEventListener('click', () => {
                this.clearLogs();
            });
        }
        
        // 切换日志面板显示/隐藏
        if (this.toggleLogsBtn) {
            this.toggleLogsBtn.addEventListener('click', () => {
                this.toggleLogPanel();
            });
        }
        
        // 初始化日志
        this.addLog('系统已启动，等待选择主题和搜索内容...', 'system');
    }
    
    addLog(message, type, customTimestamp = null) {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        
        let time;
        if (customTimestamp) {
            // 如果提供了自定义时间戳，解析并格式化
            const date = new Date(customTimestamp);
            time = date.toLocaleTimeString('zh-CN', { 
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } else {
            time = new Date().toLocaleTimeString('zh-CN', { 
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
        
        logEntry.innerHTML = `
            <span class="log-time">[${time}]</span>
            <span class="log-message">${this.escapeHtml(message)}</span>
        `;
        
        this.logContent.appendChild(logEntry);
        
        // 自动滚动到底部
        this.logContent.scrollTop = this.logContent.scrollHeight;
        
        // 限制日志条数，避免内存占用过多
        const maxLogs = 500;
        const logs = this.logContent.children;
        if (logs.length > maxLogs) {
            this.logContent.removeChild(logs[0]);
        }
    }
    
    clearLogs() {
        this.logContent.innerHTML = '';
        this.addLog('日志已清空', 'system');
    }
    
    toggleLogPanel() {
        const isHidden = this.logPanel.classList.contains('hidden');
        
        if (isHidden) {
            this.logPanel.classList.remove('hidden');
            this.toggleLogsBtn.textContent = '隐藏';
        } else {
            this.logPanel.classList.add('hidden');
            this.toggleLogsBtn.textContent = '显示';
        }
    }

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        
        this.connectWebSocket(wsUrl);
    }

    connectWebSocket(wsUrl) {
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.addLog('WebSocket连接已建立', 'system');
                console.log('WebSocket连接已建立');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const logData = JSON.parse(event.data);
                    this.addLog(logData.message, logData.type, logData.timestamp);
                } catch (e) {
                    console.error('解析WebSocket消息失败:', e);
                }
            };
            
            this.websocket.onclose = () => {
                this.addLog('WebSocket连接已断开，尝试重连...', 'warning');
                console.log('WebSocket连接已断开，尝试重连...');
                // 3秒后尝试重连
                setTimeout(() => {
                    this.connectWebSocket(wsUrl);
                }, 3000);
            };
            
            this.websocket.onerror = (error) => {
                this.addLog('WebSocket连接错误', 'error');
                console.error('WebSocket错误:', error);
            };
        } catch (e) {
            this.addLog('WebSocket初始化失败', 'error');
            console.error('WebSocket初始化失败:', e);
        }
    }
}

// 页面加载完成后初始化爬虫界面
let crawlerInterface;
document.addEventListener('DOMContentLoaded', () => {
    crawlerInterface = new CrawlerInterface();
});