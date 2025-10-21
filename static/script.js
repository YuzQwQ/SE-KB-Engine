class ChatInterface {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.loading = document.getElementById('loading');
        this.charCount = document.querySelector('.char-count');
        this.downloadButton = document.getElementById('downloadButton');
        this.downloadPanel = document.getElementById('downloadPanel');
        this.filesList = document.getElementById('filesList');
        
        this.initEventListeners();
        this.autoResizeTextarea();
        this.initDownloadFeature();
    }
    
    initEventListeners() {
        // 发送按钮点击事件
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // 输入框事件
        this.messageInput.addEventListener('input', () => {
            this.updateCharCount();
            this.updateSendButton();
            this.autoResizeTextarea();
        });
        
        // 键盘事件
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // 初始化状态
        this.updateCharCount();
        this.updateSendButton();
    }
    
    updateCharCount() {
        const length = this.messageInput.value.length;
        this.charCount.textContent = `${length}/2000`;
        
        if (length > 1800) {
            this.charCount.style.color = '#ef4444';
        } else if (length > 1500) {
            this.charCount.style.color = '#f59e0b';
        } else {
            this.charCount.style.color = '#64748b';
        }
    }
    
    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText;
    }
    
    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        const scrollHeight = this.messageInput.scrollHeight;
        const maxHeight = 120;
        this.messageInput.style.height = Math.min(scrollHeight, maxHeight) + 'px';
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // 添加用户消息到界面
        this.addMessage(message, 'user');
        
        // 清空输入框
        this.messageInput.value = '';
        this.updateCharCount();
        this.updateSendButton();
        this.autoResizeTextarea();
        
        // 显示加载状态
        this.showLoading();
        
        try {
            // 发送请求到后端
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 添加AI回复到界面（兜底处理空文本）
            const assistantText = (data && typeof data.response === 'string' && data.response.trim().length > 0)
                ? data.response
                : '这次没有生成文本回复。如果你要进行“搜索并爬取”，请直接输入：搜索并爬取 <关键词>，或调用 /api/search_extract_universal 接口。';
            this.addMessage(assistantText, 'assistant');
            
        } catch (error) {
            console.error('发送消息失败:', error);
            this.addMessage('抱歉，发生了错误，请稍后重试。', 'assistant', true);
        } finally {
            this.hideLoading();
        }
    }
    
    addMessage(text, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const currentTime = new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="message-content ${isError ? 'error' : ''}">
                <div class="message-text">${this.escapeHtml(text)}</div>
                <div class="message-time">${currentTime}</div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    showLoading() {
        this.loading.style.display = 'flex';
    }
    
    hideLoading() {
        this.loading.style.display = 'none';
    }
    
    // 下载功能相关方法
    initDownloadFeature() {
        // 检查元素是否存在
        if (!this.downloadButton) {
            console.error('下载按钮元素未找到');
            return;
        }
        if (!this.downloadPanel) {
            console.error('下载面板元素未找到');
            return;
        }
        
        console.log('初始化下载功能...');
        
        // 下载按钮点击事件
        this.downloadButton.addEventListener('click', (e) => {
            console.log('下载按钮被点击');
            e.preventDefault();
            this.showDownloadPanel();
        });
        
        // 关闭下载面板
        document.getElementById('closeDownloadPanel').addEventListener('click', () => {
            this.hideDownloadPanel();
        });
        
        // 点击面板外部关闭
        this.downloadPanel.addEventListener('click', (e) => {
            if (e.target === this.downloadPanel) {
                this.hideDownloadPanel();
            }
        });
        
        // 刷新文件列表
        document.getElementById('refreshFiles').addEventListener('click', () => {
            this.loadFilesList();
        });
        
        // 下载全部文件
        document.getElementById('downloadAll').addEventListener('click', () => {
            this.downloadAllFiles();
        });
        
        // ESC键关闭面板
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.downloadPanel.classList.contains('show')) {
                this.hideDownloadPanel();
            }
        });
    }
    
    showDownloadPanel() {
        console.log('显示下载面板');
        this.downloadPanel.classList.add('show');
        this.loadFilesList();
    }
    
    hideDownloadPanel() {
        this.downloadPanel.classList.remove('show');
    }
    
    async loadFilesList() {
        try {
            console.log('开始加载文件列表...');
            this.filesList.innerHTML = '<div class="loading-files">正在加载文件列表...</div>';
            
            const response = await fetch('/api/files');
            console.log('API响应状态:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('获取到的文件数据:', data);
            this.renderFilesList(data.files);
        } catch (error) {
            console.error('加载文件列表失败:', error);
            this.filesList.innerHTML = `
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <h4>加载失败</h4>
                    <p>无法获取文件列表: ${error.message}</p>
                </div>
            `;
        }
    }
    
    renderFilesList(files) {
        if (!files || files.length === 0) {
            this.filesList.innerHTML = `
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14,2 14,8 20,8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10,9 9,9 8,9"></polyline>
                    </svg>
                    <h4>暂无文件</h4>
                    <p>还没有爬取任何网页数据</p>
                </div>
            `;
            return;
        }
        
        const filesHtml = files.map(file => {
            const fileSize = this.formatFileSize(file.size);
            const modifiedDate = new Date(file.modified).toLocaleString('zh-CN');
            
            return `
                <div class="file-item">
                    <div class="file-info">
                        <div class="file-name">${this.escapeHtml(file.name)}</div>
                        <div class="file-meta">
                            <span class="file-type ${file.type}">${file.type}</span>
                            <span>大小: ${fileSize}</span>
                            <span>修改时间: ${modifiedDate}</span>
                        </div>
                    </div>
                    <button class="download-btn" onclick="chatInterface.downloadFile('${file.type}', '${this.escapeHtml(file.name)}')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7,10 12,15 17,10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        下载
                    </button>
                </div>
            `;
        }).join('');
        
        this.filesList.innerHTML = filesHtml;
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async downloadFile(fileType, fileName) {
        try {
            const url = `/api/download/${fileType}/${encodeURIComponent(fileName)}`;
            const link = document.createElement('a');
            link.href = url;
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('下载文件失败:', error);
            alert('下载文件失败: ' + error.message);
        }
    }
    
    async downloadAllFiles() {
        try {
            const button = document.getElementById('downloadAll');
            const originalText = button.innerHTML;
            button.innerHTML = '<span>正在打包...</span>';
            button.disabled = true;
            
            const url = '/api/download-all';
            const link = document.createElement('a');
            link.href = url;
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // 恢复按钮状态
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 2000);
        } catch (error) {
            console.error('下载全部文件失败:', error);
            alert('下载全部文件失败: ' + error.message);
            
            // 恢复按钮状态
            const button = document.getElementById('downloadAll');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }
}

// 页面加载完成后初始化聊天界面
let chatInterface;
document.addEventListener('DOMContentLoaded', () => {
    chatInterface = new ChatInterface();
    
    // 添加一些CSS样式用于错误消息
    const style = document.createElement('style');
    style.textContent = `
        .message-content.error {
            background: #fef2f2 !important;
            border: 1px solid #fecaca !important;
            color: #dc2626 !important;
        }
        
        .message.user .message-content.error {
            background: #dc2626 !important;
            color: white !important;
        }
    `;
    document.head.appendChild(style);
});

// 添加一些实用功能
window.addEventListener('beforeunload', (e) => {
    const messageInput = document.getElementById('messageInput');
    if (messageInput && messageInput.value.trim()) {
        e.preventDefault();
        e.returnValue = '您有未发送的消息，确定要离开吗？';
    }
});