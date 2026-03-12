/* ═══════════════════════════════════════════════════════════════
   LISA AI - Chat Interface JavaScript
   Handles messaging, sessions, sidebar, and interactive features
   ═══════════════════════════════════════════════════════════════ */

// ─── State ───
const state = {
    currentSessionId: null,
    sessions: [],
    isLoading: false,
};

// ─── Initialize ───
document.addEventListener("DOMContentLoaded", () => {
    loadSessions();
    document.getElementById("messageInput").focus();
});

// ═══════════════════════════════════════════════════════════════
// MESSAGING
// ═══════════════════════════════════════════════════════════════

async function sendMessage() {
    const input = document.getElementById("messageInput");
    const query = input.value.trim();
    if (!query || state.isLoading) return;

    state.isLoading = true;
    document.getElementById("sendBtn").disabled = true;

    // Hide welcome screen
    const welcome = document.getElementById("welcomeScreen");
    if (welcome) welcome.style.display = "none";

    // Add user message
    addMessage("user", query);
    input.value = "";
    autoResize(input);

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: query,
                session_id: state.currentSessionId,
            }),
        });

        const data = await response.json();
        removeTypingIndicator(typingId);

        if (!response.ok) {
            addMessage("assistant", data.error || "Something went wrong. Please try again.", null, true);
            return;
        }

        // Update session ID if new
        if (data.session_id && data.session_id !== state.currentSessionId) {
            state.currentSessionId = data.session_id;
            loadSessions();
        }

        // Add assistant response with metadata
        addMessage("assistant", data.response, {
            classification: data.classification,
            documents: data.documents,
            latency: data.latency_ms,
            message_id: data.message_id,
        });

    } catch (err) {
        removeTypingIndicator(typingId);
        addMessage("assistant", "Network error. Please check your connection and try again.", null, true);
    } finally {
        state.isLoading = false;
        document.getElementById("sendBtn").disabled = false;
        input.focus();
    }
}

function sendExample(btn) {
    document.getElementById("messageInput").value = btn.textContent;
    sendMessage();
}

function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

// ═══════════════════════════════════════════════════════════════
// MESSAGE RENDERING
// ═══════════════════════════════════════════════════════════════

function addMessage(role, content, metadata = null, isError = false) {
    const container = document.getElementById("messagesContainer");

    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const avatarLabel = role === "user" ? "Y" : "L";
    const roleLabel = role === "user" ? "You" : "LISA";

    // Render markdown for assistant messages
    let renderedContent;
    if (role === "assistant" && !isError) {
        renderedContent = DOMPurify.sanitize(marked.parse(content));
    } else if (isError) {
        renderedContent = `<span style="color: var(--danger);">${escapeHtml(content)}</span>`;
    } else {
        renderedContent = escapeHtml(content);
    }

    let badgesHtml = "";
    let actionsHtml = "";

    if (metadata && role === "assistant") {
        const cls = metadata.classification || {};
        if (cls.is_in_scope !== undefined) {
            const scopeClass = cls.is_in_scope ? "badge-in-scope" : "badge-out-scope";
            const scopeLabel = cls.is_in_scope ? "IN-SCOPE" : "OUT-OF-SCOPE";
            badgesHtml += `<span class="classification-badge ${scopeClass}">${scopeLabel} ${cls.scope_confidence || 0}%</span>`;
        }
        if (cls.intent) {
            badgesHtml += `<span class="classification-badge badge-intent">${cls.intent.replace(/_/g, " ")}</span>`;
        }

        const msgId = metadata.message_id || "";
        actionsHtml = `
            <div class="message-actions" data-msg-id="${msgId}">
                <button class="action-btn" onclick="copyMessage(this)" title="Copy">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="9" height="9" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M3 11V3a1 1 0 011-1h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                    Copy
                </button>
                <button class="action-btn" onclick="regenerateResponse()" title="Regenerate">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8a6 6 0 0111.47-2.5M14 8a6 6 0 01-11.47 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M13 2v4h-4M3 14v-4h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    Regenerate
                </button>
                <button class="action-btn" onclick="submitFeedback(this, 1)" title="Good response">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M5 9V14H3a1 1 0 01-1-1v-3a1 1 0 011-1h2zm0 0l2-5V2a1 1 0 011-1h0a2 2 0 012 2v3h3.27a1 1 0 011 1.13l-.93 5.6A1 1 0 0112.34 14H5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <button class="action-btn" onclick="submitFeedback(this, -1)" title="Bad response">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11 7V2H13a1 1 0 011 1v3a1 1 0 01-1 1h-2zm0 0l-2 5v2a1 1 0 01-1 1h0a2 2 0 01-2-2V10H2.73a1 1 0 01-1-1.13l.93-5.6A1 1 0 013.66 2H11" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
            </div>`;
    }

    row.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">${avatarLabel}</div>
            <div class="message-body">
                <div class="message-role">${roleLabel}</div>
                <div class="message-text">${renderedContent}</div>
                ${badgesHtml ? `<div style="margin-top: 8px;">${badgesHtml}</div>` : ""}
                ${actionsHtml}
            </div>
        </div>`;

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById("messagesContainer");
    const id = "typing_" + Date.now();

    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.id = id;
    row.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">L</div>
            <div class="message-body">
                <div class="message-role">LISA</div>
                <div class="typing-indicator"><span></span><span></span><span></span></div>
            </div>
        </div>`;

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ═══════════════════════════════════════════════════════════════
// SESSIONS (SIDEBAR)
// ═══════════════════════════════════════════════════════════════

async function loadSessions() {
    try {
        const response = await fetch("/api/sessions");
        const data = await response.json();
        state.sessions = data.sessions || [];
        renderSidebar();
    } catch (err) {
        console.error("Failed to load sessions:", err);
    }
}

function renderSidebar() {
    const list = document.getElementById("sessionsList");
    list.innerHTML = "";

    if (state.sessions.length === 0) {
        list.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;">No conversations yet</div>`;
        return;
    }

    // Group by date
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    const groups = { Today: [], Yesterday: [], Previous: [] };

    for (const s of state.sessions) {
        const d = new Date(s.updated_at).toDateString();
        if (d === today) groups.Today.push(s);
        else if (d === yesterday) groups.Yesterday.push(s);
        else groups.Previous.push(s);
    }

    for (const [label, sessions] of Object.entries(groups)) {
        if (sessions.length === 0) continue;

        const groupLabel = document.createElement("div");
        groupLabel.className = "session-group-label";
        groupLabel.textContent = label;
        list.appendChild(groupLabel);

        for (const s of sessions) {
            const item = document.createElement("div");
            item.className = `session-item ${s.id === state.currentSessionId ? "active" : ""}`;
            item.onclick = () => loadSession(s.id);
            item.innerHTML = `
                <span style="flex:1; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(s.title)}</span>
                <button class="delete-btn" onclick="event.stopPropagation(); deleteSession('${s.id}')" title="Delete">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                </button>`;
            list.appendChild(item);
        }
    }
}

async function loadSession(sessionId) {
    state.currentSessionId = sessionId;
    renderSidebar();

    const container = document.getElementById("messagesContainer");
    container.innerHTML = "";

    const welcome = document.getElementById("welcomeScreen");
    if (welcome) welcome.style.display = "none";

    try {
        const response = await fetch(`/api/sessions/${sessionId}/messages`);
        const data = await response.json();

        document.getElementById("chatTitle").textContent = data.title || "LISA AI";

        for (const msg of data.messages) {
            addMessage(msg.role, msg.content, msg.role === "assistant" ? {
                classification: {
                    is_in_scope: msg.is_in_scope,
                    intent: msg.intent,
                    scope_confidence: Math.round((msg.confidence || 0) * 100),
                },
            } : null);
        }
    } catch (err) {
        console.error("Failed to load session:", err);
    }

    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        document.getElementById("sidebar").classList.remove("open");
    }
}

async function createNewChat() {
    state.currentSessionId = null;
    document.getElementById("chatTitle").textContent = "LISA AI";

    const container = document.getElementById("messagesContainer");
    container.innerHTML = `
        <div class="welcome" id="welcomeScreen">
            <div class="welcome-logo">LISA</div>
            <h2>How can I help you today?</h2>
            <p>I'm your LAMF knowledge assistant, marketing co-pilot, and growth enabler.</p>
            <div class="example-queries">
                <button class="example-btn" onclick="sendExample(this)">What is Loan Against Mutual Funds?</button>
                <button class="example-btn" onclick="sendExample(this)">What are the eligibility criteria for LAMF?</button>
                <button class="example-btn" onclick="sendExample(this)">Create a WhatsApp message for LAMF promotion</button>
                <button class="example-btn" onclick="sendExample(this)">What are the interest rates and fees?</button>
            </div>
        </div>`;

    renderSidebar();
    document.getElementById("messageInput").focus();

    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        document.getElementById("sidebar").classList.remove("open");
    }
}

async function deleteSession(sessionId) {
    if (!confirm("Delete this conversation?")) return;

    try {
        await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
        if (state.currentSessionId === sessionId) {
            createNewChat();
        }
        loadSessions();
    } catch (err) {
        console.error("Failed to delete session:", err);
    }
}

async function searchChats(query) {
    if (!query.trim()) {
        renderSidebar();
        return;
    }

    try {
        const response = await fetch(`/api/sessions/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        const list = document.getElementById("sessionsList");
        list.innerHTML = "";

        if (data.results.length === 0) {
            list.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;">No results found</div>`;
            return;
        }

        const label = document.createElement("div");
        label.className = "session-group-label";
        label.textContent = "Search Results";
        list.appendChild(label);

        for (const r of data.results) {
            const item = document.createElement("div");
            item.className = "session-item";
            item.onclick = () => loadSession(r.session_id);
            item.innerHTML = `<span style="flex:1; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(r.title)}</span>`;
            list.appendChild(item);
        }
    } catch (err) {
        console.error("Search failed:", err);
    }
}

// ═══════════════════════════════════════════════════════════════
// ACTIONS (copy, regenerate, feedback, export)
// ═══════════════════════════════════════════════════════════════

function copyMessage(btn) {
    const text = btn.closest(".message-body").querySelector(".message-text").innerText;
    navigator.clipboard.writeText(text).then(() => {
        const original = btn.innerHTML;
        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 8l3 3 5-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg> Copied!';
        setTimeout(() => { btn.innerHTML = original; }, 2000);
    });
}

async function regenerateResponse() {
    if (!state.currentSessionId || state.isLoading) return;

    state.isLoading = true;
    document.getElementById("sendBtn").disabled = true;

    // Remove last assistant message from UI
    const messages = document.querySelectorAll(".message-row.assistant");
    const lastAssistant = messages[messages.length - 1];
    if (lastAssistant) lastAssistant.remove();

    const typingId = showTypingIndicator();

    try {
        const response = await fetch("/api/chat/regenerate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: state.currentSessionId }),
        });

        const data = await response.json();
        removeTypingIndicator(typingId);

        if (data.success) {
            addMessage("assistant", data.response, { latency: data.latency_ms });
        } else {
            addMessage("assistant", data.error || "Failed to regenerate response.", null, true);
        }
    } catch (err) {
        removeTypingIndicator(typingId);
        addMessage("assistant", "Network error during regeneration.", null, true);
    } finally {
        state.isLoading = false;
        document.getElementById("sendBtn").disabled = false;
    }
}

async function submitFeedback(btn, rating) {
    const actionsDiv = btn.closest(".message-actions");
    const messageId = actionsDiv?.dataset?.msgId;

    // Visual feedback
    const allBtns = actionsDiv.querySelectorAll(".action-btn");
    allBtns.forEach(b => b.classList.remove("active-up", "active-down"));
    btn.classList.add(rating === 1 ? "active-up" : "active-down");

    try {
        await fetch("/api/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message_id: messageId, rating: rating }),
        });
    } catch (err) {
        console.error("Feedback submission failed:", err);
    }
}

async function exportChat(format) {
    if (!state.currentSessionId) return;

    try {
        const response = await fetch(`/api/sessions/${state.currentSessionId}/export?format=${format}`);
        if (format === "text") {
            const text = await response.text();
            const blob = new Blob([text], { type: "text/plain" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `lisa_chat.txt`;
            a.click();
            URL.revokeObjectURL(url);
        } else {
            const data = await response.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `lisa_chat.json`;
            a.click();
            URL.revokeObjectURL(url);
        }
    } catch (err) {
        console.error("Export failed:", err);
    }
}

// ═══════════════════════════════════════════════════════════════
// UI HELPERS
// ═══════════════════════════════════════════════════════════════

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("open");
    sidebar.classList.toggle("collapsed");
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
