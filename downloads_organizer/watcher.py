"""Watcher de sistema de archivos - mueve archivos nuevos a 'Recién Descargado'."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any

import schedule
from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .classifier import classify_recent_files
from .config import get_downloads_path, get_recent_path, load_config
from .notifier import notify

logger = logging.getLogger(__name__)


class DownloadsHandler(FileSystemEventHandler):
    """Maneja eventos de nuevos archivos en la carpeta de descargas."""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self.recent_path = get_recent_path(config)
        self.downloads_path = get_downloads_path(config)
        self.recent_path.mkdir(parents=True, exist_ok=True)
        self._processing: set[str] = set()

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        self._handle_new_file(Path(event.src_path))

    def on_moved(self, event: FileMovedEvent) -> None:
        """Captura archivos que se mueven a la carpeta (ej. descargas completadas en Chrome)."""
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        if dest.parent == self.downloads_path:
            self._handle_new_file(dest)

    def _handle_new_file(self, file_path: Path) -> None:
        """Procesa un archivo nuevo: valida y mueve a Recién Descargado."""
        # Ignorar archivos ya en subcarpetas gestionadas
        if self._is_managed_folder(file_path):
            return

        # Ignorar archivos temporales o del sistema
        if not self._should_move(file_path):
            return

        # Evitar procesamiento doble
        key = str(file_path)
        if key in self._processing:
            return
        self._processing.add(key)

        try:
            # Esperar a que el archivo termine de copiarse (ej. descarga en progreso)
            if not self._wait_for_file_ready(file_path):
                logger.warning(f"Archivo no listo después de esperar: {file_path.name}")
                return

            self._move_to_recent(file_path)
        finally:
            self._processing.discard(key)

    def _move_to_recent(self, file_path: Path) -> None:
        """Mueve el archivo a la carpeta de Recién Descargado."""
        dest = self.recent_path / file_path.name

        # Evitar sobreescribir
        if dest.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            counter = 1
            while dest.exists():
                dest = self.recent_path / f"{stem}_{counter}{suffix}"
                counter += 1

        try:
            shutil.move(str(file_path), str(dest))
            logger.info(f"Nuevo archivo: {file_path.name} → Recién Descargado/")

            if self.config.get("notify_on_move", True):
                notify(
                    "📥 Nuevo archivo descargado",
                    file_path.name,
                    "Se clasificará mañana automáticamente",
                )
        except Exception as e:
            logger.error(f"Error al mover {file_path.name}: {e}")

    def _should_move(self, file_path: Path) -> bool:
        """Decide si el archivo debe ser movido."""
        name = file_path.name
        ext = file_path.suffix.lower()

        ignored_exts = self.config.get("ignored_extensions", [])
        ignored_names = self.config.get("ignored_names", [])

        if name in ignored_names:
            return False
        if ext in ignored_exts:
            return False
        if name.startswith("."):
            return False
        # Ignorar archivos de descarga incompleta
        if ext in (".crdownload", ".part", ".download", ".tmp"):
            return False
        return True

    def _is_managed_folder(self, file_path: Path) -> bool:
        """Verifica si el archivo ya está en una carpeta gestionada."""
        try:
            file_path.relative_to(self.recent_path)
            return True
        except ValueError:
            pass
        organized = self.downloads_path / self.config.get("organized_folder_name", "Organizado")
        try:
            file_path.relative_to(organized)
            return True
        except ValueError:
            return False

    def _wait_for_file_ready(self, file_path: Path, timeout: int = 30, interval: float = 1.0) -> bool:
        """Espera hasta que el archivo no esté creciendo (descarga completa)."""
        if not file_path.exists():
            return False

        prev_size = -1
        elapsed = 0

        while elapsed < timeout:
            try:
                current_size = file_path.stat().st_size
                if current_size == prev_size and current_size > 0:
                    return True
                prev_size = current_size
            except FileNotFoundError:
                return False

            time.sleep(interval)
            elapsed += interval

        return file_path.exists()


def setup_daily_scheduler(config: dict[str, Any]) -> None:
    """Configura la tarea de clasificación diaria."""
    classify_time = config.get("classify_time", "06:00")

    def run_classification():
        logger.info("Iniciando clasificación diaria...")
        fresh_config = load_config()  # Recargar config por si cambió
        classify_recent_files(fresh_config)

    schedule.every().day.at(classify_time).do(run_classification)
    logger.info(f"Clasificación diaria programada a las {classify_time}")


def start_watcher(config: dict[str, Any], foreground: bool = False) -> None:
    """Inicia el watcher de archivos y el scheduler diario."""
    downloads_path = get_downloads_path(config)

    if not downloads_path.exists():
        logger.error(f"La carpeta de descargas no existe: {downloads_path}")
        return

    # Crear carpeta de recién descargados
    recent_path = get_recent_path(config)
    recent_path.mkdir(parents=True, exist_ok=True)

    # Configurar watcher
    handler = DownloadsHandler(config)
    observer = Observer()
    observer.schedule(handler, str(downloads_path), recursive=False)
    observer.start()

    # Configurar scheduler diario
    setup_daily_scheduler(config)

    logger.info(f"Watcher activo en: {downloads_path}")
    logger.info("Downloads Organizer iniciado correctamente.")

    if foreground:
        notify("Downloads Organizer ✅", "Servicio iniciado", f"Monitoreando {downloads_path}")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Deteniendo watcher...")
    finally:
        observer.stop()
        observer.join()
        logger.info("Watcher detenido.")
