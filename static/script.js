class ChatInterface {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.loading = document.getElementById('loading');
        this.charCount = document.querySelector('.char-count');
        
        this.initEventListeners();
        this.autoResizeTextarea();
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
            
            // 添加AI回复到界面
            this.addMessage(data.response, 'assistant');
            
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
}

// 页面加载完成后初始化聊天界面
document.addEventListener('DOMContentLoaded', () => {
    new ChatInterface();
    
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