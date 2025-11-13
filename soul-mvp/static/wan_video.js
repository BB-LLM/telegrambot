// Soul MVP Wan 视频生成前端交互逻辑

class WanVideoApp {
    constructor() {
        this.selectedSoul = null;
        this.currentTab = 'style';
        this.history = [];
        this.apiBaseUrl = window.location.origin;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.updateStatus('就绪，请选择 Soul 和功能', 'info');
    }
    
    bindEvents() {
        // Soul选择事件
        document.querySelectorAll('.soul-card').forEach(card => {
            card.addEventListener('click', (e) => {
                this.selectSoul(e.currentTarget.dataset.soul);
            });
        });
        
        // 功能切换事件
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.currentTarget.dataset.tab);
            });
        });
        
        // 表单提交事件
        document.getElementById('style-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateStyleVideo();
        });
        
        document.getElementById('selfie-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateSelfieVideo();
        });
    }
    
    selectSoul(soulId) {
        // 移除之前的选中状态
        document.querySelectorAll('.soul-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 添加选中状态
        const card = document.querySelector(`[data-soul="${soulId}"]`);
        if (card) {
            card.classList.add('selected');
        }
        
        this.selectedSoul = soulId;
        this.updateStatus(`已选择 Soul: ${soulId}`, 'info');
    }
    
    switchTab(tabId) {
        // 更新按钮状态
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
        
        // 显示/隐藏内容区域
        document.querySelectorAll('.content-section').forEach(section => {
            section.style.display = 'none';
        });
        const targetSection = document.getElementById(`${tabId}-section`);
        if (targetSection) {
            targetSection.style.display = 'block';
        }
        
        this.currentTab = tabId;
        const tabName = tabId === 'style' ? 'Soul 风格视频生成' : 'Soul 自拍视频';
        this.updateStatus(`已切换到 ${tabName}`, 'info');
    }
    
    async generateStyleVideo() {
        if (!this.selectedSoul) {
            this.updateStatus('请先选择一个 Soul', 'error');
            return;
        }
        
        const cue = document.getElementById('style-cue').value.trim();
        const userId = document.getElementById('user-id').value.trim();
        
        if (!cue) {
            this.updateStatus('请输入视频描述', 'error');
            return;
        }
        
        if (!userId) {
            this.updateStatus('请输入用户 ID', 'error');
            return;
        }
        
        // 显示加载遮罩
        this.showLoading('正在生成视频，请稍候...');
        
        // 禁用生成按钮
        const generateBtn = document.querySelector('#style-form button[type="submit"]');
        const originalText = generateBtn ? generateBtn.innerHTML : '';
        if (generateBtn) {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成中...';
        }
        
        try {
            // 调用 Wan 视频生成 API（自动生成 GIF）
            const params = new URLSearchParams({
                soul_id: this.selectedSoul,
                cue: cue,
                user_id: userId
            });
            
            const response = await fetch(`${this.apiBaseUrl}/wan-video/?${params.toString()}`, {
                method: 'GET'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '视频生成失败');
            }
            
            const result = await response.json();
            
            // 显示结果
            this.displayVideoResult(result, cue);
            
            // 添加到历史记录
            this.addToHistory({
                type: 'style',
                soul_id: this.selectedSoul,
                cue: cue,
                result: result,
                timestamp: new Date().toISOString()
            });
            
            this.updateStatus('视频生成成功！', 'success');
            
        } catch (error) {
            console.error('视频生成失败:', error);
            this.updateStatus(`生成失败: ${error.message}`, 'error');
        } finally {
            // 隐藏加载遮罩
            this.hideLoading();
            
            // 恢复生成按钮
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.innerHTML = originalText;
            }
        }
    }
    
    async generateSelfieVideo() {
        if (!this.selectedSoul) {
            this.updateStatus('请先选择一个 Soul', 'error');
            return;
        }
        
        const cityKey = document.getElementById('selfie-city').value;
        const mood = document.getElementById('selfie-mood').value;
        const userId = document.getElementById('selfie-user-id').value.trim();
        
        if (!userId) {
            this.updateStatus('请输入用户 ID', 'error');
            return;
        }
        
        // 显示加载遮罩
        this.showLoading('正在生成自拍视频，请稍候...');
        
        // 禁用生成按钮
        const generateBtn = document.querySelector('#selfie-form button[type="submit"]');
        const originalText = generateBtn ? generateBtn.innerHTML : '';
        if (generateBtn) {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成中...';
        }
        
        try {
            // 调用 Wan 自拍视频生成 API（自动生成 GIF）
            const response = await fetch(`${this.apiBaseUrl}/wan-video/selfie`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    soul_id: this.selectedSoul,
                    city_key: cityKey,
                    mood: mood,
                    user_id: userId
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '自拍视频生成失败');
            }
            
            const result = await response.json();
            
            // 显示结果
            this.displayVideoResult(result, `自拍 - ${cityKey}, ${mood}`, result.landmark_key);
            
            // 添加到历史记录
            this.addToHistory({
                type: 'selfie',
                soul_id: this.selectedSoul,
                city_key: cityKey,
                mood: mood,
                landmark_key: result.landmark_key,
                result: result,
                timestamp: new Date().toISOString()
            });
            
            this.updateStatus('自拍视频生成成功！', 'success');
            
        } catch (error) {
            console.error('自拍视频生成失败:', error);
            this.updateStatus(`生成失败: ${error.message}`, 'error');
        } finally {
            // 隐藏加载遮罩
            this.hideLoading();
            
            // 恢复生成按钮
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.innerHTML = originalText;
            }
        }
    }
    
    displayVideoResult(result, description, landmarkKey = null) {
        const resultContainer = document.getElementById('result-container');
        if (!resultContainer) return;
        
        // 清空之前的结果
        resultContainer.innerHTML = '';
        
        // 创建结果卡片
        const resultCard = document.createElement('div');
        resultCard.className = 'result-card';
        
        let html = `
            <div class="result-header">
                <h4>${description}</h4>
                ${landmarkKey ? `<p class="landmark-info">地标: ${landmarkKey}</p>` : ''}
                ${result.cache_hit ? '<span class="cache-badge">缓存命中</span>' : ''}
            </div>
            <div class="result-content">
                <div class="video-preview">
                    <h5>MP4 视频</h5>
                    <video controls width="100%" style="max-width: 600px; border-radius: 8px;">
                        <source src="${result.mp4_url}" type="video/mp4">
                        您的浏览器不支持视频播放。
                    </video>
                    <a href="${result.mp4_url}" download class="download-btn">
                        <i class="fas fa-download"></i> 下载 MP4
                    </a>
                </div>
        `;
        
        if (result.gif_url) {
            html += `
                <div class="gif-preview">
                    <h5>GIF 动画</h5>
                    <img src="${result.gif_url}" alt="GIF" style="max-width: 600px; border-radius: 8px;">
                    <a href="${result.gif_url}" download class="download-btn">
                        <i class="fas fa-download"></i> 下载 GIF
                    </a>
                </div>
            `;
        }
        
        html += `
            </div>
            <div class="result-meta">
                <p><strong>变体 ID:</strong> ${result.variant_id}</p>
                <p><strong>提示词键 ID:</strong> ${result.pk_id}</p>
            </div>
        `;
        
        resultCard.innerHTML = html;
        resultContainer.appendChild(resultCard);
    }
    
    addToHistory(item) {
        this.history.unshift(item);
        if (this.history.length > 10) {
            this.history = this.history.slice(0, 10);
        }
        this.updateHistoryDisplay();
    }
    
    updateHistoryDisplay() {
        const historyContainer = document.getElementById('history-container');
        if (!historyContainer) return;
        
        if (this.history.length === 0) {
            historyContainer.innerHTML = `
                <div class="no-history">
                    <i class="fas fa-clock"></i>
                    <p>没有生成历史</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        this.history.forEach((item, index) => {
            const date = new Date(item.timestamp).toLocaleString('zh-CN');
            html += `
                <div class="history-item">
                    <div class="history-header">
                        <span class="history-type">${item.type === 'style' ? '风格视频' : '自拍视频'}</span>
                        <span class="history-date">${date}</span>
                    </div>
                    <div class="history-content">
                        ${item.type === 'style' 
                            ? `<p><strong>提示词:</strong> ${item.cue}</p>`
                            : `<p><strong>城市:</strong> ${item.city_key}, <strong>情绪:</strong> ${item.mood}</p>`
                        }
                        <p><strong>Soul:</strong> ${item.soul_id}</p>
                        <div class="history-actions">
                            <a href="${item.result.mp4_url}" target="_blank" class="history-link">
                                <i class="fas fa-video"></i> 查看视频
                            </a>
                            ${item.result.gif_url ? `
                                <a href="${item.result.gif_url}" target="_blank" class="history-link">
                                    <i class="fas fa-image"></i> 查看 GIF
                                </a>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        historyContainer.innerHTML = html;
    }
    
    updateStatus(message, type = 'info') {
        const statusDisplay = document.getElementById('status-display');
        if (!statusDisplay) return;
        
        const iconMap = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'processing': 'fa-spinner fa-spin'
        };
        
        const icon = iconMap[type] || iconMap['info'];
        const colorMap = {
            'info': '#6366f1',
            'success': '#10b981',
            'error': '#ef4444',
            'processing': '#f59e0b'
        };
        const color = colorMap[type] || colorMap['info'];
        
        statusDisplay.innerHTML = `
            <div class="status-item" style="color: ${color};">
                <i class="fas ${icon}"></i>
                <span>${message}</span>
            </div>
        `;
    }
    
    showLoading(message = '正在处理...') {
        const overlay = document.getElementById('loading-overlay');
        const loadingText = document.getElementById('loading-text');
        if (overlay) {
            overlay.style.display = 'flex';
        }
        if (loadingText) {
            loadingText.textContent = message;
        }
    }
    
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
    
    clearResults() {
        const resultContainer = document.getElementById('result-container');
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="no-result">
                    <i class="fas fa-video"></i>
                    <p>还没有生成视频，请选择功能并生成</p>
                </div>
            `;
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.wanVideoApp = new WanVideoApp();
});

