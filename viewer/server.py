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
    GET  /api/agent-hub/config               — Return API hub agent delivery config
    POST /api/agent-hub/roundtable           — Send orchestrated round-table prompts
    GET  /api/project-registry               — Get the project registry (metadata)
    POST /api/project-registry               — Create a new project in the registry

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

# Agent API hub integration config
AGENT_API_CONFIG_FILE = os.path.join(SCRIPT_DIR, 'agent-api-config.json')
AGENT_API_CONFIG = {
    'roundtable': {
        'timeout_ms': 12000,
        'allow_insecure_http': False
    },
    'agents': {
        'Pharos': {
            'platform': 'Claude (Anthropic)',
            'enabled': False,
            'endpoint': '',
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'mock_reply': 'Pharos: endpoint not configured. Add endpoint in agent-api-config.json.'
        },
        'Lodestar': {
            'platform': 'ChatGPT (OpenAI)',
            'enabled': False,
            'endpoint': '',
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'mock_reply': 'Lodestar: endpoint not configured. Add endpoint in agent-api-config.json.'
        },
        'Forge': {
            'platform': 'Codex (OpenAI)',
            'enabled': False,
            'endpoint': '',
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'mock_reply': 'Forge: endpoint not configured. Add endpoint in agent-api-config.json.'
        },
        'SpinDrift': {
            'platform': 'Cursor',
            'enabled': False,
            'endpoint': '',
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'mock_reply': 'SpinDrift: endpoint not configured. Add endpoint in agent-api-config.json.'
        }
    }
}


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


def load_agent_api_config():
    """Load API hub configuration from agent-api-config.json."""
    global AGENT_API_CONFIG
    try:
        if os.path.exists(AGENT_API_CONFIG_FILE):
            with open(AGENT_API_CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            # Round-table settings
            roundtable = loaded.get('roundtable', {})
            AGENT_API_CONFIG['roundtable'].update({
                'timeout_ms': int(roundtable.get('timeout_ms', AGENT_API_CONFIG['roundtable']['timeout_ms'])),
                'allow_insecure_http': bool(roundtable.get('allow_insecure_http', False))
            })

            # Agent settings (merge by key)
            loaded_agents = loaded.get('agents', {})
            for agent_name, cfg in loaded_agents.items():
                current = AGENT_API_CONFIG['agents'].get(agent_name, {})
                merged = dict(current)
                merged.update(cfg if isinstance(cfg, dict) else {})
                AGENT_API_CONFIG['agents'][agent_name] = merged

            print(f'[API-HUB] Loaded config for {len(AGENT_API_CONFIG["agents"])} agent(s)')
        else:
            print(f'[API-HUB] No config file at {AGENT_API_CONFIG_FILE} — using mock mode defaults')
    except (json.JSONDecodeError, IOError, ValueError) as e:
        print(f'[API-HUB] Config load error: {e} — using defaults')


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
        elif path == '/api/agent-hub/config':
            self.handle_agent_hub_config()
        elif path.startswith('/api/project/'):
            self.handle_project_resource(path)
        else:
            super().do_GET()

    def do_POST(self):
        """Route POST requests."""
        if self.path == '/api/relay':
            self.handle_relay()
        elif self.path == '/api/relay-to-n8n':
            self.handle_relay_to_n8n()
        elif self.path == '/api/agent-hub/roundtable':
            self.handle_agent_hub_roundtable()
        elif self.path == '/api/project-registry':
            self.handle_post_project_registry()
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

                    n8n_payload = json.dumps({
                        'message': raw_body,
                        'messageId': meta['id'],
                        'project': target_project,
                        'targets': ['n8n'],
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

    def handle_agent_hub_config(self):
        """
        GET /api/agent-hub/config — returns visible API hub configuration.
        Secrets are never returned; only delivery capability flags.
        """
        agents = []
        for name, cfg in AGENT_API_CONFIG.get('agents', {}).items():
            endpoint = str(cfg.get('endpoint', '') or '').strip()
            agents.append({
                'name': name,
                'platform': cfg.get('platform', ''),
                'enabled': bool(cfg.get('enabled', False)),
                'endpointConfigured': bool(endpoint)
            })

        self.send_json(200, {
            'ok': True,
            'roundtable': AGENT_API_CONFIG.get('roundtable', {}),
            'agents': agents
        })

    def handle_agent_hub_roundtable(self):
        """
        POST /api/agent-hub/roundtable
        Accepts one orchestrator prompt and sends it to selected agent endpoints
        in a deterministic turn order. Returns all replies as a transcript payload.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_json(400, 'Empty request body')
                return

            raw_body = self.rfile.read(content_length).decode('utf-8')
            payload = json.loads(raw_body)

            prompt = str(payload.get('prompt', '')).strip()
            agents = payload.get('agents', [])
            turn_order = payload.get('turnOrder', [])

            if not prompt:
                self.send_error_json(400, 'Missing prompt')
                return
            if not isinstance(agents, list) or len(agents) == 0:
                self.send_error_json(400, 'At least one agent is required')
                return

            # Keep requested order but only for selected agents.
            normalized_agents = []
            for agent in agents:
                name = str(agent).strip()
                if name and name not in normalized_agents:
                    normalized_agents.append(name)

            ordered = []
            for agent in turn_order:
                name = str(agent).strip()
                if name and name in normalized_agents and name not in ordered:
                    ordered.append(name)
            for agent in normalized_agents:
                if agent not in ordered:
                    ordered.append(agent)

            replies = []
            for idx, agent_name in enumerate(ordered):
                round_payload = {
                    'proto': payload.get('proto', 'AICP/1.0'),
                    'type': payload.get('type', 'REQUEST'),
                    'from': payload.get('from', 'Don'),
                    'task': payload.get('task', ''),
                    'project': payload.get('project', 'InterAI-Protocol'),
                    'domain': payload.get('domain', 'Multi-Agent Systems'),
                    'contextRef': payload.get('contextRef'),
                    'turnMode': payload.get('turnMode', 'round_robin'),
                    'turn': idx + 1,
                    'turnOrder': ordered,
                    'agent': agent_name,
                    'prompt': prompt,
                    'priorReplies': replies
                }
                result = self.call_agent_roundtable(agent_name, round_payload, idx + 1)
                replies.append(result)

            self.send_json(200, {
                'ok': True,
                'turnMode': payload.get('turnMode', 'round_robin'),
                'turnOrder': ordered,
                'replies': replies
            })
        except json.JSONDecodeError:
            self.send_error_json(400, 'Invalid JSON body')
        except Exception as e:
            self.send_error_json(500, f'Agent hub error: {str(e)}')

    def call_agent_roundtable(self, agent_name, outbound_payload, round_num):
        """
        Calls a configured agent endpoint.
        Falls back to deterministic mock replies when endpoint is disabled/unset.
        """
        cfg = AGENT_API_CONFIG.get('agents', {}).get(agent_name)
        if not cfg:
            return {
                'agent': agent_name,
                'round': round_num,
                'ok': False,
                'delivery': 'error',
                'error': f'Unknown agent: {agent_name}'
            }

        enabled = bool(cfg.get('enabled', False))
        endpoint = str(cfg.get('endpoint', '') or '').strip()

        if (not enabled) or (not endpoint):
            return {
                'agent': agent_name,
                'round': round_num,
                'ok': True,
                'delivery': 'mock',
                'reply': cfg.get('mock_reply', f'{agent_name}: mock mode reply')
            }

        allow_insecure = bool(AGENT_API_CONFIG.get('roundtable', {}).get('allow_insecure_http', False))
        if endpoint.startswith('http://') and not allow_insecure:
            return {
                'agent': agent_name,
                'round': round_num,
                'ok': False,
                'delivery': 'error',
                'error': 'Insecure HTTP endpoint blocked (set allow_insecure_http=true to override).'
            }

        headers = {}
        for key, value in dict(cfg.get('headers', {})).items():
            headers[str(key)] = self.resolve_header_tokens(str(value))

        # Default content type for JSON requests
        if not any(k.lower() == 'content-type' for k in headers):
            headers['Content-Type'] = 'application/json'

        data = json.dumps(outbound_payload).encode('utf-8')
        method = str(cfg.get('method', 'POST') or 'POST').upper()
        timeout_s = max(1, int(AGENT_API_CONFIG.get('roundtable', {}).get('timeout_ms', 12000)) / 1000.0)

        try:
            req = Request(endpoint, data=data, headers=headers, method=method)
            response = urlopen(req, timeout=timeout_s)
            body = response.read()
            reply_text = self.extract_reply_text(body)
            return {
                'agent': agent_name,
                'round': round_num,
                'ok': True,
                'delivery': 'https',
                'reply': reply_text
            }
        except HTTPError as e:
            return {
                'agent': agent_name,
                'round': round_num,
                'ok': False,
                'delivery': 'error',
                'error': f'HTTP {e.code}: {e.reason}'
            }
        except URLError as e:
            return {
                'agent': agent_name,
                'round': round_num,
                'ok': False,
                'delivery': 'error',
                'error': f'Network error: {e.reason}'
            }
        except Exception as e:
            return {
                'agent': agent_name,
                'round': round_num,
                'ok': False,
                'delivery': 'error',
                'error': str(e)
            }

    def resolve_header_tokens(self, value):
        """
        Resolves header values with ${ENV:VAR_NAME} placeholders.
        Missing env variables resolve to an empty string.
        """
        pattern = re.compile(r'\$\{ENV:([A-Z0-9_]+)\}')

        def repl(match):
            env_name = match.group(1)
            return os.getenv(env_name, '')

        return pattern.sub(repl, value)

    def extract_reply_text(self, body_bytes):
        """
        Extract a readable reply from arbitrary API JSON/text formats.
        """
        text = body_bytes.decode('utf-8', errors='replace').strip()
        if not text:
            return ''

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text

        if isinstance(parsed, dict):
            # Common direct fields
            for key in ('reply', 'message', 'content', 'output_text', 'text'):
                val = parsed.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()

            # OpenAI-like choices
            choices = parsed.get('choices')
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get('message')
                    if isinstance(msg, dict) and isinstance(msg.get('content'), str):
                        return msg['content']
                    if isinstance(first.get('text'), str):
                        return first['text']

            # Anthropic-like content array
            content = parsed.get('content')
            if isinstance(content, list):
                chunks = []
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get('text'), str):
                        chunks.append(item['text'])
                if chunks:
                    return '\n'.join(chunks)

        # Fallback to JSON text
        return json.dumps(parsed, ensure_ascii=False)

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

    # Load API hub integration config
    load_agent_api_config()

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
