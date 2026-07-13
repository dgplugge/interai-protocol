package transport

import (
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/klauspost/compress/zstd"
)

type Gateway struct {
	receiver        ReceiverAgentClient
	encoder         *zstd.Encoder
	encoderMu       sync.Mutex
	maxPayloadBytes int
	logger          *slog.Logger
}

func NewGateway(receiver ReceiverAgentClient, logger *slog.Logger) (*Gateway, error) {
	encoder, err := zstd.NewWriter(nil, zstd.WithEncoderLevel(zstd.SpeedFastest))
	if err != nil {
		return nil, err
	}
	if logger == nil {
		logger = slog.Default()
	}
	return &Gateway{
		receiver:        receiver,
		encoder:         encoder,
		maxPayloadBytes: MaxJSONPayloadBytes,
		logger:          logger,
	}, nil
}

func (g *Gateway) TransmitPayload(ctx context.Context, req *TransmitRequest) (*TransmitResponse, error) {
	start := time.Now()
	if req == nil {
		return nil, fmt.Errorf("request is required")
	}
	if len(req.Payload) == 0 {
		return nil, fmt.Errorf("payload is required")
	}
	if len(req.Payload) > g.maxPayloadBytes {
		return nil, fmt.Errorf("payload exceeds %d byte limit", g.maxPayloadBytes)
	}
	if req.Sender == "" || req.Receiver == "" {
		return nil, fmt.Errorf("sender and receiver are required")
	}

	originalHash := SHA256Hex(req.Payload)
	g.encoderMu.Lock()
	compressed := g.encoder.EncodeAll(req.Payload, make([]byte, 0, len(req.Payload)/2))
	g.encoderMu.Unlock()
	receiverResp, err := g.receiver.ReceiveCompressed(ctx, &ReceiveCompressedRequest{
		Sender:         req.Sender,
		Receiver:       req.Receiver,
		Algorithm:      AlgorithmZstd,
		OriginalBytes:  int64(len(req.Payload)),
		Compressed:     compressed,
		OriginalSha256: originalHash,
		SentUnixNano:   start.UnixNano(),
	})
	if err != nil {
		return nil, err
	}

	latency := time.Since(start)
	resp := &TransmitResponse{
		Accepted:         receiverResp.Accepted,
		Error:            receiverResp.Error,
		LatencyMicros:    latency.Microseconds(),
		OriginalBytes:    int64(len(req.Payload)),
		CompressedBytes:  int64(len(compressed)),
		CompressionRatio: float64(len(compressed)) / float64(len(req.Payload)),
		FidelityPercent:  receiverResp.FidelityPercent,
		OriginalSha256:   originalHash,
		ReceivedSha256:   receiverResp.ReceivedSha256,
		Algorithm:        AlgorithmZstd,
	}

	g.logger.Info("payload transmitted",
		"sender", req.Sender,
		"receiver", req.Receiver,
		"original_bytes", resp.OriginalBytes,
		"compressed_bytes", resp.CompressedBytes,
		"latency_micros", resp.LatencyMicros,
		"fidelity_percent", resp.FidelityPercent,
		"accepted", resp.Accepted,
	)
	return resp, nil
}
