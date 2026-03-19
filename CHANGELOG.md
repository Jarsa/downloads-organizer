# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.4] - 2026-03-19
### Changed
- Los archivos recién descargados ya NO se mueven a una carpeta intermedia
  "Recién Descargado" — permanecen en la raíz de Downloads hasta que se
  clasifiquen, para que se puedan abrir directamente desde el navegador
- La clasificación (diaria o con `dorg classify`) ahora lee directamente
  desde la raíz de la carpeta de descargas, excluyendo la subcarpeta "Organizado"
- El watcher sigue activo para el scheduler diario, pero no mueve archivos
  al detectar una nueva descarga
- `dorg status` muestra "Archivos en Downloads" en lugar de "Archivos pendientes"
  (archivos en "Recién Descargado")

### Removed
- Carpeta intermedia "Recién Descargado" — ya no se crea ni se usa

## [1.0.3] - 2026-03-12
### Added
- Clasificación sin Ollama por tipo/extensión de archivo
  - Nueva función `_classify_by_type()`: detecta prioridad urgente/archivo
    usando palabras clave en el nombre del archivo; instaladores y
    comprimidos van a "archivo" por defecto
  - Flag `dorg classify --no-ollama` para clasificar sin Ollama
  - Config `ollama.enabled: false` para deshabilitar Ollama globalmente
  - Config `ollama.fallback: "auto"` para clasificar por tipo automáticamente
    cuando Ollama falla/timeout (en lugar de mostrar diálogo interactivo)
- 8 tests nuevos para `_classify_by_type()`

## [1.0.2] - 2026-03-12
### Fixed
- `dorg --version` ahora lee la versión del paquete instalado en lugar de tenerla hardcodeada

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
