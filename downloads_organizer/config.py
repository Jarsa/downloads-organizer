"""Gestión de configuración de Downloads Organizer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir, user_log_dir

CONFIG_DIR = Path(user_config_dir("downloads-organizer"))
CONFIG_FILE = CONFIG_DIR / "config.yaml"
LOG_DIR = Path(user_log_dir("downloads-organizer"))
LOG_FILE = LOG_DIR / "organizer.log"

DEFAULT_CONFIG: dict[str, Any] = {
    "downloads_folder": str(Path.home() / "Downloads"),
    "recent_folder_name": "Recién Descargado",
    "organized_folder_name": "Organizado",
    "classify_time": "06:00",  # hora de clasificación diaria
    "ollama": {
        "enabled": True,              # False → clasificar solo por tipo/extensión
        "base_url": "http://localhost:11434",
        "model": "llama3.2",
        "timeout": 120,
        "confidence_threshold": 0.65,  # bajo este valor → pregunta al usuario
        "fallback": "ask",            # qué hacer si Ollama falla: "ask" o "auto"
    },
    "projects": [],  # proyectos aprobados por el usuario
    "file_types": {
        "documento": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".pages"],
        "hoja_de_calculo": [".xlsx", ".xls", ".csv", ".numbers", ".ods"],
        "presentacion": [".pptx", ".ppt", ".key", ".odp"],
        "imagen": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".heic", ".bmp", ".tiff"],
        "video": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv"],
        "audio": [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"],
        "codigo": [".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs", ".cpp", ".sh"],
        "comprimido": [".zip", ".tar", ".gz", ".rar", ".7z", ".dmg", ".pkg"],
        "instalador": [".exe", ".msi", ".deb", ".rpm", ".appimage"],
    },
    "priority_keywords": {
        "urgente": ["urgente", "urgent", "asap", "inmediato", "critico", "importante", "factura", "contrato", "deadline"],
        "archivo": ["backup", "old", "archive", "antiguo", "historico", "2020", "2021", "2022", "2023"],
    },
    "ignored_extensions": [".ds_store", ".tmp", ".crdownload", ".part", ".download"],
    "ignored_names": [".DS_Store", "Thumbs.db", "desktop.ini"],
    "min_file_age_hours": 0,  # mover inmediatamente al recién descargado
    "notify_on_move": True,
    "notify_on_classify": True,
}


def load_config() -> dict[str, Any]:
    """Carga la configuración desde el archivo YAML o crea una por defecto."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_FILE, encoding="utf-8") as f:
        user_config = yaml.safe_load(f) or {}

    # Merge con defaults para no perder claves nuevas
    merged = _deep_merge(DEFAULT_CONFIG.copy(), user_config)
    return merged


def save_config(config: dict[str, Any]) -> None:
    """Guarda la configuración en disco."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def add_project(project_name: str) -> None:
    """Agrega un proyecto aprobado a la configuración."""
    config = load_config()
    projects: list[str] = config.get("projects", [])
    if project_name not in projects:
        projects.append(project_name)
        config["projects"] = projects
        save_config(config)


def get_downloads_path(config: dict[str, Any]) -> Path:
    return Path(config["downloads_folder"]).expanduser()


def get_recent_path(config: dict[str, Any]) -> Path:
    return get_downloads_path(config) / config["recent_folder_name"]


def get_organized_path(config: dict[str, Any]) -> Path:
    return get_downloads_path(config) / config["organized_folder_name"]


def detect_file_type(file_path: Path, config: dict[str, Any]) -> str:
    """Detecta el tipo de archivo basado en su extensión."""
    ext = file_path.suffix.lower()
    for type_name, extensions in config["file_types"].items():
        if ext in extensions:
            return type_name
    return "otro"


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge profundo de diccionarios."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
