#!/usr/bin/env bash
# check-inbox.sh — Checks all agent inboxes for unread messages
# Used by /loop and scheduled tasks to monitor for incoming agent messages.

set -euo pipefail

INBOX_DIR="H:/Code/interai-protocol/viewer/inbox"

python -c "
import os, json, glob

inbox_dir = '$INBOX_DIR'
unread = []

for inbox_file in glob.glob(os.path.join(inbox_dir, '*.json')):
    agent = os.path.splitext(os.path.basename(inbox_file))[0]
    try:
        with open(inbox_file, 'r') as f:
            data = json.load(f)
        notifications = data.get('notifications', [])
        unread_msgs = [n for n in notifications if not n.get('read', False)]
        if unread_msgs:
            details = '; '.join(
                f\"{n.get('from', '?')}: {n.get('task', n.get('messageId', '?'))}\"
                for n in unread_msgs
            )
            unread.append(f'  - {agent} has {len(unread_msgs)} unread: {details}')
    except Exception as e:
        unread.append(f'  - {agent}: error reading inbox ({e})')

if unread:
    print('=== UNREAD MESSAGES ===')
    for msg in unread:
        print(msg)
else:
    print('All inboxes clear - no unread messages.')
"

# Check relay server health
if curl -s --connect-timeout 2 "http://127.0.0.1:8080/api/projects" > /dev/null 2>&1; then
  echo "Relay server: UP (port 8080)"
else
  echo "Relay server: DOWN"
fi
