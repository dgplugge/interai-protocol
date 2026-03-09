/**
 * AICP Message Loader
 * Loads AICP messages from journal-index.json and/or .md files.
 *
 * Protocol: AICP/1.0
 * Version: Slice 0 — Read and Render
 *
 * Supports two loading modes:
 *   1. Index-based: Read journal-index.json, fetch each .md file
 *   2. Standalone: Parse messages embedded directly in the page
 *
 * For local file:// usage, messages can be embedded in the HTML
 * since fetch() may be blocked by CORS on file:// protocol.
 */

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
 *   1. Try index-based loading (HTTP server)
 *   2. Fall back to embedded <script> blocks (file:// or offline)
 * @param {string} [indexPath] - Optional path to journal-index.json
 * @returns {Promise<Object[]>} Array of normalized message objects
 */
async function autoLoad(indexPath) {
    // Try index-based loading first
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
    module.exports = { loadFromIndex, loadFromEmbedded, loadFromText, autoLoad };
}
