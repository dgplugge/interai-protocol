# Exception Handling

The Hub uses a global unhandled-exception handler ported from
OperatorHub's `HelperClasses` (Jeff Atwood / `codinghorror.com`
derivation). The port lives in the new `interai-hub/AgentHubHelpers`
project and is activated in `Sub Main` before any forms open.

## What it does

When an unhandled exception bubbles past every `try/catch` in the
application:

1. **Captures system info** — date/time, machine name, IP address,
   user identity, application domain, version, module GUID,
   assembly codebase and full name.
2. **Captures the exception** — type, message, source, target site,
   and an enhanced stack trace that walks `InnerException` chains.
3. **Logs to disk** — writes the captured text to
   `%APPDATA%\InterAI-Hub\Logs\<FriendlyName>.UnhandledExceptionLog.log`.
   Append mode, so multiple crashes accumulate in one file.
4. **Optionally takes a screenshot** of the desktop (off by default;
   enable via `LogToScreenshot=true` in `app.config`).
5. **Optionally writes to the Windows Event Log** (off by default;
   enable via `LogToEventLog=true` in `app.config`).
6. **Shows a dialog** to the user with a calm explanation of what
   happened, what was affected, what they can do about it, and a
   "More" panel with the full technical detail. The dialog references
   the public GitHub Issues URL where users can file bug reports.

The handler does **not** send email. The OperatorHub original sent
SMTP to a hardcoded NIH-internal mail server with the recipient
address baked in; that approach doesn't work for a publicly-distributed
desktop app and would put the maintainer's email address in every
copy of the binary. Bug reports route through the public GitHub repo
instead — see [Report a Bug button](#report-a-bug-button) below.

## Activation

`AAAAgentHub/AgentHubMain.vb`:

```vbnet
Public Sub Main()
    AgentHubHelpers.UnhandledExceptionManager.AddHandler()
    AgentHubHelpers.UnhandledExceptionManager.AppVersion = AgentHubHelpers.VerInfo.GetVersion()
    AgentHubPresenter.OpenPresenter()
End Sub
```

`AddHandler` registers handlers for both:

- `Application.ThreadException` (WinForms UI thread exceptions)
- `AppDomain.CurrentDomain.UnhandledException` (everything else)

When the debugger is attached, the handler intentionally *does not*
install — the Visual Studio "first chance exception" UI is the
correct error handler in that case. This is controlled by the
`IgnoreDebug` config setting, default `true`.

## Configuration

Optional keys in `app.config` `<appSettings>` (all read with the
`UnhandledExceptionManager/` prefix; missing keys use the listed
default):

| Key | Default | Effect |
|---|---|---|
| `UnhandledExceptionManager/LogToFile` | `true` | Write a text log under `%APPDATA%\InterAI-Hub\Logs` |
| `UnhandledExceptionManager/LogToEventLog` | `false` | Write a Windows Event Log entry (Application log, source = friendly name) |
| `UnhandledExceptionManager/TakeScreenshot` | `false` | Capture the desktop to a PNG/JPEG alongside the log file |
| `UnhandledExceptionManager/DisplayDialog` | `true` | Show the user-facing ExceptionDialog (off only for headless or test scenarios) |
| `UnhandledExceptionManager/IgnoreDebug` | `true` | Skip handler installation when running under the VS debugger |
| `UnhandledExceptionManager/KillAppOnException` | `false` | Force-kill the process after the dialog closes (use for unrecoverable failures) |

## Handled exceptions

For `try`/`catch` blocks where you want the same dialog UX without
the global handler:

```vbnet
Try
    DoSomethingRisky()
Catch ex As Exception
    AgentHubHelpers.HandledExceptionManager.ShowDialog(
        whatHappened := "Could not load the agent config.",
        howUserAffected := "The Hub will start with default settings.",
        whatUserCanDo := "Verify that agent-hub-config.json exists in the install directory.",
        ex := ex,
        Buttons := MessageBoxButtons.OK,
        Icon := MessageBoxIcon.Warning)
End Try
```

The same dialog renders, with the exception's stack trace pre-filled
in the "More" panel. The `(app)` token in dialog title text is
substituted with `AppSettings.AppProduct`; the `(contact)` token is
substituted with `BugReporting.ContactBlurb` (the GitHub Issues URL
prose).

## Report a Bug button

`frmAgentHub` has a `cmdReportBug` button at the bottom of
`grpControls` (below `cboProject`). On click it:

1. Builds a pre-filled issue body containing the app version, OS
   string, module GUID, and the log directory path.
2. URL-encodes the body and constructs a GitHub Issues link:
   `https://github.com/dgplugge/interai-hub-clickonce/issues/new?title=...&body=...`.
3. Opens the URL in the user's default browser via
   `Process.Start`.

The user sees a new-issue page already populated with system info;
they fill in *what happened* and *steps to reproduce*, optionally
attach the most recent log file, and submit.

The recipient repo is **hardcoded as a `Const` in
`AgentHubHelpers/BugReporting.vb`**:

```vbnet
Public Const BugReportUrl As String =
    "https://github.com/dgplugge/interai-hub-clickonce/issues/new"
```

This is intentional: the address is baked into the compiled
assembly at build time and is not read from any user-editable
configuration. Changing the destination requires editing this file
and recompiling.

## Why no email?

- The OperatorHub original used `mailfwd.nih.gov:25` (NIH-internal
  SMTP) and hardcoded recipient addresses. Neither generalizes to a
  publicly-distributed desktop app.
- Embedding SMTP credentials in a binary is a security anti-pattern.
- Corporate firewalls and ISP port-25 blocks make outbound SMTP
  from a desktop app unreliable.
- The "Report a Bug" → GitHub Issues flow gives users an issue
  tracker with attachments, threading, labels, and notifications —
  better than a one-shot email.

If a server-side relay is ever needed (push-style error reporting
without user action), the smallest version is a Cloudflare Worker
or Vercel function that accepts JSON and emails or files an issue
server-side. The client-side change would be a single
`HttpClient.PostAsync` from `UnhandledExceptionManager.GenericException-
Handler` — additive, not a redesign.
