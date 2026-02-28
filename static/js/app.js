// Omni Memory - 前端应用

// 状态管理
const state = {
    endpoints: [],
    memories: [],
    memorySettings: {},
    currentSection: 'endpoints'
};

// DOM 元素
const elements = {};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initElements();
    bindEvents();
    loadAllData();
});

function initElements() {
    // 导航
    elements.navItems = document.querySelectorAll('.nav-item');
    elements.sections = document.querySelectorAll('.section');
    elements.pageTitle = document.getElementById('page-title');
    
    // 端点
    elements.endpointsTable = document.getElementById('endpoints-table').querySelector('tbody');
    elements.addEndpointBtn = document.getElementById('add-endpoint-btn');
    elements.endpointModal = document.getElementById('endpoint-modal');
    elements.endpointForm = document.getElementById('endpoint-form');
    elements.endpointModalTitle = document.getElementById('endpoint-modal-title');
    elements.endpointOriginalName = document.getElementById('endpoint-original-name');
    elements.closeEndpointModal = document.getElementById('close-endpoint-modal');
    elements.cancelEndpointBtn = document.getElementById('cancel-endpoint-btn');
    elements.saveEndpointBtn = document.getElementById('save-endpoint-btn');
    
    // 记忆设置
    elements.saveSettingsBtn = document.getElementById('save-settings-btn');
    elements.memoryModeInputs = document.querySelectorAll('input[name="memory-mode"]');
    elements.injectionModeInputs = document.querySelectorAll('input[name="injection-mode"]');
    elements.externalModelConfig = document.getElementById('external-model-config');
    elements.ragConfig = document.getElementById('rag-config');
    elements.externalEndpointSelect = document.getElementById('external-endpoint-select');
    elements.externalModelSelect = document.getElementById('external-model-select');
    elements.externalEndpoint = document.getElementById('external-endpoint');
    elements.externalApiKey = document.getElementById('external-api-key');
    elements.summaryInterval = document.getElementById('summary-interval');
    elements.ragMaxMemories = document.getElementById('rag-max-memories');
    elements.ragEndpointSelect = document.getElementById('rag-endpoint-select');
    elements.ragModelSelect = document.getElementById('rag-model-select');
    
    // 记忆管理
    elements.memoriesList = document.getElementById('memories-list');
    elements.memorySearch = document.getElementById('memory-search');
    elements.searchBtn = document.getElementById('search-btn');
    elements.addMemoryBtn = document.getElementById('add-memory-btn');
    elements.memoryCount = document.getElementById('memory-count');
    elements.memoryModal = document.getElementById('memory-modal');
    elements.memoryForm = document.getElementById('memory-form');
    elements.memoryModalTitle = document.getElementById('memory-modal-title');
    elements.memoryId = document.getElementById('memory-id');
    elements.memoryContent = document.getElementById('memory-content');
    elements.closeMemoryModal = document.getElementById('close-memory-modal');
    elements.cancelMemoryBtn = document.getElementById('cancel-memory-btn');
    elements.saveMemoryBtn = document.getElementById('save-memory-btn');
    
    // 其他
    elements.refreshBtn = document.getElementById('refresh-btn');
    elements.toastContainer = document.getElementById('toast-container');
}

function bindEvents() {
    // 导航切换
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            switchSection(section);
        });
    });
    
    // 端点管理
    elements.addEndpointBtn.addEventListener('click', () => openEndpointModal());
    elements.closeEndpointModal.addEventListener('click', closeEndpointModal);
    elements.cancelEndpointBtn.addEventListener('click', closeEndpointModal);
    elements.saveEndpointBtn.addEventListener('click', saveEndpoint);
    elements.endpointModal.addEventListener('click', (e) => {
        if (e.target === elements.endpointModal) closeEndpointModal();
    });
    
    // 记忆设置
    elements.saveSettingsBtn.addEventListener('click', saveMemorySettings);
    elements.memoryModeInputs.forEach(input => {
        input.addEventListener('change', updateSettingsVisibility);
    });
    elements.injectionModeInputs.forEach(input => {
        input.addEventListener('change', updateSettingsVisibility);
    });
    
    // 外接模型端点选择
    elements.externalEndpointSelect.addEventListener('change', () => {
        updateModelSelect(elements.externalEndpointSelect, elements.externalModelSelect, 
                         elements.externalEndpoint, elements.externalApiKey);
    });
    
    // RAG端点选择
    elements.ragEndpointSelect.addEventListener('change', () => {
        updateModelSelect(elements.ragEndpointSelect, elements.ragModelSelect);
    });
    
    // 记忆管理
    elements.addMemoryBtn.addEventListener('click', () => openMemoryModal());
    elements.closeMemoryModal.addEventListener('click', closeMemoryModal);
    elements.cancelMemoryBtn.addEventListener('click', closeMemoryModal);
    elements.saveMemoryBtn.addEventListener('click', saveMemory);
    elements.memoryModal.addEventListener('click', (e) => {
        if (e.target === elements.memoryModal) closeMemoryModal();
    });
    elements.searchBtn.addEventListener('click', () => searchMemories());
    elements.memorySearch.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchMemories();
    });
    
    // 刷新
    elements.refreshBtn.addEventListener('click', loadAllData);
}

// 填充端点下拉框
function populateEndpointSelects() {
    const externalSelect = elements.externalEndpointSelect;
    const ragSelect = elements.ragEndpointSelect;
    
    // 清空现有选项(保留第一个)
    externalSelect.innerHTML = '<option value="">-- 选择端点 --</option>';
    ragSelect.innerHTML = '<option value="">-- 选择端点 --</option>';
    
    // 添加启用的端点
    state.endpoints.forEach(ep => {
        if (ep.enabled) {
            const option1 = document.createElement('option');
            option1.value = ep.name;
            option1.textContent = `${ep.name} (${ep.provider})`;
            option1.dataset.url = ep.url;
            option1.dataset.key = ep.api_key;
            option1.dataset.models = JSON.stringify(ep.models);
            externalSelect.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = ep.name;
            option2.textContent = `${ep.name} (${ep.provider})`;
            option2.dataset.url = ep.url;
            option2.dataset.key = ep.api_key;
            option2.dataset.models = JSON.stringify(ep.models);
            ragSelect.appendChild(option2);
        }
    });
}

// 更新模型选择下拉框
function updateModelSelect(endpointSelect, modelSelect, urlInput = null, keyInput = null) {
    const selectedOption = endpointSelect.selectedOptions[0];
    
    if (!selectedOption || !selectedOption.value) {
        modelSelect.innerHTML = '<option value="">-- 先选择端点 --</option>';
        if (urlInput) urlInput.value = '';
        if (keyInput) keyInput.value = '';
        return;
    }
    
    // 更新URL和密钥
    if (urlInput) urlInput.value = selectedOption.dataset.url || '';
    if (keyInput) keyInput.value = selectedOption.dataset.key || '';
    
    // 填充模型选项
    const models = JSON.parse(selectedOption.dataset.models || '[]');
    modelSelect.innerHTML = '<option value="">-- 选择模型 --</option>';
    
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
    });
}

// 切换页面
function switchSection(section) {
    state.currentSection = section;
    
    // 更新导航
    elements.navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });
    
    // 更新页面内容
    elements.sections.forEach(sec => {
        sec.classList.toggle('active', sec.id === `${section}-section`);
    });
    
    // 更新标题
    const titles = {
        'endpoints': 'API端点管理',
        'memory-settings': '记忆功能配置',
        'memories': '记忆管理'
    };
    elements.pageTitle.textContent = titles[section];
    
    // 加载对应数据
    if (section === 'endpoints') {
        loadEndpoints();
    } else if (section === 'memory-settings') {
        loadMemorySettings();
    } else if (section === 'memories') {
        loadMemories();
    }
}

// 加载所有数据
async function loadAllData() {
    await Promise.all([
        loadEndpoints(),
        loadMemorySettings(),
        loadMemories()
    ]);
}

// 加载端点
async function loadEndpoints() {
    try {
        const response = await fetch('/api/config/endpoints');
        if (!response.ok) throw new Error('加载失败');
        state.endpoints = await response.json();
        renderEndpoints();
    } catch (error) {
        showToast('加载端点配置失败', 'error');
    }
}

// 渲染端点列表
function renderEndpoints() {
    elements.endpointsTable.innerHTML = state.endpoints.map(ep => `
        <tr>
            <td>${escapeHtml(ep.name)}</td>
            <td><span class="status-badge ${ep.provider === 'openai' ? 'status-enabled' : 'status-disabled'}">${ep.provider}</span></td>
            <td>${escapeHtml(ep.url)}</td>
            <td>${ep.models.map(m => `<span class="status-badge" style="margin-right: 4px;">${escapeHtml(m)}</span>`).join('')}</td>
            <td><span class="status-badge ${ep.enabled ? 'status-enabled' : 'status-disabled'}">${ep.enabled ? '启用' : '禁用'}</span></td>
            <td class="actions-cell">
                <button class="btn btn-secondary" onclick="editEndpoint('${escapeHtml(ep.name)}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-danger" onclick="deleteEndpoint('${escapeHtml(ep.name)}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 打开端点模态框
function openEndpointModal(endpoint = null) {
    elements.endpointForm.reset();
    elements.endpointOriginalName.value = '';
    
    if (endpoint) {
        elements.endpointModalTitle.textContent = '编辑端点';
        elements.endpointOriginalName.value = endpoint.name;
        document.getElementById('endpoint-name').value = endpoint.name;
        document.getElementById('endpoint-provider').value = endpoint.provider;
        document.getElementById('endpoint-url').value = endpoint.url;
        document.getElementById('endpoint-api-key').value = endpoint.api_key;
        document.getElementById('endpoint-models').value = endpoint.models.join(',');
        document.getElementById('endpoint-enabled').checked = endpoint.enabled;
    } else {
        elements.endpointModalTitle.textContent = '添加端点';
    }
    
    elements.endpointModal.classList.add('show');
}

// 关闭端点模态框
function closeEndpointModal() {
    elements.endpointModal.classList.remove('show');
}

// 保存端点
async function saveEndpoint() {
    const formData = {
        name: document.getElementById('endpoint-name').value.trim(),
        provider: document.getElementById('endpoint-provider').value,
        url: document.getElementById('endpoint-url').value.trim(),
        api_key: document.getElementById('endpoint-api-key').value.trim(),
        models: document.getElementById('endpoint-models').value.split(',').map(m => m.trim()).filter(m => m),
        enabled: document.getElementById('endpoint-enabled').checked
    };
    
    if (!formData.name || !formData.url || !formData.api_key || formData.models.length === 0) {
        showToast('请填写完整信息', 'error');
        return;
    }
    
    const originalName = elements.endpointOriginalName.value;
    const isEdit = !!originalName;
    
    try {
        const url = isEdit ? `/api/config/endpoints/${encodeURIComponent(originalName)}` : '/api/config/endpoints';
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '保存失败');
        }
        
        showToast(isEdit ? '端点更新成功' : '端点添加成功', 'success');
        closeEndpointModal();
        loadEndpoints();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 编辑端点
function editEndpoint(name) {
    const endpoint = state.endpoints.find(ep => ep.name === name);
    if (endpoint) {
        openEndpointModal(endpoint);
    }
}

// 删除端点
async function deleteEndpoint(name) {
    if (!confirm(`确定要删除端点 "${name}" 吗？`)) return;
    
    try {
        const response = await fetch(`/api/config/endpoints/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('删除失败');
        
        showToast('端点删除成功', 'success');
        loadEndpoints();
    } catch (error) {
        showToast('删除失败', 'error');
    }
}

// 加载记忆设置
async function loadMemorySettings() {
    try {
        const response = await fetch('/api/config/memory');
        if (!response.ok) throw new Error('加载失败');
        state.memorySettings = await response.json();
        
        // 更新UI
        const modeInput = document.querySelector(`input[name="memory-mode"][value="${state.memorySettings.memory_mode}"]`);
        if (modeInput) modeInput.checked = true;
        
        const injectionInput = document.querySelector(`input[name="injection-mode"][value="${state.memorySettings.injection_mode}"]`);
        if (injectionInput) injectionInput.checked = true;
        
        // 填充端点下拉框
        populateEndpointSelects();
        
        // 外接模型配置 - 恢复已保存的选择
        const extEndpoint = state.memorySettings.external_model_endpoint || '';
        const extModel = state.memorySettings.external_model_name || '';
        
        if (extEndpoint) {
            // 找到匹配的端点（通过URL匹配）
            const extEp = state.endpoints.find(ep => ep.url === extEndpoint && ep.enabled);
            if (extEp) {
                elements.externalEndpointSelect.value = extEp.name;
                updateModelSelect(elements.externalEndpointSelect, elements.externalModelSelect,
                                 elements.externalEndpoint, elements.externalApiKey);
                if (extModel) {
                    elements.externalModelSelect.value = extModel;
                }
            }
        }
        
        elements.summaryInterval.value = state.memorySettings.summary_interval || 5;
        
        // RAG配置 - 恢复已保存的选择
        const ragEndpoint = state.memorySettings.rag_model_endpoint || '';
        const ragModel = state.memorySettings.rag_model || '';
        
        if (ragEndpoint) {
            const ragEp = state.endpoints.find(ep => ep.url === ragEndpoint && ep.enabled);
            if (ragEp) {
                elements.ragEndpointSelect.value = ragEp.name;
                updateModelSelect(elements.ragEndpointSelect, elements.ragModelSelect);
                if (ragModel) {
                    elements.ragModelSelect.value = ragModel;
                }
            }
        }
        
        elements.ragMaxMemories.value = state.memorySettings.rag_max_memories || 10;
        
        updateSettingsVisibility();
    } catch (error) {
        showToast('加载记忆设置失败', 'error');
    }
}

// 更新设置面板可见性
function updateSettingsVisibility() {
    const memoryMode = document.querySelector('input[name="memory-mode"]:checked').value;
    const injectionMode = document.querySelector('input[name="injection-mode"]:checked').value;
    
    elements.externalModelConfig.style.display = memoryMode === 'external' ? 'block' : 'none';
    elements.ragConfig.style.display = injectionMode === 'rag' ? 'block' : 'none';
}

// 保存记忆设置
async function saveMemorySettings() {
    const settings = {
        memory_mode: document.querySelector('input[name="memory-mode"]:checked').value,
        injection_mode: document.querySelector('input[name="injection-mode"]:checked').value,
        external_model_endpoint: elements.externalEndpoint.value.trim() || null,
        external_model_api_key: elements.externalApiKey.value.trim() || null,
        external_model_name: elements.externalModelSelect.value.trim() || null,
        summary_interval: parseInt(elements.summaryInterval.value) || 5,
        rag_max_memories: parseInt(elements.ragMaxMemories.value) || 10,
        rag_model_endpoint: elements.ragEndpointSelect.value ? 
            state.endpoints.find(ep => ep.name === elements.ragEndpointSelect.value)?.url : null,
        rag_model: elements.ragModelSelect.value.trim() || null,
        memory_format: '<memory>\n{memories}\n</memory>'
    };
    
    try {
        const response = await fetch('/api/config/memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) throw new Error('保存失败');
        
        showToast('记忆设置保存成功', 'success');
        state.memorySettings = settings;
    } catch (error) {
        showToast('保存失败', 'error');
    }
}

// 加载记忆
async function loadMemories(keyword = '') {
    try {
        let url = '/api/memories';
        if (keyword) url += `?keyword=${encodeURIComponent(keyword)}`;
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('加载失败');
        state.memories = await response.json();
        renderMemories();
        updateMemoryCount();
    } catch (error) {
        showToast('加载记忆失败', 'error');
    }
}

// 渲染记忆列表
function renderMemories() {
    if (state.memories.length === 0) {
        elements.memoriesList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>暂无记忆</p>
            </div>
        `;
        return;
    }
    
    elements.memoriesList.innerHTML = state.memories.map(mem => `
        <div class="memory-item" data-id="${mem.id}">
            <div class="memory-content">${escapeHtml(mem.content)}</div>
            <div class="memory-meta">
                <span>${formatDate(mem.created_at)}</span>
                <div class="memory-actions">
                    <button class="btn btn-secondary" onclick="editMemory('${mem.id}')">
                        <i class="fas fa-edit"></i> 编辑
                    </button>
                    <button class="btn btn-danger" onclick="deleteMemory('${mem.id}')">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// 更新记忆计数
async function updateMemoryCount() {
    elements.memoryCount.textContent = state.memories.length;
}

// 搜索记忆
function searchMemories() {
    const keyword = elements.memorySearch.value.trim();
    loadMemories(keyword);
}

// 打开记忆模态框
function openMemoryModal(memory = null) {
    elements.memoryForm.reset();
    elements.memoryId.value = '';
    
    if (memory) {
        elements.memoryModalTitle.textContent = '编辑记忆';
        elements.memoryId.value = memory.id;
        elements.memoryContent.value = memory.content;
    } else {
        elements.memoryModalTitle.textContent = '添加记忆';
    }
    
    elements.memoryModal.classList.add('show');
}

// 关闭记忆模态框
function closeMemoryModal() {
    elements.memoryModal.classList.remove('show');
}

// 保存记忆
async function saveMemory() {
    const id = elements.memoryId.value;
    const content = elements.memoryContent.value.trim();
    
    if (!content) {
        showToast('请输入记忆内容', 'error');
        return;
    }
    
    try {
        let response;
        if (id) {
            // 更新
            response = await fetch(`/api/memories/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
        } else {
            // 添加
            response = await fetch('/api/memories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
        }
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '保存失败');
        }
        
        showToast(id ? '记忆更新成功' : '记忆添加成功', 'success');
        closeMemoryModal();
        loadMemories();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 编辑记忆
function editMemory(id) {
    const memory = state.memories.find(m => m.id === id);
    if (memory) {
        openMemoryModal(memory);
    }
}

// 删除记忆
async function deleteMemory(id) {
    if (!confirm('确定要删除这条记忆吗？')) return;
    
    try {
        const response = await fetch(`/api/memories/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('删除失败');
        
        showToast('记忆删除成功', 'success');
        loadMemories();
    } catch (error) {
        showToast('删除失败', 'error');
    }
}

// 显示Toast通知
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 辅助函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '未知时间';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN');
}