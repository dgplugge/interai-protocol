#!/usr/bin/env python3
"""
AICP Relay Server
A lightweight HTTP server that serves the AICP Viewer static files
and provides a POST /api/relay endpoint to save composed messages
to the journal.

Protocol: AICP/1.0
Slice 2 — Assisted Relay

Usage:
    python viewer/server.py
    # Open http://localhost:8080
"""

import os
import sys
import re
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer
from datetime import datetime

PORT = 8080

# Change to the viewer directory so static files are served correctly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# Paths relative to viewer/ directory
SAMPLES_DIR = os.path.join('samples')
MESSAGES_DIR = os.path.join(SAMPLES_DIR, 'messages')
INDEX_FILE = os.path.join(SAMPLES_DIR, 'journal-index.json')

# Also update the canonical copy in the project root
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ROOT_SAMPLES_DIR = os.path.join(PROJECT_ROOT, 'samples')
ROOT_MESSAGES_DIR = os.path.join(ROOT_SAMPLES_DIR, 'messages')
ROOT_INDEX_FILE = os.path.join(ROOT_SAMPLES_DIR, 'journal-index.json')


class RelayHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves static files and handles relay POST requests."""

    def end_headers(self):
        """Add CORS and cache-control headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # Prevent caching of JSON files so viewer always gets fresh data
        if self.path.endswith('.json'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        """Route POST requests."""
        if self.path == '/api/relay':
            self.handle_relay()
        else:
            self.send_error_json(404, 'Not found')

    def handle_relay(self):
        """
        Core relay handler:
        1. Read raw AICP text from request body
        2. Parse meta fields ($PROTO, $ID, $TYPE, etc.)
        3. Generate filename from meta
        4. Check for duplicate message ID
        5. Save .md file to samples/messages/
        6. Update journal-index.json
        7. Return success response
        """
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_json(400, 'Empty request body')
                return

            raw_body = self.rfile.read(content_length).decode('utf-8')

            # Parse AICP meta fields
            meta = self.parse_aicp_meta(raw_body)

            # Validate required fields
            if not meta.get('proto'):
                self.send_error_json(400, 'Missing $PROTO header')
                return
            if not meta.get('id'):
                self.send_error_json(400, 'Missing $ID header')
                return

            # Check for duplicate message ID
            if self.is_duplicate_id(meta['id']):
                self.send_error_json(409, f'Duplicate message ID: {meta["id"]}')
                return

            # Generate filename
            filename = self.generate_filename(meta)
            filepath = os.path.join(MESSAGES_DIR, filename)
            root_filepath = os.path.join(ROOT_MESSAGES_DIR, filename)

            # Save .md file (both viewer copy and canonical copy)
            os.makedirs(MESSAGES_DIR, exist_ok=True)
            os.makedirs(ROOT_MESSAGES_DIR, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(raw_body)

            with open(root_filepath, 'w', encoding='utf-8') as f:
                f.write(raw_body)

            # Update journal-index.json (both copies)
            relative_file = f'messages/{filename}'
            self.update_index(INDEX_FILE, meta, relative_file)
            self.update_index(ROOT_INDEX_FILE, meta, relative_file)

            # Success response
            self.send_json(200, {
                'ok': True,
                'id': meta['id'],
                'file': relative_file,
                'message': f'Relayed {meta["id"]} to journal'
            })

            print(f'[RELAY] Saved {meta["id"]} -> {filename}')

        except Exception as e:
            self.send_error_json(500, f'Relay error: {str(e)}')

    def parse_aicp_meta(self, text):
        """
        Extract AICP header fields from raw message text.
        Returns dict with: proto, type, id, from, to, time, task, ref, seq, role, intent, status, priority
        """
        meta = {}
        field_map = {
            '$PROTO': 'proto',
            '$TYPE': 'type',
            '$ID': 'id',
            '$FROM': 'from',
            '$TO': 'to',
            '$TIME': 'time',
            '$TASK': 'task',
            '$REF': 'ref',
            '$SEQ': 'seq',
            '$ROLE': 'role',
            '$INTENT': 'intent',
            '$STATUS': 'status',
            '$PRIORITY': 'priority',
            '$SUMMARY': 'summary',
        }

        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('---PAYLOAD---'):
                break  # Stop parsing at payload delimiter
            match = re.match(r'^(\$\w+):\s*(.+)$', line)
            if match:
                key, value = match.group(1), match.group(2).strip()
                if key in field_map:
                    meta[field_map[key]] = value

        return meta

    def generate_filename(self, meta):
        """
        Generate a canonical filename from message meta.
        Format: 2026-03-09-MSG-0019-request-don.md
        """
        # Extract date from $TIME or use today
        time_str = meta.get('time', '')
        try:
            # Parse ISO 8601 datetime
            date_part = time_str[:10]  # "2026-03-09"
            # Validate it's a real date
            datetime.strptime(date_part, '%Y-%m-%d')
        except (ValueError, IndexError):
            date_part = datetime.now().strftime('%Y-%m-%d')

        msg_id = meta.get('id', 'MSG-UNKNOWN')
        msg_type = meta.get('type', 'message').lower()
        sender = meta.get('from', 'unknown').lower().replace(' ', '-')

        return f'{date_part}-{msg_id}-{msg_type}-{sender}.md'

    def is_duplicate_id(self, msg_id):
        """Check if a message ID already exists in the journal index."""
        try:
            if os.path.exists(INDEX_FILE):
                with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                for entry in index.get('messages', []):
                    if entry.get('id') == msg_id:
                        return True
        except (json.JSONDecodeError, IOError):
            pass
        return False

    def update_index(self, index_path, meta, relative_file):
        """
        Append a new entry to journal-index.json.
        Creates the file if it doesn't exist.
        """
        # Read existing index
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {
                'protocol': 'AICP/1.0',
                'project': 'InterAI-Protocol',
                'participants': ['Don', 'Pharos', 'Lodestar'],
                'messages': []
            }

        # Build new entry
        to_list = [t.strip() for t in meta.get('to', '').split(',')]
        entry = {
            'id': meta.get('id'),
            'type': meta.get('type'),
            'from': meta.get('from'),
            'to': to_list,
            'time': meta.get('time'),
            'task': meta.get('task', ''),
            'file': relative_file
        }

        # Add optional fields
        if meta.get('ref'):
            entry['ref'] = meta['ref']
        if meta.get('seq'):
            try:
                entry['seq'] = int(meta['seq'])
            except ValueError:
                entry['seq'] = meta['seq']

        index['messages'].append(entry)

        # Write updated index
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
            f.write('\n')

    def send_json(self, status_code, data):
        """Send a JSON response."""
        body = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status_code, message):
        """Send a JSON error response."""
        self.send_json(status_code, {'ok': False, 'error': message})

    def log_message(self, format, *args):
        """Override to add timestamp to log output."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        sys.stderr.write(f'[{timestamp}] {format % args}\n')


def main():
    print(f'AICP Relay Server starting on port {PORT}')
    print(f'Serving from: {os.getcwd()}')
    print(f'Journal index: {os.path.abspath(INDEX_FILE)}')
    print(f'Open http://localhost:{PORT}')
    print()

    server = HTTPServer(('', PORT), RelayHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down.')
        server.server_close()


if __name__ == '__main__':
    main()
