/* ============================================
   GALACTOS - Application Logic
   ============================================ */

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

let chatHistory = [];
let selectedAssistant = null;
let chatModel = 'qwen2.5:0.5b';
let uploadedFile = null;
let currentChatId = null;
let sessions = JSON.parse(localStorage.getItem('g_sessions') || '[]');
let allBots = [];
let ollamaModels = [];

// Markdown
marked.setOptions({
    highlight: (code, lang) => lang && hljs.getLanguage(lang) ? hljs.highlight(code, { language: lang }).value : hljs.highlightAuto(code).value,
    breaks: true,
    gfm: true
});

// ---- Utilities ----
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function toast(msg, type) {
    const el = document.createElement('div');
    el.className = 'toast-msg' + (type ? ' ' + type : '');
    el.textContent = msg;
    $('#toasts').appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

function grow(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 180) + 'px';
}

function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
}

// ---- Sessions ----
function saveSessions() { localStorage.setItem('g_sessions', JSON.stringify(sessions)); }

function renderHistory() {
    const el = $('#historyList');
    if (!sessions.length) { el.innerHTML = ''; return; }
    el.innerHTML = sessions.map(s => {
        const title = esc(s.title || 'New chat');
        const active = s.id === currentChatId ? ' active' : '';
        return '<div class="hist-item' + active + '" data-id="' + s.id + '">' + title + '<button class="del" data-del="' + s.id + '">&times;</button></div>';
    }).join('');
    // Bind click events directly instead of inline onclick
    el.querySelectorAll('.hist-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.classList.contains('del')) return;
            loadSession(item.dataset.id);
        });
    });
    el.querySelectorAll('.del').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            delSession(btn.dataset.del);
        });
    });
}

function newChat() {
    const id = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
    const session = { id, title: 'New chat', messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    sessions.unshift(session);
    currentChatId = id;
    chatHistory = [];
    saveSessions();
    renderHistory();
    $('#messages').innerHTML = '';
    $('#emptyState').classList.remove('hidden');
}

function loadSession(id) {
    const s = sessions.find(x => x.id === id);
    if (!s) { toast('Session not found', 'err'); return; }
    currentChatId = id;
    chatHistory = s.messages ? [...s.messages] : [];
    $('#messages').innerHTML = '';
    if (!chatHistory.length) {
        $('#emptyState').classList.remove('hidden');
    } else {
        $('#emptyState').classList.add('hidden');
        chatHistory.forEach(m => {
            if (m && m.role && m.content) appendMsg(m.role === 'user' ? 'user' : 'ai', m.content);
        });
    }
    renderHistory();
    // Switch to chat tab
    $$('.tab').forEach(t => t.classList.remove('active'));
    $('#tab-ai').classList.add('active');
    $$('.sidebar-btn').forEach(n => n.classList.remove('active'));
}

function delSession(id) {
    sessions = sessions.filter(x => x.id !== id);
    if (currentChatId === id) {
        currentChatId = null;
        chatHistory = [];
        if (sessions.length) loadSession(sessions[0].id);
        else newChat();
    }
    saveSessions();
    renderHistory();
    toast('Deleted');
}

function saveCurrent() {
    const s = sessions.find(x => x.id === currentChatId);
    if (!s) return;
    s.messages = [...chatHistory];
    s.updatedAt = Date.now();
    if (chatHistory.length) s.title = chatHistory[0].content.substring(0, 40);
    saveSessions();
    renderHistory();
}

// ---- Messages ----
function appendMsg(role, text) {
    $('#emptyState').classList.add('hidden');
    const div = document.createElement('div');
    div.className = 'msg msg-' + role;
    if (role === 'user') {
        div.innerHTML = '<div class="msg-content">' + esc(text).replace(/\n/g, '<br>') + '</div>';
    } else {
        div.innerHTML = '<div class="msg-avatar">G</div><div class="msg-body">' + marked.parse(text) + '</div>';
        div.querySelectorAll('pre').forEach(addCopy);
    }
    $('#messages').appendChild(div);
    scrollDown();
}

function addCopy(pre) {
    if (pre.querySelector('.btn-copy')) return;
    const b = document.createElement('button');
    b.className = 'btn-copy';
    b.textContent = 'Copy';
    b.onclick = () => {
        navigator.clipboard.writeText(pre.querySelector('code').textContent).then(() => {
            b.textContent = 'Copied';
            setTimeout(() => b.textContent = 'Copy', 1200);
        });
    };
    pre.style.position = 'relative';
    pre.appendChild(b);
}

function scrollDown() { const a = $('#chatArea'); a.scrollTop = a.scrollHeight; }

function prefill(text) { $('#chatInput').value = text; $('#chatInput').focus(); }

// ---- Send ----
async function send() {
    const input = $('#chatInput');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    input.style.height = 'auto';

    if (!currentChatId) newChat();
    appendMsg('user', text);
    chatHistory.push({ role: 'user', content: text });

    // Parse selected model value for assistant_id and model name
    const modelVal = $('#modelSelect').value;
    let assistantId = null;
    let modelName = modelVal;
    if (modelVal.includes(':')) {
        const parts = modelVal.split(':');
        assistantId = parts[0];
        modelName = parts.slice(1).join(':');
    }

    const loader = document.createElement('div');
    loader.className = 'msg msg-ai';
    loader.innerHTML = '<div class="msg-avatar">G</div><div class="msg-body"><div class="typing"><i></i><i></i><i></i></div></div>';
    $('#messages').appendChild(loader);
    scrollDown();
    const body = loader.querySelector('.msg-body');

    try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 120000);
        const resp = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: chatHistory, model: modelName, assistant_id: assistantId, filename: uploadedFile }),
            signal: ctrl.signal
        });
        clearTimeout(timer);

        if (!resp.ok) {
            const e = await resp.json().catch(() => ({}));
            body.innerHTML = '<p style="color:var(--danger)">Error: ' + esc(e.error || 'Request failed') + '</p>';
            return;
        }

        const reader = resp.body.getReader();
        const dec = new TextDecoder();
        let ai = '', buf = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buf += dec.decode(value, { stream: true });
            const lines = buf.split('\n');
            buf = lines.pop() || '';
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const d = line.slice(6).trim();
                if (d === '[DONE]') continue;
                try {
                    const p = JSON.parse(d);
                    if (p.token) {
                        ai += p.token;
                        body.innerHTML = marked.parse(ai);
                        body.querySelectorAll('pre').forEach(addCopy);
                    } else if (p.error) {
                        body.innerHTML = '<p style="color:var(--danger)">Error: ' + esc(p.error) + '</p>';
                        return;
                    }
                } catch {}
            }
            scrollDown();
        }

        if (!ai) {
            body.innerHTML = '<p style="color:var(--text-ter)">No response. Is Ollama running?</p>';
        } else {
            chatHistory.push({ role: 'assistant', content: ai });
            if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
            saveCurrent();
        }
    } catch (e) {
        body.innerHTML = '<p style="color:var(--danger)">' + (e.name === 'AbortError' ? 'Timeout' : esc(e.message)) + '</p>';
    }
}

// ---- Upload ----
async function uploadFile(input) {
    if (!input.files.length) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    try {
        const r = await fetch('/api/upload', { method: 'POST', body: fd });
        const d = await r.json();
        if (d.success) { uploadedFile = d.filename; toast('Uploaded: ' + d.original_name); }
        else toast(d.error || 'Failed', 'err');
    } catch { toast('Upload error', 'err'); }
    input.value = '';
}

// ---- Sidebar ----
function toggleSidebar() {
    $('#sidebar').classList.toggle('collapsed');
}

function closeModals() {
    $$('.modal').forEach(m => m.classList.add('hidden'));
    $('#modalBg').classList.add('hidden');
}

// ---- Tabs ----
function switchTab(name) {
    $$('.tab').forEach(t => t.classList.remove('active'));
    $$('.sidebar-btn').forEach(n => n.classList.remove('active'));
    const tab = $('#tab-' + name);
    if (tab) tab.classList.add('active');
    const btn = document.querySelector('[data-tab="' + name + '"]');
    if (btn) btn.classList.add('active');
    if (name === 'settings') { loadSettings(); loadBots(); }
    if (name === 'personalization') loadPersonalization();
    if (name === 'extensions') loadExtensions();
}

// ---- Ollama ----
async function checkStatus() {
    try {
        const r = await fetch('/api/ollama/status');
        const d = await r.json();
        const dot = $('#ollamaStatus .status-dot');
        const txt = $('#ollamaStatus .status-text');
        if (d.status === 'online' && d.models.length) { dot.className = 'status-dot on'; txt.textContent = 'Online'; }
        else if (d.status === 'online') { dot.className = 'status-dot off'; txt.textContent = 'No model'; }
        else { dot.className = 'status-dot off'; txt.textContent = 'Offline'; }
    } catch {
        $('#ollamaStatus .status-dot').className = 'status-dot off';
        $('#ollamaStatus .status-text').textContent = 'Error';
    }
}

async function loadModels() {
    try {
        const r = await fetch('/api/ollama/models');
        const d = await r.json();
        if (d.models && d.models.length) {
            ollamaModels = d.models;
            chatModel = d.models[0];
            $('#modelBadge').textContent = chatModel;
        }
    } catch {}
    updateModelSelect();
}

function updateModel() {
    const val = $('#modelSelect').value;
    if (val.includes(':')) {
        const parts = val.split(':');
        chatModel = parts.slice(1).join(':');
    } else {
        chatModel = val;
    }
    $('#modelBadge').textContent = chatModel;
}

// ---- Settings ----
async function loadSettings() {
    try {
        const r = await fetch('/api/settings');
        const s = await r.json();
        $('#settingTheme').value = s.theme || 'dark';
        $('#settingTemperature').value = s.temperature || 0.7;
        $('#tempVal').textContent = s.temperature || 0.7;
        $('#settingMaxTokens').value = s.max_tokens || 2048;
        applyTheme(s.theme || 'dark');
        loadAssistantsForSettings();
    } catch {}
}

function applyTheme(t) {
    document.body.classList.remove('dark');
    if (t === 'dark') document.body.classList.add('dark');
}

async function saveSettings() {
    const s = {
        theme: $('#settingTheme').value,
        active_assistant: $('#settingActiveAssistant').value,
        default_model: $('#settingDefaultModel').value,
        temperature: parseFloat($('#settingTemperature').value),
        max_tokens: parseInt($('#settingMaxTokens').value)
    };
    selectedAssistant = s.active_assistant === 'default' ? null : s.active_assistant;
    applyTheme(s.theme);
    try {
        await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(s) });
    } catch {}
}

async function loadAssistantsForSettings() {
    try {
        const r = await fetch('/api/assistants');
        const list = await r.json();
        const sel = $('#settingActiveAssistant');
        sel.innerHTML = '<option value="default">Default</option>';
        list.forEach(a => { sel.innerHTML += '<option value="' + a.id + '">' + a.name + ' (' + a.provider + ')</option>'; });
    } catch {}
}

// ---- Chatbot Providers ----
const providerMeta = {
    ollama:     { label: 'Ollama', color: '#525252', icon: 'O', models: 'qwen2.5:0.5b, phi3, tinyllama, llama3, mistral, codellama' },
    openai:     { label: 'OpenAI', color: '#10a37f', icon: 'G', models: 'gpt-4o, gpt-4o-mini, gpt-4-turbo, o1-mini, gpt-3.5-turbo' },
    anthropic:  { label: 'Claude', color: '#d97706', icon: 'C', models: 'claude-opus-4-20250514, claude-sonnet-4-20250514, claude-3-haiku-20240307' },
    google:     { label: 'Gemini', color: '#4285f4', icon: 'G', models: 'gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash' },
    groq:       { label: 'Groq', color: '#f55036', icon: 'Q', models: 'llama-3.3-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it' },
    openrouter: { label: 'OpenRouter', color: '#6366f1', icon: 'R', models: 'anthropic/claude-3.5-sonnet, openai/gpt-4o, meta-llama/llama-3.1-405b' },
    custom:     { label: 'Custom', color: '#737373', icon: 'A', models: '' }
};

async function loadBots() {
    try {
        const r = await fetch('/api/assistants');
        allBots = await r.json();
        renderBots(allBots);
        updateModelSelect();
    } catch {}
}

function updateModelSelect() {
    const sel = $('#modelSelect');
    const def = $('#settingDefaultModel');
    let opts = '';
    // Add Ollama models
    if (ollamaModels.length) {
        ollamaModels.forEach(m => { opts += '<option value="' + m + '">' + m + ' (Local)</option>'; });
    }
    // Add bot providers
    allBots.forEach(b => {
        const models = b.models && b.models.length ? b.models : [b.model || 'default'];
        models.forEach(m => {
            opts += '<option value="' + b.id + ':' + m + '">' + b.name + ' / ' + m + '</option>';
        });
    });
    if (opts) {
        sel.innerHTML = opts;
        if (def) def.innerHTML = opts;
    }
}

function renderBots(bots) {
    const el = $('#botsList');
    if (!bots.length) { el.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-ter);font-size:13px">No providers added. Click "+ Add provider" to get started.</div>'; return; }
    el.innerHTML = bots.map(b => {
        const meta = providerMeta[b.provider] || providerMeta.custom;
        const color = meta.color;
        const models = b.models ? b.models.join(', ') : (b.model || 'Not set');
        return '<div class="bot-card">' +
            '<div class="bot-icon" style="background:' + color + '">' + meta.icon + '</div>' +
            '<div class="bot-info"><h4>' + esc(b.name) + '</h4><p>' + meta.label + ' &middot; ' + esc(models) + '</p></div>' +
            '<div class="bot-actions">' +
            '<button class="btn-sm" onclick="testBot(\'' + b.id + '\')">Test</button>' +
            '<button class="btn-sm danger" onclick="deleteBot(\'' + b.id + '\')">Delete</button>' +
            '</div></div>';
    }).join('');
}

function showAddBotModal() {
    $('#addBotModal').classList.remove('hidden');
    $('#modalBg').classList.remove('hidden');
    $('#botProvider').value = 'openai';
    onBotProviderChange();
}

function onBotProviderChange() {
    const p = $('#botProvider').value;
    const meta = providerMeta[p] || {};
    const models = meta.models || '';
    $('#botModel').placeholder = models ? 'e.g. ' + models.split(', ').slice(0, 2).join(', ') : 'Model name';
    // Hide API key for Ollama
    $('#botKeyField').style.display = p === 'ollama' ? 'none' : 'block';
    // Show URL for custom
    $('#botUrlField').style.display = p === 'custom' ? 'block' : 'none';
}

async function saveBot() {
    const provider = $('#botProvider').value;
    const name = $('#botName').value.trim();
    const model = $('#botModel').value.trim();
    const apiKey = $('#botKey').value.trim();
    const apiUrl = $('#botUrl').value.trim();
    const prompt = $('#botPrompt').value.trim();

    if (!name) { toast('Enter a name', 'err'); return; }
    if (!model && provider !== 'ollama') { toast('Enter a model name', 'err'); return; }

    // For ollama, get models from the server
    let models = model ? model.split(',').map(m => m.trim()) : [];
    if (provider === 'ollama' && !models.length) {
        try {
            const r = await fetch('/api/ollama/models');
            const d = await r.json();
            models = d.models || [];
        } catch {}
    }

    const bot = {
        name: name,
        provider: provider,
        model: models[0] || model,
        models: models,
        api_key: apiKey,
        api_url: apiUrl,
        system_prompt: prompt
    };

    try {
        const r = await fetch('/api/assistants', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(bot) });
        const d = await r.json();
        if (d.id) {
            toast('Provider added');
            closeModals();
            loadBots();
            loadAssistantsForSettings();
        } else {
            toast(d.error || 'Failed', 'err');
        }
    } catch { toast('Failed to add provider', 'err'); }
}

async function deleteBot(id) {
    if (!confirm('Delete this provider?')) return;
    try {
        await fetch('/api/assistants/' + id, { method: 'DELETE' });
        toast('Deleted');
        loadBots();
        loadAssistantsForSettings();
    } catch { toast('Failed', 'err'); }
}

async function testBot(id) {
    toast('Testing connection...');
    // Quick test via chat
    try {
        const r = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: [{ role: 'user', content: 'Say hello in one word' }], assistant_id: id })
        });
        if (r.ok) toast('Connection OK');
        else toast('Connection failed', 'err');
    } catch { toast('Connection failed', 'err'); }
}

function exportData() {
    const data = { sessions, exportedAt: new Date().toISOString() };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'galactos_export.json'; a.click();
    URL.revokeObjectURL(url);
    toast('Exported');
}

function clearAllChats() {
    if (!confirm('Delete all conversations? This cannot be undone.')) return;
    sessions = [];
    currentChatId = null;
    chatHistory = [];
    saveSessions();
    renderHistory();
    newChat();
    toast('All conversations deleted');
}

// ---- Personalization ----
async function loadPersonalization() {
    try {
        const r = await fetch('/api/personalization');
        const d = await r.json();
        ['name', 'role', 'work_style', 'language', 'tone', 'response_length', 'domain', 'code_style', 'tags'].forEach(k => {
            const el = $('#p' + k.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(''));
            if (el && d[k]) el.value = d[k];
        });
        ['auto_correct', 'explain_code', 'show_examples', 'ask_clarify'].forEach(k => {
            const el = $('#p' + k.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(''));
            if (el && d[k] !== undefined) el.checked = d[k];
        });
    } catch {}
}

function savePersonalization() {
    const d = {
        name: $('#pName').value,
        role: $('#pRole').value,
        work_style: $('#pWorkStyle').value,
        language: $('#pLanguage').value,
        tone: $('#pTone').value,
        response_length: $('#pLength').value,
        domain: $('#pDomain').value,
        code_style: $('#pCodeStyle').value,
        tags: $('#pTags').value,
        auto_correct: $('#pAutoCorrect').checked,
        explain_code: $('#pExplainCode').checked,
        show_examples: $('#pShowExamples').checked,
        ask_clarify: $('#pAskClarify').checked
    };
    fetch('/api/personalization', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) });
}

// ---- Extensions ----
let extData = [];

async function loadExtensions() {
    try {
        const r = await fetch('/api/extensions');
        extData = await r.json();
        renderExts();
    } catch {}
}

function renderExts() {
    const el = $('#extList');
    if (!extData.length) { el.innerHTML = '<p style="color:var(--text-ter);text-align:center;padding:2rem">No extensions loaded</p>'; return; }
    el.innerHTML = extData.map(e =>
        '<div class="ext-card"><div><h4>' + esc(e.display_name) + '</h4><p>' + esc(e.description) + ' v' + e.version + '</p></div>' +
        '<label class="toggle"><input type="checkbox"' + (e.enabled ? ' checked' : '') + ' onchange="toggleExt(\'' + e.name + '\',this.checked)"><span class="toggle-track"></span></label></div>'
    ).join('');
}

async function toggleExt(name, on) {
    const endpoint = on ? '/enable' : '/disable';
    await fetch('/api/extensions/' + name + endpoint, { method: 'POST' });
    loadExtensions();
}

async function reloadExts() {
    await fetch('/api/extensions/reload', { method: 'POST' });
    loadExtensions();
    toast('Extensions reloaded');
}

// ---- Keyboard ----
document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key === 'n') { e.preventDefault(); newChat(); }
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); send(); }
    if (e.ctrlKey && e.key === '/') { e.preventDefault(); $('#shortcutsModal').classList.remove('hidden'); $('#modalBg').classList.remove('hidden'); }
    if (e.key === 'Escape') closeModals();
});

// ---- Init ----
checkStatus();
setInterval(checkStatus, 30000);
loadModels();
loadBots();
// Restore last session or create new
if (sessions.length > 0) {
    renderHistory();
    loadSession(sessions[0].id);
} else {
    newChat();
}
