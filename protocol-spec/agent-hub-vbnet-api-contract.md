# Agent Hub API Contract (VB.NET-first Draft)

## Purpose

Define a stable HTTP contract and DTO schema for a **VB.NET Agent Hub** that orchestrates
multi-agent round-table conversations while preserving AICP packet semantics.

This draft assumes:
- **AICP Viewer (web)** remains archive/browse/relay UI.
- **Agent Hub (VB.NET)** is the live orchestration UI.

## Design Goals

1. Deterministic turn-taking (round-robin, sequential, parallel).
2. Provider-agnostic adapters (OpenAI/Cursor-compatible, Anthropic, custom).
3. Reliable transcript ordering and delivery auditing.
4. Safe retries/cancellation/idempotency for dispatch operations.

## Base Contract Conventions

- Content type: `application/json`
- Time format: ISO-8601 UTC (`2026-04-07T16:21:00Z`)
- IDs: ULID or UUIDv7 recommended for sortability
- Auth: `Authorization: Bearer <token>`
- Idempotency for POST mutating routes:
  - `Idempotency-Key: <unique-client-key>`
- Optional trace header:
  - `X-Correlation-Id: <guid-or-ulid>`

## Core Routes

### 1) POST `/threads/{id}/messages`

Submit a new user/agent message into a thread.

Request body:
```json
{
  "from": "Don",
  "to": ["Pharos", "Lodestar", "Forge", "SpinDrift"],
  "role": "Orchestrator",
  "provider": "human",
  "content": "Please review the dispatch policy for this round.",
  "parentId": "msg_01J....",
  "metadata": {
    "project": "InterAI-Protocol",
    "domain": "Multi-Agent Systems",
    "priority": "MEDIUM"
  }
}
```

Response:
```json
{
  "message": { "...": "MessageDto" }
}
```

### 2) GET `/threads/{id}/transcript`

Read ordered conversation for a thread.

Query params:
- `after=<timestamp-or-message-id>` (optional)
- `limit=<int>` (optional)
- `agent=<name>` (optional filter)

Response:
```json
{
  "thread": { "...": "ThreadSummaryDto" },
  "messages": [ { "...": "MessageDto" } ],
  "nextCursor": "opaque-cursor-or-null"
}
```

### 3) POST `/threads/{id}/dispatch`

Run one dispatch round.

Request body:
```json
{
  "mode": "round_robin",
  "speakerOrder": ["Pharos", "Lodestar", "Forge", "SpinDrift"],
  "sharePriorResponses": true,
  "maxTurns": 4,
  "timeoutMsDefault": 30000,
  "retryPolicy": {
    "maxRetries": 2,
    "initialBackoffMs": 1000,
    "backoffMultiplier": 2.0
  },
  "targetMessageId": "msg_01J...."
}
```

Response:
```json
{
  "round": { "...": "DispatchRoundDto" },
  "results": [ { "...": "DispatchResultDto" } ]
}
```

### 4) GET `/providers`

List configured providers/agents and capabilities.

Response:
```json
{
  "providers": [
    {
      "name": "Pharos",
      "providerType": "anthropic",
      "supportsStreaming": true,
      "supportsTools": false,
      "healthy": true
    }
  ]
}
```

## Recommended Control/Realtime Routes

These are strongly recommended for production behavior.

- POST `/threads/{id}/dispatch/{roundId}/cancel`
- POST `/threads/{id}/messages/{messageId}/retry`
- GET `/threads/{id}/events` (SSE stream)

## Status & Error Model

### Message statuses
- `pending`
- `sent`
- `succeeded`
- `failed`
- `cancelled`
- `skipped`

### Round statuses
- `queued`
- `running`
- `completed`
- `partial`
- `failed`
- `cancelled`

### Standard error payload
```json
{
  "error": {
    "code": "provider_timeout",
    "message": "Provider timed out after 30000ms",
    "correlationId": "01J....",
    "details": {
      "provider": "Pharos",
      "roundId": "rnd_01J...."
    }
  }
}
```

## Turn-Taking Policy Contract

### `mode = round_robin`
- Use `speakerOrder` as cyclic order.
- One active speaker at a time.
- Preserve strict turn sequence.

### `mode = sequential`
- Execute `speakerOrder` once, in order.
- No overlap.

### `mode = parallel`
- Fan out to all selected speakers simultaneously.
- Aggregate by completion time but keep stable sort by `requestedTurn`.

## VB.NET DTO Schema (Draft)

```vbnet
Option Strict On
Imports System.Text.Json.Serialization

Public Enum DispatchMode
    RoundRobin
    Sequential
    Parallel
End Enum

Public Enum MessageStatus
    Pending
    Sent
    Succeeded
    Failed
    Cancelled
    Skipped
End Enum

Public Enum RoundStatus
    Queued
    Running
    Completed
    Partial
    Failed
    Cancelled
End Enum

Public Class ThreadSummaryDto
    Public Property Id As String = ""
    Public Property Title As String = ""
    Public Property CreatedAtUtc As DateTimeOffset
    Public Property UpdatedAtUtc As DateTimeOffset
    Public Property LastMessageId As String = ""
End Class

Public Class MessageDto
    Public Property Id As String = ""
    Public Property ThreadId As String = ""
    Public Property From As String = ""
    Public Property [To] As List(Of String) = New()
    Public Property Role As String = ""
    Public Property Provider As String = ""
    Public Property Content As String = ""
    Public Property ParentId As String = ""
    <JsonConverter(GetType(JsonStringEnumConverter))>
    Public Property Status As MessageStatus = MessageStatus.Pending
    Public Property CreatedAtUtc As DateTimeOffset
    Public Property SentAtUtc As DateTimeOffset?
    Public Property CompletedAtUtc As DateTimeOffset?
    Public Property Metadata As Dictionary(Of String, String) = New()
End Class

Public Class RetryPolicyDto
    Public Property MaxRetries As Integer = 2
    Public Property InitialBackoffMs As Integer = 1000
    Public Property BackoffMultiplier As Double = 2.0
End Class

Public Class DispatchRequestDto
    <JsonConverter(GetType(JsonStringEnumConverter))>
    Public Property Mode As DispatchMode = DispatchMode.RoundRobin
    Public Property SpeakerOrder As List(Of String) = New()
    Public Property SharePriorResponses As Boolean = True
    Public Property MaxTurns As Integer = 4
    Public Property TimeoutMsDefault As Integer = 30000
    Public Property RetryPolicy As RetryPolicyDto = New()
    Public Property TargetMessageId As String = ""
End Class

Public Class DispatchRoundDto
    Public Property RoundId As String = ""
    Public Property ThreadId As String = ""
    <JsonConverter(GetType(JsonStringEnumConverter))>
    Public Property Mode As DispatchMode = DispatchMode.RoundRobin
    Public Property SpeakerOrder As List(Of String) = New()
    <JsonConverter(GetType(JsonStringEnumConverter))>
    Public Property Status As RoundStatus = RoundStatus.Queued
    Public Property StartedAtUtc As DateTimeOffset?
    Public Property FinishedAtUtc As DateTimeOffset?
End Class

Public Class DispatchResultDto
    Public Property RoundId As String = ""
    Public Property MessageId As String = ""
    Public Property Provider As String = ""
    Public Property Agent As String = ""
    Public Property RequestedTurn As Integer
    Public Property DurationMs As Integer
    Public Property AttemptCount As Integer
    Public Property ProviderRequestId As String = ""
    Public Property ErrorCode As String = ""
    Public Property ErrorMessage As String = ""
    Public Property OutputMessage As MessageDto
End Class

Public Class ProviderDto
    Public Property Name As String = ""
    Public Property ProviderType As String = ""
    Public Property SupportsStreaming As Boolean
    Public Property SupportsTools As Boolean
    Public Property Healthy As Boolean
    Public Property RateLimitRpm As Integer?
    Public Property TimeoutMsDefault As Integer?
End Class

Public Class ApiErrorDto
    Public Property Code As String = ""
    Public Property Message As String = ""
    Public Property CorrelationId As String = ""
    Public Property Details As Dictionary(Of String, String) = New()
End Class
```

## Provider Adapter Contract (Implementation Interface)

```vbnet
Public Interface IAgentProviderAdapter
    ReadOnly Property Name As String
    Function SendAsync(request As ProviderSendRequest, ct As CancellationToken) As Task(Of ProviderSendResult)
    Function StreamAsync(request As ProviderSendRequest, ct As CancellationToken) As IAsyncEnumerable(Of ProviderStreamChunk)
End Interface
```

Required behaviors:
- timeout-aware
- cancellation-aware
- retries only at orchestrator level (avoid nested retry storms)
- return normalized error codes

## Initial Non-Functional Requirements

1. **Single active dispatch per thread** (lock/lease).
2. **Idempotent POST** via `Idempotency-Key`.
3. **Immutable transcript entries**; retries create new attempt records.
4. **Secrets only from environment/secure store**.
5. **Correlation IDs propagated** to all provider calls and logs.

## Versioning

- Contract version header (recommended):
  - `X-Agent-Hub-Contract-Version: 1`
- Breaking changes should increment major version and add compatibility window.
