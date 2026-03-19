"""Watcher de sistema de archivos — programa clasificación diaria sin mover archivos."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import schedule
from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .classifier import classify_downloads
from .config import get_downloads_path, load_config
from .notifier import notify

logger = logging.getLogger(__name__)


class DownloadsHandler(FileSystemEventHandler):
    """Observa la carpeta de descargas solo para logging; no mueve archivos."""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self.downloads_path = get_downloads_path(config)

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        if self._should_log(file_path):
            logger.debug(f"Nuevo archivo detectado: {file_path.name}")

    def on_moved(self, event: FileMovedEvent) -> None:
        """Captura archivos que se mueven a la carpeta (ej. descargas completadas en Chrome)."""
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        if dest.parent == self.downloads_path and self._should_log(dest):
            logger.debug(f"Archivo descargado: {dest.name}")

    def _should_log(self, file_path: Path) -> bool:
        """Decide si vale la pena registrar el archivo."""
        name = file_path.name
        ext = file_path.suffix.lower()
        if name.startswith("."):
            return False
        if ext in (".crdownload", ".part", ".download", ".tmp"):
            return False
        return True

    def _is_managed_folder(self, file_path: Path) -> bool:
        """Verifica si el archivo ya está en una carpeta gestionada."""
        organized = self.downloads_path / self.config.get("organized_folder_name", "Organizado")
        try:
            file_path.relative_to(organized)
            return True
        except ValueError:
            return False


def setup_daily_scheduler(config: dict[str, Any]) -> None:
    """Configura la tarea de clasificación diaria."""
    classify_time = config.get("classify_time", "06:00")

    def run_classification():
        logger.info("Iniciando clasificación diaria...")
        fresh_config = load_config()  # Recargar config por si cambió
        classify_downloads(fresh_config)

    schedule.every().day.at(classify_time).do(run_classification)
    logger.info(f"Clasificación diaria programada a las {classify_time}")


def start_watcher(config: dict[str, Any], foreground: bool = False) -> None:
    """Inicia el watcher de archivos y el scheduler diario."""
    downloads_path = get_downloads_path(config)

    if not downloads_path.exists():
        logger.error(f"La carpeta de descargas no existe: {downloads_path}")
        return

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
