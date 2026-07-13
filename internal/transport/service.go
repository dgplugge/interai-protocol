package transport

import (
	"context"

	"google.golang.org/grpc"
)

const (
	CompressionGatewayServiceName = "interai.transport.CompressionGateway"
	ReceiverAgentServiceName      = "interai.transport.ReceiverAgent"
)

type CompressionGatewayClient interface {
	TransmitPayload(ctx context.Context, in *TransmitRequest, opts ...grpc.CallOption) (*TransmitResponse, error)
}

type compressionGatewayClient struct {
	cc grpc.ClientConnInterface
}

func NewCompressionGatewayClient(cc grpc.ClientConnInterface) CompressionGatewayClient {
	return &compressionGatewayClient{cc: cc}
}

func (c *compressionGatewayClient) TransmitPayload(ctx context.Context, in *TransmitRequest, opts ...grpc.CallOption) (*TransmitResponse, error) {
	out := new(TransmitResponse)
	err := c.cc.Invoke(ctx, "/"+CompressionGatewayServiceName+"/TransmitPayload", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

type CompressionGatewayServer interface {
	TransmitPayload(context.Context, *TransmitRequest) (*TransmitResponse, error)
}

func RegisterCompressionGatewayServer(s grpc.ServiceRegistrar, srv CompressionGatewayServer) {
	s.RegisterService(&CompressionGateway_ServiceDesc, srv)
}

var CompressionGateway_ServiceDesc = grpc.ServiceDesc{
	ServiceName: CompressionGatewayServiceName,
	HandlerType: (*CompressionGatewayServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "TransmitPayload",
			Handler:    _CompressionGateway_TransmitPayload_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "transport.proto",
}

func _CompressionGateway_TransmitPayload_Handler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	in := new(TransmitRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(CompressionGatewayServer).TransmitPayload(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/" + CompressionGatewayServiceName + "/TransmitPayload",
	}
	handler := func(ctx context.Context, req any) (any, error) {
		return srv.(CompressionGatewayServer).TransmitPayload(ctx, req.(*TransmitRequest))
	}
	return interceptor(ctx, in, info, handler)
}

type ReceiverAgentClient interface {
	ReceiveCompressed(ctx context.Context, in *ReceiveCompressedRequest, opts ...grpc.CallOption) (*ReceiveCompressedResponse, error)
}

type receiverAgentClient struct {
	cc grpc.ClientConnInterface
}

func NewReceiverAgentClient(cc grpc.ClientConnInterface) ReceiverAgentClient {
	return &receiverAgentClient{cc: cc}
}

func (c *receiverAgentClient) ReceiveCompressed(ctx context.Context, in *ReceiveCompressedRequest, opts ...grpc.CallOption) (*ReceiveCompressedResponse, error) {
	out := new(ReceiveCompressedResponse)
	err := c.cc.Invoke(ctx, "/"+ReceiverAgentServiceName+"/ReceiveCompressed", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

type ReceiverAgentServer interface {
	ReceiveCompressed(context.Context, *ReceiveCompressedRequest) (*ReceiveCompressedResponse, error)
}

func RegisterReceiverAgentServer(s grpc.ServiceRegistrar, srv ReceiverAgentServer) {
	s.RegisterService(&ReceiverAgent_ServiceDesc, srv)
}

var ReceiverAgent_ServiceDesc = grpc.ServiceDesc{
	ServiceName: ReceiverAgentServiceName,
	HandlerType: (*ReceiverAgentServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "ReceiveCompressed",
			Handler:    _ReceiverAgent_ReceiveCompressed_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "transport.proto",
}

func _ReceiverAgent_ReceiveCompressed_Handler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	in := new(ReceiveCompressedRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(ReceiverAgentServer).ReceiveCompressed(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/" + ReceiverAgentServiceName + "/ReceiveCompressed",
	}
	handler := func(ctx context.Context, req any) (any, error) {
		return srv.(ReceiverAgentServer).ReceiveCompressed(ctx, req.(*ReceiveCompressedRequest))
	}
	return interceptor(ctx, in, info, handler)
}
