/**
 * AICP Message Builder
 * Form UI for composing AICP messages with auto-filled fields.
 *
 * Protocol: AICP/1.0
 * Version: Slice 1 — Read, Render, and Build
 *
 * Features:
 *   - Form with dropdowns for $TYPE, $STATUS, $PRIORITY
 *   - Auto-fills $PROTO, $ID, $TIME, $SEQ
 *   - Live preview of generated AICP text
 *   - One-click copy to clipboard
 *   - Adds composed message to viewer list
 */

let builderVisible = false;

/**
 * Toggles the builder panel visibility.
 */
function toggleBuilder() {
    builderVisible = !builderVisible;
    const panel = document.getElementById('builder-panel');
    const btn = document.getElementById('builder-toggle');
    if (panel) {
        panel.style.display = builderVisible ? 'flex' : 'none';
    }
    if (btn) {
        btn.textContent = builderVisible ? 'Close Builder' : 'New Message';
        btn.classList.toggle('active', builderVisible);
    }
    if (builderVisible) {
        resetBuilder();
        updatePreview();
    }
}

/**
 * Resets the builder form to defaults.
 */
function resetBuilder() {
    const form = document.getElementById('builder-form');
    if (!form) return;

    // Auto-fill defaults with smart sequential values
    setFieldValue('b-proto', 'AICP/1.0');
    setFieldValue('b-type', 'REQUEST');
    setFieldValue('b-id', generateNextMessageId());
    setFieldValue('b-from', 'Don');
    setFieldValue('b-to', 'Pharos, Lodestar');
    setFieldValue('b-time', nowISO());
    setFieldValue('b-task', '');
    setFieldValue('b-status', 'PENDING');
    setFieldValue('b-priority', '');
    setFieldValue('b-role', 'Orchestrator');
    setFieldValue('b-intent', '');
    setFieldValue('b-ref', getLastMessageId() || '');
    setFieldValue('b-seq', getNextSeq());
    setFieldValue('b-project', 'InterAI-Protocol');
    setFieldValue('b-domain', 'Multi-Agent Systems');
    setFieldValue('b-payload', '');
}

/**
 * Gets the next $SEQ value based on loaded messages.
 * @returns {string} Next sequence number
 */
function getNextSeq() {
    if (!allMessages || allMessages.length === 0) return '1';
    const maxSeq = allMessages.reduce((max, msg) => {
        const seq = msg.meta.seq;
        return (seq !== null && seq > max) ? seq : max;
    }, 0);
    return String(maxSeq + 1);
}

/**
 * Builds a message object from the current form values.
 * @returns {Object} Normalized message object
 */
function buildMessageFromForm() {
    const defaults = {
        proto:    getFieldValue('b-proto'),
        type:     getFieldValue('b-type'),
        id:       getFieldValue('b-id'),
        from:     getFieldValue('b-from'),
        to:       getFieldValue('b-to'),
        time:     getFieldValue('b-time'),
        task:     getFieldValue('b-task'),
        status:   getFieldValue('b-status'),
        priority: getFieldValue('b-priority') || null,
        role:     getFieldValue('b-role') || null,
        intent:   getFieldValue('b-intent') || null,
        ref:      getFieldValue('b-ref') || null,
        seq:      getFieldValue('b-seq') || null,
        payload:  getFieldValue('b-payload'),
        custom: {}
    };

    // Custom fields
    const project = getFieldValue('b-project');
    const domain = getFieldValue('b-domain');
    if (project) defaults.custom['PROJECT'] = project;
    if (domain) defaults.custom['DOMAIN'] = domain;

    return createDraftMessage(defaults);
}

/**
 * Updates the live preview pane with current form values.
 */
function updatePreview() {
    const previewEl = document.getElementById('builder-preview-text');
    if (!previewEl) return;

    const msg = buildMessageFromForm();
    const text = serializeMessage(msg);
    previewEl.textContent = text;

    // Update validation
    const validation = validateMessage(msg);
    const validEl = document.getElementById('builder-validation');
    if (validEl) {
        if (validation.valid) {
            validEl.textContent = 'Valid';
            validEl.className = 'builder-valid';
        } else {
            validEl.textContent = validation.errors.join('; ');
            validEl.className = 'builder-invalid';
        }
    }
}

/**
 * Copies the generated AICP text to clipboard.
 */
async function copyPacket() {
    const msg = buildMessageFromForm();
    const text = serializeMessage(msg);

    try {
        await navigator.clipboard.writeText(text);
        const btn = document.getElementById('copy-btn');
        if (btn) {
            const original = btn.textContent;
            btn.textContent = 'Copied!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.textContent = original;
                btn.classList.remove('copied');
            }, 1500);
        }
    } catch (e) {
        // Fallback for file:// protocol
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);

        const btn = document.getElementById('copy-btn');
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
}

/**
 * Adds the composed message to the viewer list.
 */
function addToViewer() {
    const msg = buildMessageFromForm();
    const validation = validateMessage(msg);

    if (!validation.valid) {
        alert('Cannot add: message has validation errors.\n\n' + validation.errors.join('\n'));
        return;
    }

    // Update raw text
    msg.raw = serializeMessage(msg);

    // Add to global messages array and re-render
    allMessages.push(msg);
    renderMessageList();
    selectMessage(allMessages.length - 1);

    // Scroll the new message into view
    const item = document.querySelector(`.message-item[data-index="${allMessages.length - 1}"]`);
    if (item) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Update status
    const statusEl = document.getElementById('status');
    if (statusEl) statusEl.textContent = `${allMessages.length} messages loaded`;

    // Close builder
    toggleBuilder();
}

// === Slice 2: Relay Message ===

/**
 * Relays the composed message to the server for persistent storage.
 * POSTs raw AICP text to /api/relay, which saves the .md file
 * and updates journal-index.json.
 */
async function relayMessage() {
    const msg = buildMessageFromForm();
    const validation = validateMessage(msg);

    if (!validation.valid) {
        showToast('Cannot relay: ' + validation.errors.join('; '), 'error');
        return;
    }

    const text = serializeMessage(msg);
    const relayBtn = document.getElementById('relay-btn');

    // Disable button during relay
    if (relayBtn) {
        relayBtn.disabled = true;
        relayBtn.textContent = 'Relaying...';
    }

    try {
        const response = await fetch('/api/relay', {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: text
        });

        const result = await response.json();

        if (result.ok) {
            showToast('Relayed ' + result.id + ' to journal', 'success');
            // Refresh viewer to show new message
            await refreshMessages();
            // Close builder
            toggleBuilder();
        } else {
            showToast('Relay failed: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        showToast('Relay error: ' + e.message, 'error');
    } finally {
        if (relayBtn) {
            relayBtn.disabled = false;
            relayBtn.textContent = 'Relay Message';
        }
    }
}

// === Slice 4: Approval Pre-fill ===

/**
 * Opens the builder pre-filled as an ACK approval for the given message.
 * Called from the Approve button in the detail toolbar.
 * @param {Object} refMsg - The message being approved
 */
function prefillApproval(refMsg) {
    // Show builder if hidden
    if (!builderVisible) toggleBuilder();

    // Build recipient list from original sender + recipients, deduped
    var recipients = [];
    if (refMsg.envelope.from) recipients.push(refMsg.envelope.from);
    if (refMsg.envelope.to) {
        refMsg.envelope.to.split(',').forEach(function(r) {
            var name = r.trim();
            if (name && recipients.indexOf(name) === -1) recipients.push(name);
        });
    }

    // Pre-fill as approval ACK
    setFieldValue('b-proto', 'AICP/1.0');
    setFieldValue('b-type', 'ACK');
    setFieldValue('b-id', generateNextMessageId());
    setFieldValue('b-from', 'Don');
    setFieldValue('b-to', recipients.join(', '));
    setFieldValue('b-time', nowISO());
    setFieldValue('b-task', 'Approve: ' + (refMsg.meta.task || refMsg.envelope.id));
    setFieldValue('b-status', 'COMPLETE');
    setFieldValue('b-priority', refMsg.meta.priority || '');
    setFieldValue('b-role', 'Orchestrator');
    setFieldValue('b-intent', 'Orchestrator authorization to proceed');
    setFieldValue('b-ref', refMsg.envelope.id);
    setFieldValue('b-seq', getNextSeq());
    setFieldValue('b-project', 'InterAI-Protocol');
    setFieldValue('b-domain', 'Multi-Agent Systems');
    setFieldValue('b-payload', 'APPROVED.\n\nProceeding as proposed.');

    updatePreview();
}

// --- Helper functions ---

function getFieldValue(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
}

function setFieldValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value || '';
}

/**
 * Creates the builder panel HTML and inserts it into the DOM.
 */
function initBuilder() {
    const body = document.querySelector('.app-body');
    if (!body) return;

    const panel = document.createElement('div');
    panel.id = 'builder-panel';
    panel.className = 'builder-panel';
    panel.style.display = 'none';

    panel.innerHTML = `
        <div class="builder-content">
            <div class="builder-form-section">
                <h3 class="section-title">Compose Message</h3>
                <form id="builder-form" onsubmit="return false;">
                    <div class="builder-row">
                        <div class="builder-field">
                            <label for="b-type">$TYPE</label>
                            <select id="b-type" onchange="updatePreview()">
                                <option value="REQUEST">REQUEST</option>
                                <option value="RESPONSE">RESPONSE</option>
                                <option value="ACK">ACK</option>
                                <option value="REVIEW">REVIEW</option>
                                <option value="ERROR">ERROR</option>
                                <option value="HANDOFF">HANDOFF</option>
                            </select>
                        </div>
                        <div class="builder-field">
                            <label for="b-status">$STATUS</label>
                            <select id="b-status" onchange="updatePreview()">
                                <option value="PENDING">PENDING</option>
                                <option value="IN_PROGRESS">IN_PROGRESS</option>
                                <option value="COMPLETE">COMPLETE</option>
                                <option value="FAILED">FAILED</option>
                            </select>
                        </div>
                        <div class="builder-field">
                            <label for="b-priority">$PRIORITY</label>
                            <select id="b-priority" onchange="updatePreview()">
                                <option value="">—</option>
                                <option value="LOW">LOW</option>
                                <option value="NORMAL">NORMAL</option>
                                <option value="HIGH">HIGH</option>
                            </select>
                        </div>
                    </div>
                    <div class="builder-row">
                        <div class="builder-field">
                            <label for="b-from">$FROM</label>
                            <input type="text" id="b-from" placeholder="Don" oninput="updatePreview()">
                        </div>
                        <div class="builder-field">
                            <label for="b-to">$TO</label>
                            <input type="text" id="b-to" placeholder="Pharos, Lodestar" oninput="updatePreview()">
                        </div>
                    </div>
                    <div class="builder-row">
                        <div class="builder-field full">
                            <label for="b-task">$TASK</label>
                            <input type="text" id="b-task" placeholder="Short task description" oninput="updatePreview()">
                        </div>
                    </div>
                    <div class="builder-row">
                        <div class="builder-field full">
                            <label for="b-intent">$INTENT</label>
                            <input type="text" id="b-intent" placeholder="Why this task matters (optional)" oninput="updatePreview()">
                        </div>
                    </div>
                    <div class="builder-row">
                        <div class="builder-field">
                            <label for="b-role">$ROLE</label>
                            <input type="text" id="b-role" placeholder="e.g., Orchestrator" oninput="updatePreview()">
                        </div>
                        <div class="builder-field">
                            <label for="b-ref">$REF</label>
                            <input type="text" id="b-ref" placeholder="e.g., MSG-0011" oninput="updatePreview()">
                        </div>
                    </div>
                    <div class="builder-row">
                        <div class="builder-field">
                            <label for="b-project">PROJECT</label>
                            <input type="text" id="b-project" value="InterAI-Protocol" oninput="updatePreview()">
                        </div>
                        <div class="builder-field">
                            <label for="b-domain">DOMAIN</label>
                            <input type="text" id="b-domain" value="Multi-Agent Systems" oninput="updatePreview()">
                        </div>
                    </div>
                    <div class="builder-row">
                        <div class="builder-field full">
                            <label for="b-payload">Payload</label>
                            <textarea id="b-payload" rows="8" placeholder="Message content (markdown)" oninput="updatePreview()"></textarea>
                        </div>
                    </div>
                    <!-- Hidden auto-filled fields -->
                    <input type="hidden" id="b-proto" value="AICP/1.0">
                    <input type="hidden" id="b-id">
                    <input type="hidden" id="b-time">
                    <input type="hidden" id="b-seq">
                </form>
                <div class="builder-actions">
                    <button id="relay-btn" class="btn btn-relay" onclick="relayMessage()">Relay Message</button>
                    <button id="copy-btn" class="btn btn-primary" onclick="copyPacket()">Copy Packet</button>
                    <button class="btn btn-secondary" onclick="addToViewer()">Add to Viewer</button>
                    <button class="btn btn-ghost" onclick="resetBuilder(); updatePreview();">Reset</button>
                    <div id="builder-validation" class="builder-valid">Valid</div>
                </div>
            </div>
            <div class="builder-preview-section">
                <h3 class="section-title">Live Preview</h3>
                <pre id="builder-preview-text" class="builder-preview-text"></pre>
            </div>
        </div>
    `;

    body.appendChild(panel);
}

// Initialize builder when DOM is ready
document.addEventListener('DOMContentLoaded', initBuilder);
