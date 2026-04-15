#!/usr/bin/env bash
# check-journal-post.sh — Stop hook
# Reminds to post an AICP journal entry after completing work with code changes.

set -euo pipefail

# Check if any files were modified or added in the repo (excluding .claude/ and __pycache__)
CHANGED=$(git -C "H:/Code/interai-protocol" diff --name-only HEAD 2>/dev/null || true)
CHANGED=$(echo "$CHANGED" | grep -v -E '(__pycache__|\.claude/)' || true)

if [[ -z "$CHANGED" ]]; then
  echo '{"result": "No code changes detected, journal post not required."}'
  exit 0
fi

# Check if a journal message was recently created (within last 30 minutes)
python -c "
import os, time

messages_dir = 'H:/Code/interai-protocol/viewer/messages'
cutoff = time.time() - 1800  # 30 minutes ago
found = False

for root, dirs, files in os.walk(messages_dir):
    for f in files:
        if f.endswith('.md'):
            path = os.path.join(root, f)
            if os.path.getmtime(path) > cutoff:
                found = True
                break
    if found:
        break

if found:
    print('{\"result\": \"Journal entry already posted.\"}')
else:
    print('{\"result\": \"Reminder: Code changes detected but no AICP journal entry posted. Consider posting a journal update.\"}')
"
exit 0
