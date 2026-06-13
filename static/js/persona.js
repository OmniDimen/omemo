document.addEventListener('DOMContentLoaded',function(){
    var grid=document.getElementById('personas-grid');
    var modal=document.getElementById('persona-modal');
    if(!grid){console.error('personas-grid not found');return}
    if(!modal){console.error('persona-modal not found');return}
    console.log('persona.js loaded ok');

    function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}

    // authFetch 辅助函数（与 app.js 保持一致，使用 admin_token）
    function personaAuthFetch(url, options) {
        options = options || {};
        var headers = Object.assign({'Content-Type': 'application/json'}, options.headers || {});
        var adminToken = localStorage.getItem('admin_token');
        if (adminToken) {
            headers['Authorization'] = 'Bearer ' + adminToken;
        }
        options.headers = headers;
        return fetch(url, options).then(function(response) {
            if (response.status === 401) {
                localStorage.removeItem('admin_token');
                window.location.href = '/login';
                throw new Error('Unauthorized');
            }
            return response;
        });
    }

    // 加载可用模型列表并填充下拉框（显示供应商前缀）
    function loadPersonaModelSelect(selectedModel){
        var sel=document.getElementById('persona-model');
        sel.innerHTML='<option value="">-- 请选择模型 --</option>';
        personaAuthFetch('/api/models').then(function(r){return r.json()}).then(function(models){
            models.forEach(function(m){
                var opt=document.createElement('option');
                opt.value=m.display_name;
                opt.textContent=m.display_name+(m.has_conflict?' (冲突)':'');
                if(m.display_name===selectedModel)opt.selected=true;
                sel.appendChild(opt);
            });
        }).catch(function(){});
    }

    var addBtn=document.getElementById('add-persona-btn');
    if(addBtn)addBtn.onclick=function(){
        document.getElementById('persona-modal-title').textContent='添加人格';
        document.getElementById('persona-id').value='';
        document.getElementById('persona-name').value='';
        document.getElementById('persona-description').value='';
        document.getElementById('persona-system-prompt').value='';
        loadPersonaModelSelect('');
        modal.classList.add('show');
    };

    var closeBtn=document.getElementById('close-persona-modal');
    if(closeBtn)closeBtn.onclick=function(){modal.classList.remove('show')};
    var cancelBtn=document.getElementById('cancel-persona-btn');
    if(cancelBtn)cancelBtn.onclick=function(){modal.classList.remove('show')};

    var saveBtn=document.getElementById('save-persona-btn');
    if(saveBtn)saveBtn.onclick=function(){
        var id=document.getElementById('persona-id').value;
        var d={name:document.getElementById('persona-name').value.trim(),description:document.getElementById('persona-description').value.trim(),system_prompt:document.getElementById('persona-system-prompt').value,model:document.getElementById('persona-model').value};
        if(!d.name){if(typeof showToast==='function')showToast('名称不能为空','error');return}
        if(!d.model){if(typeof showToast==='function')showToast('请选择绑定模型','error');return}
        var url=id?'/api/personas/'+id:'/api/personas';
        var method=id?'PUT':'POST';
        personaAuthFetch(url,{method:method,body:JSON.stringify(d)}).then(function(r){
            if(!r.ok)throw new Error('fail');
            modal.classList.remove('show');
            loadPersonas();
            if(typeof showToast==='function')showToast(id?'人格已更新':'人格已添加','success');
        }).catch(function(e){if(e.message!=='Unauthorized'&&typeof showToast==='function')showToast('操作失败','error')});
    };

    function loadPersonas(){
        personaAuthFetch('/api/personas').then(function(r){return r.json()}).then(function(ps){
            if(!ps.length){grid.innerHTML='<div class="persona-empty"><i class="fas fa-masks-theater"></i><p>暂无人格，点击上方按钮添加</p></div>';return}
            grid.innerHTML=ps.map(function(p){
                var pv=p.system_prompt?p.system_prompt.substring(0,120)+(p.system_prompt.length>120?'...':''):'未设置 System Prompt';
                return '<div class="persona-card'+(p.active?' active':'')+'">'
                    +'<div class="p-top">'
                    +'<div class="p-name">'+esc(p.name)+(p.active?' <span class="p-badge">已激活</span>':'')+'</div>'
                    +'<label class="toggle-switch" title="'+(p.active?'点击停用':'点击激活')+'">'
                    +'<input type="checkbox" '+(p.active?'checked':'')+' onchange="togglePersonaActive(\''+p.id+'\')">'
                    +'<span class="toggle-slider"></span>'
                    +'</label>'
                    +'</div>'
                    +(p.description?'<div class="p-desc">'+esc(p.description)+'</div>':'')
                    +(p.model?'<span class="p-model">'+esc(p.model)+'</span>':'')
                    +'<div class="p-preview">'+esc(pv)+'</div>'
                    +'<div class="p-actions">'
                    +'<div class="btn-group">'
                    +'<button class="btn btn-secondary btn-sm" onclick="editPersona(\''+p.id+'\')"><i class="fas fa-edit"></i> 编辑</button>'
                    +'<button class="btn btn-danger btn-sm" onclick="deletePersona(\''+p.id+'\')"><i class="fas fa-trash"></i></button>'
                    +'</div>'
                    +'</div></div>'
            }).join('');
        }).catch(function(e){if(e.message!=='Unauthorized')grid.innerHTML='<div class="persona-empty">加载失败</div>'});
    }
    window.loadPersonas=loadPersonas;

    window.togglePersonaActive=function(id){
        personaAuthFetch('/api/personas/'+id+'/activate',{method:'POST'}).then(function(r){return r.json()}).then(function(data){
            loadPersonas();
            if(typeof showToast==='function')showToast(data.active?'人格已激活':'人格已停用','success');
        });
    };
    window.editPersona=function(id){personaAuthFetch('/api/personas').then(function(r){return r.json()}).then(function(all){var p=all.find(function(x){return x.id===id});if(!p)return;document.getElementById('persona-modal-title').textContent='编辑人格';document.getElementById('persona-id').value=p.id;document.getElementById('persona-name').value=p.name;document.getElementById('persona-description').value=p.description||'';document.getElementById('persona-system-prompt').value=p.system_prompt||'';loadPersonaModelSelect(p.model||'');modal.classList.add('show')})};
    window.deletePersona=function(id){if(!confirm('确定删除此人格？'))return;personaAuthFetch('/api/personas/'+id,{method:'DELETE'}).then(function(){loadPersonas();if(typeof showToast==='function')showToast('人格已删除','success')})};

    // 监听tab切换
    var nav=document.querySelector('[data-section="personas"]');
    if(nav)nav.addEventListener('click',function(){setTimeout(loadPersonas,150)});
    // 监听section class变化
    var sec=document.getElementById('personas-section');
    if(sec)new MutationObserver(function(){if(sec.classList.contains('active'))loadPersonas()}).observe(sec,{attributes:true,attributeFilter:['class']});
});
