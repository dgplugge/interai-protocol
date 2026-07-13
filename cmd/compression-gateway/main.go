package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"log/slog"
	"net"
	"os"

	"interai-protocol/internal/transport"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	mode := flag.String("mode", "gateway", "server mode: gateway or receiver")
	listenAddr := flag.String("listen", "127.0.0.1:9090", "gRPC listen address")
	receiverAddr := flag.String("receiver", "127.0.0.1:9091", "receiver gRPC address for gateway mode")
	serviceName := flag.String("service-name", "InterAICompressionGateway", "Windows service name")
	flag.Parse()

	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	ranAsService, err := maybeRunWindowsService(*serviceName, *mode, *listenAddr, *receiverAddr, logger)
	if err != nil {
		log.Fatal(err)
	}
	if ranAsService {
		return
	}

	switch *mode {
	case "receiver":
		runReceiver(*listenAddr, logger)
	case "gateway":
		runGateway(*listenAddr, *receiverAddr, logger)
	default:
		log.Fatalf("unsupported mode %q", *mode)
	}
}

func runReceiver(addr string, logger *slog.Logger) {
	server, cleanup, err := newReceiverServer(logger)
	if err != nil {
		log.Fatal(err)
	}
	defer cleanup()
	serve(server, addr, logger)
}

func runGateway(addr string, receiverAddr string, logger *slog.Logger) {
	server, cleanup, err := newGatewayServer(receiverAddr, logger)
	if err != nil {
		log.Fatal(err)
	}
	defer cleanup()
	serve(server, addr, logger)
}

func newReceiverServer(logger *slog.Logger) (*grpc.Server, func(), error) {
	server := grpc.NewServer(
		grpc.MaxRecvMsgSize(transport.MaxGRPCMessageBytes),
		grpc.MaxSendMsgSize(transport.MaxGRPCMessageBytes),
	)
	receiver, err := transport.NewReceiver(logger)
	if err != nil {
		return nil, nil, err
	}
	transport.RegisterReceiverAgentServer(server, receiver)
	return server, func() {}, nil
}

func newGatewayServer(receiverAddr string, logger *slog.Logger) (*grpc.Server, func(), error) {
	conn, err := grpc.DialContext(
		context.Background(),
		receiverAddr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(
			grpc.CallContentSubtype(transport.CodecName),
			grpc.MaxCallRecvMsgSize(transport.MaxGRPCMessageBytes),
			grpc.MaxCallSendMsgSize(transport.MaxGRPCMessageBytes),
		),
	)
	if err != nil {
		return nil, nil, err
	}

	gateway, err := transport.NewGateway(transport.NewReceiverAgentClient(conn), logger)
	if err != nil {
		_ = conn.Close()
		return nil, nil, err
	}
	server := grpc.NewServer(
		grpc.MaxRecvMsgSize(transport.MaxGRPCMessageBytes),
		grpc.MaxSendMsgSize(transport.MaxGRPCMessageBytes),
	)
	transport.RegisterCompressionGatewayServer(server, gateway)
	return server, func() { _ = conn.Close() }, nil
}

func serve(server *grpc.Server, addr string, logger *slog.Logger) {
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatal(err)
	}
	logger.Info("grpc server listening", "addr", addr)
	if err := server.Serve(lis); err != nil {
		log.Fatal(err)
	}
}

func startServer(server *grpc.Server, addr string, logger *slog.Logger) (net.Listener, <-chan error, error) {
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, nil, err
	}
	errCh := make(chan error, 1)
	go func() {
		logger.Info("grpc server listening", "addr", addr)
		if err := server.Serve(lis); err != nil {
			errCh <- err
			return
		}
		errCh <- nil
	}()
	return lis, errCh, nil
}

func newModeServer(mode string, listenAddr string, receiverAddr string, logger *slog.Logger) (*grpc.Server, func(), error) {
	switch mode {
	case "receiver":
		return newReceiverServer(logger)
	case "gateway":
		return newGatewayServer(receiverAddr, logger)
	default:
		return nil, nil, fmt.Errorf("unsupported mode %q", mode)
	}
}
