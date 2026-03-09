/**
 * AICP Message Parser
 * Parses raw AICP message text into normalized message objects.
 *
 * Protocol: AICP/1.0
 * Version: Slice 1 — Read, Render, and Build
 *
 * Format:
 *   $KEY: value        (keyword/value pairs — envelope, meta, audit)
 *   KEY: value         (custom fields — no $ prefix, may contain spaces/hyphens)
 *   ---PAYLOAD---      (payload delimiter start)
 *   <content>          (freeform markdown)
 *   ---END---          (payload delimiter end)
 *
 * Hardening (per LodeStar review MSG-0011):
 *   - Custom keys may contain spaces, hyphens, dots
 *   - Invalid $SEQ normalized to null with warning
 *   - Duplicate keys: last-write-wins with console warning
 *   - Timestamp validation: catch Invalid Date
 */

// Parser warnings collected during last parse
let _parseWarnings = [];

/**
 * Returns warnings from the most recent parseMessage() call.
 * @returns {string[]} Array of warning strings
 */
function getParseWarnings() {
    return [..._parseWarnings];
}

/**
 * Parses raw AICP message text into a normalized message object.
 * @param {string} rawText - The raw AICP message text
 * @returns {Object} Normalized message object (via createMessage)
 */
function parseMessage(rawText) {
    _parseWarnings = [];

    if (!rawText || typeof rawText !== 'string') {
        return createMessage({}, '', rawText);
    }

    const fields = {};

    // Split into lines
    const lines = rawText.split('\n');

    let inPayload = false;
    let payloadLines = [];

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
            continue;
        }

        // Collect payload lines
        if (inPayload) {
            payloadLines.push(line);
            continue;
        }

        // Parse keyword/value pairs (before and after payload)
        // Supports:
        //   $KEY: value           (system keywords)
        //   KEY: value            (simple custom)
        //   MULTI WORD KEY: value (custom with spaces)
        //   HYPHEN-KEY: value     (custom with hyphens)
        const kvMatch = trimmed.match(/^(\$?[A-Za-z][A-Za-z0-9_ .-]*?)\s*:\s*(.*)$/);
        if (kvMatch) {
            const key = kvMatch[1].trim();
            const value = kvMatch[2].trim();

            // Duplicate key detection: last-write-wins with warning
            if (fields.hasOwnProperty(key)) {
                _parseWarnings.push(`Duplicate key "${key}" — using last value`);
            }

            fields[key] = value;
        }
    }

    // Validate $SEQ: must be a positive integer or null
    if (fields['$SEQ'] !== undefined) {
        const seqVal = parseInt(fields['$SEQ'], 10);
        if (isNaN(seqVal) || seqVal < 0) {
            _parseWarnings.push(`Invalid $SEQ value "${fields['$SEQ']}" — normalized to null`);
            fields['$SEQ'] = null;
        }
    }

    // Validate $TIME: catch Invalid Date
    if (fields['$TIME']) {
        const d = new Date(fields['$TIME']);
        if (isNaN(d.getTime())) {
            _parseWarnings.push(`Invalid $TIME value "${fields['$TIME']}" — could not parse as date`);
        }
    }

    // Join payload lines, trim leading/trailing blank lines
    const payload = payloadLines.join('\n').replace(/^\n+|\n+$/g, '');

    const msg = createMessage(fields, payload, rawText);
    msg._parseWarnings = [..._parseWarnings];
    return msg;
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
    module.exports = { parseMessage, parseMultipleMessages, extractPreview, getParseWarnings };
}
