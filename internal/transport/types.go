package transport

const (
	MaxJSONPayloadBytes = 10 * 1024 * 1024
	MaxGRPCMessageBytes = 16 * 1024 * 1024
	AlgorithmZstd       = "zstd"
)

type TransmitRequest struct {
	Sender   string
	Receiver string
	Payload  []byte
}

type TransmitResponse struct {
	Accepted         bool
	Error            string
	LatencyMicros    int64
	OriginalBytes    int64
	CompressedBytes  int64
	CompressionRatio float64
	FidelityPercent  float64
	OriginalSha256   string
	ReceivedSha256   string
	Algorithm        string
}

type ReceiveCompressedRequest struct {
	Sender         string
	Receiver       string
	Algorithm      string
	OriginalBytes  int64
	Compressed     []byte
	OriginalSha256 string
	SentUnixNano   int64
}

type ReceiveCompressedResponse struct {
	Accepted        bool
	Error           string
	OriginalBytes   int64
	ReceivedSha256  string
	FidelityPercent float64
}
