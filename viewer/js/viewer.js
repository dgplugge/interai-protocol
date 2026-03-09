/**
 * AICP Message Viewer
 * Renders parsed AICP messages as an interactive timeline.
 *
 * Protocol: AICP/1.0
 * Version: Slice 1 — Read, Render, and Build
 *
 * Layout:
 *   Left panel:  Message list (ID, FROM, TYPE, TIME) with validation badges
 *   Right panel: Selected message detail (meta + payload) with toolbar
 *
 * Slice 1 additions:
 *   - Copy Packet button (copies serialized AICP text to clipboard)
 *   - Raw/formatted toggle
 *   - Validation badges in message list
 *   - Builder integration
 */

// Global state
let allMessages = [];
let selectedIndex = -1;
let showRaw = false;

/**
 * Initializes the viewer — loads messages and renders the UI.
 */
async function initViewer() {
    const statusEl = document.getElementById('status');
    if (statusEl) statusEl.textContent = 'Loading messages...';

    // Auto-load: try index first, then embedded
    allMessages = await autoLoad('samples/journal-index.json');

    if (allMessages.length === 0) {
        if (statusEl) statusEl.textContent = 'No messages found. Check console for details.';
        return;
    }

    // Sort by $SEQ if available, otherwise by $TIME
    allMessages.sort((a, b) => {
        if (a.meta.seq !== null && b.meta.seq !== null) {
            return a.meta.seq - b.meta.seq;
        }
        return new Date(a.envelope.time) - new Date(b.envelope.time);
    });

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

    if (statusEl) {
        statusEl.textContent = `${allMessages.length} messages loaded`;
    }
}

/**
 * Renders the message list in the left panel.
 */
function renderMessageList() {
    const listEl = document.getElementById('message-list');
    if (!listEl) return;

    listEl.innerHTML = '';

    allMessages.forEach((msg, index) => {
        const item = document.createElement('div');
        item.className = 'message-item';
        item.dataset.index = index;

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

        // Build item
        item.appendChild(header);
        item.appendChild(task);
        item.appendChild(time);

        // Click handler
        item.addEventListener('click', () => selectMessage(index));

        // Maintain selection
        if (index === selectedIndex) {
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
    document.querySelectorAll('.message-item').forEach((item, i) => {
        item.classList.toggle('selected', i === index);
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
        'HIGH':   '#d32f2f'
    };
    return colors[priority] || '#757575';
}

// === Slice 2: Refresh & Toast ===

/**
 * Refreshes the message list from the server.
 * Reloads journal-index.json with a cache-bust parameter,
 * re-sorts, re-renders, and selects the newest message.
 */
async function refreshMessages() {
    const cacheBust = `samples/journal-index.json?t=${Date.now()}`;
    const freshMessages = await autoLoad(cacheBust);

    if (freshMessages.length > 0) {
        allMessages = freshMessages;

        // Sort by $SEQ if available, otherwise by $TIME
        allMessages.sort((a, b) => {
            if (a.meta.seq !== null && b.meta.seq !== null) {
                return a.meta.seq - b.meta.seq;
            }
            return new Date(a.envelope.time) - new Date(b.envelope.time);
        });

        renderMessageList();

        // Select the newest message (last in sorted order)
        selectMessage(allMessages.length - 1);
        const item = document.querySelector(`.message-item[data-index="${allMessages.length - 1}"]`);
        if (item) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        const statusEl = document.getElementById('status');
        if (statusEl) statusEl.textContent = `${allMessages.length} messages loaded`;
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

// === Slice 4: Approve Button ===

/**
 * Opens the builder pre-filled as an approval ACK for the selected message.
 * The Orchestrator clicks "Approve" → builder opens with ACK defaults →
 * user edits/confirms → clicks "Relay Message" to save.
 */
function approveMessage() {
    if (selectedIndex < 0) return;
    const msg = allMessages[selectedIndex];
    // Delegate to builder's prefillApproval
    prefillApproval(msg);
}

// --- Keyboard navigation ---
document.addEventListener('keydown', (e) => {
    // Don't navigate when typing in builder form
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
        return;
    }

    if (e.key === 'ArrowDown' && selectedIndex < allMessages.length - 1) {
        e.preventDefault();
        selectMessage(selectedIndex + 1);
        const item = document.querySelector(`.message-item[data-index="${selectedIndex}"]`);
        if (item) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (e.key === 'ArrowUp' && selectedIndex > 0) {
        e.preventDefault();
        selectMessage(selectedIndex - 1);
        const item = document.querySelector(`.message-item[data-index="${selectedIndex}"]`);
        if (item) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    // Escape closes builder
    if (e.key === 'Escape' && builderVisible) {
        toggleBuilder();
    }
});

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initViewer);
