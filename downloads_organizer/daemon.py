"""Instalación y gestión del servicio del sistema (launchd / systemd)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# ── macOS launchd ──────────────────────────────────────────────────────────

LAUNCHD_LABEL = "com.jarsa.downloads-organizer"
LAUNCHD_PLIST_PATH = Path.home() / "Library/LaunchAgents" / f"{LAUNCHD_LABEL}.plist"

LAUNCHD_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{executable}</string>
        <string>_run-daemon</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{log_dir}/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>{log_dir}/stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:{pipx_bin}</string>
        <key>HOME</key>
        <string>{home}</string>
    </dict>
</dict>
</plist>
"""

# ── Linux systemd ──────────────────────────────────────────────────────────

SYSTEMD_SERVICE_NAME = "downloads-organizer"
SYSTEMD_SERVICE_PATH = Path.home() / ".config/systemd/user" / f"{SYSTEMD_SERVICE_NAME}.service"

SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=Downloads Organizer - Organizador inteligente de descargas
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart={executable} _run-daemon
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=HOME={home}
Environment=PATH={pipx_bin}:/usr/local/bin:/usr/bin:/bin
Environment=DISPLAY=:0
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus

[Install]
WantedBy=default.target
"""


def get_executable() -> str:
    """Obtiene la ruta al ejecutable de downloads-organizer."""
    exe = shutil.which("downloads-organizer") or shutil.which("dorg")
    if exe:
        return exe
    # Buscar en pipx bin
    pipx_bin = Path.home() / ".local/bin/downloads-organizer"
    if pipx_bin.exists():
        return str(pipx_bin)
    return sys.executable + " -m downloads_organizer"


def get_log_dir() -> Path:
    from platformdirs import user_log_dir
    log_dir = Path(user_log_dir("downloads-organizer"))
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_pipx_bin() -> str:
    return str(Path.home() / ".local/bin")


def install_service() -> bool:
    """Instala el servicio del sistema."""
    if IS_MACOS:
        return _install_launchd()
    elif IS_LINUX:
        return _install_systemd()
    else:
        print("❌ Sistema operativo no soportado para instalación automática de servicio.")
        print("   Puedes correr manualmente: downloads-organizer watch")
        return False


def uninstall_service() -> bool:
    """Desinstala el servicio del sistema."""
    if IS_MACOS:
        return _uninstall_launchd()
    elif IS_LINUX:
        return _uninstall_systemd()
    return False


def is_service_running() -> bool:
    """Comprueba si el servicio está activo."""
    if IS_MACOS:
        r = subprocess.run(
            ["launchctl", "list", LAUNCHD_LABEL],
            capture_output=True, text=True
        )
        return r.returncode == 0
    elif IS_LINUX:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", SYSTEMD_SERVICE_NAME],
            capture_output=True, text=True
        )
        return r.stdout.strip() == "active"
    return False


def get_service_status() -> str:
    """Obtiene el estado detallado del servicio."""
    if IS_MACOS:
        r = subprocess.run(
            ["launchctl", "list", LAUNCHD_LABEL],
            capture_output=True, text=True
        )
        return r.stdout if r.returncode == 0 else "Servicio no instalado"
    elif IS_LINUX:
        r = subprocess.run(
            ["systemctl", "--user", "status", SYSTEMD_SERVICE_NAME],
            capture_output=True, text=True
        )
        return r.stdout
    return "Estado desconocido"


# ── macOS ──────────────────────────────────────────────────────────────────

def _install_launchd() -> bool:
    executable = get_executable()
    log_dir = get_log_dir()
    home = str(Path.home())
    pipx_bin = get_pipx_bin()

    plist_content = LAUNCHD_PLIST_TEMPLATE.format(
        label=LAUNCHD_LABEL,
        executable=executable,
        log_dir=log_dir,
        home=home,
        pipx_bin=pipx_bin,
    )

    LAUNCHD_PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHD_PLIST_PATH.write_text(plist_content)
    print(f"✅ Plist creado: {LAUNCHD_PLIST_PATH}")

    # Descargar si ya estaba cargado
    subprocess.run(
        ["launchctl", "unload", str(LAUNCHD_PLIST_PATH)],
        capture_output=True
    )

    r = subprocess.run(
        ["launchctl", "load", str(LAUNCHD_PLIST_PATH)],
        capture_output=True, text=True
    )

    if r.returncode == 0:
        print("✅ Servicio launchd instalado y activo.")
        return True
    else:
        print(f"❌ Error al cargar el servicio: {r.stderr}")
        return False


def _uninstall_launchd() -> bool:
    if not LAUNCHD_PLIST_PATH.exists():
        print("⚠️  El servicio no estaba instalado.")
        return True

    subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST_PATH)], capture_output=True)
    LAUNCHD_PLIST_PATH.unlink()
    print("✅ Servicio launchd eliminado.")
    return True


# ── Linux ──────────────────────────────────────────────────────────────────

def _install_systemd() -> bool:
    executable = get_executable()
    home = str(Path.home())
    pipx_bin = get_pipx_bin()
    uid = os.getuid()

    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        executable=executable,
        home=home,
        pipx_bin=pipx_bin,
        uid=uid,
    )

    SYSTEMD_SERVICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYSTEMD_SERVICE_PATH.write_text(service_content)
    print(f"✅ Servicio creado: {SYSTEMD_SERVICE_PATH}")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", SYSTEMD_SERVICE_NAME], check=True)
    print("✅ Servicio systemd instalado y activo.")
    return True


def _uninstall_systemd() -> bool:
    subprocess.run(["systemctl", "--user", "stop", SYSTEMD_SERVICE_NAME], capture_output=True)
    subprocess.run(["systemctl", "--user", "disable", SYSTEMD_SERVICE_NAME], capture_output=True)

    if SYSTEMD_SERVICE_PATH.exists():
        SYSTEMD_SERVICE_PATH.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)

    print("✅ Servicio systemd eliminado.")
    return True
