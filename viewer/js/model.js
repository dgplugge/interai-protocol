/**
 * AICP Message Model
 * Defines the normalized message object shape and schema helpers
 * for the Inter-AI Communication Protocol.
 *
 * Protocol: AICP/1.0
 * Version: Slice 0 — Read and Render
 */

// Required envelope keywords (must be present in every message)
const REQUIRED_KEYWORDS = ['$PROTO', '$TYPE', '$ID', '$FROM', '$TO', '$TIME'];

// Valid message types
const MESSAGE_TYPES = ['REQUEST', 'RESPONSE', 'ACK', 'ERROR', 'HANDOFF', 'REVIEW'];

// Valid status values
const STATUS_VALUES = ['PENDING', 'IN_PROGRESS', 'COMPLETE', 'FAILED'];

// Valid priority values
const PRIORITY_VALUES = ['LOW', 'NORMAL', 'HIGH'];

// Keyword classification: which segment each keyword belongs to
const ENVELOPE_KEYWORDS = ['$PROTO', '$TYPE', '$ID', '$FROM', '$TO', '$TIME'];
const META_KEYWORDS = ['$TASK', '$STATUS', '$REF', '$SEQ', '$PRIORITY', '$CONTEXT', '$ACCEPT', '$ROLE', '$INTENT'];
const AUDIT_KEYWORDS = ['$SUMMARY', '$CHANGES', '$CHECKSUM'];

// Sender color assignments
const SENDER_COLORS = {
    'Don':      { bg: '#e8f5e9', border: '#4caf50', text: '#2e7d32', badge: '#4caf50' },
    'Pharos':   { bg: '#e3f2fd', border: '#2196f3', text: '#1565c0', badge: '#2196f3' },
    'LodeStar': { bg: '#fff8e1', border: '#ffc107', text: '#f57f17', badge: '#ffa000' },
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
 * @param {string} isoTime - ISO 8601 timestamp
 * @returns {string} Formatted time string
 */
function formatTime(isoTime) {
    try {
        const date = new Date(isoTime);
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

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        createMessage, validateMessage, getSenderColor, formatTime,
        REQUIRED_KEYWORDS, MESSAGE_TYPES, STATUS_VALUES, PRIORITY_VALUES,
        ENVELOPE_KEYWORDS, META_KEYWORDS, AUDIT_KEYWORDS, SENDER_COLORS
    };
}
