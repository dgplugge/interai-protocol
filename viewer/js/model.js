/**
 * AICP Message Model
 * Defines the normalized message object shape and schema helpers
 * for the Inter-AI Communication Protocol.
 *
 * Protocol: AICP/1.0
 * Version: Slice 1 — Read, Render, and Build
 */

// Required envelope keywords (must be present in every message)
const REQUIRED_KEYWORDS = ['$PROTO', '$TYPE', '$ID', '$FROM', '$TO', '$TIME'];

// Valid message types
const MESSAGE_TYPES = ['REQUEST', 'RESPONSE', 'ACK', 'ERROR', 'HANDOFF', 'REVIEW'];

// Valid status values
const STATUS_VALUES = ['PENDING', 'IN_PROGRESS', 'COMPLETE', 'FAILED'];

// Valid priority values
const PRIORITY_VALUES = ['LOW', 'NORMAL', 'MEDIUM', 'HIGH'];

// Keyword classification: which segment each keyword belongs to
const ENVELOPE_KEYWORDS = ['$PROTO', '$TYPE', '$ID', '$FROM', '$TO', '$TIME'];
const META_KEYWORDS = ['$TASK', '$STATUS', '$REF', '$SEQ', '$PRIORITY', '$CONTEXT', '$ACCEPT', '$ROLE', '$INTENT'];
const AUDIT_KEYWORDS = ['$SUMMARY', '$CHANGES', '$CHECKSUM'];

// Sender color assignments
const SENDER_COLORS = {
    'Don':      { bg: '#e8f5e9', border: '#4caf50', text: '#2e7d32', badge: '#4caf50' },
    'Pharos':   { bg: '#e3f2fd', border: '#2196f3', text: '#1565c0', badge: '#2196f3' },
    'Lodestar': { bg: '#fff8e1', border: '#ffc107', text: '#f57f17', badge: '#ffa000' },
    'default':  { bg: '#f5f5f5', border: '#9e9e9e', text: '#616161', badge: '#9e9e9e' }
};

/**
 * Creates a normalized AICP message object from parsed data.
 * @param {Object} fields - Key/value pairs from the message header
 * @param {string} payload - The payload content (between ---PAYLOAD--- and ---END---)
 * @param {string} rawText - The original raw message text
 * @returns {Object} Normalized message object
 */
function createMessage(fields, payload, rawText) {
    return {
        // Envelope (required routing)
        envelope: {
            proto:  fields['$PROTO'] || '',
            type:   fields['$TYPE'] || '',
            id:     fields['$ID'] || '',
            from:   fields['$FROM'] || '',
            to:     fields['$TO'] || '',
            time:   fields['$TIME'] || ''
        },
        // Meta (task metadata)
        meta: {
            task:     fields['$TASK'] || '',
            status:   fields['$STATUS'] || '',
            ref:      fields['$REF'] || null,
            seq:      fields['$SEQ'] ? parseInt(fields['$SEQ'], 10) : null,
            priority: fields['$PRIORITY'] || null,
            context:  fields['$CONTEXT'] || null,
            accept:   fields['$ACCEPT'] || null,
            role:     fields['$ROLE'] || null,
            intent:   fields['$INTENT'] || null
        },
        // Custom fields (no $ prefix)
        custom: extractCustomFields(fields),
        // Payload (markdown content)
        payload: payload || '',
        // Audit (optional verification)
        audit: {
            summary:  fields['$SUMMARY'] || null,
            changes:  fields['$CHANGES'] || null,
            checksum: fields['$CHECKSUM'] || null
        },
        // Raw text for debugging
        raw: rawText || ''
    };
}

/**
 * Extracts custom (non-$ prefixed) keyword/value pairs.
 * @param {Object} fields - All parsed key/value pairs
 * @returns {Object} Only the custom fields
 */
function extractCustomFields(fields) {
    const custom = {};
    for (const [key, value] of Object.entries(fields)) {
        if (!key.startsWith('$')) {
            custom[key] = value;
        }
    }
    return custom;
}

/**
 * Validates a message object against AICP requirements.
 * @param {Object} msg - A normalized message object
 * @returns {Object} { valid: boolean, errors: string[] }
 */
function validateMessage(msg) {
    const errors = [];

    // Check required envelope fields
    if (!msg.envelope.proto) errors.push('Missing $PROTO');
    if (!msg.envelope.type) errors.push('Missing $TYPE');
    if (!msg.envelope.id) errors.push('Missing $ID');
    if (!msg.envelope.from) errors.push('Missing $FROM');
    if (!msg.envelope.to) errors.push('Missing $TO');
    if (!msg.envelope.time) errors.push('Missing $TIME');

    // Validate message type
    if (msg.envelope.type && !MESSAGE_TYPES.includes(msg.envelope.type)) {
        errors.push(`Invalid $TYPE: "${msg.envelope.type}". Expected one of: ${MESSAGE_TYPES.join(', ')}`);
    }

    // Validate status if present
    if (msg.meta.status && !STATUS_VALUES.includes(msg.meta.status)) {
        errors.push(`Invalid $STATUS: "${msg.meta.status}". Expected one of: ${STATUS_VALUES.join(', ')}`);
    }

    // Validate priority if present
    if (msg.meta.priority && !PRIORITY_VALUES.includes(msg.meta.priority)) {
        errors.push(`Invalid $PRIORITY: "${msg.meta.priority}". Expected one of: ${PRIORITY_VALUES.join(', ')}`);
    }

    return {
        valid: errors.length === 0,
        errors: errors
    };
}

/**
 * Returns the color scheme for a given sender name.
 * @param {string} sender - The sender name
 * @returns {Object} Color scheme object { bg, border, text, badge }
 */
function getSenderColor(sender) {
    // Normalize: check if sender name starts with a known sender
    for (const [name, colors] of Object.entries(SENDER_COLORS)) {
        if (name !== 'default' && sender && sender.toLowerCase().includes(name.toLowerCase())) {
            return colors;
        }
    }
    return SENDER_COLORS['default'];
}

/**
 * Formats an ISO 8601 timestamp into a human-readable string.
 * Handles Invalid Date gracefully (per Lodestar review MSG-0011).
 * @param {string} isoTime - ISO 8601 timestamp
 * @returns {string} Formatted time string
 */
function formatTime(isoTime) {
    if (!isoTime) return '';
    try {
        const date = new Date(isoTime);
        if (isNaN(date.getTime())) return isoTime; // Return raw if invalid
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (e) {
        return isoTime;
    }
}

/**
 * Generates a UUID v4 string for message IDs (fallback).
 * @returns {string} UUID string like "MSG-xxxxxxxx"
 */
function generateMessageId() {
    const hex = () => Math.floor(Math.random() * 0x10000).toString(16).padStart(4, '0');
    return `MSG-${hex()}${hex()}`;
}

/**
 * Generates the next sequential message ID based on loaded messages.
 * Scans allMessages for the highest MSG-NNNN number and returns MSG-(N+1).
 * Falls back to generateMessageId() if no sequential IDs found.
 * @returns {string} Next sequential ID like "MSG-0014"
 */
function generateNextMessageId() {
    if (typeof allMessages === 'undefined' || !allMessages || allMessages.length === 0) {
        return generateMessageId();
    }
    let maxNum = 0;
    allMessages.forEach(msg => {
        const match = msg.envelope.id.match(/^MSG-(\d+)$/);
        if (match) {
            const num = parseInt(match[1], 10);
            if (num > maxNum) maxNum = num;
        }
    });
    if (maxNum === 0) return generateMessageId();
    return `MSG-${String(maxNum + 1).padStart(4, '0')}`;
}

/**
 * Returns the ID of the most recent message (for $REF default).
 * @returns {string|null} The last message ID or null
 */
function getLastMessageId() {
    if (typeof allMessages === 'undefined' || !allMessages || allMessages.length === 0) {
        return null;
    }
    return allMessages[allMessages.length - 1].envelope.id || null;
}

/**
 * Returns the current time as an ISO 8601 string with timezone offset.
 * @returns {string} ISO 8601 timestamp
 */
function nowISO() {
    const now = new Date();
    const offset = -now.getTimezoneOffset();
    const sign = offset >= 0 ? '+' : '-';
    const pad = (n) => String(Math.abs(n)).padStart(2, '0');
    const hours = Math.floor(Math.abs(offset) / 60);
    const minutes = Math.abs(offset) % 60;
    return now.getFullYear() +
        '-' + pad(now.getMonth() + 1) +
        '-' + pad(now.getDate()) +
        'T' + pad(now.getHours()) +
        ':' + pad(now.getMinutes()) +
        ':' + pad(now.getSeconds()) +
        sign + pad(hours) + ':' + pad(minutes);
}

/**
 * Creates a draft message with auto-filled default fields.
 * Used by the Message Builder to pre-populate required fields.
 * @param {Object} [defaults] - Optional overrides for default values
 * @returns {Object} Normalized message object with defaults filled in
 */
function createDraftMessage(defaults = {}) {
    const fields = {
        '$PROTO':    defaults.proto    || 'AICP/1.0',
        '$TYPE':     defaults.type     || 'REQUEST',
        '$ID':       defaults.id       || generateMessageId(),
        '$FROM':     defaults.from     || '',
        '$TO':       defaults.to       || '',
        '$TIME':     defaults.time     || nowISO(),
        '$TASK':     defaults.task     || '',
        '$STATUS':   defaults.status   || 'PENDING',
        '$REF':      defaults.ref      || null,
        '$SEQ':      defaults.seq      || null,
        '$PRIORITY': defaults.priority || null,
        '$ROLE':     defaults.role     || null,
        '$INTENT':   defaults.intent   || null
    };

    // Add custom fields
    if (defaults.custom) {
        for (const [key, value] of Object.entries(defaults.custom)) {
            fields[key] = value;
        }
    }

    return createMessage(fields, defaults.payload || '', '');
}

/**
 * Serializes a normalized message object back to canonical AICP text.
 * This is the inverse of parseMessage().
 * @param {Object} msg - Normalized message object
 * @returns {string} Canonical AICP message text
 */
function serializeMessage(msg) {
    const lines = [];

    // Envelope (required)
    lines.push(`$PROTO: ${msg.envelope.proto}`);
    lines.push(`$TYPE: ${msg.envelope.type}`);
    lines.push(`$ID: ${msg.envelope.id}`);
    if (msg.meta.ref) lines.push(`$REF: ${msg.meta.ref}`);
    if (msg.meta.seq !== null) lines.push(`$SEQ: ${msg.meta.seq}`);
    lines.push(`$FROM: ${msg.envelope.from}`);
    lines.push(`$TO: ${msg.envelope.to}`);
    lines.push(`$TIME: ${msg.envelope.time}`);

    // Meta
    if (msg.meta.task) lines.push(`$TASK: ${msg.meta.task}`);
    if (msg.meta.status) lines.push(`$STATUS: ${msg.meta.status}`);
    if (msg.meta.priority) lines.push(`$PRIORITY: ${msg.meta.priority}`);
    if (msg.meta.role) lines.push(`$ROLE: ${msg.meta.role}`);
    if (msg.meta.intent) lines.push(`$INTENT: ${msg.meta.intent}`);
    if (msg.meta.context) lines.push(`$CONTEXT: ${msg.meta.context}`);
    if (msg.meta.accept) lines.push(`$ACCEPT: ${msg.meta.accept}`);

    // Custom fields
    for (const [key, value] of Object.entries(msg.custom || {})) {
        lines.push(`${key}: ${value}`);
    }

    // Payload
    if (msg.payload) {
        lines.push('');
        lines.push('---PAYLOAD---');
        lines.push(msg.payload);
        lines.push('---END---');
    }

    // Audit
    if (msg.audit.summary || msg.audit.changes || msg.audit.checksum) {
        lines.push('');
        if (msg.audit.summary) lines.push(`$SUMMARY: ${msg.audit.summary}`);
        if (msg.audit.changes) lines.push(`$CHANGES: ${msg.audit.changes}`);
        if (msg.audit.checksum) lines.push(`$CHECKSUM: ${msg.audit.checksum}`);
    }

    return lines.join('\n');
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        createMessage, createDraftMessage, serializeMessage,
        validateMessage, getSenderColor, formatTime,
        generateMessageId, generateNextMessageId, getLastMessageId, nowISO,
        REQUIRED_KEYWORDS, MESSAGE_TYPES, STATUS_VALUES, PRIORITY_VALUES,
        ENVELOPE_KEYWORDS, META_KEYWORDS, AUDIT_KEYWORDS, SENDER_COLORS
    };
}
