/**
 * AICP Message Loader
 * Loads AICP messages from journal-index.json and/or .md files.
 *
 * Protocol: AICP/1.0
 * Version: Slice 8 — Multi-Project Support
 *
 * Supports loading modes:
 *   1. Multi-project: Load from /api/projects, then each project's index
 *   2. Index-based: Read journal-index.json, fetch each .md file
 *   3. Standalone: Parse messages embedded directly in the page
 *
 * For local file:// usage, messages can be embedded in the HTML
 * since fetch() may be blocked by CORS on file:// protocol.
 */

/**
 * Fetches the list of configured projects from the server.
 * @returns {Promise<Object[]>} Array of project objects {id, name, color, messageCount}
 */
async function loadAllProjects() {
    try {
        const response = await fetch('/api/projects');
        if (!response.ok) {
            throw new Error(`Failed to load projects: ${response.status}`);
        }
        const result = await response.json();
        if (result.ok && result.projects) {
            console.log(`Loaded ${result.projects.length} project(s)`);
            return result.projects;
        }
        return [];
    } catch (e) {
        console.warn('Could not load projects from API, falling back to legacy mode:', e);
        return [];
    }
}

/**
 * Loads messages for a specific project via the multi-project API.
 * @param {string} projectId - The project ID
 * @returns {Promise<Object[]>} Array of normalized message objects with _projectId
 */
async function loadProjectMessages(projectId) {
    try {
        // Fetch the project's journal index
        const indexUrl = `/api/project/${encodeURIComponent(projectId)}/index`;
        const response = await fetch(indexUrl);
        if (!response.ok) {
            throw new Error(`Failed to load index for ${projectId}: ${response.status}`);
        }
        const index = await response.json();

        if (!index.messages || !Array.isArray(index.messages)) {
            console.warn(`No messages array in index for project: ${projectId}`);
            return [];
        }

        // Fetch each message file
        const messages = [];
        for (const entry of index.messages) {
            try {
                // Skip entries without a file reference (e.g., historical notes)
                if (!entry.file) {
                    continue;
                }
                const fileUrl = `/api/project/${encodeURIComponent(projectId)}/messages/${encodeURIComponent(entry.file.replace('messages/', ''))}`;
                const fileResponse = await fetch(fileUrl);
                if (fileResponse.ok) {
                    const rawText = await fileResponse.text();
                    const msg = parseMessage(rawText);
                    msg._projectId = projectId;
                    messages.push(msg);
                } else {
                    console.warn(`Could not load message file: ${entry.file} for project ${projectId}`);
                }
            } catch (e) {
                console.warn(`Error loading ${entry.file}:`, e);
            }
        }

        return messages;
    } catch (e) {
        console.error(`Error loading messages for project ${projectId}:`, e);
        return [];
    }
}

/**
 * Loads messages from journal-index.json and fetches each .md file.
 * Works when served via HTTP (python -m http.server).
 * @param {string} indexPath - Path to journal-index.json
 * @returns {Promise<Object[]>} Array of normalized message objects
 */
async function loadFromIndex(indexPath) {
    try {
        const response = await fetch(indexPath);
        if (!response.ok) {
            throw new Error(`Failed to load index: ${response.status}`);
        }
        const index = await response.json();

        if (!index.messages || !Array.isArray(index.messages)) {
            throw new Error('Invalid index: missing messages array');
        }

        // Determine base path from index path
        const basePath = indexPath.substring(0, indexPath.lastIndexOf('/') + 1);

        // Fetch each message file
        const messages = [];
        for (const entry of index.messages) {
            try {
                const filePath = basePath + entry.file;
                const fileResponse = await fetch(filePath);
                if (fileResponse.ok) {
                    const rawText = await fileResponse.text();
                    const msg = parseMessage(rawText);
                    messages.push(msg);
                } else {
                    console.warn(`Could not load message file: ${entry.file}`);
                }
            } catch (e) {
                console.warn(`Error loading ${entry.file}:`, e);
            }
        }

        return messages;
    } catch (e) {
        console.error('Error loading from index:', e);
        return [];
    }
}

/**
 * Loads messages from embedded <script type="text/aicp"> blocks in the HTML.
 * Works on file:// protocol without a server.
 * @returns {Object[]} Array of normalized message objects
 */
function loadFromEmbedded() {
    const blocks = document.querySelectorAll('script[type="text/aicp"]');
    const messages = [];

    blocks.forEach(block => {
        const rawText = block.textContent.trim();
        if (rawText) {
            const msg = parseMessage(rawText);
            messages.push(msg);
        }
    });

    return messages;
}

/**
 * Loads messages from a raw text string (e.g., pasted into a textarea).
 * @param {string} text - Raw text containing one or more AICP messages
 * @returns {Object[]} Array of normalized message objects
 */
function loadFromText(text) {
    return parseMultipleMessages(text);
}

/**
 * Auto-detect the best loading method and load messages.
 * Priority:
 *   1. Multi-project API (if server supports it)
 *   2. Legacy index-based loading (HTTP server)
 *   3. Embedded <script> blocks (file:// or offline)
 * @param {string} [indexPath] - Optional path to journal-index.json (legacy mode)
 * @param {string} [projectId] - Optional: load only this project ('all' or specific ID)
 * @returns {Promise<Object[]>} Array of normalized message objects
 */
async function autoLoad(indexPath, projectId) {
    // Try multi-project API first
    const projects = await loadAllProjects();

    if (projects.length > 0) {
        const allMsgs = [];

        if (projectId && projectId !== 'all') {
            // Load a single project
            const msgs = await loadProjectMessages(projectId);
            allMsgs.push(...msgs);
        } else {
            // Load all projects
            for (const proj of projects) {
                const msgs = await loadProjectMessages(proj.id);
                allMsgs.push(...msgs);
            }
        }

        if (allMsgs.length > 0) {
            console.log(`Loaded ${allMsgs.length} messages from ${projects.length} project(s)`);
            return allMsgs;
        }
    }

    // Fall back to legacy index-based loading
    if (indexPath) {
        const messages = await loadFromIndex(indexPath);
        if (messages.length > 0) {
            console.log(`Loaded ${messages.length} messages from index`);
            return messages;
        }
    }

    // Fall back to embedded blocks
    const embedded = loadFromEmbedded();
    if (embedded.length > 0) {
        console.log(`Loaded ${embedded.length} messages from embedded blocks`);
        return embedded;
    }

    console.warn('No messages found');
    return [];
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { loadFromIndex, loadFromEmbedded, loadFromText, autoLoad, loadAllProjects, loadProjectMessages };
}
