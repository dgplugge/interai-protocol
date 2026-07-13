package transport

import (
	"context"
	"fmt"
	"log/slog"
	"sync"

	"github.com/klauspost/compress/zstd"
)

type Receiver struct {
	decoder   *zstd.Decoder
	decoderMu sync.Mutex
	logger    *slog.Logger
}

func NewReceiver(logger *slog.Logger) (*Receiver, error) {
	decoder, err := zstd.NewReader(nil)
	if err != nil {
		return nil, err
	}
	if logger == nil {
		logger = slog.Default()
	}
	return &Receiver{decoder: decoder, logger: logger}, nil
}

func (r *Receiver) ReceiveCompressed(ctx context.Context, req *ReceiveCompressedRequest) (*ReceiveCompressedResponse, error) {
	if req == nil {
		return nil, fmt.Errorf("request is required")
	}
	if req.Algorithm != AlgorithmZstd {
		return nil, fmt.Errorf("unsupported compression algorithm: %s", req.Algorithm)
	}
	if req.OriginalBytes > MaxJSONPayloadBytes {
		return nil, fmt.Errorf("payload exceeds %d byte limit", MaxJSONPayloadBytes)
	}

	r.decoderMu.Lock()
	payload, err := r.decoder.DecodeAll(req.Compressed, nil)
	r.decoderMu.Unlock()
	if err != nil {
		return nil, err
	}
	receivedHash := SHA256Hex(payload)
	fidelity := 0.0
	accepted := false
	var message string
	if int64(len(payload)) == req.OriginalBytes && receivedHash == req.OriginalSha256 {
		fidelity = 100.0
		accepted = true
	} else {
		message = "checksum or size mismatch"
	}

	r.logger.Info("payload received",
		"sender", req.Sender,
		"receiver", req.Receiver,
		"original_bytes", req.OriginalBytes,
		"received_bytes", len(payload),
		"fidelity_percent", fidelity,
		"accepted", accepted,
	)
	return &ReceiveCompressedResponse{
		Accepted:        accepted,
		Error:           message,
		OriginalBytes:   int64(len(payload)),
		ReceivedSha256:  receivedHash,
		FidelityPercent: fidelity,
	}, nil
}
