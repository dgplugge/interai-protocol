# Licensing

The Hub uses an offline, ECDSA-signed license key system with a 30-day
trial. Designed to be the right level of friction for a Phase 1 rollout
to thousands of users without a license server, while leaving a clean
upgrade path to online activation if abuse appears.

## States

| State | Behavior |
|---|---|
| **Trial** | First 30 days from first launch. Full speed. Status banner shows days remaining |
| **Licensed** | A valid signed key is loaded. Full speed. Status banner shows the licensed user |
| **Expired** | Trial elapsed and no valid license. **Degraded mode: 10-second delay before each agent dispatch.** All features still work; just slow |
| **Invalid** | License file present but signature does not verify, or major version does not match. Same degraded mode as Expired |

The user is never hard-locked out. The 10-second delay accumulates
quickly across a multi-agent round (60s for a 6-agent round) which
makes the friction obvious without breaking workflows.

## Trial tracking

First-run timestamp is stored in **two places** for defense in depth:

- `HKCU\Software\dgplugge\InterAI Hub\FirstRun` (registry, ISO-8601 string)
- `%APPDATA%\InterAI-Hub\.first-run` (hidden text file, ISO-8601)

On read, `TrialTracker` takes the **earlier** of the two values. If
one location is missing, it's silently restored from the other. A
clock-rewind is capped at the original 30-day window.

This is not perfect anti-piracy — a determined user can clear both
locations. The intent is to deter the casual "I'll uninstall and
reinstall" without requiring a server.

## License key format

A license key is a single-line base64-encoded string. Decoded, it's
a pipe-delimited line:

```
<user>|<majorVersion>|<issuedISO>|<expiresISO-or-"never">|<sigBase64>
```

The signature is **ECDSA P-256 + SHA-256** over the bytes of the
first four fields joined by `|`. Default signature format is IEEE
P1363 (`r || s`, 64 bytes raw — not DER/ASN.1).

Asymmetric crypto: the public key is embedded in the shipped binary
at `LicenseSigner.Pub_X` / `Pub_Y` (compile-time `Const` strings).
The matching private key lives only on the maintainer's machine at
`H:\Code\interai-hub-keys\signing.key`. **Even with full source
access, a user cannot forge new keys without that private key.**

The whole pipe-delimited line is base64-encoded for transport so the
key copy-pastes cleanly through email without word-wrap or whitespace
issues.

## Generating keys (maintainer only)

The `LicenseTool` console project (in the same solution; not shipped
to users) signs new keys.

```
LicenseTool.exe --user <email> [--version <major>] [--expires <yyyy-MM-dd|never>] [--key <path>]
```

Defaults:
- `--version` 1
- `--expires` never (perpetual)
- `--key` `H:\Code\interai-hub-keys\signing.key`

Examples:

```
LicenseTool.exe --user alice@example.com
LicenseTool.exe --user bob@example.com --version 1 --expires 2027-12-31
```

Output goes to stdout (the wire-format key, single line) with a
human-readable summary on stderr. Copy the stdout line verbatim into
the email you send the customer.

## Customer activation flow

1. Customer purchases.
2. Maintainer runs `LicenseTool` and emails the resulting line to
   the customer.
3. Customer opens the Hub, clicks **Register…** in the bottom-left
   controls panel.
4. Customer pastes the key into the multi-line textbox in
   `frmRegister`, clicks **Activate**.
5. `LicenseManager.TryActivate` parses the key, verifies the
   signature against the embedded public key, and checks the major
   version covers the running build.
6. On success the key is written to
   `%APPDATA%\InterAI-Hub\license.lic` so subsequent launches pick
   it up automatically. The dialog confirms with a MessageBox and
   closes.
7. On failure the dialog stays open with a red status message
   identifying the problem (empty input / bad signature / wrong
   version / expired).

## Version coverage

A license key contains a single integer `MajorVersion`. The license
covers **all releases sharing that major** — a 1.x license is valid
for 1.0, 1.1, 1.2, etc. Upgrading to 2.0 requires a new key.

This matches Don's "buy once for current version and subversion, may
have upgrade fee" intent. To make the rule stricter (e.g., one minor
version per key), change the comparison in `LicenseManager` from
`parsed.MajorVersion < RunningMajorVersion` to a more granular check.

## Files (shipped binary)

`AgentHubHelpers/`:

| File | Role |
|---|---|
| `LicenseStatus.vb` | Enum: Unknown / Trial / Licensed / Expired / Invalid |
| `LicenseKey.vb` | Wire-format model: parse + serialize |
| `LicenseSigner.vb` | ECDSA verify (and sign, used only by LicenseTool). Embeds public key |
| `TrialTracker.vb` | First-run timestamp persistence (registry + AppData) |
| `LicenseManager.vb` | Single static API: `CurrentStatus`, `TryActivate`, `StatusLine` |

`AgentHubView/frmRegister.vb` — the paste-and-activate modal dialog.

`AgentHubPresenter/AgentHubPresenter.vb` — `ApplyLicenseDelay()`
inserted before each `adapter.SendMessage` call; sleeps 10 seconds in
Expired/Invalid states. `LoadEvent` handler appends a `[license]`
status line to the activity log on session start.

`AAAAgentHub/AgentHubMain.vb` — `Sub Main` parses
`VerInfo.GetVersion()` for the major version, sets
`LicenseManager.RunningMajorVersion`, calls
`LicenseManager.Initialize()` before the presenter opens.

## Files (out-of-repo, maintainer only)

`H:\Code\interai-hub-keys\signing.key` — ECDSA P-256 private key.
**Never commit. Never email. Never paste.** If this file leaks, every
license key ever issued becomes potentially forgeable; you would need
to rotate the keypair, ship a new build with a new public key, and
re-issue all customer keys.

`LicenseTool/` (in the solution, but **not** in the ClickOnce
publish manifest) — the console exe that reads `signing.key` and
produces signed keys.

## Future enhancements (out of scope for Phase 1)

- **Online activation.** Add a tiny relay endpoint (Cloudflare Worker
  / Vercel function) that accepts `{key, machine_id_hash}` and
  returns `{ok, expires}`. Enables machine-binding (one key, one
  machine) and revocation (server can decline a stolen key). Cache
  the response locally for 30 days of offline grace. ~3-5 days of work
  when there's evidence of need.
- **Subscription billing.** Built on top of online activation: server
  returns `expires` based on Stripe subscription status; client
  re-checks at startup and after the cached grace period.
- **Third-party SaaS** (Cryptlex, LicenseSpring, KeyGen). Appropriate
  if the management overhead of self-hosted licensing exceeds the
  ~$30-100/mo SaaS cost. Phase 3.

## Trade-offs

The Phase 1 design accepts these limitations:

- **No revocation.** A leaked key is permanent until the keypair is
  rotated. With "thousands of users" target and asymmetric crypto,
  the realistic exposure is one customer's key being shared, not
  mass forgery.
- **Trial reset is possible.** A user can clear both registry and
  AppData to get a fresh trial. The dual-location storage deters
  the casual case; determined users always win.
- **No anti-debug / no obfuscation.** The .NET binary is decompilable,
  but the asymmetric private key is not in it.
- **No machine binding.** A purchased key works on every machine the
  customer copies the `.lic` file to. With online activation (Phase 2)
  this becomes per-machine.

These trade-offs are appropriate for a Phase 1 rollout. They become
worth revisiting only if measured abuse exceeds tolerance.
