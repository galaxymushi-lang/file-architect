let chatHistory = [];
let selectedAssistant = null;
let assistants = [];
let chatModel = 'qwen2.5:0.5b';
let uploadedFile = null;
let currentChatId = null;
let chatSessions = JSON.parse(localStorage.getItem('chatSessions') || '[]');
let isRecording = false;
let recognition = null;

// ========== MARKDOWN SETUP ==========
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
});

function renderMarkdown(text) {
    const html = marked.parse(text);
    return html.replace(/<pre><code class="language-(\w+)">/g, '<pre><code class="language-$1 hljs">')
               .replace(/<pre><code>/g, '<pre><code class="hljs">');
}

function addCodeCopyButtons() {
    document.querySelectorAll('.msg-bubble pre').forEach(pre => {
        if (pre.querySelector('.code-copy-btn')) return;
        const btn = document.createElement('button');
        btn.className = 'code-copy-btn';
        btn.textContent = 'COPY';
        btn.onclick = () => {
            const code = pre.querySelector('code');
            navigator.clipboard.writeText(code.textContent).then(() => {
                btn.textContent = 'COPIED!';
                showToast('Code copied');
                setTimeout(() => btn.textContent = 'COPY', 1500);
            });
        };
        pre.appendChild(btn);
    });
}

// ========== TOKEN COUNTER ==========
function estimateTokens(text) {
    return Math.ceil(text.length / 4);
}

function updateTokenCount() {
    let total = 0;
    chatHistory.forEach(msg => {
        total += estimateTokens(msg.content);
    });
    document.getElementById('tokenCount').textContent = total;
}

// ========== NOTIFICATIONS ==========
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = `> ${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ========== CHAT HISTORY ==========
function saveChatSessions() {
    localStorage.setItem('chatSessions', JSON.stringify(chatSessions));
}

function renderChatHistory() {
    const list = document.getElementById('chatHistoryList');
    if (!chatSessions.length) {
        list.innerHTML = '<p style="color:var(--text-dim);font-size:0.65rem;text-align:center;padding:1rem">> NO SESSIONS YET</p>';
        return;
    }
    list.innerHTML = chatSessions.map(s => {
        const active = s.id === currentChatId ? 'active' : '';
        const preview = s.messages.length > 0 ? s.messages[s.messages.length - 1].content.substring(0, 40) : 'Empty';
        const date = new Date(s.updatedAt).toLocaleDateString();
        return `
            <div class="chat-history-item ${active}" onclick="loadChatSession('${s.id}')">
                <div class="chat-history-item-title">${escapeHtml(s.title)}</div>
                <div class="chat-history-item-meta">
                    <span>${date} • ${s.messages.length} msgs</span>
                    <button class="chat-history-item-delete" onclick="event.stopPropagation(); deleteChatSession('${s.id}')">DEL</button>
                </div>
            </div>
        `;
    }).join('');
}

function newChat() {
    const id = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
    const session = {
        id,
        title: 'New Session',
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now()
    };
    chatSessions.unshift(session);
    currentChatId = id;
    chatHistory = [];
    saveChatSessions();
    renderChatHistory();
    
    const container = document.getElementById('chatMessages');
    container.innerHTML = `
        <div class="msg ai">
            <div class="msg-avatar">AI</div>
            <div class="msg-bubble">> NEW SESSION INITIALIZED<br>> Neural interface ready.<br>> Awaiting input, operator.</div>
        </div>
    `;
    updateTokenCount();
    showToast('New chat started');
}

function saveCurrentChat() {
    if (!currentChatId) return;
    const session = chatSessions.find(s => s.id === currentChatId);
    if (!session) return;
    session.messages = [...chatHistory];
    session.updatedAt = Date.now();
    if (chatHistory.length > 0) {
        const firstMsg = chatHistory[0].content;
        session.title = firstMsg.substring(0, 40) + (firstMsg.length > 40 ? '...' : '');
    }
    saveChatSessions();
    renderChatHistory();
}

function loadChatSession(id) {
    const session = chatSessions.find(s => s.id === id);
    if (!session) return;
    currentChatId = id;
    chatHistory = [...session.messages];
    
    const container = document.getElementById('chatMessages');
    container.innerHTML = '';
    
    if (chatHistory.length === 0) {
        container.innerHTML = `
            <div class="msg ai">
                <div class="msg-avatar">AI</div>
                <div class="msg-bubble">> SESSION LOADED<br>> Ready for input.</div>
            </div>
        `;
    } else {
        chatHistory.forEach(msg => {
            const isUser = msg.role === 'user';
            const div = document.createElement('div');
            div.className = `msg ${isUser ? 'user' : 'ai'}`;
            const avatar = isUser ? 'YOU' : 'AI';
            const content = isUser ? escapeHtml(msg.content).replace(/\n/g, '<br>') : renderMarkdown(msg.content);
            div.innerHTML = `<div class="msg-avatar">${avatar}</div><div class="msg-bubble">${content}</div>`;
            container.appendChild(div);
        });
        addCodeCopyButtons();
    }
    
    container.scrollTop = container.scrollHeight;
    renderChatHistory();
    updateTokenCount();
}

function deleteChatSession(id) {
    chatSessions = chatSessions.filter(s => s.id !== id);
    if (currentChatId === id) {
        currentChatId = null;
        chatHistory = [];
        newChat();
    }
    saveChatSessions();
    renderChatHistory();
    showToast('Session deleted');
}

// ========== EXPORT CHAT ==========
function exportChat(format = 'md') {
    if (!chatHistory.length) {
        showToast('No messages to export', 'warning');
        return;
    }
    
    let content = '';
    if (format === 'md') {
        content = chatHistory.map(msg => {
            const role = msg.role === 'user' ? '**You**' : '**AI**';
            return `### ${role}\n\n${msg.content}\n\n---\n`;
        }).join('\n');
    } else {
        content = chatHistory.map(msg => {
            const role = msg.role === 'user' ? 'YOU' : 'AI';
            return `[${role}]\n${msg.content}\n`;
        }).join('\n---\n\n');
    }
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().split('T')[0]}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Exported as .${format}`);
}

// ========== SEARCH IN CHAT ==========
function toggleSearch() {
    const bar = document.getElementById('chatSearchBar');
    bar.classList.toggle('hidden');
    if (!bar.classList.contains('hidden')) {
        document.getElementById('chatSearchInput').focus();
    } else {
        clearSearch();
    }
}

function searchInChat() {
    const query = document.getElementById('chatSearchInput').value.toLowerCase();
    const msgs = document.querySelectorAll('.msg-bubble');
    
    msgs.forEach(bubble => {
        bubble.querySelectorAll('.search-highlight').forEach(el => {
            el.replaceWith(document.createTextNode(el.textContent));
        });
    });
    
    if (!query) return;
    
    msgs.forEach(bubble => {
        const text = bubble.textContent;
        if (text.toLowerCase().includes(query)) {
            const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            bubble.innerHTML = bubble.innerHTML.replace(regex, '<span class="search-highlight">$1</span>');
        }
    });
}

function clearSearch() {
    document.querySelectorAll('.search-highlight').forEach(el => {
        el.replaceWith(document.createTextNode(el.textContent));
    });
}

// ========== PROMPT TEMPLATES ==========
const templates = {
    explain: 'Explain this in simple terms: ',
    write: 'Write a detailed ',
    summarize: 'Summarize the following: ',
    code: 'Write code for: ',
    fix: 'Fix the following code/error: ',
    translate: 'Translate this to English: ',
    email: 'Write a professional email about: ',
    brainstorm: 'Brainstorm ideas for: '
};

function useTemplate(key) {
    const input = document.getElementById('chatInput');
    input.value = templates[key];
    input.focus();
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
}

// ========== VOICE INPUT ==========
function toggleVoice() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        showToast('Voice input not supported', 'error');
        return;
    }
    
    if (isRecording) {
        if (recognition) recognition.stop();
        isRecording = false;
        document.getElementById('voiceBtn').classList.remove('recording');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    
    recognition.onstart = () => {
        isRecording = true;
        document.getElementById('voiceBtn').classList.add('recording');
        showToast('Listening...');
    };
    
    recognition.onresult = (event) => {
        const transcript = Array.from(event.results).map(r => r[0].transcript).join('');
        document.getElementById('chatInput').value = transcript;
    };
    
    recognition.onend = () => {
        isRecording = false;
        document.getElementById('voiceBtn').classList.remove('recording');
    };
    
    recognition.onerror = (event) => {
        isRecording = false;
        document.getElementById('voiceBtn').classList.remove('recording');
        showToast('Voice error: ' + event.error, 'error');
    };
    
    recognition.start();
}

// ========== SYSTEM DASHBOARD ==========
async function loadSystemDashboard() {
    try {
        const resp = await fetch('/api/system');
        const data = await resp.json();
        
        document.getElementById('cpuFill').style.height = data.cpu_percent + '%';
        document.getElementById('cpuText').textContent = data.cpu_percent.toFixed(0) + '%';
        
        document.getElementById('memFill').style.height = data.memory_percent + '%';
        document.getElementById('memText').textContent = data.memory_percent.toFixed(0) + '%';
        const memUsedGB = (data.memory_used / 1073741824).toFixed(1);
        const memTotalGB = (data.memory_total / 1073741824).toFixed(1);
        document.getElementById('memLabel').textContent = `${memUsedGB} / ${memTotalGB} GB`;
        
        document.getElementById('diskFill').style.height = data.disk_percent + '%';
        document.getElementById('diskText').textContent = data.disk_percent.toFixed(0) + '%';
        const diskUsedGB = (data.disk_used / 1073741824).toFixed(1);
        const diskTotalGB = (data.disk_total / 1073741824).toFixed(1);
        document.getElementById('diskLabel').textContent = `${diskUsedGB} / ${diskTotalGB} GB`;
        
        const modelsList = document.getElementById('systemModels');
        if (data.models && data.models.length) {
            modelsList.innerHTML = data.models.map(m => {
                const sizeGB = (m.size / 1073741824).toFixed(2);
                return `<div class="system-model-item"><span class="name">${m.name}</span><span class="size">${sizeGB} GB</span></div>`;
            }).join('');
        } else {
            modelsList.innerHTML = '<p style="color:var(--text-dim)">No models found</p>';
        }
    } catch (err) {
        console.error('Failed to load system info:', err);
    }
}

// ========== TAB NAVIGATION ==========
const pageTitles = {
    ai: '// TERMINAL',
    dashboard: '// SYSTEM',
    assistants: '// AGENTS',
    personalization: '// PERSONALIZE',
    extensions: '// EXTENSIONS',
    settings: '// CONFIG'
};

function switchTab(name) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    const navBtn = document.querySelector(`[data-tab="${name}"]`);
    if (navBtn) navBtn.classList.add('active');
    const tab = document.getElementById(`tab-${name}`);
    if (tab) tab.classList.add('active');
    document.getElementById('pageTitle').textContent = pageTitles[name] || '// ' + name.toUpperCase();
    if (name === 'assistants') loadAssistants();
    if (name === 'settings') loadSettings();
    if (name === 'personalization') loadPersonalization();
    if (name === 'dashboard') loadSystemDashboard();
    if (name === 'extensions') loadExtensions();
}

// ========== OLLAMA STATUS ==========
async function checkOllamaStatus() {
    try {
        const resp = await fetch('/api/ollama/status');
        const data = await resp.json();
        const el = document.getElementById('ollamaStatus');
        if (data.status === 'online' && data.models.length > 0) {
            el.className = 'status-badge online';
            el.innerHTML = `<span class="status-dot"></span> ONLINE`;
        } else if (data.status === 'online') {
            el.className = 'status-badge offline';
            el.innerHTML = `<span class="status-dot"></span> NO MODEL`;
        } else {
            el.className = 'status-badge offline';
            el.innerHTML = `<span class="status-dot"></span> OFFLINE`;
        }
    } catch {
        document.getElementById('ollamaStatus').className = 'status-badge offline';
        document.getElementById('ollamaStatus').innerHTML = '<span class="status-dot"></span> ERROR';
    }
}
checkOllamaStatus();

// ========== CHAT MODEL SELECTOR ==========
async function loadChatModels() {
    try {
        const resp = await fetch('/api/ollama/models');
        const data = await resp.json();
        const select = document.getElementById('chatModelSelect');
        if (data.models && data.models.length) {
            select.innerHTML = data.models.map(m => `<option value="${m}" ${m === chatModel ? 'selected' : ''}>${m}</option>`).join('');
            chatModel = data.models[0];
        } else {
            select.innerHTML = '<option value="qwen2.5:0.5b">qwen2.5:0.5b</option>';
        }
        document.getElementById('chatModelInfo').textContent = chatModel;
    } catch {
        document.getElementById('chatModelSelect').innerHTML = '<option value="qwen2.5:0.5b">qwen2.5:0.5b</option>';
    }
}

function switchChatModel() {
    const select = document.getElementById('chatModelSelect');
    chatModel = select.value;
    document.getElementById('chatModelInfo').textContent = chatModel;
    showToast(`Switched to ${chatModel}`);
}
loadChatModels();

// ========== AI CHAT ==========
function addAIMessage(text, isUser = false) {
    const container = document.getElementById('chatMessages');
    const msg = document.createElement('div');
    msg.className = `msg ${isUser ? 'user' : 'ai'}`;
    const avatar = isUser ? 'YOU' : 'AI';
    const content = isUser ? escapeHtml(text).replace(/\n/g, '<br>') : renderMarkdown(text);
    msg.innerHTML = `<div class="msg-avatar">${avatar}</div><div class="msg-bubble">${content}</div>`;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    addCodeCopyButtons();
}

async function sendChat() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    input.style.height = 'auto';
    
    if (!currentChatId) newChat();
    
    addAIMessage(text, true);
    chatHistory.push({ role: 'user', content: text });
    updateTokenCount();

    const container = document.getElementById('chatMessages');
    const msgEl = document.createElement('div');
    msgEl.className = 'msg ai';
    msgEl.innerHTML = '<div class="msg-avatar">AI</div><div class="msg-bubble" style="color:var(--text-muted)">> PROCESSING...</div>';
    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;
    const bubble = msgEl.querySelector('.msg-bubble');

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);

        const body = { messages: chatHistory, model: chatModel };
        if (uploadedFile) body.filename = uploadedFile;
        if (selectedAssistant) body.assistant_id = selectedAssistant;

        const resp = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            bubble.textContent = '> ERROR: ' + (errData.error || 'Request failed');
            bubble.style.color = 'var(--danger)';
            return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let aiResponse = '';
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const d = line.slice(6).trim();
                if (d === '[DONE]') continue;
                try {
                    const parsed = JSON.parse(d);
                    if (parsed.token) {
                        aiResponse += parsed.token;
                        bubble.innerHTML = renderMarkdown(aiResponse);
                        addCodeCopyButtons();
                    } else if (parsed.error) {
                        bubble.textContent = '> ERROR: ' + parsed.error;
                        bubble.style.color = 'var(--danger)';
                        return;
                    }
                } catch {}
            }
            container.scrollTop = container.scrollHeight;
        }

        if (!aiResponse) {
            bubble.textContent = '> NO RESPONSE. Check if Ollama is running.';
            bubble.style.color = 'var(--warning)';
        } else {
            chatHistory.push({ role: 'assistant', content: aiResponse });
            if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
            updateTokenCount();
            saveCurrentChat();
        }

    } catch (err) {
        if (err.name === 'AbortError') {
            bubble.textContent = '> TIMEOUT: Model too slow.';
        } else {
            bubble.textContent = '> ERROR: ' + err.message;
        }
        bubble.style.color = 'var(--danger)';
    }
}

// ========== KEYBOARD SHORTCUTS ==========
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        newChat();
    } else if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        sendChat();
    } else if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        toggleSearch();
    } else if (e.ctrlKey && e.key === 'e') {
        e.preventDefault();
        exportChat('md');
    } else if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        document.getElementById('shortcutsModal').classList.remove('hidden');
    } else if (e.key === 'Escape') {
        document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
        document.getElementById('chatSearchBar').classList.add('hidden');
        clearSearch();
    }
});

document.getElementById('chatInput').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

document.getElementById('chatInput').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// ========== FILE UPLOAD IN CHAT ==========
document.getElementById('chatFileInput').addEventListener('change', async function(e) {
    if (!e.target.files.length) return;
    const file = e.target.files[0];
    showLoading();
    const fd = new FormData();
    fd.append('file', file);
    try {
        const resp = await fetch('/api/upload', { method: 'POST', body: fd });
        const data = await resp.json();
        if (data.success) {
            uploadedFile = data.filename;
            addAIMessage(`> DATA LOADED: ${data.original_name}\n> Ready for analysis.`);
            showToast('File uploaded: ' + data.original_name);
        } else {
            addAIMessage(`> UPLOAD FAILED: ${data.error || 'Unknown error'}`);
        }
    } catch (err) {
        addAIMessage(`> UPLOAD ERROR: ${err.message}`);
    }
    hideLoading();
    this.value = '';
});

// ========== ASSISTANTS ==========
async function loadAssistants() {
    try {
        const resp = await fetch('/api/assistants');
        assistants = await resp.json();
        renderAssistants();
    } catch (err) { console.error('Failed:', err); }
}

function renderAssistants() {
    const container = document.getElementById('assistantList');
    if (!assistants.length) {
        container.innerHTML = '<p style="color:var(--text-dim);text-align:center;padding:2rem;letter-spacing:2px">> NO AGENTS DEPLOYED<br>> CLICK "+ DEPLOY" TO INITIALIZE</p>';
        return;
    }
    container.innerHTML = assistants.map(a => `
        <div class="assistant-card ${selectedAssistant === a.id ? 'selected' : ''}" onclick="selectAssistant('${a.id}')">
            <div class="assistant-card-header">
                <div class="assistant-icon" style="background:${a.provider === 'openai' ? '#22c55e' : a.provider === 'groq' ? '#f59e0b' : a.provider === 'gemini' ? '#4285f4' : '#00ff41'};box-shadow:0 0 10px ${a.provider === 'openai' ? '#22c55e40' : a.provider === 'groq' ? '#f59e0b40' : a.provider === 'gemini' ? '#4285f440' : '#00ff4140'}">${a.provider[0].toUpperCase()}</div>
                <div>
                    <h4>${a.name}</h4>
                    <span class="assistant-provider">${a.provider}</span>
                </div>
                <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); deleteAssistant('${a.id}')" title="Terminate">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <div class="assistant-card-body">
                <div class="assistant-detail"><span>MODEL:</span> ${a.model}</div>
                ${a.api_key ? '<div class="assistant-detail"><span>KEY:</span> ***' + a.api_key.slice(-4) + '</div>' : ''}
            </div>
        </div>
    `).join('');
}

function selectAssistant(id) {
    selectedAssistant = selectedAssistant === id ? null : id;
    renderAssistants();
    const name = selectedAssistant ? assistants.find(a => a.id === id)?.name : 'DEFAULT';
    addAIMessage(`> AGENT ACTIVE: ${name}`);
    showToast(`Agent: ${name}`);
}

async function deleteAssistant(id) {
    if (!confirm('Terminate this agent?')) return;
    try {
        await fetch(`/api/assistants/${id}`, { method: 'DELETE' });
        if (selectedAssistant === id) selectedAssistant = null;
        loadAssistants();
        showToast('Agent terminated');
    } catch (err) { alert('Error: ' + err.message); }
}

function showAddAssistantModal() {
    document.getElementById('addAssistantModal').classList.remove('hidden');
    loadOllamaModels();
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

async function loadOllamaModels() {
    try {
        const resp = await fetch('/api/ollama/models');
        const data = await resp.json();
        const select = document.getElementById('assistantModel');
        if (data.models && data.models.length) {
            select.innerHTML = data.models.map(m => `<option value="${m}">${m}</option>`).join('');
        } else {
            select.innerHTML = '<option value="qwen2.5:0.5b">qwen2.5:0.5b</option>';
        }
    } catch { document.getElementById('assistantModel').innerHTML = '<option value="qwen2.5:0.5b">qwen2.5:0.5b</option>'; }
}

function updateModelOptions() {
    const provider = document.getElementById('assistantProvider').value;
    document.getElementById('apiKeyGroup').classList.toggle('hidden', provider === 'ollama');
    document.getElementById('ollamaModelsGroup').classList.toggle('hidden', provider !== 'ollama');
    
    const modelSelect = document.getElementById('assistantModel');
    if (provider === 'openai') {
        modelSelect.innerHTML = '<option value="gpt-3.5-turbo">GPT-3.5 TURBO</option><option value="gpt-4">GPT-4</option><option value="gpt-4-turbo">GPT-4 TURBO</option>';
    } else if (provider === 'groq') {
        modelSelect.innerHTML = '<option value="llama3-8b-8192">LLAMA3 8B</option><option value="llama3-70b-8192">LLAMA3 70B</option><option value="mixtral-8x7b-32768">MIXTRAL 8X7B</option>';
    } else if (provider === 'gemini') {
        modelSelect.innerHTML = '<option value="gemini-1.5-flash">GEMINI 1.5 FLASH</option><option value="gemini-1.5-pro">GEMINI 1.5 PRO</option><option value="gemini-2.0-flash">GEMINI 2.0 FLASH</option>';
    }
}

async function addAssistant() {
    const name = document.getElementById('assistantName').value.trim() || 'AGENT';
    const provider = document.getElementById('assistantProvider').value;
    const model = document.getElementById('assistantModel').value;
    const api_key = document.getElementById('assistantApiKey').value;
    const system_prompt = document.getElementById('assistantPrompt').value;
    
    try {
        const resp = await fetch('/api/assistants', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, provider, model, api_key, system_prompt })
        });
        const data = await resp.json();
        if (data.success) {
            closeModal('addAssistantModal');
            document.getElementById('assistantName').value = '';
            document.getElementById('assistantApiKey').value = '';
            document.getElementById('assistantPrompt').value = '';
            loadAssistants();
            addAIMessage(`> AGENT DEPLOYED: ${name}`);
            showToast(`Agent deployed: ${name}`);
        }
    } catch (err) { alert('Error: ' + err.message); }
}

// ========== PERSONALIZATION ==========
async function loadPersonalization() {
    try {
        const resp = await fetch('/api/personalization');
        const p = await resp.json();
        document.getElementById('pName').value = p.name || '';
        document.getElementById('pRole').value = p.role || 'developer';
        document.getElementById('pWorkStyle').value = p.work_style || 'concise';
        document.getElementById('pLanguage').value = p.language || 'en';
        document.getElementById('pTone').value = p.tone || 'professional';
        document.getElementById('pLength').value = p.length || 'medium';
        document.getElementById('pDomain').value = p.domain || 'general';
        document.getElementById('pCodeStyle').value = p.code_style || 'python';
        document.getElementById('pTags').value = p.tags || '';
        document.getElementById('pAutoCorrect').checked = p.auto_correct !== false;
        document.getElementById('pExplainCode').checked = p.explain_code !== false;
        document.getElementById('pShowExamples').checked = p.show_examples !== false;
        document.getElementById('pAskClarify').checked = p.ask_clarify !== false;
    } catch (err) { console.error('Failed:', err); }
}

async function savePersonalization() {
    const p = {
        name: document.getElementById('pName').value,
        role: document.getElementById('pRole').value,
        work_style: document.getElementById('pWorkStyle').value,
        language: document.getElementById('pLanguage').value,
        tone: document.getElementById('pTone').value,
        length: document.getElementById('pLength').value,
        domain: document.getElementById('pDomain').value,
        code_style: document.getElementById('pCodeStyle').value,
        tags: document.getElementById('pTags').value,
        auto_correct: document.getElementById('pAutoCorrect').checked,
        explain_code: document.getElementById('pExplainCode').checked,
        show_examples: document.getElementById('pShowExamples').checked,
        ask_clarify: document.getElementById('pAskClarify').checked
    };
    try {
        await fetch('/api/personalization', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(p)
        });
        showToast('Personalization saved');
    } catch (err) { console.error('Failed:', err); }
}

// ========== SETTINGS ==========
async function loadSettings() {
    try {
        const resp = await fetch('/api/settings');
        const settings = await resp.json();
        document.getElementById('settingTheme').value = settings.theme || 'matrix';
        document.getElementById('settingTemperature').value = settings.temperature || 0.7;
        document.getElementById('tempValue').textContent = settings.temperature || 0.7;
        document.getElementById('settingMaxTokens').value = settings.max_tokens || 2048;
        loadOllamaModelsForSettings(settings.default_model);
        loadAssistantsForSettings();
    } catch (err) { console.error('Failed:', err); }
}

async function loadOllamaModelsForSettings(selected) {
    try {
        const resp = await fetch('/api/ollama/models');
        const data = await resp.json();
        const select = document.getElementById('settingDefaultModel');
        if (data.models && data.models.length) {
            select.innerHTML = data.models.map(m => `<option value="${m}" ${m === selected ? 'selected' : ''}>${m}</option>`).join('');
        }
    } catch {}
}

async function loadAssistantsForSettings() {
    try {
        const resp = await fetch('/api/assistants');
        const list = await resp.json();
        const select = document.getElementById('settingActiveAssistant');
        select.innerHTML = '<option value="default">DEFAULT [LOCAL]</option>';
        list.forEach(a => {
            select.innerHTML += `<option value="${a.id}">${a.name} (${a.provider})</option>`;
        });
    } catch {}
}

async function saveSettings() {
    const settings = {
        theme: document.getElementById('settingTheme').value,
        active_assistant: document.getElementById('settingActiveAssistant').value,
        default_model: document.getElementById('settingDefaultModel').value,
        temperature: parseFloat(document.getElementById('settingTemperature').value),
        max_tokens: parseInt(document.getElementById('settingMaxTokens').value)
    };
    selectedAssistant = settings.active_assistant === 'default' ? null : settings.active_assistant;
    try {
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        showToast('Settings saved');
    } catch (err) { console.error('Failed:', err); }
}

// ========== UTILITIES ==========
function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function showLoading() { document.getElementById('loadingOverlay').classList.remove('hidden'); }
function hideLoading() { document.getElementById('loadingOverlay').classList.add('hidden'); }

// ========== EXTENSIONS ==========
let extensionsData = [];

async function loadExtensions() {
    try {
        const res = await fetch('/api/extensions');
        extensionsData = await res.json();
        renderExtensions();
    } catch (err) {
        document.getElementById('extensionsList').innerHTML = '<p style="color:#ff4444">Failed to load extensions</p>';
    }
}

function renderExtensions() {
    const container = document.getElementById('extensionsList');
    if (!extensionsData.length) {
        container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:2rem">No extensions found.<br>Copy <code>extensions/plugins/example.py</code> to create your own!</p>';
        return;
    }
    container.innerHTML = extensionsData.map(ext => `
        <div class="extension-card ${ext.enabled ? '' : 'disabled'}">
            <div class="extension-icon">${getExtIcon(ext.icon)}</div>
            <div class="extension-info">
                <h4>${escapeHtml(ext.display_name)}</h4>
                <p>${escapeHtml(ext.description)}</p>
                <div class="extension-meta">
                    <span>v${ext.version}</span>
                    <span>by ${escapeHtml(ext.author)}</span>
                    ${ext.has_tools ? '<span>🔧 Tools</span>' : ''}
                    ${ext.has_routes ? '<span>🌐 API</span>' : ''}
                    ${ext.has_settings ? '<span>⚙ Settings</span>' : ''}
                </div>
            </div>
            <div class="extension-actions">
                ${ext.has_settings ? `<button class="extension-settings-btn" onclick="showExtSettings('${ext.name}')" title="Settings">⚙</button>` : ''}
                <div class="toggle-switch ${ext.enabled ? 'active' : ''}" onclick="toggleExtension('${ext.name}', ${!ext.enabled})"></div>
            </div>
        </div>
    `).join('');
}

function getExtIcon(icon) {
    const icons = {
        search: '🔍', tts: '🔊', code: '💻', email: '📧',
        drive: '📁', webhook: '🔗', puzzle: '🧩', cpu: '⚙',
        brain: '🧠', globe: '🌐', shield: '🛡', chart: '📊'
    };
    return icons[icon] || '🧩';
}

async function toggleExtension(name, enable) {
    try {
        await fetch(`/api/extensions/${name}/${enable ? 'enable' : 'disable'}`, { method: 'POST' });
        loadExtensions();
        showToast(`Extension ${enable ? 'enabled' : 'disabled'}`);
    } catch (err) { showToast('Failed', 'error'); }
}

async function reloadExtensions() {
    try {
        await fetch('/api/extensions/reload', { method: 'POST' });
        loadExtensions();
        showToast('Extensions reloaded');
    } catch (err) { showToast('Failed to reload', 'error'); }
}

function showExtSettings(name) {
    const ext = extensionsData.find(e => e.name === name);
    if (!ext) return;
    showToast(`Settings for ${ext.display_name} (coming soon)`);
}

function showPluginDocs() {
    const docs = `
        <div class="plugin-docs">
            <h4>// HOW TO CREATE AN EXTENSION</h4>
            <p>1. Copy <code>extensions/plugins/example.py</code></p>
            <p>2. Rename and edit the class</p>
            <p>3. Reload extensions</p>
            <h4>// AVAILABLE HOOKS</h4>
            <p><code>on_chat_message(msg, ctx)</code> - Process messages before AI</p>
            <p><code>on_ai_response(msg, ctx)</code> - Process AI responses</p>
            <p><code>get_chat_tools()</code> - Add tools the AI can use</p>
            <p><code>execute_tool(name, params)</code> - Handle tool calls</p>
            <p><code>get_routes()</code> - Add custom API endpoints</p>
            <p><code>get_settings_schema()</code> - Add settings UI</p>
            <h4>// FILES</h4>
            <p><code>extensions/plugins/</code> - Your custom plugins</p>
            <p><code>extensions/builtin/</code> - Built-in extensions</p>
        </div>
    `;
    const container = document.getElementById('extensionsList');
    const existing = container.querySelector('.plugin-docs');
    if (existing) existing.remove();
    container.insertAdjacentHTML('afterbegin', docs);
}

// ========== INIT ==========
newChat();
