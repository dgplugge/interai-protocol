/**
 * AICP Message Viewer
 * Renders parsed AICP messages as an interactive timeline.
 *
 * Protocol: AICP/1.0
 * Version: Slice 8 — Multi-Project Support
 *
 * Layout:
 *   Left panel:  Message list (ID, FROM, TYPE, TIME) with validation badges
 *   Right panel: Selected message detail (meta + payload) with toolbar
 *
 * Features:
 *   - Multi-project support with project selector dropdown
 *   - Copy Packet button (copies serialized AICP text to clipboard)
 *   - Raw/formatted toggle
 *   - Validation badges in message list
 *   - Builder integration
 */

// Global state
let allMessages = [];
let selectedIndex = -1;
let showRaw = false;
let activeProject = 'all';  // 'all' or a project ID
let projectList = [];        // Array of {id, name, color, messageCount}
let searchQuery = '';        // Current search filter text
let autoRefreshTimer = null; // Polling interval handle
const AUTO_REFRESH_INTERVAL = 30000; // 30 seconds

/**
 * Initializes the viewer — loads projects, messages, and renders the UI.
 */
async function initViewer() {
    const statusEl = document.getElementById('status');
    if (statusEl) statusEl.textContent = 'Loading projects...';

    // Load project registry (metadata: domains, agents, status)
    if (typeof loadProjectRegistry === 'function') {
        await loadProjectRegistry();
    }

    // Load project list
    projectList = await loadAllProjects();

    // Populate project selector
    populateProjectSelector();

    if (statusEl) statusEl.textContent = 'Loading messages...';

    // Auto-load: multi-project API, then index, then embedded
    allMessages = await autoLoad(null, activeProject);

    if (allMessages.length === 0) {
        if (statusEl) statusEl.textContent = 'No messages found. Check console for details.';
        return;
    }

    // Sort by $SEQ if available, otherwise by $TIME
    sortMessages();

    // Validate messages
    allMessages.forEach((msg, i) => {
        const result = validateMessage(msg);
        if (!result.valid) {
            console.warn(`Message ${msg.envelope.id || i} validation:`, result.errors);
        }
    });

    renderMessageList();

    // Select first message
    if (allMessages.length > 0) {
        selectMessage(0);
    }

    updateStatusPill();

    // Start auto-refresh polling
    startAutoRefresh();

    // Show keyboard shortcut hint briefly on first load
    showShortcutHint();
}

/**
 * Sorts allMessages by $SEQ (if available) then by $TIME.
 */
function sortMessages() {
    allMessages.sort((a, b) => {
        if (a.meta.seq !== null && b.meta.seq !== null) {
            return a.meta.seq - b.meta.seq;
        }
        return new Date(a.envelope.time) - new Date(b.envelope.time);
    });
}

/**
 * Returns the filtered message list based on activeProject and search query.
 * @returns {Object[]} Filtered messages
 */
function getFilteredMessages() {
    let msgs = activeProject === 'all' ? allMessages : allMessages.filter(m => m._projectId === activeProject);

    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        msgs = msgs.filter(m => {
            return (m.envelope.from && m.envelope.from.toLowerCase().includes(q)) ||
                   (m.envelope.to && m.envelope.to.toLowerCase().includes(q)) ||
                   (m.envelope.type && m.envelope.type.toLowerCase().includes(q)) ||
                   (m.envelope.id && m.envelope.id.toLowerCase().includes(q)) ||
                   (m.meta.task && m.meta.task.toLowerCase().includes(q)) ||
                   (m.meta.status && m.meta.status.toLowerCase().includes(q)) ||
                   (m.payload && m.payload.toLowerCase().includes(q)) ||
                   (m._projectId && m._projectId.toLowerCase().includes(q));
        });
    }

    return msgs;
}

/**
 * Populates the project selector dropdown with loaded projects.
 */
function populateProjectSelector() {
    const sel = document.getElementById('project-selector');
    if (!sel) return;

    // Clear existing options (except "All Projects")
    sel.innerHTML = '';

    // "All Projects" option
    const allOpt = document.createElement('option');
    allOpt.value = 'all';
    allOpt.textContent = 'All Projects';
    sel.appendChild(allOpt);

    // "All Projects" count
    const totalCount = allMessages.length;
    if (totalCount > 0) {
        allOpt.textContent = `All Projects (${totalCount})`;
    }

    // One option per project with message count
    projectList.forEach(proj => {
        const opt = document.createElement('option');
        opt.value = proj.id;
        const count = allMessages.filter(m => m._projectId === proj.id).length;
        opt.textContent = count > 0 ? `${proj.name} (${count})` : proj.name;
        opt.style.color = proj.color;
        sel.appendChild(opt);
    });

    sel.value = activeProject;
}

/**
 * Handles project selector change.
 */
function onProjectChange() {
    const sel = document.getElementById('project-selector');
    if (!sel) return;

    activeProject = sel.value;
    clearSearch();
    renderMessageList();

    // Select newest message in filtered list
    const filtered = getFilteredMessages();
    if (filtered.length > 0) {
        const newest = filtered[filtered.length - 1];
        const globalIdx = allMessages.indexOf(newest);
        selectMessage(globalIdx);
    } else {
        selectedIndex = -1;
        const detailEl = document.getElementById('message-detail');
        if (detailEl) detailEl.innerHTML = '<div class="empty-state">No messages in this project</div>';
    }

    updateStatusPill();
}

/**
 * Updates the status pill text with message count and project info.
 */
function updateStatusPill() {
    const statusEl = document.getElementById('status');
    if (!statusEl) return;

    const filtered = getFilteredMessages();
    const projectMsgs = activeProject === 'all' ? allMessages : allMessages.filter(m => m._projectId === activeProject);
    const projLabel = activeProject === 'all' ? 'all projects' : (projectList.find(p => p.id === activeProject) || {}).name || activeProject;

    if (searchQuery) {
        statusEl.textContent = `${filtered.length} of ${projectMsgs.length} messages (${projLabel}) matching "${searchQuery}"`;
    } else {
        statusEl.textContent = `${filtered.length} messages (${projLabel})`;
    }
}

/**
 * Gets the project color for a given project ID.
 * @param {string} projectId - Project ID
 * @returns {string} Hex color
 */
function getProjectColor(projectId) {
    const proj = projectList.find(p => p.id === projectId);
    return proj ? proj.color : '#888888';
}

/**
 * Renders the message list in the left panel.
 */
function renderMessageList() {
    const listEl = document.getElementById('message-list');
    if (!listEl) return;

    listEl.innerHTML = '';

    const filtered = getFilteredMessages().slice().reverse();

    filtered.forEach((msg) => {
        const globalIndex = allMessages.indexOf(msg);
        const item = document.createElement('div');
        item.className = 'message-item';
        item.dataset.index = globalIndex;

        const colors = getSenderColor(msg.envelope.from);
        item.style.borderLeftColor = colors.border;

        // Type badge
        const typeBadge = document.createElement('span');
        typeBadge.className = 'type-badge';
        typeBadge.textContent = msg.envelope.type;
        typeBadge.style.backgroundColor = getTypeBadgeColor(msg.envelope.type);

        // Sender
        const sender = document.createElement('span');
        sender.className = 'sender';
        sender.textContent = msg.envelope.from;
        sender.style.color = colors.text;

        // Message ID
        const msgId = document.createElement('span');
        msgId.className = 'msg-id';
        msgId.textContent = msg.envelope.id;

        // Validation badge
        const validation = validateMessage(msg);
        const validBadge = document.createElement('span');
        validBadge.className = `validation-badge ${validation.valid ? 'valid' : 'invalid'}`;
        validBadge.title = validation.valid ? 'Valid' : validation.errors.join(', ');

        // Time
        const time = document.createElement('span');
        time.className = 'msg-time';
        time.textContent = formatTime(msg.envelope.time);

        // Task (truncated)
        const task = document.createElement('div');
        task.className = 'msg-task';
        const taskText = msg.meta.task || '(no task)';
        task.textContent = taskText.length > 60 ? taskText.substring(0, 57) + '...' : taskText;

        // Header row
        const header = document.createElement('div');
        header.className = 'msg-header-row';
        header.appendChild(typeBadge);
        header.appendChild(sender);
        header.appendChild(validBadge);
        header.appendChild(msgId);

        // Project tag (show when viewing all projects)
        if (activeProject === 'all' && msg._projectId) {
            const projTag = document.createElement('span');
            projTag.className = 'project-tag';
            projTag.textContent = msg._projectId;
            projTag.style.borderColor = getProjectColor(msg._projectId);
            projTag.style.color = getProjectColor(msg._projectId);
            header.appendChild(projTag);
        }

        // Build item
        item.appendChild(header);
        item.appendChild(task);
        item.appendChild(time);

        // Click handler
        item.addEventListener('click', () => selectMessage(globalIndex));

        // Maintain selection
        if (globalIndex === selectedIndex) {
            item.classList.add('selected');
        }

        listEl.appendChild(item);
    });
}

/**
 * Selects and displays a message in the detail panel.
 * @param {number} index - Index into allMessages
 */
function selectMessage(index) {
    if (index < 0 || index >= allMessages.length) return;

    // Update selection state
    selectedIndex = index;
    showRaw = false; // Reset to formatted view on selection change

    // Update list item highlighting
    document.querySelectorAll('.message-item').forEach((item) => {
        item.classList.toggle('selected', parseInt(item.dataset.index) === index);
    });

    const msg = allMessages[index];
    renderDetail(msg);
}

/**
 * Toggles between formatted and raw view.
 */
function toggleRawView() {
    showRaw = !showRaw;
    if (selectedIndex >= 0 && selectedIndex < allMessages.length) {
        renderDetail(allMessages[selectedIndex]);
    }
}

/**
 * Copies the selected message as AICP text to clipboard.
 */
async function copyDetailPacket() {
    if (selectedIndex < 0) return;

    const msg = allMessages[selectedIndex];
    const text = msg.raw || serializeMessage(msg);

    try {
        await navigator.clipboard.writeText(text);
    } catch (e) {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }

    const btn = document.getElementById('copy-detail-btn');
    if (btn) {
        const original = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = original;
            btn.classList.remove('copied');
        }, 1500);
    }
}

/**
 * Renders the message detail in the right panel.
 * @param {Object} msg - Normalized message object
 */
function renderDetail(msg) {
    const detailEl = document.getElementById('message-detail');
    if (!detailEl) return;

    const colors = getSenderColor(msg.envelope.from);

    // Toolbar
    let html = '<div class="detail-toolbar">';
    html += `<button id="copy-detail-btn" class="btn-copy-detail" onclick="copyDetailPacket()">Copy Packet</button>`;
    html += `<button class="btn-raw-toggle ${showRaw ? 'active' : ''}" onclick="toggleRawView()">${showRaw ? 'Formatted' : 'Raw'}</button>`;
    html += `<button class="btn-approve" onclick="approveMessage()">Approve</button>`;
    html += `<button class="btn-request-review" onclick="requestReviewMessage()">Request Review</button>`;
    html += `<button class="btn-ack" onclick="ackMessage()">ACK</button>`;
    html += '</div>';

    // Raw view mode
    if (showRaw) {
        const rawText = msg.raw || serializeMessage(msg);
        html += `<div class="raw-content">${escapeHtml(rawText)}</div>`;
        detailEl.innerHTML = html;
        return;
    }

    // Envelope section
    html += '<div class="detail-section">';
    html += '<h3 class="section-title">Envelope</h3>';
    html += '<div class="field-grid">';
    html += renderField('$PROTO', msg.envelope.proto);
    html += renderField('$TYPE', msg.envelope.type, getTypeBadgeColor(msg.envelope.type));
    html += renderField('$ID', msg.envelope.id);
    html += renderField('$FROM', msg.envelope.from, colors.badge);
    html += renderField('$TO', msg.envelope.to);
    html += renderField('$TIME', formatTime(msg.envelope.time));
    html += '</div></div>';

    // Meta section
    html += '<div class="detail-section">';
    html += '<h3 class="section-title">Meta</h3>';
    html += '<div class="field-grid">';
    if (msg.meta.task) html += renderField('$TASK', msg.meta.task);
    if (msg.meta.status) html += renderField('$STATUS', msg.meta.status, getStatusColor(msg.meta.status));
    if (msg.meta.ref) html += renderFieldLink('$REF', msg.meta.ref);
    if (msg.meta.seq !== null) html += renderField('$SEQ', msg.meta.seq);
    if (msg.meta.priority) html += renderField('$PRIORITY', msg.meta.priority, getPriorityColor(msg.meta.priority));
    if (msg.meta.role) html += renderField('$ROLE', msg.meta.role);
    if (msg.meta.intent) html += renderField('$INTENT', msg.meta.intent);
    if (msg.meta.context) html += renderField('$CONTEXT', msg.meta.context);
    if (msg.meta.accept) html += renderField('$ACCEPT', msg.meta.accept);
    html += '</div></div>';

    // Custom fields section (if any)
    const customKeys = Object.keys(msg.custom);
    if (customKeys.length > 0) {
        html += '<div class="detail-section">';
        html += '<h3 class="section-title">Custom</h3>';
        html += '<div class="field-grid">';
        customKeys.forEach(key => {
            html += renderField(key, msg.custom[key]);
        });
        html += '</div></div>';
    }

    // Payload section
    if (msg.payload) {
        html += '<div class="detail-section">';
        html += '<h3 class="section-title">Payload</h3>';
        html += '<div class="payload-content">';
        html += escapeHtml(msg.payload);
        html += '</div></div>';
    }

    // Audit section (if any audit fields present)
    if (msg.audit.summary || msg.audit.changes || msg.audit.checksum) {
        html += '<div class="detail-section">';
        html += '<h3 class="section-title">Audit</h3>';
        html += '<div class="field-grid">';
        if (msg.audit.summary) html += renderField('$SUMMARY', msg.audit.summary);
        if (msg.audit.changes) html += renderField('$CHANGES', msg.audit.changes);
        if (msg.audit.checksum) html += renderField('$CHECKSUM', msg.audit.checksum);
        html += '</div></div>';
    }

    // Validation
    const validation = validateMessage(msg);
    if (!validation.valid) {
        html += '<div class="detail-section validation-errors">';
        html += '<h3 class="section-title">Validation Issues</h3>';
        validation.errors.forEach(err => {
            html += `<div class="validation-error">${escapeHtml(err)}</div>`;
        });
        html += '</div>';
    }

    detailEl.innerHTML = html;

    // Wire up $REF link clicks
    detailEl.querySelectorAll('.ref-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const refId = link.dataset.ref;
            const refIndex = allMessages.findIndex(m => m.envelope.id === refId);
            if (refIndex >= 0) {
                selectMessage(refIndex);
                // Scroll list item into view
                const listItem = document.querySelector(`.message-item[data-index="${refIndex}"]`);
                if (listItem) listItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        });
    });
}

// --- Render helpers ---

function renderField(key, value, badgeColor) {
    const displayValue = escapeHtml(String(value));
    if (badgeColor) {
        return `<div class="field"><span class="field-key">${escapeHtml(key)}</span><span class="field-value badge" style="background:${badgeColor}">${displayValue}</span></div>`;
    }
    return `<div class="field"><span class="field-key">${escapeHtml(key)}</span><span class="field-value">${displayValue}</span></div>`;
}

function renderFieldLink(key, refId) {
    return `<div class="field"><span class="field-key">${escapeHtml(key)}</span><a href="#" class="field-value ref-link" data-ref="${escapeHtml(refId)}">${escapeHtml(refId)}</a></div>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getTypeBadgeColor(type) {
    const colors = {
        'REQUEST':  '#1976d2',
        'RESPONSE': '#388e3c',
        'ACK':      '#7b1fa2',
        'ERROR':    '#d32f2f',
        'HANDOFF':  '#f57c00',
        'REVIEW':   '#0097a7'
    };
    return colors[type] || '#757575';
}

function getStatusColor(status) {
    const colors = {
        'PENDING':     '#ffa000',
        'IN_PROGRESS': '#1976d2',
        'COMPLETE':    '#388e3c',
        'FAILED':      '#d32f2f'
    };
    return colors[status] || '#757575';
}

function getPriorityColor(priority) {
    const colors = {
        'LOW':    '#757575',
        'NORMAL': '#1976d2',
        'MEDIUM': '#f57c00',
        'HIGH':   '#d32f2f'
    };
    return colors[priority] || '#757575';
}

// === Slice 2: Refresh & Toast ===

/**
 * Refreshes the message list from the server.
 * Reloads all project messages with a cache-bust parameter,
 * re-sorts, re-renders, and selects the newest message.
 */
async function refreshMessages() {
    const freshMessages = await autoLoad(null, activeProject);

    if (freshMessages.length > 0) {
        allMessages = freshMessages;
        sortMessages();
        populateProjectSelector();
        renderMessageList();

        // Select the newest message in the filtered view
        const filtered = getFilteredMessages();
        if (filtered.length > 0) {
            const lastMsg = filtered[filtered.length - 1];
            const globalIdx = allMessages.indexOf(lastMsg);
            selectMessage(globalIdx);
            const item = document.querySelector(`.message-item[data-index="${globalIdx}"]`);
            if (item) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        updateStatusPill();

        // Hide the refresh badge after loading
        const badge = document.getElementById('auto-refresh-badge');
        if (badge) badge.style.display = 'none';
    }
}

/**
 * Shows a toast notification.
 * @param {string} message - The message to display
 * @param {string} type - 'success', 'error', or 'info'
 * @param {number} [duration=4000] - Auto-dismiss after ms
 */
function showToast(message, type, duration) {
    if (typeof type === 'undefined') type = 'info';
    if (typeof duration === 'undefined') duration = 4000;

    // Create container if it doesn't exist
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    // Trigger slide-in animation
    requestAnimationFrame(function() {
        toast.classList.add('show');
    });

    // Auto-dismiss
    setTimeout(function() {
        toast.classList.remove('show');
        setTimeout(function() {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, duration);
}

// === Action Palette (Step 1: Hardcoded high-value actions) ===

/**
 * Opens the builder pre-filled as an approval ACK for the selected message.
 */
function approveMessage() {
    if (selectedIndex < 0) return;
    prefillApproval(allMessages[selectedIndex]);
}

/**
 * Opens the builder pre-filled as a review request for the selected message.
 * Typically used after an implementation RESPONSE to request Lodestar's review.
 */
function requestReviewMessage() {
    if (selectedIndex < 0) return;
    prefillRequestReview(allMessages[selectedIndex]);
}

/**
 * Opens the builder pre-filled as a quick ACK for the selected message.
 */
function ackMessage() {
    if (selectedIndex < 0) return;
    prefillAck(allMessages[selectedIndex]);
}

// === Search / Filter ===

/**
 * Handles search input changes. Filters the message list in real time.
 */
function onSearchInput() {
    const input = document.getElementById('search-input');
    const clearBtn = document.getElementById('search-clear');
    if (!input) return;

    searchQuery = input.value.trim();
    if (clearBtn) clearBtn.style.display = searchQuery ? 'block' : 'none';

    renderMessageList();
    updateStatusPill();

    // Auto-select first visible message if current selection is filtered out
    const filtered = getFilteredMessages();
    if (filtered.length > 0) {
        const currentVisible = filtered.find(m => allMessages.indexOf(m) === selectedIndex);
        if (!currentVisible) {
            selectMessage(allMessages.indexOf(filtered[filtered.length - 1]));
        }
    }
}

/**
 * Clears the search input and resets the filter.
 */
function clearSearch() {
    const input = document.getElementById('search-input');
    if (input) input.value = '';
    searchQuery = '';
    const clearBtn = document.getElementById('search-clear');
    if (clearBtn) clearBtn.style.display = 'none';
    renderMessageList();
    updateStatusPill();
}

// === Auto-Refresh Polling ===

/**
 * Starts the auto-refresh polling timer.
 * Checks for new messages every AUTO_REFRESH_INTERVAL ms.
 */
function startAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    autoRefreshTimer = setInterval(checkForNewMessages, AUTO_REFRESH_INTERVAL);
}

/**
 * Checks for new messages without disrupting the current view.
 * Shows a badge if new messages are found.
 */
async function checkForNewMessages() {
    try {
        const freshMessages = await autoLoad(null, activeProject);
        if (freshMessages.length > allMessages.length) {
            const newCount = freshMessages.length - allMessages.length;
            showRefreshBadge(newCount);
        }
    } catch (e) {
        // Silent — don't disrupt the user on polling errors
    }
}

/**
 * Shows the auto-refresh badge with the count of new messages.
 * @param {number} count - Number of new messages
 */
function showRefreshBadge(count) {
    const badge = document.getElementById('auto-refresh-badge');
    if (!badge) return;
    badge.textContent = '+' + count;
    badge.style.display = 'inline-block';
    badge.title = count + ' new message(s) — click to refresh';
    badge.onclick = function() {
        badge.style.display = 'none';
        refreshMessages();
    };
}

// === Keyboard Shortcut Hint ===

/**
 * Shows a brief keyboard shortcut hint at the bottom of the screen.
 * Disappears after 5 seconds.
 */
function showShortcutHint() {
    let hint = document.getElementById('shortcut-hint');
    if (!hint) {
        hint = document.createElement('div');
        hint.id = 'shortcut-hint';
        hint.className = 'shortcut-hint';
        hint.innerHTML = '<kbd>j</kbd>/<kbd>k</kbd> navigate &nbsp; <kbd>/</kbd> search &nbsp; <kbd>r</kbd> raw toggle &nbsp; <kbd>Esc</kbd> close';
        document.body.appendChild(hint);
    }
    requestAnimationFrame(function() {
        hint.classList.add('show');
    });
    setTimeout(function() {
        hint.classList.remove('show');
    }, 5000);
}

// --- Keyboard navigation ---
document.addEventListener('keydown', (e) => {
    // "/" focuses search bar from anywhere (even in inputs)
    if (e.key === '/' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        const searchInput = document.getElementById('search-input');
        if (searchInput) searchInput.focus();
        return;
    }

    // Escape: clear search if focused, close builder, or close agent panel
    if (e.key === 'Escape') {
        const searchInput = document.getElementById('search-input');
        if (document.activeElement === searchInput) {
            clearSearch();
            searchInput.blur();
            return;
        }
        if (typeof builderVisible !== 'undefined' && builderVisible) {
            toggleBuilder();
            return;
        }
        if (typeof agentPanelVisible !== 'undefined' && agentPanelVisible) {
            toggleAgentPanel();
            return;
        }
        return;
    }

    // Don't navigate when typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
        return;
    }

    const filtered = getFilteredMessages();

    // j/ArrowDown = next message (list is reversed, so "next" = previous in filtered array)
    if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault();
        const currentFilterIdx = filtered.findIndex(m => allMessages.indexOf(m) === selectedIndex);
        if (currentFilterIdx < filtered.length - 1) {
            const nextGlobalIdx = allMessages.indexOf(filtered[currentFilterIdx + 1]);
            selectMessage(nextGlobalIdx);
            const item = document.querySelector(`.message-item[data-index="${nextGlobalIdx}"]`);
            if (item) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // k/ArrowUp = previous message
    if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault();
        const currentFilterIdx = filtered.findIndex(m => allMessages.indexOf(m) === selectedIndex);
        if (currentFilterIdx > 0) {
            const prevGlobalIdx = allMessages.indexOf(filtered[currentFilterIdx - 1]);
            selectMessage(prevGlobalIdx);
            const item = document.querySelector(`.message-item[data-index="${prevGlobalIdx}"]`);
            if (item) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // r = toggle raw view
    if (e.key === 'r') {
        toggleRawView();
    }

    // ? = show keyboard shortcut hint
    if (e.key === '?') {
        showShortcutHint();
    }
});

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initViewer);
