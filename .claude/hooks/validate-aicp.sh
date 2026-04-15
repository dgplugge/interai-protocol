#!/usr/bin/env bash
# validate-aicp.sh — PostToolUse hook
# Validates that .md files written to messages/ directories have valid AICP headers.
# Reads JSON from stdin (Claude's PostToolUse event payload).

set -euo pipefail

# Parse file path from stdin JSON using Python
FILE_PATH=$(python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    fp = data.get('tool_input', {}).get('file_path', '')
    if not fp:
        fp = data.get('tool_input', {}).get('command', '')
    print(fp)
except:
    print('')
")

# Only validate .md files in messages/ directories
if [[ ! "$FILE_PATH" =~ messages/.*\.md$ ]]; then
  exit 0
fi

# Check file exists
if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Validate AICP envelope using Python
python << PYEOF
import json

file_path = r"""$FILE_PATH"""
required = ['\$PROTO:', '\$ID:', '\$FROM:', '\$TO:', '\$TIME:', '\$TYPE:']
missing = []

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

for field in required:
    if field not in content:
        missing.append(field.rstrip(':'))

if '---PAYLOAD---' not in content:
    missing.append('---PAYLOAD---')

if missing:
    joined = ', '.join(missing)
    print(json.dumps({"result": f"AICP validation warning: missing {joined} in {file_path}"}))
else:
    print(json.dumps({"result": f"AICP envelope valid: {file_path}"}))
PYEOF
exit 0
