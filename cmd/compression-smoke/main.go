package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"interai-protocol/internal/transport"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	gatewayAddr := flag.String("gateway", "127.0.0.1:9090", "compression gateway gRPC address")
	payloadPath := flag.String("payload", "", "path to a JSON payload file; when omitted, a generated 10MB payload is sent")
	sender := flag.String("sender", "Forge", "sender agent name")
	receiver := flag.String("receiver", "Pharos", "receiver agent name")
	timeout := flag.Duration("timeout", 5*time.Second, "request timeout")
	flag.Parse()

	payload, err := loadPayload(*payloadPath)
	if err != nil {
		exitf("payload error: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), *timeout)
	defer cancel()

	conn, err := grpc.DialContext(
		ctx,
		*gatewayAddr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(
			grpc.CallContentSubtype(transport.CodecName),
			grpc.MaxCallRecvMsgSize(transport.MaxGRPCMessageBytes),
			grpc.MaxCallSendMsgSize(transport.MaxGRPCMessageBytes),
		),
	)
	if err != nil {
		exitf("gateway connection failed: %v", err)
	}
	defer conn.Close()

	start := time.Now()
	resp, err := transport.NewCompressionGatewayClient(conn).TransmitPayload(ctx, &transport.TransmitRequest{
		Sender:   *sender,
		Receiver: *receiver,
		Payload:  payload,
	})
	wallClock := time.Since(start)
	if err != nil {
		exitf("transmit failed: %v", err)
	}

	status := "PASS"
	if !resp.Accepted || resp.FidelityPercent < 95.0 || resp.LatencyMicros > 100_000 {
		status = "FAIL"
	}
	report := map[string]any{
		"status":            status,
		"accepted":          resp.Accepted,
		"error":             resp.Error,
		"algorithm":         resp.Algorithm,
		"original_bytes":    resp.OriginalBytes,
		"compressed_bytes":  resp.CompressedBytes,
		"compression_ratio": resp.CompressionRatio,
		"fidelity_percent":  resp.FidelityPercent,
		"latency_micros":    resp.LatencyMicros,
		"wall_clock_micros": wallClock.Microseconds(),
		"original_sha256":   resp.OriginalSha256,
		"received_sha256":   resp.ReceivedSha256,
	}
	encoded, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		exitf("report encoding failed: %v", err)
	}
	fmt.Println(string(encoded))
	if status != "PASS" {
		os.Exit(1)
	}
}

func loadPayload(path string) ([]byte, error) {
	if path != "" {
		payload, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		if !json.Valid(payload) {
			return nil, fmt.Errorf("%s is not valid JSON", path)
		}
		return payload, nil
	}
	return tenMBJSONBlob(), nil
}

func tenMBJSONBlob() []byte {
	prefix := `{"sender":"Forge","receiver":"Pharos","data":"`
	suffix := `"}`
	fillerSize := transport.MaxJSONPayloadBytes - len(prefix) - len(suffix)
	return []byte(prefix + strings.Repeat("x", fillerSize) + suffix)
}

func exitf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
	os.Exit(1)
}
