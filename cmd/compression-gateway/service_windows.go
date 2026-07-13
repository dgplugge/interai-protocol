//go:build windows

package main

import (
	"log/slog"
	"os"
	"path/filepath"
	"time"

	"golang.org/x/sys/windows/svc"
	"google.golang.org/grpc"
)

type compressionService struct {
	mode         string
	listenAddr   string
	receiverAddr string
	logger       *slog.Logger
	server       *grpc.Server
	cleanup      func()
}

func maybeRunWindowsService(serviceName string, mode string, listenAddr string, receiverAddr string, logger *slog.Logger) (bool, error) {
	isService, err := svc.IsWindowsService()
	if err != nil {
		return false, err
	}
	if !isService {
		return false, nil
	}
	logger = newServiceLogger(serviceName, logger)
	return true, svc.Run(serviceName, &compressionService{
		mode:         mode,
		listenAddr:   listenAddr,
		receiverAddr: receiverAddr,
		logger:       logger,
	})
}

func (s *compressionService) Execute(args []string, requests <-chan svc.ChangeRequest, changes chan<- svc.Status) (bool, uint32) {
	changes <- svc.Status{State: svc.StartPending}

	server, cleanup, err := newModeServer(s.mode, s.listenAddr, s.receiverAddr, s.logger)
	if err != nil {
		s.logger.Error("service startup failed", "error", err)
		return true, 1
	}
	s.server = server
	s.cleanup = cleanup

	_, errCh, err := startServer(s.server, s.listenAddr, s.logger)
	if err != nil {
		s.logger.Error("service listener failed", "error", err)
		s.cleanup()
		return true, 1
	}

	changes <- svc.Status{
		State:   svc.Running,
		Accepts: svc.AcceptStop | svc.AcceptShutdown,
	}

	for {
		select {
		case request := <-requests:
			switch request.Cmd {
			case svc.Interrogate:
				changes <- request.CurrentStatus
			case svc.Stop, svc.Shutdown:
				changes <- svc.Status{State: svc.StopPending}
				s.server.GracefulStop()
				s.cleanup()
				changes <- svc.Status{State: svc.Stopped}
				return false, 0
			default:
				s.logger.Warn("unsupported service control request", "command", request.Cmd)
			}
		case err := <-errCh:
			if err != nil {
				s.logger.Error("grpc server exited", "error", err)
				s.cleanup()
				return true, 1
			}
			s.cleanup()
			return false, 0
		case <-time.After(24 * time.Hour):
			if s.server == nil {
				s.cleanup()
				return true, 1
			}
		}
	}
}

func newServiceLogger(serviceName string, fallback *slog.Logger) *slog.Logger {
	logDir := filepath.Join(os.Getenv("ProgramData"), "InterAI", "CompressionMVP", "logs")
	if err := os.MkdirAll(logDir, 0755); err != nil {
		fallback.Warn("failed to create service log directory", "error", err)
		return fallback
	}
	logPath := filepath.Join(logDir, serviceName+".log")
	file, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		fallback.Warn("failed to open service log file", "path", logPath, "error", err)
		return fallback
	}
	return slog.New(slog.NewJSONHandler(file, nil))
}
