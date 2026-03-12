# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-03-12
### Fixed
- Ollama timeout aumentado de 60s a 120s (mejora para máquinas con CPU lenta)
- `httpx.TimeoutException` ahora se captura por separado y muestra mensaje claro
  (antes todos los errores decían "No se pudo conectar con Ollama")
- `dorg logs` ya no crashea cuando líneas del log contienen corchetes `[...]`
  (pdfminer, watchdog, etc.) — se usa `rich.markup.escape` correctamente
- Loggers de pdfminer, httpx y httpcore silenciados en WARNING para evitar
  inundar el archivo de log con miles de líneas DEBUG

## [1.0.0] - 2025-01-01
### Added
- Initial release
- Real-time watcher with watchdog
- Daily classification with Ollama (local AI)
- Native notifications for macOS (osascript) and Linux (zenity)
- Interactive dialogs for low-confidence classifications
- New project approval suggested by AI
- launchd (macOS) and systemd (Linux) support
- Full CLI: install, uninstall, watch, classify, status, logs, config, projects
