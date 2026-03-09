/**
 * AICP Agent Registry Panel
 * Displays team members, roles, capabilities, and status.
 *
 * Protocol: AICP/1.0
 * Version: Slice 3 — Agent Registry
 *
 * Features:
 *   - Loads agent-registry.json from samples/
 *   - Renders agent cards with name, type, roles, status, capabilities
 *   - Toggleable side panel via "Agents" button in header
 */

let agentPanelVisible = false;
let registryData = null;

/**
 * Loads the agent registry from the server.
 * @returns {Promise<Object|null>} Registry data or null on error
 */
async function loadRegistry() {
    try {
        const response = await fetch('samples/agent-registry.json');
        if (!response.ok) {
            console.warn('Could not load agent registry:', response.status);
            return null;
        }
        registryData = await response.json();
        return registryData;
    } catch (e) {
        console.warn('Error loading agent registry:', e);
        return null;
    }
}

/**
 * Renders the agent panel HTML with all agents.
 */
function renderAgentPanel() {
    const panel = document.getElementById('agent-panel');
    if (!panel || !registryData || !registryData.agents) return;

    const body = panel.querySelector('.agent-panel-body');
    if (!body) return;

    let html = '';

    registryData.agents.forEach(function(agent) {
        html += '<div class="agent-card">';

        // Header: name + type badge + platform
        html += '<div class="agent-card-header">';
        html += '<span class="agent-name">' + escapeHtml(agent.name) + '</span>';
        html += '<span class="agent-type-badge type-' + agent.type + '">' + agent.type + '</span>';
        if (agent.platform) {
            html += '<span class="agent-platform">' + escapeHtml(agent.platform) + '</span>';
        }
        html += '</div>';

        // Status
        html += '<div class="agent-status">';
        html += '<span class="status-dot status-' + agent.status + '"></span>';
        html += '<span class="status-label">' + agent.status + '</span>';
        html += '</div>';

        // Roles
        if (agent.roles && agent.roles.length > 0) {
            html += '<div class="agent-roles">';
            agent.roles.forEach(function(role) {
                html += '<span class="role-tag">' + escapeHtml(role) + '</span>';
            });
            html += '</div>';
        }

        // Capabilities
        if (agent.capabilities && agent.capabilities.length > 0) {
            html += '<div class="agent-capabilities">';
            agent.capabilities.forEach(function(cap) {
                html += '<span class="capability-pill">' + escapeHtml(cap) + '</span>';
            });
            html += '</div>';
        }

        html += '</div>'; // .agent-card
    });

    body.innerHTML = html;
}

/**
 * Toggles the agent panel visibility.
 */
function toggleAgentPanel() {
    agentPanelVisible = !agentPanelVisible;
    const panel = document.getElementById('agent-panel');
    const btn = document.getElementById('agents-toggle');

    if (panel) {
        if (agentPanelVisible) {
            panel.classList.add('visible');
            // Load and render if not yet loaded
            if (!registryData) {
                loadRegistry().then(function() {
                    renderAgentPanel();
                });
            }
        } else {
            panel.classList.remove('visible');
        }
    }

    if (btn) {
        btn.classList.toggle('active', agentPanelVisible);
    }
}

/**
 * Creates the agent panel DOM and inserts it into the page.
 */
function initAgentPanel() {
    // Create the panel element
    const panel = document.createElement('div');
    panel.id = 'agent-panel';
    panel.className = 'agent-panel';

    panel.innerHTML =
        '<div class="agent-panel-header">' +
            '<h3>Agent Registry</h3>' +
            '<button class="agent-panel-close" onclick="toggleAgentPanel()" title="Close">&times;</button>' +
        '</div>' +
        '<div class="agent-panel-body">' +
            '<div class="empty-state">Loading agents...</div>' +
        '</div>';

    document.body.appendChild(panel);
}

// Initialize agent panel when DOM is ready
document.addEventListener('DOMContentLoaded', initAgentPanel);
