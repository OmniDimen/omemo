// Omni Memory - 前端应用

// 状态管理
const state = {
    endpoints: [],
    models: [],
    memories: [],
    memorySettings: {},
    currentSection: 'endpoints',
    isLoggedIn: false,
    loginEnabled: false
};

// DOM 元素
const elements = {};

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    // 首先检查登录状态
    const shouldContinue = await checkAuthStatus();
    if (!shouldContinue) return;
    
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
    elements.fetchModelsBtn = document.getElementById('fetch-models-btn');
    
    // 模型选择弹窗
    elements.modelPickerModal = document.getElementById('model-picker-modal');
    elements.modelPickerStatus = document.getElementById('model-picker-status');
    elements.modelPickerList = document.getElementById('model-picker-list');
    elements.closeModelPickerModal = document.getElementById('close-model-picker-modal');
    elements.cancelModelPickerBtn = document.getElementById('cancel-model-picker-btn');
    elements.confirmModelPickerBtn = document.getElementById('confirm-model-picker-btn');
    elements.pickerSelectAll = document.getElementById('picker-select-all');
    elements.pickerDeselectAll = document.getElementById('picker-deselect-all');
    
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
    
    // 通用设置
    elements.saveGeneralSettingsBtn = document.getElementById('save-general-settings-btn');
    elements.debugModeToggle = document.getElementById('debug-mode-toggle');
    elements.loginToggle = document.getElementById('login-toggle');
    elements.loginActions = document.getElementById('login-actions');
    elements.resetKeyBtn = document.getElementById('reset-key-btn');
    
    // Session Key 弹窗
    elements.sessionKeyModal = document.getElementById('session-key-modal');
    elements.sessionKeyDisplay = document.getElementById('session-key-display');
    elements.closeSessionKeyModal = document.getElementById('close-session-key-modal');
    elements.closeSessionKeyBtn = document.getElementById('close-session-key-btn');
    
    // 模型列表
    elements.modelsTable = document.getElementById('models-table')?.querySelector('tbody');
    elements.refreshModelsBtn = document.getElementById('refresh-models-btn');
    elements.conflictHint = document.getElementById('conflict-hint');
    
    // 模型别名弹窗
    elements.aliasModal = document.getElementById('alias-modal');
    elements.aliasOriginalModel = document.getElementById('alias-original-model');
    elements.aliasEndpoint = document.getElementById('alias-endpoint');
    elements.aliasInput = document.getElementById('alias-input');
    elements.closeAliasModal = document.getElementById('close-alias-modal');
    elements.cancelAliasBtn = document.getElementById('cancel-alias-btn');
    elements.saveAliasBtn = document.getElementById('save-alias-btn');
    
    // 移动端菜单
    elements.mobileMenuBtn = document.getElementById('mobile-menu-btn');
    elements.sidebar = document.getElementById('sidebar');
    elements.sidebarOverlay = document.getElementById('sidebar-overlay');
    
    // 其他
    elements.refreshBtn = document.getElementById('refresh-btn');
    elements.toastContainer = document.getElementById('toast-container');
}

function bindEvents() {
    // 移动端菜单
    if (elements.mobileMenuBtn) {
        elements.mobileMenuBtn.addEventListener('click', toggleMobileSidebar);
    }
    if (elements.sidebarOverlay) {
        elements.sidebarOverlay.addEventListener('click', closeMobileSidebar);
    }
    
    // 导航切换
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            switchSection(section);
            // 移动端点击导航后关闭侧边栏
            if (window.innerWidth <= 768) {
                closeMobileSidebar();
            }
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
    elements.fetchModelsBtn.addEventListener('click', fetchModelsFromEndpoint);
    
    // 模型选择弹窗
    elements.closeModelPickerModal.addEventListener('click', closeModelPickerModal);
    elements.cancelModelPickerBtn.addEventListener('click', closeModelPickerModal);
    elements.confirmModelPickerBtn.addEventListener('click', confirmModelSelection);
    elements.modelPickerModal.addEventListener('click', (e) => {
        if (e.target === elements.modelPickerModal) closeModelPickerModal();
    });
    elements.pickerSelectAll.addEventListener('click', () => toggleAllPickerModels(true));
    elements.pickerDeselectAll.addEventListener('click', () => toggleAllPickerModels(false));
    
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
    
    // 通用设置
    elements.saveGeneralSettingsBtn.addEventListener('click', saveGeneralSettings);
    
    // 登录认证
    if (elements.loginToggle) {
        elements.loginToggle.addEventListener('change', toggleLogin);
    }
    if (elements.resetKeyBtn) {
        elements.resetKeyBtn.addEventListener('click', resetSessionKey);
    }
    if (elements.closeSessionKeyModal) {
        elements.closeSessionKeyModal.addEventListener('click', closeSessionKeyModal);
    }
    if (elements.closeSessionKeyBtn) {
        elements.closeSessionKeyBtn.addEventListener('click', closeSessionKeyModal);
    }
    if (elements.sessionKeyModal) {
        elements.sessionKeyModal.addEventListener('click', (e) => {
            if (e.target === elements.sessionKeyModal) closeSessionKeyModal();
        });
    }
    
    // 模型列表
    if (elements.refreshModelsBtn) {
        elements.refreshModelsBtn.addEventListener('click', loadModels);
    }
    if (elements.closeAliasModal) {
        elements.closeAliasModal.addEventListener('click', closeAliasModal);
    }
    if (elements.cancelAliasBtn) {
        elements.cancelAliasBtn.addEventListener('click', closeAliasModal);
    }
    if (elements.saveAliasBtn) {
        elements.saveAliasBtn.addEventListener('click', saveAlias);
    }
    if (elements.aliasModal) {
        elements.aliasModal.addEventListener('click', (e) => {
            if (e.target === elements.aliasModal) closeAliasModal();
        });
    }
    
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
        'models': '模型列表',
        'memory-settings': '记忆功能配置',
        'memories': '记忆管理',
        'general-settings': '通用设置'
    };
    elements.pageTitle.textContent = titles[section];
    
    // 加载对应数据
    if (section === 'endpoints') {
        loadEndpoints();
    } else if (section === 'models') {
        loadModels();
    } else if (section === 'memory-settings') {
        loadMemorySettings();
    } else if (section === 'memories') {
        loadMemories();
    } else if (section === 'general-settings') {
        loadGeneralSettings();
    }
}

// 加载所有数据
async function loadAllData() {
    await Promise.all([
        loadEndpoints(),
        loadModels(),
        loadMemorySettings(),
        loadMemories()
    ]);
    // 通用设置使用同一接口，在memorySettings加载后更新
    updateGeneralSettingsUI();
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

// 加载模型列表
async function loadModels() {
    try {
        const response = await fetch('/api/models');
        if (!response.ok) throw new Error('加载失败');
        state.models = await response.json();
        renderModels();
    } catch (error) {
        showToast('加载模型列表失败', 'error');
    }
}

// 渲染模型列表
function renderModels() {
    if (!elements.modelsTable) return;
    
    // 检查是否有冲突
    const hasConflicts = state.models.some(m => m.has_conflict);
    if (elements.conflictHint) {
        elements.conflictHint.style.display = hasConflicts ? 'inline-flex' : 'none';
    }
    
    elements.modelsTable.innerHTML = state.models.map(m => `
        <tr>
            <td ${m.has_conflict && !m.alias ? 'style="color: var(--danger-color); font-weight: 600;"' : ''}>
                ${m.has_conflict && !m.alias ? '<i class="fas fa-exclamation-triangle" style="margin-right: 6px;"></i>' : ''}
                ${escapeHtml(m.available_name)}
            </td>
            <td style="color: var(--text-secondary); font-size: 13px;">
                ${m.alias ? `<span style="text-decoration: line-through;">${escapeHtml(m.model)}</span>` : '-'}
            </td>
            <td>${escapeHtml(m.endpoint)}</td>
            <td><span class="status-badge ${m.provider === 'openai' ? 'status-enabled' : 'status-disabled'}">${m.provider}</span></td>
            <td>${m.has_conflict && !m.alias ? `<span class="status-badge" style="background: rgba(239, 68, 68, 0.1); color: var(--danger-color);">冲突 (${m.conflict_endpoints.length}个端点)</span>` : '<span class="status-badge status-enabled">正常</span>'}</td>
            <td class="actions-cell">
                <button class="btn btn-secondary" onclick="openAliasModal('${escapeHtml(m.endpoint)}', '${escapeHtml(m.model)}', '${m.alias ? escapeHtml(m.alias) : ''}')" title="设置别名">
                    <i class="fas fa-tag"></i>
                </button>
            </td>
        </tr>
    `).join('');
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

// 存储获取到的模型列表（用于弹窗选择）
state.pickerModels = [];
state.pickerSelected = [];

// 从端点获取模型列表并打开选择弹窗
async function fetchModelsFromEndpoint() {
    const url = document.getElementById('endpoint-url').value.trim();
    const apiKey = document.getElementById('endpoint-api-key').value.trim();
    const provider = document.getElementById('endpoint-provider').value;
    
    if (!url || !apiKey) {
        showToast('请先填写API基础URL和API密钥', 'error');
        return;
    }
    
    // 打开弹窗并显示加载状态
    openModelPickerModal();
    elements.modelPickerStatus.textContent = '正在获取模型列表...';
    elements.modelPickerStatus.className = 'model-picker-status loading';
    elements.modelPickerList.innerHTML = '<div class="model-list-placeholder"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>';
    elements.confirmModelPickerBtn.disabled = true;
    
    try {
        const response = await fetch('/api/models/fetch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, api_key: apiKey, provider })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '获取失败');
        }
        
        const data = await response.json();
        state.pickerModels = data.models || [];
        
        // 预选当前已有的模型
        const currentModels = document.getElementById('endpoint-models').value
            .split(',')
            .map(m => m.trim())
            .filter(m => m);
        state.pickerSelected = currentModels.filter(m => state.pickerModels.includes(m));
        
        // 渲染模型列表
        renderModelPickerList();
        
        elements.modelPickerStatus.textContent = `已获取 ${state.pickerModels.length} 个模型`;
        elements.modelPickerStatus.className = 'model-picker-status success';
        elements.confirmModelPickerBtn.disabled = false;
    } catch (error) {
        elements.modelPickerStatus.textContent = error.message;
        elements.modelPickerStatus.className = 'model-picker-status error';
        elements.modelPickerList.innerHTML = '<div class="model-list-placeholder">获取失败</div>';
    }
}

// 打开模型选择弹窗
function openModelPickerModal() {
    state.pickerModels = [];
    state.pickerSelected = [];
    elements.modelPickerStatus.textContent = '';
    elements.modelPickerStatus.className = 'model-picker-status';
    elements.modelPickerList.innerHTML = '<div class="model-list-placeholder">点击"从端点获取"加载模型</div>';
    elements.modelPickerModal.classList.add('show');
}

// 关闭模型选择弹窗
function closeModelPickerModal() {
    elements.modelPickerModal.classList.remove('show');
}

// 渲染模型选择列表
function renderModelPickerList() {
    if (state.pickerModels.length === 0) {
        elements.modelPickerList.innerHTML = '<div class="model-list-placeholder">暂无可用模型</div>';
        return;
    }
    
    elements.modelPickerList.innerHTML = state.pickerModels.map(model => `
        <div class="model-item ${state.pickerSelected.includes(model) ? 'selected' : ''}" data-model="${escapeHtml(model)}">
            <input type="checkbox" ${state.pickerSelected.includes(model) ? 'checked' : ''}>
            <span class="model-item-name">${escapeHtml(model)}</span>
        </div>
    `).join('');
    
    // 绑定点击事件
    elements.modelPickerList.querySelectorAll('.model-item').forEach(item => {
        item.addEventListener('click', () => {
            const model = item.dataset.model;
            togglePickerModelSelection(model);
        });
    });
}

// 切换模型选择
function togglePickerModelSelection(model) {
    const index = state.pickerSelected.indexOf(model);
    if (index === -1) {
        state.pickerSelected.push(model);
    } else {
        state.pickerSelected.splice(index, 1);
    }
    renderModelPickerList();
}

// 全选/取消全选
function toggleAllPickerModels(selectAll) {
    if (selectAll) {
        state.pickerSelected = [...state.pickerModels];
    } else {
        state.pickerSelected = [];
    }
    renderModelPickerList();
}

// 确认模型选择，将结果dump到输入框
function confirmModelSelection() {
    if (state.pickerSelected.length === 0) {
        showToast('请至少选择一个模型', 'error');
        return;
    }
    
    // 将选中的模型写入输入框
    document.getElementById('endpoint-models').value = state.pickerSelected.join(',');
    showToast(`已添加 ${state.pickerSelected.length} 个模型`, 'success');
    closeModelPickerModal();
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

// 加载通用设置
function loadGeneralSettings() {
    updateGeneralSettingsUI();
}

// 更新通用设置UI
function updateGeneralSettingsUI() {
    if (elements.debugModeToggle) {
        elements.debugModeToggle.checked = state.memorySettings.debug_mode || false;
    }
    if (elements.loginToggle) {
        elements.loginToggle.checked = state.memorySettings.login_enabled || false;
        updateLoginActionsVisibility();
    }
}

// 更新登录操作按钮可见性
function updateLoginActionsVisibility() {
    if (elements.loginActions) {
        elements.loginActions.style.display = state.memorySettings.login_enabled ? 'block' : 'none';
    }
}

// 保存通用设置
async function saveGeneralSettings() {
    const settings = {
        ...state.memorySettings,
        debug_mode: elements.debugModeToggle.checked
    };
    
    try {
        const response = await fetch('/api/config/memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) throw new Error('保存失败');
        
        showToast('设置保存成功', 'success');
        state.memorySettings = settings;
    } catch (error) {
        showToast('保存失败', 'error');
    }
}

// 切换登录功能
async function toggleLogin() {
    const enabled = elements.loginToggle.checked;
    
    try {
        let response;
        if (enabled) {
            // 启用登录，生成新的 session key
            response = await fetch('/api/auth/enable', { method: 'POST' });
        } else {
            // 禁用登录
            response = await fetch('/api/auth/disable', { method: 'POST' });
        }
        
        const data = await response.json();
        
        if (response.ok) {
            state.memorySettings.login_enabled = enabled;
            updateLoginActionsVisibility();
            
            if (data.session_key) {
                // 显示 session key
                showSessionKey(data.session_key);
            }
            
            if (!enabled) {
                // 禁用登录时清除本地保存的session_key
                localStorage.removeItem('session_key');
                state.isLoggedIn = false;
            }
            
            showToast(enabled ? '登录功能已启用' : '登录功能已禁用', 'success');
        } else {
            // 恢复开关状态
            elements.loginToggle.checked = !enabled;
            showToast(data.detail || '操作失败', 'error');
        }
    } catch (error) {
        elements.loginToggle.checked = !enabled;
        showToast('操作失败', 'error');
    }
}

// 重置 Session Key
async function resetSessionKey() {
    if (!confirm('确定要重置 Session Key 吗？重置后旧的 Key 将失效。')) {
        return;
    }
    
    try {
        const response = await fetch('/api/auth/reset-key', { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showSessionKey(data.session_key);
            showToast('Session Key 已重置', 'success');
        } else {
            showToast(data.detail || '重置失败', 'error');
        }
    } catch (error) {
        showToast('重置失败', 'error');
    }
}

// 显示 Session Key
function showSessionKey(key) {
    if (elements.sessionKeyDisplay) {
        elements.sessionKeyDisplay.textContent = key;
    }
    if (elements.sessionKeyModal) {
        elements.sessionKeyModal.classList.add('show');
    }
}

// 关闭 Session Key 弹窗
function closeSessionKeyModal() {
    if (elements.sessionKeyModal) {
        elements.sessionKeyModal.classList.remove('show');
    }
}

// 复制 Session Key
function copySessionKey() {
    const key = elements.sessionKeyDisplay?.textContent;
    if (key) {
        navigator.clipboard.writeText(key).then(() => {
            showToast('已复制到剪贴板', 'success');
        }).catch(() => {
            showToast('复制失败', 'error');
        });
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

// ==================== 登录认证相关 ====================

// 检查登录状态
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();
        
        state.loginEnabled = data.login_enabled;
        
        // 如果未启用登录，直接继续
        if (!data.login_enabled) {
            state.isLoggedIn = true;
            return true;
        }
        
        // 检查本地存储的 session key
        const savedKey = localStorage.getItem('session_key');
        if (savedKey) {
            const verifyResponse = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_key: savedKey })
            });
            
            if (verifyResponse.ok) {
                state.isLoggedIn = true;
                return true;
            }
        }
        
        // 未登录，跳转到登录页面
        window.location.href = '/login';
        return false;
    } catch (error) {
        console.error('Auth check failed:', error);
        return true; // 出错时允许继续，避免死循环
    }
}

// 获取认证头
function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const sessionKey = localStorage.getItem('session_key');
    if (sessionKey && state.loginEnabled) {
        headers['Authorization'] = `Bearer ${sessionKey}`;
    }
    return headers;
}

// 带认证的fetch封装
async function authFetch(url, options = {}) {
    const headers = { ...getAuthHeaders(), ...options.headers };
    const response = await fetch(url, { ...options, headers });
    
    // 如果返回401，跳转到登录页面
    if (response.status === 401) {
        localStorage.removeItem('session_key');
        localStorage.removeItem('logged_in');
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }
    
    return response;
}

// 登出
function logout() {
    localStorage.removeItem('session_key');
    localStorage.removeItem('logged_in');
    window.location.href = '/login';
}

// ==================== 模型别名管理 ====================

// 当前编辑的模型信息
state.editingModel = { endpoint: '', model: '' };

// 打开别名编辑弹窗
function openAliasModal(endpoint, model, currentAlias) {
    state.editingModel = { endpoint, model };
    elements.aliasOriginalModel.value = model;
    elements.aliasEndpoint.value = endpoint;
    elements.aliasInput.value = currentAlias || '';
    elements.aliasModal.classList.add('show');
}

// 关闭别名编辑弹窗
function closeAliasModal() {
    elements.aliasModal.classList.remove('show');
    state.editingModel = { endpoint: '', model: '' };
}

// 保存别名
async function saveAlias() {
    const { endpoint, model } = state.editingModel;
    const alias = elements.aliasInput.value.trim();
    
    try {
        const response = await fetch('/api/models/alias', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                endpoint_name: endpoint,
                model: model,
                alias: alias
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || '保存失败');
        }
        
        closeAliasModal();
        await loadModels();
        showToast(alias ? '别名已设置' : '别名已清除', 'success');
    } catch (error) {
        showToast(error.message || '保存失败', 'error');
    }
}

// 暴露到全局作用域供内联事件使用
window.fetchModelsFromEndpoint = fetchModelsFromEndpoint;
window.toggleAllPickerModels = toggleAllPickerModels;
window.confirmModelSelection = confirmModelSelection;
window.closeModelPickerModal = closeModelPickerModal;
window.editEndpoint = editEndpoint;
window.deleteEndpoint = deleteEndpoint;
window.editMemory = editMemory;
window.deleteMemory = deleteMemory;
window.logout = logout;
window.copySessionKey = copySessionKey;
window.openAliasModal = openAliasModal;

// ==================== 移动端菜单 ====================

function toggleMobileSidebar() {
    elements.sidebar.classList.toggle('open');
    elements.sidebarOverlay.classList.toggle('show');
}

function closeMobileSidebar() {
    elements.sidebar.classList.remove('open');
    elements.sidebarOverlay.classList.remove('show');
}
