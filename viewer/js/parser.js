/**
 * AICP Message Parser
 * Parses raw AICP message text into normalized message objects.
 *
 * Protocol: AICP/1.0
 * Version: Slice 0 — Read and Render
 *
 * Format:
 *   $KEY: value        (keyword/value pairs — envelope, meta, audit)
 *   KEY: value         (custom fields — no $ prefix)
 *   ---PAYLOAD---      (payload delimiter start)
 *   <content>          (freeform markdown)
 *   ---END---          (payload delimiter end)
 */

/**
 * Parses raw AICP message text into a normalized message object.
 * @param {string} rawText - The raw AICP message text
 * @returns {Object} Normalized message object (via createMessage)
 */
function parseMessage(rawText) {
    if (!rawText || typeof rawText !== 'string') {
        return createMessage({}, '', rawText);
    }

    const fields = {};
    let payload = '';

    // Split into lines
    const lines = rawText.split('\n');

    let inPayload = false;
    let payloadLines = [];
    let pastPayload = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        // Detect payload boundaries
        if (trimmed === '---PAYLOAD---') {
            inPayload = true;
            continue;
        }
        if (trimmed === '---END---') {
            inPayload = false;
            pastPayload = true;
            continue;
        }

        // Collect payload lines
        if (inPayload) {
            payloadLines.push(line);
            continue;
        }

        // Parse keyword/value pairs (before and after payload)
        // Match lines like "$KEY: value" or "KEY: value"
        const kvMatch = trimmed.match(/^(\$?[A-Z_][A-Z0-9_]*)\s*:\s*(.*)$/);
        if (kvMatch) {
            const key = kvMatch[1];
            const value = kvMatch[2].trim();
            fields[key] = value;
        }
    }

    // Join payload lines, trim leading/trailing blank lines
    payload = payloadLines.join('\n').replace(/^\n+|\n+$/g, '');

    return createMessage(fields, payload, rawText);
}

/**
 * Parses multiple AICP messages from a single text block.
 * Messages are separated by lines starting with $PROTO.
 * @param {string} text - Text potentially containing multiple messages
 * @returns {Object[]} Array of normalized message objects
 */
function parseMultipleMessages(text) {
    if (!text || typeof text !== 'string') return [];

    // Split on lines that start with $PROTO (keeping the delimiter)
    const chunks = text.split(/(?=^\$PROTO\s*:)/m).filter(c => c.trim());

    return chunks.map(chunk => parseMessage(chunk));
}

/**
 * Extracts just the envelope fields from raw text without full parsing.
 * Useful for quick previews in message lists.
 * @param {string} rawText - The raw AICP message text
 * @returns {Object} Partial envelope: { id, type, from, to, time, task }
 */
function extractPreview(rawText) {
    if (!rawText) return {};

    const extract = (key) => {
        const match = rawText.match(new RegExp(`^\\${key}\\s*:\\s*(.*)$`, 'm'));
        return match ? match[1].trim() : '';
    };

    return {
        id:   extract('$ID'),
        type: extract('$TYPE'),
        from: extract('$FROM'),
        to:   extract('$TO'),
        time: extract('$TIME'),
        task: extract('$TASK')
    };
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { parseMessage, parseMultipleMessages, extractPreview };
}
