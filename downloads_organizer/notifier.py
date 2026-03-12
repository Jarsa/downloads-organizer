"""Notificaciones nativas para macOS y Linux con diálogos interactivos."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def notify(title: str, message: str, subtitle: str = "") -> None:
    """Envía una notificación nativa del sistema."""
    try:
        if IS_MACOS:
            _notify_macos(title, message, subtitle)
        elif IS_LINUX:
            _notify_linux(title, message)
    except Exception as e:
        logger.warning(f"No se pudo enviar notificación: {e}")


def ask_classification(
    file_path: Path,
    suggested_project: str | None,
    suggested_priority: str,
    suggested_type: str,
    reasoning: str,
    known_projects: list[str],
) -> dict | None:
    """
    Muestra un diálogo interactivo pidiendo al usuario que clasifique el archivo.
    Retorna dict con la decisión o None si se ignora.
    """
    file_name = file_path.name

    if IS_MACOS:
        return _ask_macos(file_name, suggested_project, suggested_priority, suggested_type, reasoning, known_projects)
    elif IS_LINUX:
        return _ask_linux(file_name, suggested_project, suggested_priority, suggested_type, reasoning, known_projects)
    else:
        logger.warning("Sistema operativo no soportado para diálogos interactivos.")
        return None


def ask_approve_project(project_name: str, file_name: str) -> str | None:
    """
    Pregunta al usuario si aprueba un nuevo proyecto sugerido por la IA.
    Retorna el nombre aprobado (puede ser modificado), o None para rechazar.
    """
    if IS_MACOS:
        return _approve_project_macos(project_name, file_name)
    elif IS_LINUX:
        return _approve_project_linux(project_name, file_name)
    return None


# ── macOS ──────────────────────────────────────────────────────────────────

def _notify_macos(title: str, message: str, subtitle: str = "") -> None:
    sub_part = f'subtitle "{subtitle}"' if subtitle else ""
    script = f'display notification "{message}" with title "{title}" {sub_part}'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def _ask_macos(
    file_name: str,
    suggested_project: str | None,
    suggested_priority: str,
    suggested_type: str,
    reasoning: str,
    known_projects: list[str],
) -> dict | None:
    project_info = suggested_project if suggested_project else "Sin proyecto detectado"
    priority_map = {"urgente": "🔴 Urgente", "normal": "🟡 Normal", "archivo": "📦 Archivo"}
    priority_label = priority_map.get(suggested_priority, suggested_priority)

    # Primer diálogo: mostrar sugerencia y pedir acción
    script = f'''
set msg to "Archivo: {file_name}

🤖 Sugerencia de IA:
• Prioridad: {priority_label}
• Tipo: {suggested_type}
• Proyecto: {project_info}
• Razón: {reasoning[:120]}..."

set resp to button returned of (display dialog msg ¬
    with title "Downloads Organizer" ¬
    buttons {{"Sin Clasificar", "Modificar", "Aprobar"}} ¬
    default button "Aprobar" ¬
    with icon note)
resp
'''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    choice = result.stdout.strip()

    if not choice or choice == "Sin Clasificar":
        return {"priority": "sin_clasificar", "project": "Sin Clasificar", "file_type": suggested_type}

    if choice == "Aprobar":
        return {"priority": suggested_priority, "project": suggested_project or "Sin Clasificar", "file_type": suggested_type}

    if choice == "Modificar":
        return _modify_classification_macos(file_name, suggested_priority, suggested_type, suggested_project, known_projects)

    return None


def _modify_classification_macos(
    file_name: str,
    priority: str,
    file_type: str,
    project: str | None,
    known_projects: list[str],
) -> dict | None:
    # Seleccionar prioridad
    priority_script = '''
set prioridades to {"🔴 Urgente", "🟡 Normal", "📦 Archivo", "Sin Clasificar"}
set sel to choose from list prioridades with title "Downloads Organizer" with prompt "Elige la prioridad para el archivo:"
if sel is false then return ""
return item 1 of sel
'''
    r = subprocess.run(["osascript", "-e", priority_script], capture_output=True, text=True)
    prio_choice = r.stdout.strip()
    if not prio_choice:
        return None

    prio_map = {"🔴 Urgente": "urgente", "🟡 Normal": "normal", "📦 Archivo": "archivo", "Sin Clasificar": "sin_clasificar"}
    new_priority = prio_map.get(prio_choice, "normal")

    # Seleccionar proyecto
    projects_list = known_projects + ["➕ Nuevo proyecto", "Sin proyecto"]
    projects_applescript = "{" + ", ".join(f'"{p}"' for p in projects_list) + "}"
    proj_script = f'''
set proyectos to {projects_applescript}
set sel to choose from list proyectos with title "Downloads Organizer" with prompt "Elige el proyecto:"
if sel is false then return ""
return item 1 of sel
'''
    r2 = subprocess.run(["osascript", "-e", proj_script], capture_output=True, text=True)
    proj_choice = r2.stdout.strip()

    if proj_choice == "➕ Nuevo proyecto":
        new_script = 'set r to text returned of (display dialog "Nombre del nuevo proyecto:" default answer "" with title "Downloads Organizer")\nr'
        r3 = subprocess.run(["osascript", "-e", new_script], capture_output=True, text=True)
        proj_choice = r3.stdout.strip() or "Sin Clasificar"
    elif proj_choice == "Sin proyecto" or not proj_choice:
        proj_choice = "Sin Clasificar"

    return {"priority": new_priority, "project": proj_choice, "file_type": file_type}


def _approve_project_macos(project_name: str, file_name: str) -> str | None:
    script = f'''
set resp to display dialog "La IA sugiere crear el proyecto:\\n\\n\\"{project_name}\\"\\n\\npara el archivo: {file_name}\\n\\n¿Aprobar, renombrar o rechazar?" ¬
    with title "Nuevo Proyecto Sugerido" ¬
    buttons {{"Rechazar", "Renombrar", "Aprobar"}} ¬
    default button "Aprobar" ¬
    with icon note
button returned of resp
'''
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    choice = r.stdout.strip()

    if choice == "Aprobar":
        return project_name
    if choice == "Renombrar":
        rename_script = f'set r to text returned of (display dialog "Nuevo nombre para el proyecto:" default answer "{project_name}" with title "Downloads Organizer")\nr'
        r2 = subprocess.run(["osascript", "-e", rename_script], capture_output=True, text=True)
        return r2.stdout.strip() or project_name
    return None


# ── Linux ──────────────────────────────────────────────────────────────────

def _notify_linux(title: str, message: str) -> None:
    subprocess.run(["notify-send", "-a", "Downloads Organizer", title, message], capture_output=True)


def _ask_linux(
    file_name: str,
    suggested_project: str | None,
    suggested_priority: str,
    suggested_type: str,
    reasoning: str,
    known_projects: list[str],
) -> dict | None:
    """Usa zenity para diálogos interactivos en Linux."""
    project_info = suggested_project or "Sin proyecto detectado"
    msg = (
        f"Archivo: {file_name}\n\n"
        f"🤖 Sugerencia de IA:\n"
        f"• Prioridad: {suggested_priority}\n"
        f"• Tipo: {suggested_type}\n"
        f"• Proyecto: {project_info}\n"
        f"• Razón: {reasoning[:120]}"
    )
    r = subprocess.run(
        ["zenity", "--question", "--title=Downloads Organizer",
         f"--text={msg}", "--ok-label=Aprobar", "--cancel-label=Sin Clasificar",
         "--extra-button=Modificar"],
        capture_output=True, text=True
    )
    stdout = r.stdout.strip()

    if r.returncode == 0:
        return {"priority": suggested_priority, "project": suggested_project or "Sin Clasificar", "file_type": suggested_type}
    if "Modificar" in stdout:
        return _modify_classification_linux(file_name, suggested_priority, suggested_type, suggested_project, known_projects)
    return {"priority": "sin_clasificar", "project": "Sin Clasificar", "file_type": suggested_type}


def _modify_classification_linux(
    file_name: str,
    priority: str,
    file_type: str,
    project: str | None,
    known_projects: list[str],
) -> dict | None:
    r = subprocess.run(
        ["zenity", "--list", "--title=Prioridad", "--text=Elige la prioridad:",
         "--column=Prioridad", "urgente", "normal", "archivo", "sin_clasificar"],
        capture_output=True, text=True
    )
    new_priority = r.stdout.strip() or priority

    options = known_projects + ["[Nuevo proyecto]"]
    r2 = subprocess.run(
        ["zenity", "--list", "--title=Proyecto", "--text=Elige el proyecto:",
         "--column=Proyecto"] + options,
        capture_output=True, text=True
    )
    proj = r2.stdout.strip()

    if proj == "[Nuevo proyecto]":
        r3 = subprocess.run(
            ["zenity", "--entry", "--title=Nuevo Proyecto", "--text=Nombre del proyecto:"],
            capture_output=True, text=True
        )
        proj = r3.stdout.strip() or "Sin Clasificar"

    return {"priority": new_priority, "project": proj or "Sin Clasificar", "file_type": file_type}


def _approve_project_linux(project_name: str, file_name: str) -> str | None:
    r = subprocess.run(
        ["zenity", "--question", "--title=Nuevo Proyecto Sugerido",
         f"--text=La IA sugiere crear el proyecto:\n\"{project_name}\"\npara: {file_name}",
         "--ok-label=Aprobar", "--cancel-label=Rechazar"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        return project_name
    return None
