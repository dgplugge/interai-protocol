/**
 * AICP API Hub
 * A round-table dialog for orchestrated agent API discussions.
 *
 * Features:
 *   - Select participants and speaking protocol
 *   - Send one prompt to multiple agents over HTTPS (via server relay)
 *   - Render per-agent replies in a shared transcript pane
 */

let apiHubVisible = false;
let apiHubAgents = [
    { name: 'Pharos', platform: 'Claude (Anthropic)', enabled: false, endpointConfigured: false, selected: true },
    { name: 'Lodestar', platform: 'ChatGPT (OpenAI)', enabled: false, endpointConfigured: false, selected: true },
    { name: 'Forge', platform: 'Codex (OpenAI)', enabled: false, endpointConfigured: false, selected: true },
    { name: 'SpinDrift', platform: 'Cursor', enabled: false, endpointConfigured: false, selected: true }
];

function apiEscapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function apiHubNotify(message, type) {
    if (typeof showToast === 'function') {
        showToast(message, type || 'info');
    } else {
        console.log('[API HUB]', message);
    }
}

async function loadApiHubConfig() {
    try {
        const response = await fetch('/api/agent-hub/config');
        if (!response.ok) return;
        const data = await response.json();
        if (!data.ok || !Array.isArray(data.agents)) return;
        apiHubAgents = data.agents.map((agent) => ({
            name: agent.name,
            platform: agent.platform || '',
            enabled: !!agent.enabled,
            endpointConfigured: !!agent.endpointConfigured,
            selected: true
        }));
        renderApiHubAgents();
        renderApiTurnOrder();
    } catch (e) {
        // Offline/file mode fallback: keep defaults.
    }
}

function toggleApiHub() {
    apiHubVisible = !apiHubVisible;
    const panel = document.getElementById('api-hub-panel');
    const btn = document.getElementById('api-hub-toggle');
    if (panel) panel.style.display = apiHubVisible ? 'flex' : 'none';
    if (btn) {
        btn.textContent = apiHubVisible ? 'Close Hub' : 'API Hub';
        btn.classList.toggle('active', apiHubVisible);
    }
    if (apiHubVisible) {
        syncHubProjectDefaults();
        renderApiTurnOrder();
    }
}

function syncHubProjectDefaults() {
    let projectId = 'InterAI-Protocol';

    if (typeof activeProject !== 'undefined' && activeProject && activeProject !== 'all') {
        projectId = activeProject;
    } else if (typeof selectedIndex !== 'undefined' && selectedIndex >= 0 &&
               typeof allMessages !== 'undefined' && allMessages[selectedIndex] && allMessages[selectedIndex]._projectId) {
        projectId = allMessages[selectedIndex]._projectId;
    }

    const projectEl = document.getElementById('hub-project');
    const domainEl = document.getElementById('hub-domain');
    if (projectEl) projectEl.value = projectId;

    let domain = 'Multi-Agent Systems';
    if (typeof getDomainForProject === 'function') {
        domain = getDomainForProject(projectId) || domain;
    }
    if (domainEl) domainEl.value = domain;
}

function renderApiHubAgents() {
    const grid = document.getElementById('hub-agent-grid');
    if (!grid) return;
    grid.innerHTML = '';

    apiHubAgents.forEach((agent) => {
        const chip = document.createElement('label');
        chip.className = 'api-agent-chip';
        chip.innerHTML = `
            <input type="checkbox" name="hub-agent" value="${apiEscapeHtml(agent.name)}" ${agent.selected ? 'checked' : ''} onchange="renderApiTurnOrder()">
            <span>${apiEscapeHtml(agent.name)}</span>
            <span class="api-hub-delivery ${agent.enabled && agent.endpointConfigured ? 'success' : ''}">
                ${agent.enabled && agent.endpointConfigured ? 'https' : 'mock'}
            </span>
        `;
        chip.title = `${agent.platform || 'Agent'}${agent.endpointConfigured ? ' • endpoint configured' : ' • endpoint not configured'}`;
        grid.appendChild(chip);
    });
}

function getSelectedHubAgents() {
    const nodes = document.querySelectorAll('input[name="hub-agent"]:checked');
    return Array.from(nodes).map(n => n.value.trim()).filter(Boolean);
}

function getTurnOrder() {
    const selected = getSelectedHubAgents();
    const modeEl = document.getElementById('hub-turn-mode');
    const starterEl = document.getElementById('hub-starter');

    const mode = modeEl ? modeEl.value : 'round_robin';
    const starter = starterEl ? starterEl.value.trim() : '';
    if (selected.length === 0) return [];

    if (mode === 'alphabetical') {
        return selected.slice().sort((a, b) => a.localeCompare(b));
    }

    let first = starter;
    if (!first || selected.indexOf(first) === -1) first = selected[0];

    // round_robin and priority_first both place starter first in this version.
    const rest = selected.filter(name => name !== first);
    return [first].concat(rest);
}

function renderApiTurnOrder() {
    const container = document.getElementById('hub-turn-order');
    if (!container) return;
    const order = getTurnOrder();
    container.innerHTML = '';
    if (order.length === 0) {
        container.innerHTML = '<span class="api-turn-pill">Select at least one agent</span>';
        return;
    }

    order.forEach((name, i) => {
        const el = document.createElement('span');
        el.className = 'api-turn-pill';
        el.textContent = `${i + 1}. ${name}`;
        container.appendChild(el);
    });
}

function clearApiHubTranscript() {
    const transcript = document.getElementById('hub-transcript');
    if (!transcript) return;
    transcript.innerHTML = '<div class="empty-state">No round-table activity yet.</div>';
}

function appendApiHubMessage(entry) {
    const transcript = document.getElementById('hub-transcript');
    if (!transcript) return;

    const empty = transcript.querySelector('.empty-state');
    if (empty) transcript.removeChild(empty);

    const node = document.createElement('div');
    node.className = 'api-hub-message';
    const deliveryClass = entry.ok ? 'success' : 'error';
    node.innerHTML = `
        <div class="api-hub-message-header">
            <span class="api-hub-agent">${apiEscapeHtml(entry.agent)}</span>
            <span class="api-hub-round">Round ${entry.round}</span>
            <span class="api-hub-delivery ${deliveryClass}">${apiEscapeHtml(entry.delivery || (entry.ok ? 'ok' : 'error'))}</span>
        </div>
        <div class="api-hub-body">${apiEscapeHtml(entry.reply || entry.error || '(no response content)')}</div>
    `;
    transcript.appendChild(node);
    transcript.scrollTop = transcript.scrollHeight;
}

function buildHubPayload() {
    const promptEl = document.getElementById('hub-prompt');
    const taskEl = document.getElementById('hub-task');
    const fromEl = document.getElementById('hub-from');
    const projectEl = document.getElementById('hub-project');
    const domainEl = document.getElementById('hub-domain');
    const turnModeEl = document.getElementById('hub-turn-mode');

    return {
        proto: 'AICP/1.0',
        type: 'REQUEST',
        from: fromEl ? fromEl.value.trim() : 'Don',
        task: taskEl ? taskEl.value.trim() : 'Round-table API discussion',
        project: projectEl ? projectEl.value.trim() : 'InterAI-Protocol',
        domain: domainEl ? domainEl.value.trim() : 'Multi-Agent Systems',
        prompt: promptEl ? promptEl.value.trim() : '',
        agents: getSelectedHubAgents(),
        turnMode: turnModeEl ? turnModeEl.value : 'round_robin',
        turnOrder: getTurnOrder(),
        contextRef: (typeof selectedIndex !== 'undefined' && selectedIndex >= 0 && allMessages[selectedIndex])
            ? allMessages[selectedIndex].envelope.id
            : null
    };
}

async function runApiRoundTable() {
    const payload = buildHubPayload();
    const statusEl = document.getElementById('hub-status');
    const sendBtn = document.getElementById('hub-send-btn');

    if (!payload.prompt) {
        apiHubNotify('Enter a prompt before sending to agents.', 'error');
        return;
    }
    if (!payload.agents.length) {
        apiHubNotify('Select at least one agent for the round table.', 'error');
        return;
    }

    if (statusEl) statusEl.textContent = 'Sending...';
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';
    }

    try {
        appendApiHubMessage({
            agent: payload.from || 'Orchestrator',
            round: 0,
            ok: true,
            delivery: 'prompt',
            reply: payload.prompt
        });

        const response = await fetch('/api/agent-hub/roundtable', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (!result.ok) {
            throw new Error(result.error || 'Round-table request failed');
        }

        (result.replies || []).forEach((entry) => appendApiHubMessage(entry));

        if (statusEl) {
            statusEl.textContent = `Completed ${result.replies ? result.replies.length : 0} turn(s)`;
        }
        apiHubNotify('API hub round table complete.', 'success');
    } catch (e) {
        if (statusEl) statusEl.textContent = 'Error';
        appendApiHubMessage({
            agent: 'System',
            round: 0,
            ok: false,
            delivery: 'error',
            error: e.message
        });
        apiHubNotify(`API hub error: ${e.message}`, 'error');
    } finally {
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = 'Send Round Table';
        }
    }
}

async function copyHubTranscript() {
    const transcript = document.getElementById('hub-transcript');
    if (!transcript) return;
    const text = transcript.innerText || '';
    try {
        await navigator.clipboard.writeText(text.trim());
        apiHubNotify('Round-table transcript copied.', 'success');
    } catch (e) {
        apiHubNotify('Could not copy transcript.', 'error');
    }
}

function initApiHub() {
    const panel = document.createElement('div');
    panel.id = 'api-hub-panel';
    panel.className = 'api-hub-panel';
    panel.style.display = 'none';

    panel.innerHTML = `
        <div class="api-hub-content">
            <div class="api-hub-config">
                <h3 class="section-title">API Hub Round Table</h3>
                <div class="api-hub-protocol-banner">
                    Round-table protocol: orchestrator posts one prompt, agents reply in speaking order,
                    and all responses are captured in one dialog stream.
                </div>

                <div class="api-hub-row">
                    <div class="api-hub-field">
                        <label for="hub-from">Orchestrator</label>
                        <input type="text" id="hub-from" value="Don">
                    </div>
                    <div class="api-hub-field">
                        <label for="hub-task">Task</label>
                        <input type="text" id="hub-task" value="Communicate with AI Agents via API">
                    </div>
                </div>

                <div class="api-hub-row">
                    <div class="api-hub-field">
                        <label for="hub-project">Project</label>
                        <input type="text" id="hub-project" value="InterAI-Protocol">
                    </div>
                    <div class="api-hub-field">
                        <label for="hub-domain">Domain</label>
                        <input type="text" id="hub-domain" value="Multi-Agent Systems">
                    </div>
                </div>

                <div class="api-hub-row">
                    <div class="api-hub-field">
                        <label for="hub-turn-mode">Speaking Protocol</label>
                        <select id="hub-turn-mode" onchange="renderApiTurnOrder()">
                            <option value="round_robin">Round robin</option>
                            <option value="priority_first">Priority first</option>
                            <option value="alphabetical">Alphabetical</option>
                        </select>
                    </div>
                    <div class="api-hub-field">
                        <label for="hub-starter">First speaker</label>
                        <input type="text" id="hub-starter" value="Pharos" oninput="renderApiTurnOrder()">
                    </div>
                </div>

                <div class="api-hub-row">
                    <div class="api-hub-field full">
                        <label>Participants</label>
                        <div id="hub-agent-grid" class="api-agent-grid"></div>
                        <div id="hub-turn-order" class="api-turn-order"></div>
                    </div>
                </div>

                <div class="api-hub-row">
                    <div class="api-hub-field full">
                        <label for="hub-prompt">Prompt</label>
                        <textarea id="hub-prompt" placeholder="Type the orchestrator prompt for all selected agents..."></textarea>
                    </div>
                </div>

                <div class="api-hub-actions">
                    <button id="hub-send-btn" class="btn btn-api-send" onclick="runApiRoundTable()">Send Round Table</button>
                    <button class="btn btn-secondary" onclick="copyHubTranscript()">Copy Transcript</button>
                    <button class="btn btn-ghost" onclick="clearApiHubTranscript()">Clear Stream</button>
                    <button class="btn btn-cancel" onclick="toggleApiHub()">Close</button>
                    <div id="hub-status" class="api-hub-status">Idle</div>
                </div>
            </div>
            <div class="api-hub-stream">
                <h3 class="section-title">Round-table Dialog</h3>
                <div id="hub-transcript" class="api-hub-transcript">
                    <div class="empty-state">No round-table activity yet.</div>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(panel);
    renderApiHubAgents();
    renderApiTurnOrder();
    loadApiHubConfig();
}

document.addEventListener('DOMContentLoaded', initApiHub);
