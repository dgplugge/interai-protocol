#!/usr/bin/env python3
"""
AICP Relay Server — Multi-Project Edition
A lightweight HTTP server that serves the AICP Viewer static files
and provides relay endpoints for saving and forwarding AICP messages.

Protocol: AICP/1.0
Slice 8 — Multi-Project Journal Support

Endpoints:
    GET  /api/projects                       — List all configured projects
    GET  /api/project/<id>/index             — Get a project's journal-index.json
    GET  /api/project/<id>/messages/<file>   — Get a message .md file
    POST /api/relay                          — Save message to correct project journal
    POST /api/relay-to-n8n                   — Save locally + forward to n8n webhook
    GET  /api/integrations                   — Return configured integration status
    GET  /api/project-registry               — Get the project registry (metadata)
    POST /api/project-registry               — Create a new project in the registry
    POST /agents/<id>/notify                 — Receive notification webhook from n8n
    POST /agents/<id>/deliver                — Receive full delivery webhook from n8n
    GET  /agents/<id>/inbox                  — Read agent's pending notifications
    POST /agents/<id>/inbox/clear            — Mark notifications as read

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
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import unquote

PORT = 8080

# Change to the viewer directory so static files are served correctly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# Multi-project configuration
PROJECTS_FILE = os.path.join(SCRIPT_DIR, 'projects.json')
PROJECTS = {}  # id -> project config dict

# Parent of viewer dir (repo root) — used only for static file serving
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# n8n integration config
N8N_CONFIG_FILE = os.path.join(SCRIPT_DIR, 'n8n-config.json')
N8N_CONFIG = {
    'N8N_ENABLED': False,
    'N8N_WEBHOOK_URL': '',
    'N8N_TIMEOUT_MS': 5000
}

# Project registry
PROJECT_REGISTRY_FILE = os.path.join(SCRIPT_DIR, 'project-registry.json')

# Agent notification inbox
INBOX_DIR = os.path.join(SCRIPT_DIR, 'inbox')
VALID_AGENTS = {'don', 'pharos', 'lodestar', 'forge', 'spindrift'}


def load_projects_config():
    """Load multi-project configuration from projects.json."""
    global PROJECTS
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for proj in config.get('projects', []):
                pid = proj.get('id')
                if pid:
                    # Normalize path separators for the OS
                    proj['path'] = os.path.normpath(proj['path'])
                    PROJECTS[pid] = proj
            print(f'[PROJECTS] Loaded {len(PROJECTS)} project(s): {", ".join(PROJECTS.keys())}')
        else:
            print(f'[PROJECTS] No projects.json found — using legacy single-project mode')
            # Fallback: register the default InterAI-Protocol project
            PROJECTS['InterAI-Protocol'] = {
                'id': 'InterAI-Protocol',
                'name': 'Inter-AI Protocol',
                'path': os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', 'Agent-Journals', 'InterAI-Protocol')),
                'color': '#4a9eff'
            }
    except (json.JSONDecodeError, IOError) as e:
        print(f'[PROJECTS] Config load error: {e}')


def load_n8n_config():
    """Load n8n configuration from n8n-config.json."""
    global N8N_CONFIG
    try:
        if os.path.exists(N8N_CONFIG_FILE):
            with open(N8N_CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            N8N_CONFIG.update(loaded)
            if N8N_CONFIG['N8N_ENABLED']:
                print(f'[N8N] Integration ENABLED — webhook: {N8N_CONFIG["N8N_WEBHOOK_URL"]}')
            else:
                print(f'[N8N] Integration disabled (set N8N_ENABLED=true in n8n-config.json)')
        else:
            print(f'[N8N] No config file found at {N8N_CONFIG_FILE} — integration disabled')
    except (json.JSONDecodeError, IOError) as e:
        print(f'[N8N] Config load error: {e} — integration disabled')


def get_project_index_path(project_id):
    """Get the journal-index.json path for a project."""
    proj = PROJECTS.get(project_id)
    if not proj:
        return None
    return os.path.join(proj['path'], 'journal-index.json')


def get_project_messages_dir(project_id):
    """Get the messages/ directory path for a project."""
    proj = PROJECTS.get(project_id)
    if not proj:
        return None
    return os.path.join(proj['path'], 'messages')


class RelayHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves static files and handles relay POST requests."""

    def end_headers(self):
        """Add CORS and cache-control headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # Prevent caching so viewer always gets fresh data
        if self.path.endswith('.json') or self.path.endswith('.js') or self.path.endswith('.css'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """Route GET requests — API endpoints and static files."""
        path = self.path.split('?')[0]  # Strip query params

        if path == '/api/projects':
            self.handle_projects()
        elif path == '/api/project-registry':
            self.handle_get_project_registry()
        elif path == '/api/integrations':
            self.handle_integrations()
        elif path.startswith('/api/project/'):
            self.handle_project_resource(path)
        elif re.match(r'^/agents/\w+/inbox$', path):
            self.handle_get_inbox(path)
        else:
            super().do_GET()

    def do_POST(self):
        """Route POST requests."""
        if self.path == '/api/relay':
            self.handle_relay()
        elif self.path == '/api/relay-to-n8n':
            self.handle_relay_to_n8n()
        elif self.path == '/api/project-registry':
            self.handle_post_project_registry()
        elif re.match(r'^/agents/\w+/notify$', self.path):
            self.handle_agent_notify(self.path)
        elif re.match(r'^/agents/\w+/deliver$', self.path):
            self.handle_agent_deliver(self.path)
        elif re.match(r'^/agents/\w+/inbox/clear$', self.path):
            self.handle_inbox_clear(self.path)
        else:
            self.send_error_json(404, 'Not found')

    def handle_projects(self):
        """
        GET /api/projects — returns the list of configured projects
        with their id, name, color, and message counts.
        """
        project_list = []
        for pid, proj in PROJECTS.items():
            entry = {
                'id': proj['id'],
                'name': proj['name'],
                'color': proj.get('color', '#888888'),
                'messageCount': 0
            }
            # Count messages from index
            index_path = get_project_index_path(pid)
            if index_path and os.path.exists(index_path):
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        index = json.load(f)
                    entry['messageCount'] = len(index.get('messages', []))
                except (json.JSONDecodeError, IOError):
                    pass
            project_list.append(entry)

        self.send_json(200, {'ok': True, 'projects': project_list})

    def handle_project_resource(self, path):
        """
        Route /api/project/<id>/index and /api/project/<id>/messages/<file>.
        Serves journal data from any configured project path.
        """
        # Parse: /api/project/<id>/index or /api/project/<id>/messages/<file>
        # Strip the prefix
        rest = path[len('/api/project/'):]
        parts = rest.split('/', 2)

        if len(parts) < 2:
            self.send_error_json(400, 'Invalid project resource path')
            return

        project_id = unquote(parts[0])
        resource = parts[1]

        if project_id not in PROJECTS:
            self.send_error_json(404, f'Unknown project: {project_id}')
            return

        if resource == 'index':
            # Serve journal-index.json
            index_path = get_project_index_path(project_id)
            if index_path and os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.send_json(200, data)
            else:
                self.send_error_json(404, f'No journal index for project: {project_id}')

        elif resource == 'messages' and len(parts) == 3:
            # Serve a message .md file
            filename = unquote(parts[2])
            # Security: prevent path traversal
            if '..' in filename or '/' in filename or '\\' in filename:
                self.send_error_json(400, 'Invalid filename')
                return

            messages_dir = get_project_messages_dir(project_id)
            filepath = os.path.join(messages_dir, filename)

            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                body = content.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/markdown; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error_json(404, f'Message file not found: {filename}')
        else:
            self.send_error_json(400, 'Invalid project resource path')

    def handle_relay(self):
        """
        Core relay handler:
        1. Read raw AICP text from request body
        2. Parse meta fields ($PROTO, $ID, $TYPE, PROJECT, etc.)
        3. Determine target project from PROJECT custom field
        4. Generate filename from meta
        5. Check for duplicate message ID in target project
        6. Save .md file to the correct project's messages/ dir
        7. Update that project's journal-index.json
        8. Return success response
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

            # Determine target project
            target_project = meta.get('project', 'InterAI-Protocol')
            if target_project not in PROJECTS:
                self.send_error_json(400, f'Unknown project: {target_project}. Configure it in projects.json.')
                return

            # Check for duplicate message ID in target project
            if self.is_duplicate_id_in(meta['id'], target_project):
                self.send_error_json(409, f'Duplicate message ID: {meta["id"]}')
                return

            # Generate filename
            filename = self.generate_filename(meta)

            # Get project-specific paths
            messages_dir = get_project_messages_dir(target_project)
            index_path = get_project_index_path(target_project)
            filepath = os.path.join(messages_dir, filename)

            # Save .md file to project directory
            os.makedirs(messages_dir, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(raw_body)

            # Update journal-index.json
            relative_file = f'messages/{filename}'
            self.update_index(index_path, meta, relative_file, target_project)

            # Success response
            self.send_json(200, {
                'ok': True,
                'id': meta['id'],
                'file': relative_file,
                'project': target_project,
                'message': f'Relayed {meta["id"]} to {target_project} journal'
            })

            print(f'[RELAY] Saved {meta["id"]} -> {target_project}/{filename}')

        except Exception as e:
            self.send_error_json(500, f'Relay error: {str(e)}')

    def handle_relay_to_n8n(self):
        """
        Relay-to-n8n handler (Slice 7):
        1. Read raw AICP text from request body
        2. Parse meta fields
        3. Save locally to correct project (same as /api/relay)
        4. Forward to configured n8n webhook
        5. Return combined delivery result
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

            # Determine target project
            target_project = meta.get('project', 'InterAI-Protocol')
            if target_project not in PROJECTS:
                self.send_error_json(400, f'Unknown project: {target_project}')
                return

            # Check for duplicate message ID
            if self.is_duplicate_id_in(meta['id'], target_project):
                self.send_error_json(409, f'Duplicate message ID: {meta["id"]}')
                return

            # Step 1: Save locally
            filename = self.generate_filename(meta)
            messages_dir = get_project_messages_dir(target_project)
            index_path = get_project_index_path(target_project)
            filepath = os.path.join(messages_dir, filename)

            os.makedirs(messages_dir, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(raw_body)

            relative_file = f'messages/{filename}'
            self.update_index(index_path, meta, relative_file, target_project)

            print(f'[RELAY] Saved {meta["id"]} -> {target_project}/{filename}')

            # Step 2: Forward to n8n webhook
            delivery = 'local_saved'
            n8n_status = None
            n8n_error = None

            if not N8N_CONFIG.get('N8N_ENABLED'):
                n8n_error = 'n8n integration is disabled'
                print(f'[N8N] Skipped — integration disabled')
            elif not N8N_CONFIG.get('N8N_WEBHOOK_URL'):
                n8n_error = 'No webhook URL configured'
                print(f'[N8N] Skipped — no webhook URL')
            else:
                try:
                    webhook_url = N8N_CONFIG['N8N_WEBHOOK_URL']
                    timeout_s = N8N_CONFIG.get('N8N_TIMEOUT_MS', 5000) / 1000.0

                    # Include parsed routing hints so n8n can evolve from
                    # passive ingress logging to protocol-aware dispatch.
                    to_field = meta.get('to', '') or ''
                    target_list = [t.strip() for t in to_field.split(',') if t.strip()]
                    route = 'route_unknown'
                    lower_targets = [t.lower() for t in target_list]
                    if len(target_list) > 1:
                        route = 'route_multi'
                    elif 'pharos' in lower_targets:
                        route = 'route_pharos'
                    elif 'lodestar' in lower_targets:
                        route = 'route_lodestar'
                    elif 'don' in lower_targets:
                        route = 'route_don'

                    n8n_payload = json.dumps({
                        'message': raw_body,
                        'messageId': meta['id'],
                        'project': target_project,
                        'targets': target_list,
                        'routing': {
                            'route': route,
                            'isMulti': len(target_list) > 1
                        },
                        'meta': {
                            'type': meta.get('type'),
                            'from': meta.get('from'),
                            'to': meta.get('to'),
                            'task': meta.get('task', ''),
                            'time': meta.get('time')
                        }
                    }).encode('utf-8')

                    req = Request(
                        webhook_url,
                        data=n8n_payload,
                        headers={'Content-Type': 'application/json'},
                        method='POST'
                    )

                    response = urlopen(req, timeout=timeout_s)
                    n8n_status = response.status
                    delivery = 'n8n_sent'
                    print(f'[N8N] Sent {meta["id"]} -> {webhook_url} (HTTP {n8n_status})')

                except HTTPError as e:
                    n8n_status = e.code
                    n8n_error = f'HTTP {e.code}: {e.reason}'
                    delivery = 'n8n_failed'
                    print(f'[N8N] Failed {meta["id"]} -> HTTP {e.code}: {e.reason}')

                except URLError as e:
                    n8n_error = str(e.reason)
                    delivery = 'n8n_failed'
                    print(f'[N8N] Failed {meta["id"]} -> {e.reason}')

                except Exception as e:
                    n8n_error = str(e)
                    delivery = 'n8n_failed'
                    print(f'[N8N] Failed {meta["id"]} -> {e}')

            # Build response
            result = {
                'ok': True,
                'id': meta['id'],
                'file': relative_file,
                'project': target_project,
                'delivery': delivery,
                'message': f'Saved locally'
            }

            if delivery == 'n8n_sent':
                result['externalStatus'] = n8n_status
                result['message'] = f'Saved locally + sent to n8n'
            elif delivery == 'n8n_failed':
                result['n8nError'] = n8n_error
                if n8n_status:
                    result['externalStatus'] = n8n_status
                result['message'] = f'Saved locally, n8n delivery failed'
            elif n8n_error:
                result['n8nError'] = n8n_error
                result['message'] = f'Saved locally ({n8n_error})'

            self.send_json(200, result)

        except Exception as e:
            self.send_error_json(500, f'Relay-to-n8n error: {str(e)}')

    def handle_integrations(self):
        """
        GET /api/integrations — returns configured integration status flags.
        No secrets exposed — just enabled/disabled and connectivity state.
        """
        integrations = {
            'n8n': {
                'enabled': N8N_CONFIG.get('N8N_ENABLED', False),
                'configured': bool(N8N_CONFIG.get('N8N_WEBHOOK_URL')),
                'timeout_ms': N8N_CONFIG.get('N8N_TIMEOUT_MS', 5000)
            }
        }
        self.send_json(200, {'ok': True, 'integrations': integrations})

    def handle_get_project_registry(self):
        """
        GET /api/project-registry — serve the project registry JSON.
        """
        try:
            if os.path.exists(PROJECT_REGISTRY_FILE):
                with open(PROJECT_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.send_json(200, data)
            else:
                self.send_json(200, {'projects': []})
        except (json.JSONDecodeError, IOError) as e:
            self.send_error_json(500, f'Failed to load project registry: {e}')

    def handle_post_project_registry(self):
        """
        POST /api/project-registry — add a new project to the registry.
        Expects JSON body with: projectName, domain, and optional fields.
        Validates for duplicates, normalizes ID, and persists to file.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_json(400, 'Empty request body')
                return

            raw_body = self.rfile.read(content_length).decode('utf-8')
            new_project = json.loads(raw_body)

            # Validate required fields
            if not new_project.get('projectName', '').strip():
                self.send_error_json(400, 'projectName is required')
                return
            if not new_project.get('domain', '').strip():
                self.send_error_json(400, 'domain is required')
                return

            # Generate ID from name if not provided
            if not new_project.get('projectId'):
                name = new_project['projectName']
                new_project['projectId'] = ''.join(
                    word.capitalize()
                    for word in re.sub(r'[^a-zA-Z0-9]+', ' ', name).strip().split()
                )

            # Load existing registry
            if os.path.exists(PROJECT_REGISTRY_FILE):
                with open(PROJECT_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
            else:
                registry = {'projects': []}

            projects = registry.get('projects', [])

            # Check for duplicate ID
            for p in projects:
                if p.get('projectId') == new_project['projectId']:
                    self.send_error_json(409, f'Project ID already exists: {new_project["projectId"]}')
                    return

            # Check for duplicate name (case-insensitive)
            new_name_lower = new_project['projectName'].lower().strip()
            for p in projects:
                if p.get('projectName', '').lower().strip() == new_name_lower:
                    self.send_error_json(409, f'Project name already exists: {new_project["projectName"]}')
                    return

            # Set defaults
            new_project.setdefault('status', 'incubating')
            new_project.setdefault('createdOn', datetime.now().astimezone().isoformat())
            new_project.setdefault('defaultAgents', [])
            new_project.setdefault('tags', [])
            new_project.setdefault('description', '')

            # Append and save
            projects.append(new_project)
            registry['projects'] = projects

            with open(PROJECT_REGISTRY_FILE, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
                f.write('\n')

            print(f'[REGISTRY] Created project: {new_project["projectId"]} ({new_project["projectName"]})')

            self.send_json(201, {
                'ok': True,
                'projectId': new_project['projectId'],
                'message': f'Created project: {new_project["projectName"]}'
            })

        except json.JSONDecodeError:
            self.send_error_json(400, 'Invalid JSON body')
        except Exception as e:
            self.send_error_json(500, f'Registry error: {str(e)}')

    def parse_aicp_meta(self, text):
        """
        Extract AICP header fields from raw message text.
        Parses both $-prefixed keywords and custom fields (e.g., PROJECT, DOMAIN).
        Returns dict with: proto, type, id, from, to, time, task, ref, seq,
                           role, intent, status, priority, project, domain
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

        # Custom field mapping (non-$ prefixed)
        custom_map = {
            'PROJECT': 'project',
            'DOMAIN': 'domain',
        }

        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('---PAYLOAD---'):
                break  # Stop parsing at payload delimiter

            # Match $-prefixed keywords
            match = re.match(r'^(\$\w+):\s*(.+)$', line)
            if match:
                key, value = match.group(1), match.group(2).strip()
                if key in field_map:
                    meta[field_map[key]] = value
                continue

            # Match custom keywords (WORD: value)
            match = re.match(r'^([A-Z][A-Z0-9_]+):\s*(.+)$', line)
            if match:
                key, value = match.group(1), match.group(2).strip()
                if key in custom_map:
                    meta[custom_map[key]] = value

        return meta

    def generate_filename(self, meta):
        """
        Generate a canonical filename from message meta.
        Format: 2026-03-09-MSG-0019-request-don.md
        """
        # Extract date from $TIME or use today
        time_str = meta.get('time', '')
        try:
            date_part = time_str[:10]  # "2026-03-09"
            datetime.strptime(date_part, '%Y-%m-%d')
        except (ValueError, IndexError):
            date_part = datetime.now().strftime('%Y-%m-%d')

        msg_id = meta.get('id', 'MSG-UNKNOWN')
        msg_type = meta.get('type', 'message').lower()
        sender = meta.get('from', 'unknown').lower().replace(' ', '-')

        return f'{date_part}-{msg_id}-{msg_type}-{sender}.md'

    def is_duplicate_id_in(self, msg_id, project_id):
        """Check if a message ID already exists in a project's journal index."""
        index_path = get_project_index_path(project_id)
        if not index_path:
            return False
        try:
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                for entry in index.get('messages', []):
                    if entry.get('id') == msg_id:
                        return True
        except (json.JSONDecodeError, IOError):
            pass
        return False

    def update_index(self, index_path, meta, relative_file, project_id=None):
        """
        Append a new entry to journal-index.json.
        Creates the file if it doesn't exist.
        Uses project_id to set the correct project name in new indexes.
        """
        # Read existing index
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            # Determine project info for new index
            proj = PROJECTS.get(project_id, {}) if project_id else {}
            proj_name = proj.get('id', project_id or 'Unknown')
            index = {
                'protocol': 'AICP/1.0',
                'project': proj_name,
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
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
            f.write('\n')

    # ---- Agent Notification Handlers ----

    def _extract_agent_id(self, path):
        """Extract agent ID from /agents/{agentId}/... path."""
        parts = path.strip('/').split('/')
        if len(parts) >= 2:
            return parts[1].lower()
        return None

    def _get_inbox_path(self, agent_id):
        """Get the inbox JSON file path for an agent."""
        return os.path.join(INBOX_DIR, f'{agent_id}.json')

    def _read_inbox(self, agent_id):
        """Read an agent's inbox, creating if needed."""
        inbox_path = self._get_inbox_path(agent_id)
        if os.path.exists(inbox_path):
            try:
                with open(inbox_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {'agentId': agent_id, 'notifications': []}

    def _write_inbox(self, agent_id, inbox_data):
        """Write an agent's inbox to disk."""
        os.makedirs(INBOX_DIR, exist_ok=True)
        inbox_path = self._get_inbox_path(agent_id)
        with open(inbox_path, 'w', encoding='utf-8') as f:
            json.dump(inbox_data, f, indent=2)

    def _append_notification(self, agent_id, payload, event_type):
        """Append a notification to an agent's inbox."""
        inbox = self._read_inbox(agent_id)
        notification = dict(payload)
        notification['receivedAt'] = datetime.now().astimezone().isoformat()
        notification['read'] = False
        notification['eventType'] = event_type
        inbox['notifications'].append(notification)
        self._write_inbox(agent_id, inbox)
        return notification

    def handle_agent_notify(self, path):
        """POST /agents/{agentId}/notify — receive notification webhook from n8n."""
        agent_id = self._extract_agent_id(path)
        if agent_id not in VALID_AGENTS:
            self.send_error_json(404, f'Unknown agent: {agent_id}')
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_json(400, 'Empty request body')
                return

            body = self.rfile.read(content_length).decode('utf-8')
            payload = json.loads(body)

            notification = self._append_notification(agent_id, payload, 'notify')
            msg_id = payload.get('messageId', 'unknown')
            sender = payload.get('from', 'unknown')

            print(f'[NOTIFY] New message for {agent_id}: {msg_id} from {sender}')

            self.send_json(200, {
                'ok': True,
                'received': True,
                'agentId': agent_id,
                'messageId': msg_id,
                'timestamp': notification['receivedAt']
            })

        except json.JSONDecodeError:
            self.send_error_json(400, 'Invalid JSON body')
        except Exception as e:
            self.send_error_json(500, f'Notification error: {str(e)}')

    def handle_agent_deliver(self, path):
        """POST /agents/{agentId}/deliver — receive full delivery webhook from n8n."""
        agent_id = self._extract_agent_id(path)
        if agent_id not in VALID_AGENTS:
            self.send_error_json(404, f'Unknown agent: {agent_id}')
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_json(400, 'Empty request body')
                return

            body = self.rfile.read(content_length).decode('utf-8')
            payload = json.loads(body)

            notification = self._append_notification(agent_id, payload, 'deliver')
            msg_id = payload.get('messageId', 'unknown')
            sender = payload.get('from', 'unknown')

            print(f'[DELIVER] Full message for {agent_id}: {msg_id} from {sender}')

            self.send_json(200, {
                'ok': True,
                'received': True,
                'agentId': agent_id,
                'messageId': msg_id,
                'deliveryMode': 'full',
                'timestamp': notification['receivedAt']
            })

        except json.JSONDecodeError:
            self.send_error_json(400, 'Invalid JSON body')
        except Exception as e:
            self.send_error_json(500, f'Delivery error: {str(e)}')

    def handle_get_inbox(self, path):
        """GET /agents/{agentId}/inbox — read agent's pending notifications."""
        agent_id = self._extract_agent_id(path)
        if agent_id not in VALID_AGENTS:
            self.send_error_json(404, f'Unknown agent: {agent_id}')
            return

        # Check for ?unread=true query param
        query = self.path.split('?')[1] if '?' in self.path else ''
        unread_only = 'unread=true' in query

        inbox = self._read_inbox(agent_id)

        if unread_only:
            inbox['notifications'] = [n for n in inbox['notifications'] if not n.get('read')]

        inbox['unreadCount'] = sum(1 for n in inbox['notifications'] if not n.get('read'))
        self.send_json(200, inbox)

    def handle_inbox_clear(self, path):
        """POST /agents/{agentId}/inbox/clear — mark all notifications as read."""
        agent_id = self._extract_agent_id(path)
        if agent_id not in VALID_AGENTS:
            self.send_error_json(404, f'Unknown agent: {agent_id}')
            return

        inbox = self._read_inbox(agent_id)
        cleared = 0
        for n in inbox['notifications']:
            if not n.get('read'):
                n['read'] = True
                cleared += 1
        self._write_inbox(agent_id, inbox)

        print(f'[INBOX] Cleared {cleared} notifications for {agent_id}')
        self.send_json(200, {'ok': True, 'agentId': agent_id, 'cleared': cleared})

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

    # Load multi-project config
    load_projects_config()

    # Load n8n integration config
    load_n8n_config()

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
