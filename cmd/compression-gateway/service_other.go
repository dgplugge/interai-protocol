//go:build !windows

package main

import "log/slog"

func maybeRunWindowsService(serviceName string, mode string, listenAddr string, receiverAddr string, logger *slog.Logger) (bool, error) {
	return false, nil
}
