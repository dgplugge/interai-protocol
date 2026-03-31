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
    var projDefaults = getActiveProjectDefaults();
    setFieldValue('b-id', generateNextMessageId(projDefaults.project));
    setFieldValue('b-from', 'Don');
    setFieldValue('b-to', 'SpinDrift, Lodestar');
    setFieldValue('b-time', nowISO());
    setFieldValue('b-task', '');
    setFieldValue('b-status', 'PENDING');
    setFieldValue('b-priority', '');
    setFieldValue('b-role', 'Orchestrator');
    setFieldValue('b-intent', '');
    setFieldValue('b-ref', getLastMessageId() || '');
    setFieldValue('b-seq', getNextSeq());
    // Set project/domain from active project via registry dropdown
    if (projectRegistryLoaded && projectRegistry.length > 0) {
        populateProjectDropdown('b-project-select', projDefaults.project);
    }
    setFieldValue('b-project', projDefaults.project);
    setFieldValue('b-domain', projDefaults.domain);
    var domainEl = document.getElementById('b-domain');
    if (domainEl) domainEl.readOnly = true;
    // Hide new project form on reset
    var npForm = document.getElementById('new-project-form');
    if (npForm) npForm.style.display = 'none';
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

// === Slice 7: Relay to n8n ===

/**
 * Relays the composed message to the server for local storage + n8n forwarding.
 * POSTs raw AICP text to /api/relay-to-n8n, which saves the .md file,
 * updates journal-index.json, and forwards to the configured n8n webhook.
 *
 * Toast shows combined result:
 *   "Saved locally + Sent to n8n"  (success)
 *   "Saved locally, n8n delivery failed" (partial)
 *   or error details
 */
async function relayToN8n() {
    var msg = buildMessageFromForm();
    var validation = validateMessage(msg);

    if (!validation.valid) {
        showToast('Cannot relay: ' + validation.errors.join('; '), 'error');
        return;
    }

    var text = serializeMessage(msg);
    var btn = document.getElementById('relay-n8n-btn');

    // Disable button during relay
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Sending...';
    }

    try {
        var response = await fetch('/api/relay-to-n8n', {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: text
        });

        var result = await response.json();

        if (result.ok) {
            // Show delivery-specific toast
            if (result.delivery === 'n8n_sent') {
                showToast('Saved locally + Sent to n8n (' + result.id + ')', 'success');
            } else if (result.delivery === 'n8n_failed') {
                showToast('Saved locally, n8n failed: ' + (result.n8nError || 'unknown'), 'error', 6000);
            } else {
                // local_saved only (n8n disabled or no URL)
                showToast(result.message + ' (' + result.id + ')', 'info');
            }
            // Refresh viewer to show new message
            await refreshMessages();
            // Close builder
            toggleBuilder();
        } else {
            showToast('Relay failed: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        showToast('Relay-to-n8n error: ' + e.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Relay to n8n';
        }
    }
}

/**
 * Checks n8n integration status and updates the Relay to n8n button visibility.
 * Called on page load to show/hide the button based on configuration.
 */
async function checkN8nStatus() {
    try {
        var response = await fetch('/api/integrations');
        var result = await response.json();
        var btn = document.getElementById('relay-n8n-btn');
        if (btn && result.ok) {
            var n8n = result.integrations && result.integrations.n8n;
            if (n8n && n8n.enabled && n8n.configured) {
                btn.classList.add('n8n-active');
                btn.title = 'n8n webhook configured and enabled';
            } else if (n8n && n8n.enabled) {
                btn.title = 'n8n enabled but no webhook URL configured';
            } else {
                btn.title = 'n8n integration disabled — edit n8n-config.json to enable';
            }
        }
    } catch (e) {
        // Silent — button stays in default state
    }
}

// Check n8n status when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Delay slightly to let builder init first
    setTimeout(checkN8nStatus, 500);
});

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
    var approveDefaults = getActiveProjectDefaults(refMsg);
    setFieldValue('b-proto', 'AICP/1.0');
    setFieldValue('b-type', 'ACK');
    setFieldValue('b-id', generateNextMessageId(approveDefaults.project));
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
    setFieldValue('b-project', approveDefaults.project);
    setFieldValue('b-domain', approveDefaults.domain);
    syncProjectDropdown(approveDefaults.project);
    setFieldValue('b-payload', 'APPROVED.\n\nProceeding as proposed.');

    updatePreview();
}

/**
 * Opens the builder pre-filled as a review request.
 * Typically used to ask Lodestar to review an implementation.
 * @param {Object} refMsg - The message to request review of
 */
function prefillRequestReview(refMsg) {
    if (!builderVisible) toggleBuilder();

    var reviewDefaults = getActiveProjectDefaults(refMsg);
    setFieldValue('b-proto', 'AICP/1.0');
    setFieldValue('b-type', 'REQUEST');
    setFieldValue('b-id', generateNextMessageId(reviewDefaults.project));
    setFieldValue('b-from', 'Don');
    setFieldValue('b-to', 'Lodestar');
    setFieldValue('b-time', nowISO());
    setFieldValue('b-task', 'Review: ' + (refMsg.meta.task || refMsg.envelope.id));
    setFieldValue('b-status', 'PENDING');
    setFieldValue('b-priority', refMsg.meta.priority || 'HIGH');
    setFieldValue('b-role', 'Orchestrator');
    setFieldValue('b-intent', 'Request design/implementation review from Lodestar');
    setFieldValue('b-ref', refMsg.envelope.id);
    setFieldValue('b-seq', getNextSeq());
    setFieldValue('b-project', reviewDefaults.project);
    setFieldValue('b-domain', reviewDefaults.domain);
    syncProjectDropdown(reviewDefaults.project);
    setFieldValue('b-payload', 'Please review the referenced message and provide feedback.\n\nAreas of interest:\n- Correctness\n- Design alignment\n- Suggestions for improvement');

    updatePreview();
}

/**
 * Opens the builder pre-filled as a quick ACK.
 * @param {Object} refMsg - The message to acknowledge
 */
function prefillAck(refMsg) {
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

    var ackDefaults = getActiveProjectDefaults(refMsg);
    setFieldValue('b-proto', 'AICP/1.0');
    setFieldValue('b-type', 'ACK');
    setFieldValue('b-id', generateNextMessageId(ackDefaults.project));
    setFieldValue('b-from', 'Don');
    setFieldValue('b-to', recipients.join(', '));
    setFieldValue('b-time', nowISO());
    setFieldValue('b-task', 'Acknowledge: ' + (refMsg.meta.task || refMsg.envelope.id));
    setFieldValue('b-status', 'COMPLETE');
    setFieldValue('b-priority', '');
    setFieldValue('b-role', 'Orchestrator');
    setFieldValue('b-intent', 'Acknowledge receipt and understanding');
    setFieldValue('b-ref', refMsg.envelope.id);
    setFieldValue('b-seq', getNextSeq());
    setFieldValue('b-project', ackDefaults.project);
    setFieldValue('b-domain', ackDefaults.domain);
    syncProjectDropdown(ackDefaults.project);
    setFieldValue('b-payload', 'Acknowledged.');

    updatePreview();
}

/**
 * Returns default PROJECT and DOMAIN values based on the active project.
 * If a reference message is provided, uses that message's project.
 * @param {Object} [refMsg] - Optional reference message
 * @returns {Object} { project: string, domain: string }
 */
function getActiveProjectDefaults(refMsg) {
    // If a reference message has a project, use that
    if (refMsg && refMsg._projectId) {
        var proj = refMsg._projectId;
        var domain = (refMsg.custom && refMsg.custom['DOMAIN']) || getDomainForProject(proj);
        return { project: proj, domain: domain };
    }
    // If a reference message has PROJECT in custom fields, use that
    if (refMsg && refMsg.custom && refMsg.custom['PROJECT']) {
        var proj2 = refMsg.custom['PROJECT'];
        var domain2 = refMsg.custom['DOMAIN'] || getDomainForProject(proj2);
        return { project: proj2, domain: domain2 };
    }
    // Use active project if it's specific (not "all")
    if (typeof activeProject !== 'undefined' && activeProject && activeProject !== 'all') {
        return { project: activeProject, domain: getDomainForProject(activeProject) };
    }
    // Fallback: if viewing all and a message is selected, use its project
    if (typeof selectedIndex !== 'undefined' && selectedIndex >= 0 &&
        typeof allMessages !== 'undefined' && allMessages[selectedIndex]) {
        var selMsg = allMessages[selectedIndex];
        if (selMsg._projectId) {
            return { project: selMsg._projectId, domain: (selMsg.custom && selMsg.custom['DOMAIN']) || getDomainForProject(selMsg._projectId) };
        }
    }
    return { project: 'InterAI-Protocol', domain: 'Multi-Agent Systems' };
}

/**
 * Returns a default DOMAIN value for a project ID.
 * Uses the project registry if loaded, with hardcoded fallback.
 * @param {string} projectId
 * @returns {string}
 */
function getDomainForProject(projectId) {
    // Use registry if available
    if (typeof getRegistryDomain === 'function') {
        var domain = getRegistryDomain(projectId);
        if (domain) return domain;
    }
    // Hardcoded fallback for backward compatibility
    var fallback = {
        'InterAI-Protocol': 'Multi-Agent Systems',
        'OperatorHub': 'Flow Cytometry Lab Operations'
    };
    return fallback[projectId] || '';
}

/**
 * Handles project dropdown selection change in the Builder.
 * Auto-fills DOMAIN and shows/hides the new project form.
 */
function onBuilderProjectChange() {
    var select = document.getElementById('b-project-select');
    if (!select) return;

    var val = select.value;
    var newForm = document.getElementById('new-project-form');
    var domainEl = document.getElementById('b-domain');

    if (val === '__new__') {
        // Show new project creation form
        if (newForm) newForm.style.display = 'block';
        setFieldValue('b-project', '');
        if (domainEl) {
            domainEl.value = '';
            domainEl.readOnly = false;
        }
        return;
    }

    // Hide new project form
    if (newForm) newForm.style.display = 'none';

    // Set hidden project field and auto-fill domain
    setFieldValue('b-project', val);
    var domain = getDomainForProject(val);
    setFieldValue('b-domain', domain);
    if (domainEl) domainEl.readOnly = true;

    updatePreview();
}

/**
 * Creates a new project from the inline form and adds it to the registry.
 */
async function createNewProject() {
    var name = getFieldValue('np-name');
    var domain = getFieldValue('np-domain');
    var description = getFieldValue('np-description');
    var agentsStr = getFieldValue('np-agents');

    if (!name || !domain) {
        showToast('Project name and domain are required', 'error');
        return;
    }

    var agents = agentsStr ? agentsStr.split(',').map(function(a) { return a.trim(); }).filter(Boolean) : [];

    var project = {
        projectName: name,
        domain: domain,
        description: description,
        defaultAgents: agents
    };

    var result = await saveRegistryProject(project);

    if (result.ok) {
        showToast('Created project: ' + name, 'success');

        // Repopulate dropdown and select the new project
        populateProjectDropdown('b-project-select', project.projectId);
        onBuilderProjectChange();

        // Clear and hide the form
        cancelNewProject();
    } else {
        showToast('Failed: ' + result.error, 'error');
    }
}

/**
 * Cancels new project creation and resets the dropdown.
 */
function cancelNewProject() {
    var newForm = document.getElementById('new-project-form');
    if (newForm) newForm.style.display = 'none';

    // Clear form fields
    setFieldValue('np-name', '');
    setFieldValue('np-domain', '');
    setFieldValue('np-description', '');
    setFieldValue('np-agents', '');

    // Reset dropdown to first project
    var select = document.getElementById('b-project-select');
    if (select && select.options.length > 0 && select.value === '__new__') {
        select.value = projectRegistry.length > 0 ? projectRegistry[0].projectId : '';
        onBuilderProjectChange();
    }

    var domainEl = document.getElementById('b-domain');
    if (domainEl) domainEl.readOnly = true;
}

// --- Helper functions ---

/**
 * Syncs the project dropdown to match a given project ID.
 * If the ID isn't in the registry, keeps the hidden field value as-is (backward compat).
 * @param {string} projectId
 */
function syncProjectDropdown(projectId) {
    var select = document.getElementById('b-project-select');
    if (!select) return;
    // Check if the value exists in the dropdown
    for (var i = 0; i < select.options.length; i++) {
        if (select.options[i].value === projectId) {
            select.value = projectId;
            return;
        }
    }
    // Not in dropdown — leave it; the hidden b-project field has the correct value
}

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
                                <option value="MEDIUM">MEDIUM</option>
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
                            <input type="text" id="b-to" placeholder="SpinDrift, Lodestar" oninput="updatePreview()">
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
                            <label for="b-project-select">PROJECT</label>
                            <select id="b-project-select" onchange="onBuilderProjectChange()"></select>
                            <input type="hidden" id="b-project">
                        </div>
                        <div class="builder-field">
                            <label for="b-domain">DOMAIN</label>
                            <input type="text" id="b-domain" value="" readonly oninput="updatePreview()">
                        </div>
                    </div>
                    <div id="new-project-form" class="builder-new-project" style="display:none;">
                        <div class="builder-row">
                            <div class="builder-field">
                                <label for="np-name">Project Name</label>
                                <input type="text" id="np-name" placeholder="e.g., Study Guide">
                            </div>
                            <div class="builder-field">
                                <label for="np-domain">Domain</label>
                                <input type="text" id="np-domain" placeholder="e.g., AI-Assisted Learning">
                            </div>
                        </div>
                        <div class="builder-row">
                            <div class="builder-field full">
                                <label for="np-description">Description</label>
                                <input type="text" id="np-description" placeholder="Short project description">
                            </div>
                        </div>
                        <div class="builder-row">
                            <div class="builder-field">
                                <label for="np-agents">Default Agents</label>
                                <input type="text" id="np-agents" placeholder="SpinDrift, Lodestar">
                            </div>
                            <div class="builder-field" style="display:flex;align-items:flex-end;gap:6px;">
                                <button type="button" class="btn btn-primary btn-sm" onclick="createNewProject()">Create</button>
                                <button type="button" class="btn btn-ghost btn-sm" onclick="cancelNewProject()">Cancel</button>
                            </div>
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
                    <button id="relay-n8n-btn" class="btn btn-relay-n8n" onclick="relayToN8n()">Relay to n8n</button>
                    <button id="copy-btn" class="btn btn-primary" onclick="copyPacket()">Copy Packet</button>
                    <button class="btn btn-secondary" onclick="addToViewer()">Add to Viewer</button>
                    <button class="btn btn-ghost" onclick="resetBuilder(); updatePreview();">Reset</button>
                    <button class="btn btn-cancel" onclick="toggleBuilder()">Cancel</button>
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
