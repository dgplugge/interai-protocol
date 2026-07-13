package transport_test

import (
	"context"
	"net"
	"strings"
	"testing"
	"time"

	"interai-protocol/internal/transport"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/test/bufconn"
)

const bufSize = 32 * 1024 * 1024

func TestSingleAPICallCompressesTransmits10MBJSON(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	receiverClient, stopReceiver := startReceiver(t, ctx)
	defer stopReceiver()

	gateway, err := transport.NewGateway(receiverClient, nil)
	if err != nil {
		t.Fatal(err)
	}
	gatewayClient, stopGateway := startGateway(t, ctx, gateway)
	defer stopGateway()

	payload := tenMBJSONBlob(t)
	start := time.Now()
	resp, err := gatewayClient.TransmitPayload(ctx, &transport.TransmitRequest{
		Sender:   "Forge",
		Receiver: "Pharos",
		Payload:  payload,
	})
	elapsed := time.Since(start)
	if err != nil {
		t.Fatal(err)
	}
	if !resp.Accepted {
		t.Fatalf("expected payload accepted, got error: %s", resp.Error)
	}
	if resp.FidelityPercent < 95.0 {
		t.Fatalf("fidelity %.2f%% is below target", resp.FidelityPercent)
	}
	if resp.OriginalSha256 != resp.ReceivedSha256 {
		t.Fatalf("checksum mismatch: original=%s received=%s", resp.OriginalSha256, resp.ReceivedSha256)
	}
	if resp.LatencyMicros > 100_000 {
		t.Fatalf("reported latency %dus exceeds 100ms target; wall clock was %s", resp.LatencyMicros, elapsed)
	}
	if resp.CompressedBytes >= resp.OriginalBytes {
		t.Fatalf("expected compression to reduce payload: original=%d compressed=%d", resp.OriginalBytes, resp.CompressedBytes)
	}
}

func TestGatewayRejectsPayloadsOver10MB(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()

	receiverClient, stopReceiver := startReceiver(t, ctx)
	defer stopReceiver()
	gateway, err := transport.NewGateway(receiverClient, nil)
	if err != nil {
		t.Fatal(err)
	}

	_, err = gateway.TransmitPayload(ctx, &transport.TransmitRequest{
		Sender:   "Forge",
		Receiver: "Pharos",
		Payload:  []byte(strings.Repeat("x", transport.MaxJSONPayloadBytes+1)),
	})
	if err == nil {
		t.Fatal("expected oversize payload to fail")
	}
}

func startReceiver(t *testing.T, ctx context.Context) (transport.ReceiverAgentClient, func()) {
	t.Helper()
	lis := bufconn.Listen(bufSize)
	server := grpc.NewServer(
		grpc.MaxRecvMsgSize(transport.MaxGRPCMessageBytes),
		grpc.MaxSendMsgSize(transport.MaxGRPCMessageBytes),
	)
	receiver, err := transport.NewReceiver(nil)
	if err != nil {
		t.Fatal(err)
	}
	transport.RegisterReceiverAgentServer(server, receiver)
	go func() {
		_ = server.Serve(lis)
	}()

	conn, err := dialBufConn(ctx, lis)
	if err != nil {
		t.Fatal(err)
	}
	return transport.NewReceiverAgentClient(conn), func() {
		_ = conn.Close()
		server.Stop()
	}
}

func startGateway(t *testing.T, ctx context.Context, gateway *transport.Gateway) (transport.CompressionGatewayClient, func()) {
	t.Helper()
	lis := bufconn.Listen(bufSize)
	server := grpc.NewServer(
		grpc.MaxRecvMsgSize(transport.MaxGRPCMessageBytes),
		grpc.MaxSendMsgSize(transport.MaxGRPCMessageBytes),
	)
	transport.RegisterCompressionGatewayServer(server, gateway)
	go func() {
		_ = server.Serve(lis)
	}()

	conn, err := dialBufConn(ctx, lis)
	if err != nil {
		t.Fatal(err)
	}
	return transport.NewCompressionGatewayClient(conn), func() {
		_ = conn.Close()
		server.Stop()
	}
}

func dialBufConn(ctx context.Context, lis *bufconn.Listener) (*grpc.ClientConn, error) {
	return grpc.DialContext(
		ctx,
		"bufnet",
		grpc.WithContextDialer(func(context.Context, string) (net.Conn, error) {
			return lis.Dial()
		}),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(
			grpc.CallContentSubtype(transport.CodecName),
			grpc.MaxCallRecvMsgSize(transport.MaxGRPCMessageBytes),
			grpc.MaxCallSendMsgSize(transport.MaxGRPCMessageBytes),
		),
	)
}

func tenMBJSONBlob(t *testing.T) []byte {
	t.Helper()
	prefix := `{"sender":"Forge","receiver":"Pharos","data":"`
	suffix := `"}`
	fillerSize := transport.MaxJSONPayloadBytes - len(prefix) - len(suffix)
	if fillerSize <= 0 {
		t.Fatal("invalid payload sizing")
	}
	return []byte(prefix + strings.Repeat("x", fillerSize) + suffix)
}
