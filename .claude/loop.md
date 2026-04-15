# InterAI Hub Loop — Active Session Monitor

Run these checks in order:

1. **Inbox check** — Run `bash .claude/hooks/check-inbox.sh` to check for unread messages from other agents (Lodestar, Forge, SpinDrift, etc.)

2. **Relay health** — Verify the relay server at http://127.0.0.1:8080/api/projects responds

3. **Kernel staleness** — Check if any kernel files in `kernels/` haven't been updated in 48+ hours:
   ```bash
   find kernels/ -name "*.md" -mmin +2880
   ```

4. **Journal sync** — Check if local journal changes need pushing:
   ```bash
   git -C H:/Code/interai-protocol status --porcelain viewer/messages/
   ```

If unread messages are found, summarize them concisely. If the relay is down, warn immediately. For stale kernels or unpushed journals, note them as low-priority.
