"""Clasificación inteligente de archivos usando Ollama (IA local)."""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

import httpx

from .config import add_project, detect_file_type, get_organized_path
from .notifier import ask_approve_project, ask_classification, notify

logger = logging.getLogger(__name__)

PRIORITY_DIRS = {
    "urgente": "🔴 Urgente",
    "normal": "🟡 Normal",
    "archivo": "📦 Archivo",
    "sin_clasificar": "❓ Sin Clasificar",
}


def extract_content_preview(file_path: Path, max_chars: int = 2000) -> str:
    """Extrae una vista previa del contenido del archivo para el análisis."""
    suffix = file_path.suffix.lower()

    try:
        # Archivos de texto plano
        if suffix in (".txt", ".md", ".rst", ".log", ".csv", ".json", ".yaml", ".yml", ".xml", ".html", ".htm"):
            return file_path.read_text(encoding="utf-8", errors="ignore")[:max_chars]

        # Código fuente
        if suffix in (".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".sh", ".rb", ".php"):
            return file_path.read_text(encoding="utf-8", errors="ignore")[:max_chars]

        # PDF
        if suffix == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page in pdf.pages[:3]:
                        text += (page.extract_text() or "") + "\n"
                    return text[:max_chars]
            except Exception as e:
                logger.debug(f"No se pudo leer PDF {file_path.name}: {e}")

        # Word (.docx)
        if suffix == ".docx":
            try:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join(p.text for p in doc.paragraphs[:30])
                return text[:max_chars]
            except Exception as e:
                logger.debug(f"No se pudo leer DOCX {file_path.name}: {e}")

    except Exception as e:
        logger.debug(f"Error leyendo contenido de {file_path.name}: {e}")

    return ""


def classify_file_with_ollama(
    file_path: Path,
    file_type: str,
    known_projects: list[str],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Envía el archivo a Ollama para clasificación.
    Retorna dict con: priority, file_type, project, is_new_project, confidence, reasoning
    """
    ollama_cfg = config["ollama"]
    base_url = ollama_cfg["base_url"]
    model = ollama_cfg["model"]
    timeout = ollama_cfg.get("timeout", 60)

    content_preview = extract_content_preview(file_path)
    size_bytes = file_path.stat().st_size
    size_str = _format_size(size_bytes)

    projects_str = ", ".join(known_projects) if known_projects else "Ninguno aún"

    prompt = f"""Eres un asistente que organiza archivos descargados. Analiza este archivo y clasifícalo.

INFORMACIÓN DEL ARCHIVO:
- Nombre: {file_path.name}
- Tipo detectado: {file_type}
- Tamaño: {size_str}
- Vista previa del contenido:
{content_preview[:1500] if content_preview else "(no disponible para este tipo de archivo)"}

PROYECTOS EXISTENTES DEL USUARIO: {projects_str}

INSTRUCCIONES:
1. Determina la PRIORIDAD:
   - "urgente": facturas por pagar, contratos, documentos legales, fechas límite inminentes, solicitudes urgentes
   - "normal": documentos de trabajo habituales, imágenes, referencias, materiales de estudio
   - "archivo": backups, documentos históricos, archivos de más de 1 año, instaladores ya usados

2. Determina el PROYECTO o contexto más apropiado (trabajo, personal, finanzas, estudio, etc.)
   - Preferentemente usa uno de los proyectos existentes si encaja
   - Si no encaja en ninguno, sugiere uno nuevo con is_new_project: true

3. Tu CONFIANZA debe reflejar qué tan seguro estás con base en la información disponible

Responde ÚNICAMENTE con JSON válido, sin texto adicional:
{{
  "priority": "urgente|normal|archivo",
  "file_type": "{file_type}",
  "project": "nombre del proyecto",
  "is_new_project": false,
  "confidence": 0.85,
  "reasoning": "Explicación breve en español de por qué elegiste esta clasificación"
}}"""

    try:
        response = httpx.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        raw = response.json().get("response", "")

        # Extraer JSON del response (puede tener texto adicional)
        json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if not json_match:
            logger.warning(f"No se pudo extraer JSON del response de Ollama: {raw[:200]}")
            return None

        result = json.loads(json_match.group())
        # Validar campos requeridos
        for field in ("priority", "project", "confidence"):
            if field not in result:
                logger.warning(f"Campo faltante en respuesta de Ollama: {field}")
                return None

        result["file_type"] = file_type  # Usamos el tipo detectado localmente
        return result

    except httpx.ConnectError:
        logger.error("No se pudo conectar a Ollama. ¿Está corriendo? (ollama serve)")
        notify("Downloads Organizer ⚠️", "No se puede conectar a Ollama. Verifica que esté activo.")
        return {"_error": "connect"}
    except httpx.TimeoutException:
        logger.error(f"Ollama tardó más de {timeout}s en responder. Considera aumentar ollama.timeout en la config.")
        notify("Downloads Organizer ⚠️", f"Ollama no respondió en {timeout}s.", "Aumenta ollama.timeout en la config.")
        return {"_error": "timeout"}
    except Exception as e:
        logger.error(f"Error al clasificar con Ollama: {e}")
        return {"_error": str(e)}


def move_file_to_organized(
    file_path: Path,
    priority: str,
    project: str,
    file_type: str,
    config: dict[str, Any],
) -> Path:
    """Mueve el archivo a la carpeta organizada según su clasificación."""
    organized = get_organized_path(config)
    priority_dir = PRIORITY_DIRS.get(priority, "❓ Sin Clasificar")

    # Estructura: Organizado / 🔴 Urgente / Trabajo / documentos /
    dest_dir = organized / priority_dir / project / file_type
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / file_path.name

    # Evitar sobreescribir
    if dest_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        counter = 1
        while dest_path.exists():
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.move(str(file_path), str(dest_path))
    logger.info(f"Movido: {file_path.name} → {dest_path.relative_to(Path(config['downloads_folder']))}")
    return dest_path


def classify_recent_files(config: dict[str, Any], use_ollama: bool = True) -> None:
    """
    Clasifica todos los archivos en la carpeta 'Recién Descargado'.
    Este proceso corre diariamente.
    """
    from .config import get_recent_path

    recent_path = get_recent_path(config)
    if not recent_path.exists():
        logger.info("No hay carpeta de recién descargados.")
        return

    files = [f for f in recent_path.iterdir() if f.is_file() and _should_process(f, config)]

    if not files:
        logger.info("No hay archivos para clasificar hoy.")
        return

    logger.info(f"Clasificando {len(files)} archivos...")
    notify(
        "Downloads Organizer",
        f"Clasificando {len(files)} archivo(s) descargado(s)...",
        "Proceso diario iniciado"
    )

    known_projects: list[str] = config.get("projects", [])
    classified = 0
    skipped = 0

    for file_path in files:
        try:
            result = _classify_single_file(file_path, known_projects, config, use_ollama=use_ollama)
            if result:
                classified += 1
                # Actualizar lista de proyectos conocidos para los siguientes archivos
                proj = result.get("project", "")
                if proj and proj not in known_projects and proj != "Sin Clasificar":
                    known_projects.append(proj)
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"Error al procesar {file_path.name}: {e}")
            skipped += 1

    notify(
        "Downloads Organizer ✅",
        f"Clasificación completa: {classified} archivos organizados, {skipped} pendientes.",
    )


def _classify_by_type(file_type: str, file_path: Path, config: dict[str, Any]) -> dict:
    """
    Clasifica un archivo basándose únicamente en su tipo/extensión y palabras
    clave en el nombre del archivo. No requiere Ollama.
    """
    name_lower = file_path.name.lower()
    priority_keywords = config.get("priority_keywords", {})

    priority = "normal"
    for kw in priority_keywords.get("urgente", []):
        if kw in name_lower:
            priority = "urgente"
            break
    if priority == "normal":
        for kw in priority_keywords.get("archivo", []):
            if kw in name_lower:
                priority = "archivo"
                break

    # Instaladores y comprimidos → archivo por defecto (ya procesados normalmente)
    if file_type in ("instalador", "comprimido") and priority == "normal":
        priority = "archivo"

    # Usar el primer proyecto configurado, o Sin Clasificar
    projects = config.get("projects", [])
    project = projects[0] if projects else "Sin Clasificar"

    return {"priority": priority, "project": project, "file_type": file_type}


def _classify_single_file(
    file_path: Path,
    known_projects: list[str],
    config: dict[str, Any],
    use_ollama: bool = True,
) -> dict | None:
    """Clasifica y mueve un archivo individual."""
    file_type = detect_file_type(file_path, config)
    ollama_cfg = config.get("ollama", {})
    ollama_enabled = use_ollama and ollama_cfg.get("enabled", True)
    fallback = ollama_cfg.get("fallback", "ask")

    threshold = ollama_cfg.get("confidence_threshold", 0.65)
    decision = None

    if not ollama_enabled:
        # Modo sin Ollama: clasificar directamente por tipo
        decision = _classify_by_type(file_type, file_path, config)
        logger.info(f"[sin-ollama] {file_path.name} → {decision['priority']} / {decision['project']}")
    else:
        ollama_result = classify_file_with_ollama(file_path, file_type, known_projects, config)

        if ollama_result is None or "_error" in (ollama_result or {}):
            error_code = (ollama_result or {}).get("_error", "connect")
            if error_code == "timeout":
                reasoning = "Ollama tardó demasiado en responder. Considera aumentar ollama.timeout en la configuración."
            elif error_code == "connect":
                reasoning = "No se pudo conectar con Ollama. Verifica que esté corriendo (ollama serve)."
            else:
                reasoning = f"Error al contactar Ollama: {error_code}"

            if fallback == "auto":
                decision = _classify_by_type(file_type, file_path, config)
                logger.info(f"[fallback-auto] {file_path.name} → {decision['priority']} / {decision['project']} ({reasoning})")
            else:
                decision = ask_classification(
                    file_path,
                    suggested_project=None,
                    suggested_priority="normal",
                    suggested_type=file_type,
                    reasoning=reasoning,
                    known_projects=known_projects,
                )
        elif ollama_result["confidence"] < threshold or ollama_result.get("is_new_project", False):
            # Baja confianza O proyecto nuevo → aprobar proyecto si aplica
            project_name = ollama_result["project"]
            approved_project = project_name

            if ollama_result.get("is_new_project", False) and project_name not in known_projects:
                approved = ask_approve_project(project_name, file_path.name)
                if approved:
                    approved_project = approved
                    add_project(approved_project)
                else:
                    approved_project = "Sin Clasificar"

            if ollama_result["confidence"] < threshold:
                decision = ask_classification(
                    file_path,
                    suggested_project=approved_project,
                    suggested_priority=ollama_result["priority"],
                    suggested_type=file_type,
                    reasoning=ollama_result.get("reasoning", ""),
                    known_projects=known_projects,
                )
            else:
                decision = {
                    "priority": ollama_result["priority"],
                    "project": approved_project,
                    "file_type": file_type,
                }
        else:
            # Alta confianza con proyecto conocido → clasificar automáticamente
            decision = {
                "priority": ollama_result["priority"],
                "project": ollama_result["project"],
                "file_type": file_type,
            }

    if decision:
        move_file_to_organized(
            file_path,
            priority=decision["priority"],
            project=decision["project"],
            file_type=decision["file_type"],
            config=config,
        )
        if config.get("notify_on_classify"):
            notify(
                "Archivo organizado 📁",
                f"{file_path.name}",
                f"→ {decision['project']} / {decision['priority']}",
            )
        return decision

    return None


def _should_process(file_path: Path, config: dict[str, Any]) -> bool:
    """Determina si un archivo debe ser procesado."""
    name = file_path.name
    ext = file_path.suffix.lower()

    if name in config.get("ignored_names", []):
        return False
    if ext in config.get("ignored_extensions", []):
        return False
    if name.startswith("."):
        return False
    return True


def _format_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
