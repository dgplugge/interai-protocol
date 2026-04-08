Option Strict On
Imports System.Text.Json.Serialization

Namespace InterAI.Protocol.AgentHub.Contracts

    ' Note: wire-format enum values in the OpenAPI doc use lower_snake_case
    ' (e.g., "round_robin"). Configure a custom enum converter when needed.
    <JsonConverter(GetType(JsonStringEnumConverter))>
    Public Enum DispatchMode
        RoundRobin
        Sequential
        Parallel
    End Enum

    <JsonConverter(GetType(JsonStringEnumConverter))>
    Public Enum MessageStatus
        Pending
        Sent
        Succeeded
        Failed
        Cancelled
        Skipped
    End Enum

    <JsonConverter(GetType(JsonStringEnumConverter))>
    Public Enum RoundStatus
        Queued
        Running
        Completed
        Partial
        Failed
        Cancelled
    End Enum

    Public Class ThreadSummaryDto
        <JsonPropertyName("id")>
        Public Property Id As String = ""

        <JsonPropertyName("title")>
        Public Property Title As String = ""

        <JsonPropertyName("createdAtUtc")>
        Public Property CreatedAtUtc As DateTimeOffset

        <JsonPropertyName("updatedAtUtc")>
        Public Property UpdatedAtUtc As DateTimeOffset

        <JsonPropertyName("lastMessageId")>
        Public Property LastMessageId As String = ""
    End Class

    Public Class MessageDto
        <JsonPropertyName("id")>
        Public Property Id As String = ""

        <JsonPropertyName("threadId")>
        Public Property ThreadId As String = ""

        <JsonPropertyName("from")>
        Public Property [From] As String = ""

        <JsonPropertyName("to")>
        Public Property [To] As List(Of String) = New()

        <JsonPropertyName("role")>
        Public Property Role As String = ""

        <JsonPropertyName("provider")>
        Public Property Provider As String = ""

        <JsonPropertyName("content")>
        Public Property Content As String = ""

        <JsonPropertyName("parentId")>
        Public Property ParentId As String?

        <JsonPropertyName("status")>
        Public Property Status As MessageStatus = MessageStatus.Pending

        <JsonPropertyName("createdAtUtc")>
        Public Property CreatedAtUtc As DateTimeOffset

        <JsonPropertyName("sentAtUtc")>
        Public Property SentAtUtc As DateTimeOffset?

        <JsonPropertyName("completedAtUtc")>
        Public Property CompletedAtUtc As DateTimeOffset?

        <JsonPropertyName("metadata")>
        Public Property Metadata As Dictionary(Of String, String) = New()
    End Class

    Public Class CreateMessageRequestDto
        <JsonPropertyName("from")>
        Public Property [From] As String = ""

        <JsonPropertyName("to")>
        Public Property [To] As List(Of String) = New()

        <JsonPropertyName("role")>
        Public Property Role As String = ""

        <JsonPropertyName("provider")>
        Public Property Provider As String = ""

        <JsonPropertyName("content")>
        Public Property Content As String = ""

        <JsonPropertyName("parentId")>
        Public Property ParentId As String?

        <JsonPropertyName("metadata")>
        Public Property Metadata As Dictionary(Of String, String) = New()
    End Class

    Public Class CreateMessageResponseDto
        <JsonPropertyName("message")>
        Public Property Message As MessageDto = New()
    End Class

    Public Class GetTranscriptResponseDto
        <JsonPropertyName("thread")>
        Public Property Thread As ThreadSummaryDto = New()

        <JsonPropertyName("messages")>
        Public Property Messages As List(Of MessageDto) = New()

        <JsonPropertyName("nextCursor")>
        Public Property NextCursor As String?
    End Class

    Public Class RetryPolicyDto
        <JsonPropertyName("maxRetries")>
        Public Property MaxRetries As Integer = 2

        <JsonPropertyName("initialBackoffMs")>
        Public Property InitialBackoffMs As Integer = 1000

        <JsonPropertyName("backoffMultiplier")>
        Public Property BackoffMultiplier As Double = 2.0
    End Class

    Public Class DispatchRequestDto
        <JsonPropertyName("mode")>
        Public Property Mode As DispatchMode = DispatchMode.RoundRobin

        <JsonPropertyName("speakerOrder")>
        Public Property SpeakerOrder As List(Of String) = New()

        <JsonPropertyName("sharePriorResponses")>
        Public Property SharePriorResponses As Boolean = True

        <JsonPropertyName("maxTurns")>
        Public Property MaxTurns As Integer = 4

        <JsonPropertyName("timeoutMsDefault")>
        Public Property TimeoutMsDefault As Integer = 30000

        <JsonPropertyName("retryPolicy")>
        Public Property RetryPolicy As RetryPolicyDto = New()

        <JsonPropertyName("targetMessageId")>
        Public Property TargetMessageId As String = ""
    End Class

    Public Class DispatchRoundDto
        <JsonPropertyName("roundId")>
        Public Property RoundId As String = ""

        <JsonPropertyName("threadId")>
        Public Property ThreadId As String = ""

        <JsonPropertyName("mode")>
        Public Property Mode As DispatchMode = DispatchMode.RoundRobin

        <JsonPropertyName("speakerOrder")>
        Public Property SpeakerOrder As List(Of String) = New()

        <JsonPropertyName("status")>
        Public Property Status As RoundStatus = RoundStatus.Queued

        <JsonPropertyName("startedAtUtc")>
        Public Property StartedAtUtc As DateTimeOffset?

        <JsonPropertyName("finishedAtUtc")>
        Public Property FinishedAtUtc As DateTimeOffset?
    End Class

    Public Class DispatchResultDto
        <JsonPropertyName("roundId")>
        Public Property RoundId As String = ""

        <JsonPropertyName("messageId")>
        Public Property MessageId As String = ""

        <JsonPropertyName("provider")>
        Public Property Provider As String = ""

        <JsonPropertyName("agent")>
        Public Property Agent As String = ""

        <JsonPropertyName("requestedTurn")>
        Public Property RequestedTurn As Integer

        <JsonPropertyName("durationMs")>
        Public Property DurationMs As Integer

        <JsonPropertyName("attemptCount")>
        Public Property AttemptCount As Integer

        <JsonPropertyName("providerRequestId")>
        Public Property ProviderRequestId As String?

        <JsonPropertyName("errorCode")>
        Public Property ErrorCode As String?

        <JsonPropertyName("errorMessage")>
        Public Property ErrorMessage As String?

        <JsonPropertyName("outputMessage")>
        Public Property OutputMessage As MessageDto?
    End Class

    Public Class DispatchResponseDto
        <JsonPropertyName("round")>
        Public Property Round As DispatchRoundDto = New()

        <JsonPropertyName("results")>
        Public Property Results As List(Of DispatchResultDto) = New()
    End Class

    Public Class ProviderDto
        <JsonPropertyName("name")>
        Public Property Name As String = ""

        <JsonPropertyName("providerType")>
        Public Property ProviderType As String = ""

        <JsonPropertyName("supportsStreaming")>
        Public Property SupportsStreaming As Boolean

        <JsonPropertyName("supportsTools")>
        Public Property SupportsTools As Boolean

        <JsonPropertyName("healthy")>
        Public Property Healthy As Boolean

        <JsonPropertyName("rateLimitRpm")>
        Public Property RateLimitRpm As Integer?

        <JsonPropertyName("timeoutMsDefault")>
        Public Property TimeoutMsDefault As Integer?
    End Class

    Public Class GetProvidersResponseDto
        <JsonPropertyName("providers")>
        Public Property Providers As List(Of ProviderDto) = New()
    End Class

    Public Class CancelDispatchRequestDto
        <JsonPropertyName("reason")>
        Public Property Reason As String?
    End Class

    Public Class AckResponseDto
        <JsonPropertyName("status")>
        Public Property Status As String = ""

        <JsonPropertyName("correlationId")>
        Public Property CorrelationId As String?
    End Class

    Public Class ApiErrorDto
        <JsonPropertyName("code")>
        Public Property Code As String = ""

        <JsonPropertyName("message")>
        Public Property Message As String = ""

        <JsonPropertyName("correlationId")>
        Public Property CorrelationId As String = ""

        <JsonPropertyName("details")>
        Public Property Details As Dictionary(Of String, String) = New()
    End Class

    Public Class ErrorResponseDto
        <JsonPropertyName("error")>
        Public Property [Error] As ApiErrorDto = New()
    End Class

End Namespace
