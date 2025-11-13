// Soul MVP 前端交互逻辑

class SoulApp {
    constructor() {
        this.selectedSoul = null;
        this.currentTab = 'style';
        this.history = [];
        this.currentTask = null;
        this.taskPollingInterval = null;
        this.activeTasks = [];  // 存储所有活跃的任务
        this.apiBaseUrl = window.location.origin;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.updateStatus('Ready, please select Soul and function', 'info');
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
            this.generateStyleImage();
        });
        
        document.getElementById('selfie-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateSelfie();
        });
    }
    
    selectSoul(soulId) {
        // 移除之前的选中状态
        document.querySelectorAll('.soul-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 添加选中状态
        document.querySelector(`[data-soul="${soulId}"]`).classList.add('selected');
        
        this.selectedSoul = soulId;
        this.updateStatus(`Selected Soul: ${soulId}`, 'info');
    }
    
    switchTab(tabId) {
        // 更新按钮状态
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
        
        // 显示/隐藏内容区域
        document.querySelectorAll('.content-section').forEach(section => {
            section.style.display = 'none';
        });
        document.getElementById(`${tabId}-section`).style.display = 'block';
        
        this.currentTab = tabId;
        this.updateStatus(`Switched to ${tabId === 'style' ? 'Soul Style Generation' : 'Soul Selfie'} function`, 'info');
    }
    
    async generateStyleImage() {
        if (!this.selectedSoul) {
            this.updateStatus('Please select a Soul first', 'error');
            return;
        }
        
        const cue = document.getElementById('style-cue').value.trim();
        const userId = document.getElementById('user-id').value.trim();
        
        if (!cue) {
            this.updateStatus('Please enter image description', 'error');
            return;
        }
        
        if (!userId) {
            this.updateStatus('Please enter user ID', 'error');
            return;
        }
        
        // 启动加载状态，但不禁用按钮（允许创建多个任务）
        const generateBtn = document.querySelector('#style-form button[type="submit"]');
        const originalText = generateBtn ? generateBtn.innerHTML : '';
        
        if (generateBtn) {
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting task...';
        }
        
        // 清空之前的生成结果
        this.clearResults();
        
        try {
            // 启动后台任务
            const response = await fetch(`${this.apiBaseUrl}/tasks/generate?soul_id=${this.selectedSoul}&cue=${encodeURIComponent(cue)}&user_id=${userId}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start task');
            }
            
            const taskInfo = await response.json();
            this.currentTask = taskInfo.task_id;
            
            // 添加到活跃任务列表
            if (!this.activeTasks.find(t => t.task_id === taskInfo.task_id)) {
                this.activeTasks.push(taskInfo);
            }
            
            this.updateStatus('Task started, generating in background...', 'processing');
            this.updateTasksDisplay();
            this.startTaskPolling();
            
            // 任务启动成功，恢复按钮
            if (generateBtn) {
                generateBtn.innerHTML = originalText;
            }
            
        } catch (error) {
            console.error('Failed to start task:', error);
            this.updateStatus(`Failed to start task: ${error.message}`, 'error');
            
            // 恢复生成按钮
            if (generateBtn) {
                generateBtn.innerHTML = originalText;
            }
        }
    }
    
    async generateSelfie() {
        if (!this.selectedSoul) {
            this.updateStatus('Please select a Soul first', 'error');
            return;
        }
        
        const cityKey = document.getElementById('selfie-city').value;
        const mood = document.getElementById('selfie-mood').value;
        const userId = document.getElementById('selfie-user-id').value.trim();
        
        if (!userId) {
            this.updateStatus('Please enter user ID', 'error');
            return;
        }
        
        // 启动加载状态，但不禁用按钮（允许创建多个任务）
        const generateBtn = document.querySelector('#selfie-form button[type="submit"]');
        const originalText = generateBtn ? generateBtn.innerHTML : '';
        
        if (generateBtn) {
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting task...';
        }
        
        // 清空之前的生成结果
        this.clearResults();
        
        try {
            // 启动后台自拍任务
            const response = await fetch(`${this.apiBaseUrl}/tasks/selfie?soul_id=${this.selectedSoul}&city_key=${cityKey}&mood=${mood}&user_id=${userId}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start selfie task');
            }
            
            const taskInfo = await response.json();
            this.currentTask = taskInfo.task_id;
            
            // 添加到活跃任务列表
            if (!this.activeTasks.find(t => t.task_id === taskInfo.task_id)) {
                this.activeTasks.push(taskInfo);
            }
            
            this.updateStatus('Selfie task started, generating in background...', 'processing');
            this.updateTasksDisplay();
            this.startTaskPolling();
            
            // 任务启动成功，恢复按钮
            if (generateBtn) {
                generateBtn.innerHTML = originalText;
            }
            
        } catch (error) {
            console.error('Failed to start selfie task:', error);
            this.updateStatus(`Failed to start selfie task: ${error.message}`, 'error');
            
            // 恢复生成按钮
            if (generateBtn) {
                generateBtn.innerHTML = originalText;
            }
        }
    }
    
    showResult(result, type, extraInfo = {}) {
        const container = document.getElementById('result-container');
        
        // 检查是否已经有任务卡片在显示
        const existingTasks = container.querySelector('.tasks-container');
        
        // 生成唯一ID用于按钮绑定
        const resultId = `result-${result.variant_id || Date.now()}`;
        
        let resultHtml = `
            <div class="result-item" id="${resultId}">
                <img src="${result.url}" alt="Generated image" class="result-image" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDQwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjRjNGNEY2Ii8+Cjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjOUNBM0FGIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTgiPkp1c3QgYSBxdWljayBsb2FkaW5nIHBsYWNlaG9sZGVyPC90ZXh0Pgo8L3N2Zz4='">
                <div class="result-info">
                    <h4>Generation Result</h4>
                    <p><strong>Variant ID:</strong> ${result.variant_id}</p>
                    <p><strong>Prompt Key:</strong> ${result.pk_id}</p>
        `;
        
        if (type === 'selfie' && extraInfo.city) {
            resultHtml += `
                <p><strong>City:</strong> ${extraInfo.city}</p>
                <p><strong>Mood:</strong> ${extraInfo.mood}</p>
                <p><strong>Landmark:</strong> ${extraInfo.landmark}</p>
            `;
        }
        
        resultHtml += `
                    <p><strong>Cache Hit:</strong> ${result.cache_hit ? 'Yes' : 'No'}</p>
                    <div class="result-actions">
                        <button class="btn-convert-gif" id="convert-gif-btn-${result.variant_id}" 
                                onclick="app.convertToGif('${result.variant_id}', '${result.url}')">
                            <i class="fas fa-video"></i> Transform to GIF
                        </button>
                        <div id="gif-estimate-${result.variant_id}" class="gif-estimate" style="display: none;"></div>
                    </div>
                    <div id="gif-result-${result.variant_id}" class="gif-result" style="display: none;"></div>
                </div>
            </div>
        `;
        
        // 如果有活跃任务卡片，就追加结果，否则覆盖
        if (existingTasks) {
            // 追加结果到现有任务卡片后面
            container.insertAdjacentHTML('beforeend', resultHtml);
        } else {
            // 覆盖容器内容
            container.innerHTML = resultHtml;
        }
        
        // 标记变体为已看
        this.markVariantSeen(result.variant_id);
    }
    
    async markVariantSeen(variantId) {
        try {
            // 获取当前用户ID
            const userId = document.getElementById('user-id').value.trim() || 
                          document.getElementById('selfie-user-id').value.trim();
            
            if (!userId) {
                console.warn('Cannot mark variant as seen: user ID not set');
                return;
            }
            
            const response = await fetch(`${this.apiBaseUrl}/image/mark-seen?variant_id=${variantId}&user_id=${userId}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                console.log(`Variant ${variantId} marked as seen`);
            } else {
                console.warn(`Failed to mark variant ${variantId} as seen`);
            }
        } catch (error) {
            console.warn(`Error marking variant ${variantId} as seen:`, error);
        }
    }
    
    async convertToGif(variantId, imageUrl) {
        try {
            // 禁用按钮并显示加载状态
            const convertBtn = document.getElementById(`convert-gif-btn-${variantId}`);
            const estimateDiv = document.getElementById(`gif-estimate-${variantId}`);
            const resultDiv = document.getElementById(`gif-result-${variantId}`);
            
            if (!convertBtn || !estimateDiv || !resultDiv) {
                console.error('Cannot find convert GIF elements');
                return;
            }
            
            const originalText = convertBtn.innerHTML;
            convertBtn.disabled = true;
            convertBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            
            // 1. 首先获取预估时间
            try {
                const estimateResponse = await fetch(`${this.apiBaseUrl}/video/estimate`);
                if (estimateResponse.ok) {
                    const estimate = await estimateResponse.json();
                    estimateDiv.style.display = 'block';
                    estimateDiv.innerHTML = `
                        <div class="estimate-info">
                            <i class="fas fa-clock"></i>
                            <span>Estimated time: ${estimate.estimated_minutes} minutes (${estimate.estimated_seconds} seconds)</span>
                        </div>
                    `;
                }
            } catch (error) {
                console.warn('Failed to get estimate:', error);
            }
            
            // 2. 构建图像路径（优先使用variant_id从数据库获取真实路径）
            let imagePath = null;
            
            // 首先尝试使用variant_id获取真实路径（推荐方式）
            try {
                const variantResponse = await fetch(`${this.apiBaseUrl}/image/variants/${variantId}`);
                if (variantResponse.ok) {
                    const variantData = await variantResponse.json();
                    if (variantData.variants && variantData.variants.length > 0) {
                        const variant = variantData.variants[0];
                        // 从meta中获取local_filepath，这是真实路径
                        if (variant.meta && variant.meta.local_filepath) {
                            imagePath = variant.meta.local_filepath;
                        } else {
                            // 如果没有local_filepath，从URL转换
                            const url = variant.url || imageUrl;
                            if (url) {
                                // 将 /generated/xxx.png 转换为 generated_images/xxx.png
                                if (url.startsWith('/generated/')) {
                                    const filename = url.replace('/generated/', '');
                                    imagePath = `generated_images/${filename}`;
                                } else if (url.startsWith('/')) {
                                    imagePath = url.substring(1);
                                } else {
                                    imagePath = url;
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                console.warn('Failed to get variant info:', error);
            }
            
            // 如果从variant_id获取失败，尝试从imageUrl解析
            if (!imagePath) {
                // 从URL中提取路径
                if (imageUrl.startsWith('http')) {
                    const urlObj = new URL(imageUrl);
                    imagePath = urlObj.pathname;
                } else {
                    imagePath = imageUrl;
                }
                
                // 移除前导斜杠
                if (imagePath.startsWith('/')) {
                    imagePath = imagePath.substring(1);
                }
                
                // 将 /generated/ 转换为 generated_images/
                if (imagePath.startsWith('generated/')) {
                    imagePath = imagePath.replace('generated/', 'generated_images/');
                } else if (!imagePath.startsWith('generated_images/')) {
                    // 如果路径不包含目录，假设它在generated_images目录下
                    const filename = imagePath.split('/').pop();
                    imagePath = `generated_images/${filename}`;
                }
            }
            
            console.log('Using image path:', imagePath);
            
            // 3. 调用视频生成API
            convertBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating GIF...';
            
            const response = await fetch(`${this.apiBaseUrl}/video/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image_path: imagePath,
                    generate_gif: true
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || 'Failed to generate GIF');
            }
            
            const result = await response.json();
            
            // 4. 显示结果
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div class="gif-success">
                    <h5><i class="fas fa-check-circle"></i> GIF generated successfully!</h5>
                    <div class="gif-preview">
                        <img src="${result.gif_url}" alt="Generated GIF" class="gif-image" />
                    </div>
                    <div class="gif-info">
                        <p><strong>File size:</strong> ${result.gif_size_mb} MB</p>
                        <p><strong>Frame count:</strong> ${result.num_frames}</p>
                        <p><strong>Frame rate:</strong> ${result.fps} fps</p>
                        <p><strong>Total time:</strong> ${result.total_seconds} seconds</p>
                        <a href="${result.gif_url}" download="${result.gif_filename}" class="btn-download-gif">
                            <i class="fas fa-download"></i> Download GIF
                        </a>
                    </div>
                </div>
            `;
            
            // 恢复按钮（但标记为已完成）
            convertBtn.innerHTML = '<i class="fas fa-check"></i> Generated successfully';
            convertBtn.style.opacity = '0.6';
            
            this.updateStatus('GIF generated successfully!', 'success');
            
        } catch (error) {
            console.error('Failed to convert to GIF:', error);
            
            const convertBtn = document.getElementById(`convert-gif-btn-${variantId}`);
            const resultDiv = document.getElementById(`gif-result-${variantId}`);
            
            if (convertBtn) {
                convertBtn.disabled = false;
                convertBtn.innerHTML = '<i class="fas fa-video"></i> Transform to GIF';
            }
            
            if (resultDiv) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `
                    <div class="gif-error">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Failed to generate GIF: ${error.message}</p>
                        ${error.message.includes('409') || error.message.includes('The system is processing other tasks, please try again later') ? 
                            '<p class="error-hint">The system is processing other tasks, please try again later</p>' : ''}
                    </div>
                `;
            }
            
            this.updateStatus(`Failed to generate GIF: ${error.message}`, 'error');
        }
    }
    
    updateTasksDisplay() {
        const container = document.getElementById('result-container');
        
        // 过滤出活跃的任务（pending 或 running）
        const activeTasks = this.activeTasks.filter(
            t => t.status === 'pending' || t.status === 'running'
        );
        
        // 生成所有活跃任务的HTML
        let tasksHtml = '<div class="tasks-container">';
        activeTasks.forEach(task => {
            tasksHtml += this.generateTaskCard(task);
        });
        tasksHtml += '</div>';
        
        // 获取现有的结果项（已完成的图片）
        const existingResults = container.querySelectorAll('.result-item');
        
        // 如果有结果项，就保留它们并添加任务卡片
        if (existingResults.length > 0) {
            // 创建任务卡片
            let tasksContainer = container.querySelector('.tasks-container');
            if (tasksContainer) {
                // 更新现有任务容器
                tasksContainer.innerHTML = '';
                activeTasks.forEach(task => {
                    tasksContainer.insertAdjacentHTML('beforeend', this.generateTaskCard(task));
                });
            } else if (activeTasks.length > 0) {
                // 添加新的任务容器
                container.insertAdjacentHTML('afterbegin', tasksHtml);
            }
        } else if (activeTasks.length > 0) {
            // 没有结果项，覆盖容器
            container.innerHTML = tasksHtml;
        } else {
            // 没有活跃任务且没有结果项，显示空状态
            container.innerHTML = `
                <div class="no-result">
                    <i class="fas fa-image"></i>
                    <p>No images generated yet, please select function and generate</p>
                </div>
            `;
            return;
        }
        
        // 为每个任务绑定取消按钮事件
        activeTasks.forEach(task => {
            const cancelBtn = document.getElementById(`cancel-task-btn-${task.task_id}`);
            if (cancelBtn) {
                cancelBtn.addEventListener('click', async () => {
                    await this.cancelTask(task.task_id);
                });
            }
        });
    }
    
    generateTaskCard(taskInfo) {
        const progressHtml = `
            <div class="task-progress">
                <div class="progress-header">
                    <h4>Task ${taskInfo.task_id.substring(0, 8)}... (${taskInfo.task_type === 'style_generation' ? 'Style' : 'Selfie'})</h4>
                    <button class="cancel-btn" id="cancel-task-btn-${taskInfo.task_id}">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${taskInfo.progress}%"></div>
                </div>
                <div class="progress-info">
                    <span class="progress-text">${taskInfo.progress}%</span>
                    <span class="task-status">${this.getStatusText(taskInfo.status)}</span>
                </div>
                <div class="task-details">
                    <p><strong>Type:</strong> ${taskInfo.task_type === 'style_generation' ? 'Style Generation' : 'Selfie Generation'}</p>
                    <p><strong>Created:</strong> ${new Date(taskInfo.created_at).toLocaleString()}</p>
                </div>
            </div>
        `;
        return progressHtml;
    }
    
    showTaskProgress(taskInfo) {
        // 兼容旧代码，调用新的更新方法
        this.updateTasksDisplay();
    }
    
    getStatusText(status) {
        const statusMap = {
            'pending': 'Pending',
            'running': 'Running',
            'completed': 'Completed',
            'failed': 'Failed',
            'cancelled': 'Cancelled'
        };
        return statusMap[status] || status;
    }
    
    startTaskPolling() {
        if (this.taskPollingInterval) {
            clearInterval(this.taskPollingInterval);
        }
        
        let pollCount = 0;
        const maxPolls = 200; // 最多轮询800次（约40分钟，防止真正超时）
        let lastProgress = 0;
        let stalledCount = 0;
        
        const pollTask = async () => {
            // 更新所有活跃任务的状态
            const tasksToUpdate = [...this.activeTasks.filter(t => t.status === 'pending' || t.status === 'running')];
            
            if (tasksToUpdate.length === 0) {
                clearInterval(this.taskPollingInterval);
                this.taskPollingInterval = null;
                this.updateTasksDisplay();
                return;
            }
            
            // 更新轮询计数
            pollCount++;
            
            // 检查是否超时
            if (pollCount > 200) {
                console.log('Long-running task monitoring...');
                this.updateStatus('Task is taking longer, still processing in background, please wait...', 'warning');
                pollCount = 0; // 重置计数器继续监控
            }
            
            let hasActiveTasks = false;
            
            for (const task of tasksToUpdate) {
                try {
                    const response = await fetch(`${this.apiBaseUrl}/tasks/${task.task_id}`);
                    if (response.ok) {
                        const taskInfo = await response.json();
                        
                        // 更新任务信息
                        const taskIndex = this.activeTasks.findIndex(t => t.task_id === task.task_id);
                        if (taskIndex !== -1) {
                            this.activeTasks[taskIndex] = taskInfo;
                        }
                        
                        // 检查任务是否完成
                        if (taskInfo.status === 'completed' || taskInfo.status === 'failed' || taskInfo.status === 'cancelled') {
                            this.handleTaskComplete(taskInfo);
                        } else {
                            hasActiveTasks = true;
                        }
                    }
                } catch (error) {
                    console.error(`Failed to poll task ${task.task_id}:`, error);
                }
            }
            
            // 更新显示
            this.updateTasksDisplay();
            
            // 如果没有活跃任务了，停止轮询
            if (!hasActiveTasks) {
                this.stopTaskPolling();
            }
        };
        
        // 立即执行一次
        pollTask();
        
        // 然后每3秒轮询一次
        this.taskPollingInterval = setInterval(pollTask, 3000);
    }
    
    startSlowPolling() {
        if (this.taskPollingInterval) {
            clearInterval(this.taskPollingInterval);
        }
        
        let pollCount = 0;
        const maxPolls = 240; // 最多轮询240次（约20分钟，防止真正超时）
        
        this.taskPollingInterval = setInterval(async () => {
            if (!this.currentTask) {
                clearInterval(this.taskPollingInterval);
                return;
            }
            
            pollCount++;
            if (pollCount > maxPolls) {
                console.log('长期运行任务监控中...');
                this.updateStatus('Task is taking longer, still processing in background, please wait...', 'warning');
                pollCount = 0; // 重置计数器继续监控
            }
            
            try {
                const response = await fetch(`${this.apiBaseUrl}/tasks/${this.currentTask}`);
                if (response.ok) {
                    const taskInfo = await response.json();
                    this.updateTaskProgress(taskInfo);
                    
                    if (taskInfo.status === 'completed' || taskInfo.status === 'failed' || taskInfo.status === 'cancelled') {
                        this.stopTaskPolling();
                        this.handleTaskComplete(taskInfo);
                    }
                }
            } catch (error) {
                console.error('Failed to slow poll task status:', error);
            }
        }, 5000); // 每5秒轮询一次
    }
    
    stopTaskPolling() {
        if (this.taskPollingInterval) {
            clearInterval(this.taskPollingInterval);
            this.taskPollingInterval = null;
        }
    }
    
    updateTaskProgress(taskInfo) {
        // 更新任务信息
        const taskIndex = this.activeTasks.findIndex(t => t.task_id === taskInfo.task_id);
        if (taskIndex !== -1) {
            this.activeTasks[taskIndex] = taskInfo;
        }
        this.updateTasksDisplay();
    }
    
    handleTaskComplete(taskInfo) {
        console.log('Task completion handling:', taskInfo.status);
        
        // 从活跃任务列表中移除
        this.activeTasks = this.activeTasks.filter(t => t.task_id !== taskInfo.task_id);
        
        // 如果这是当前任务，清除引用
        if (this.currentTask === taskInfo.task_id) {
            this.currentTask = null;
            this.restoreGenerateButton();
        }
        
        if (taskInfo.status === 'completed' && taskInfo.result) {
            this.updateStatus('Task completed!', 'success');
            this.showResult(taskInfo.result, taskInfo.task_type);
            
            // 添加到历史记录
            const params = taskInfo.params || {};
            if (taskInfo.task_type === 'style_generation') {
                this.addToHistory(taskInfo.result, 'style', params.cue || '');
            } else if (taskInfo.task_type === 'selfie_generation') {
                this.addToHistory(
                    taskInfo.result, 
                    'selfie', 
                    `${params.city_key} - ${params.mood}`, 
                    { 
                        city: params.city_key, 
                        mood: params.mood, 
                        landmark: taskInfo.result.landmark_key 
                    }
                );
            }
        } else if (taskInfo.status === 'failed') {
            this.updateStatus(`Task failed: ${taskInfo.error || 'Unknown error'}`, 'error');
            this.showTaskError(taskInfo);
        } else if (taskInfo.status === 'cancelled') {
            console.log('Task was cancelled');
            this.updateStatus('Task cancelled', 'info');
            this.showTaskCancelled(taskInfo);
        }
        
        // 更新任务卡片显示（移除已完成的任务）
        this.updateTasksDisplay();
    }
    
    showTaskError(taskInfo) {
        const container = document.getElementById('result-container');
        container.innerHTML = `
            <div class="task-error">
                <i class="fas fa-exclamation-triangle"></i>
                <h4>Task Failed</h4>
                <p>${taskInfo.error || 'Unknown error'}</p>
                <button class="retry-btn" onclick="app.retryLastTask()">
                    <i class="fas fa-redo"></i> Retry
                </button>
            </div>
        `;
    }
    
    showTaskCancelled(taskInfo) {
        const container = document.getElementById('result-container');
        container.innerHTML = `
            <div class="task-cancelled">
                <i class="fas fa-ban"></i>
                <h4>Task Cancelled</h4>
                <p>Task was cancelled by user</p>
                <button class="retry-btn" onclick="app.retryLastTask()">
                    <i class="fas fa-redo"></i> Start Over
                </button>
            </div>
        `;
    }
    
    async cancelTask(taskId) {
        console.log('Cancelling task:', taskId);
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/tasks/${taskId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                console.log('Task cancelled successfully');
                
                // 从活跃任务列表中移除
                this.activeTasks = this.activeTasks.filter(t => t.task_id !== taskId);
                
                // 更新显示
                this.updateTasksDisplay();
                
                // 如果这是当前任务，清除引用
                if (this.currentTask === taskId) {
                    this.currentTask = null;
                    this.restoreGenerateButton();
                }
                
                this.updateStatus('Task cancelled successfully', 'success');
            } else if (response.status === 404) {
                console.log('Task does not exist or is already completed');
                // 从列表中移除（可能已完成）
                this.activeTasks = this.activeTasks.filter(t => t.task_id !== taskId);
                this.updateTasksDisplay();
            } else {
                const errorData = await response.json();
                console.error('Failed to cancel task:', errorData);
                throw new Error(errorData.detail || 'Failed to cancel task');
            }
        } catch (error) {
            console.error('Failed to cancel task:', error);
            this.updateStatus(`Failed to cancel task: ${error.message}`, 'error');
            throw error;
        }
    }
    
    async cancelCurrentTask() {
        if (!this.currentTask) {
            this.updateStatus('No running task', 'warning');
            return;
        }
        
        await this.cancelTask(this.currentTask);
    }
    
    restoreGenerateButton() {
        // 恢复生成按钮（按钮应该一直是可用状态）
        const generateBtn = document.querySelector(`#${this.currentTab}-form button[type="submit"]`);
        if (generateBtn) {
            // 按钮不禁用，只是恢复文本
            if (this.currentTab === 'style') {
                generateBtn.innerHTML = '<i class="fas fa-magic"></i> Generate Soul Style Image';
            } else {
                generateBtn.innerHTML = '<i class="fas fa-camera"></i> Generate Soul Selfie';
            }
        }
    }
    
    retryLastTask() {
        // 重新提交最后一个任务
        if (this.currentTab === 'style') {
            this.generateStyleImage();
        } else {
            this.generateSelfie();
        }
    }
    
    addToHistory(result, type, description, extraInfo = {}) {
        const historyItem = {
            id: result.variant_id,
            url: result.url,
            type: type,
            description: description,
            timestamp: new Date().toLocaleString(),
            extraInfo: extraInfo
        };
        
        this.history.unshift(historyItem);
        
        // 限制历史记录数量
        if (this.history.length > 20) {
            this.history = this.history.slice(0, 20);
        }
        
        this.updateHistoryDisplay();
    }
    
    updateHistoryDisplay() {
        const container = document.getElementById('history-container');
        
        if (this.history.length === 0) {
            container.innerHTML = `
                <div class="no-history">
                    <i class="fas fa-clock"></i>
                    <p>No generation history</p>
                </div>
            `;
            return;
        }
        
        const historyHtml = `
            <div class="history-list">
                ${this.history.map(item => `
                    <div class="history-item" onclick="app.showHistoryDetail('${item.id}')">
                        <img src="${item.url}" alt="${item.description}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjEyMCIgdmlld0JveD0iMCAwIDIwMCAxMjAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiBmaWxsPSIjRjNGNEY2Ii8+Cjx0ZXh0IHg9IjEwMCIgeT0iNjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiM5Q0EzQUYiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCI+5Yqg6L295Yqg6L295Yqg6L29PC90ZXh0Pgo8L3N2Zz4='">
                        <h4>${item.type === 'style' ? 'Style Generation' : 'Selfie'}</h4>
                        <p>${item.description}</p>
                        <p>${item.timestamp}</p>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = historyHtml;
    }
    
    showHistoryDetail(historyId) {
        const item = this.history.find(h => h.id === historyId);
        if (item) {
            // 清空之前的结果
            this.clearResults();
            
            this.showResult(item, item.type, item.extraInfo);
            this.updateStatus(`View history: ${item.description}`, 'info');
        }
    }
    
    clearResults() {
        const container = document.getElementById('result-container');
        if (container) {
            // 清空所有结果和任务卡片
            container.innerHTML = '';
        }
    }
    
    updateStatus(message, type = 'info') {
        const statusDisplay = document.getElementById('status-display');
        const statusItem = statusDisplay.querySelector('.status-item');
        
        let iconClass = 'fas fa-info-circle';
        if (type === 'processing') {
            iconClass = 'fas fa-spinner';
        } else if (type === 'success') {
            iconClass = 'fas fa-check-circle';
        } else if (type === 'error') {
            iconClass = 'fas fa-exclamation-circle';
        }
        
        statusItem.className = `status-item ${type}`;
        statusItem.innerHTML = `
            <i class="${iconClass}"></i>
            <span>${message}</span>
        `;
    }
    
    showLoading(customText = 'Generating image...') {
        const overlay = document.getElementById('loading-overlay');
        const loadingText = document.getElementById('loading-text');
        
        loadingText.textContent = customText;
        overlay.style.display = 'flex';
    }
    
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = 'none';
    }
    
    // 工具方法
    async checkApiHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/healthz`);
            if (response.ok) {
                this.updateStatus('API service is healthy', 'success');
                return true;
            } else {
                this.updateStatus('API service is not healthy', 'error');
                return false;
            }
        } catch (error) {
            this.updateStatus('Cannot connect to API service', 'error');
            return false;
        }
    }
    
    async loadSystemInfo() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/info`);
            if (response.ok) {
                const info = await response.json();
                console.log('System information:', info);
                return info;
            }
        } catch (error) {
            console.error('Failed to get system information:', error);
        }
        return null;
    }
}

// 全局应用实例
let app;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    app = new SoulApp();
    
    // 检查API健康状态
    app.checkApiHealth();
    
    // 加载系统信息
    app.loadSystemInfo();
    
    console.log('Soul MVP 前端应用已启动');
});

// 错误处理
window.addEventListener('error', (event) => {
    console.error('全局错误:', event.error);
    if (app) {
        app.updateStatus('Unknown error occurred, please refresh the page and try again', 'error');
    }
});

// 网络状态检测
window.addEventListener('online', () => {
    if (app) {
        app.updateStatus('Network connection restored', 'success');
    }
});

window.addEventListener('offline', () => {
    if (app) {
        app.updateStatus('Network connection lost', 'error');
    }
});
