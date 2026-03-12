"""CLI principal de Downloads Organizer."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from .config import (
    CONFIG_FILE,
    LOG_FILE,
    get_downloads_path,
    get_organized_path,
    get_recent_path,
    load_config,
    save_config,
)

console = Console()


def _setup_logging(verbose: bool = False) -> None:
    from .config import LOG_FILE
    LOG_DIR = Path(str(LOG_FILE).replace("organizer.log", ""))
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout) if verbose else logging.NullHandler(),
        ],
    )
    # Silenciar librerías externas que inundan el log con DEBUG
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


@click.group()
@click.version_option(package_name="downloads-organizer", prog_name="Downloads Organizer")
def main():
    """
    📥 Downloads Organizer — Organiza tu carpeta de descargas con IA local (Ollama).

    \b
    Flujo:
      1. Los archivos nuevos van a 'Recién Descargado/' al instante
      2. Cada día a las 06:00 AM se clasifican con IA
      3. Se organizan en: Organizado / Prioridad / Proyecto / Tipo
    """
    pass


@main.command()
def install():
    """Instala el servicio del sistema (launchd en macOS, systemd en Linux)."""
    from .daemon import install_service

    console.print(Panel.fit(
        "[bold green]Instalando Downloads Organizer[/bold green]\n"
        "El servicio se iniciará automáticamente con cada sesión.",
        border_style="green"
    ))

    # Crear config por defecto si no existe
    config = load_config()
    downloads_path = get_downloads_path(config)

    if not downloads_path.exists():
        console.print(f"[yellow]⚠️  La carpeta de descargas no existe: {downloads_path}[/yellow]")
        new_path = click.prompt("Ingresa la ruta correcta", default=str(Path.home() / "Downloads"))
        config["downloads_folder"] = new_path
        save_config(config)

    console.print(f"[cyan]📁 Carpeta monitoreada:[/cyan] {get_downloads_path(config)}")
    console.print(f"[cyan]📥 Recién descargado:[/cyan] {get_recent_path(config)}")
    console.print(f"[cyan]📂 Organizado en:[/cyan] {get_organized_path(config)}")
    console.print(f"[cyan]⏰ Clasificación diaria:[/cyan] {config.get('classify_time', '06:00')}")
    console.print(f"[cyan]🤖 Modelo Ollama:[/cyan] {config['ollama']['model']}")
    console.print()

    # Verificar Ollama
    _check_ollama(config)

    ok = install_service()
    if ok:
        console.print("\n[bold green]✅ ¡Listo! El servicio está activo.[/bold green]")
        console.print(f"[dim]Configuración en: {CONFIG_FILE}[/dim]")
        console.print(f"[dim]Logs en: {LOG_FILE}[/dim]")
        console.print("\nComandos útiles:")
        console.print("  [cyan]dorg status[/cyan]     → Ver estado del servicio")
        console.print("  [cyan]dorg classify[/cyan]   → Clasificar archivos ahora")
        console.print("  [cyan]dorg logs[/cyan]       → Ver logs en tiempo real")
        console.print("  [cyan]dorg config[/cyan]     → Editar configuración")
    else:
        console.print("\n[red]❌ Ocurrió un error. Intenta correr manualmente:[/red]")
        console.print("  [cyan]dorg watch[/cyan]")


@main.command()
def uninstall():
    """Desinstala el servicio del sistema."""
    from .daemon import uninstall_service

    if not click.confirm("¿Desinstalar Downloads Organizer?"):
        return

    ok = uninstall_service()
    if ok:
        console.print("[green]✅ Servicio desinstalado.[/green]")
        if click.confirm("¿Eliminar también la configuración?"):
            if CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
                console.print("[dim]Configuración eliminada.[/dim]")


@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Mostrar logs detallados")
def watch(verbose: bool):
    """Inicia el watcher en primer plano (útil para debug o instalación manual)."""
    from .watcher import start_watcher

    _setup_logging(verbose=verbose)
    config = load_config()

    console.print(Panel.fit(
        f"[bold]📥 Downloads Organizer — Watcher activo[/bold]\n"
        f"Monitoreando: [cyan]{get_downloads_path(config)}[/cyan]\n"
        f"Clasificación diaria: [yellow]{config.get('classify_time', '06:00')}[/yellow]\n"
        f"Presiona [red]Ctrl+C[/red] para detener.",
        border_style="blue"
    ))

    start_watcher(config, foreground=True)


@main.command()
@click.option("--force", "-f", is_flag=True, help="Clasificar sin importar fecha")
@click.option("--no-ollama", "no_ollama", is_flag=True, help="Clasificar solo por tipo/extensión, sin usar Ollama")
def classify(force: bool, no_ollama: bool):
    """Clasifica ahora los archivos en 'Recién Descargado' (ejecución manual)."""
    from .classifier import classify_recent_files

    _setup_logging(verbose=True)
    config = load_config()
    recent = get_recent_path(config)

    if not recent.exists() or not any(recent.iterdir()):
        console.print("[yellow]No hay archivos en 'Recién Descargado' para clasificar.[/yellow]")
        return

    files = list(recent.iterdir())
    n = len([f for f in files if f.is_file()])

    if no_ollama:
        console.print(f"[cyan]Clasificando {n} archivo(s) por tipo/extensión (sin Ollama)...[/cyan]")
    else:
        console.print(f"[cyan]Clasificando {n} archivo(s) con Ollama...[/cyan]")

    classify_recent_files(config, use_ollama=not no_ollama)
    console.print("[green]✅ Clasificación completada.[/green]")


@main.command()
def status():
    """Muestra el estado del servicio y estadísticas de archivos."""
    from .daemon import is_service_running

    config = load_config()
    running = is_service_running()

    # Panel de estado
    status_color = "green" if running else "red"
    status_text = "✅ Activo" if running else "❌ Inactivo"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row("Servicio", f"[{status_color}]{status_text}[/{status_color}]")
    table.add_row("Carpeta descargada", str(get_downloads_path(config)))
    table.add_row("Recién descargado", str(get_recent_path(config)))
    table.add_row("Organizado", str(get_organized_path(config)))
    table.add_row("Modelo IA", config["ollama"]["model"])
    table.add_row("Clasificación diaria", config.get("classify_time", "06:00"))
    table.add_row("Configuración", str(CONFIG_FILE))
    table.add_row("Logs", str(LOG_FILE))

    # Contar archivos
    recent = get_recent_path(config)
    if recent.exists():
        pending = sum(1 for f in recent.iterdir() if f.is_file())
        table.add_row("Archivos pendientes", f"[yellow]{pending}[/yellow]")

    organized = get_organized_path(config)
    if organized.exists():
        total = sum(1 for f in organized.rglob("*") if f.is_file())
        table.add_row("Archivos organizados", f"[green]{total}[/green]")

    projects = config.get("projects", [])
    table.add_row("Proyectos aprobados", str(len(projects)))

    console.print(Panel(table, title="[bold]Downloads Organizer — Estado[/bold]", border_style="blue"))

    if projects:
        console.print("\n[bold]Proyectos:[/bold] " + ", ".join(f"[cyan]{p}[/cyan]" for p in projects))


@main.command("config")
@click.option("--set", "key_value", metavar="KEY=VALUE", help="Establece un valor de configuración")
def config_cmd(key_value: str | None):
    """Edita o muestra la configuración."""
    if key_value:
        try:
            key, value = key_value.split("=", 1)
            config = load_config()
            # Soporte para claves anidadas: ollama.model=llama3.2
            keys = key.split(".")
            d = config
            for k in keys[:-1]:
                d = d[k]
            # Convertir tipos básicos
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            d[keys[-1]] = value
            save_config(config)
            console.print(f"[green]✅ {key} = {value}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    else:
        editor = subprocess.run(
            ["which", "code", "nano", "vim", "vi"],
            capture_output=True, text=True
        ).stdout.split()[0] if True else "nano"
        
        try:
            editor = next(
                e for e in ["code", "nano", "vim", "vi"]
                if subprocess.run(["which", e], capture_output=True).returncode == 0
            )
        except StopIteration:
            editor = "open"

        console.print(f"[cyan]Abriendo configuración en {editor}...[/cyan]")
        console.print(f"[dim]{CONFIG_FILE}[/dim]")
        subprocess.run([editor, str(CONFIG_FILE)])


@main.command()
@click.option("--lines", "-n", default=50, help="Número de líneas a mostrar")
def logs(lines: int):
    """Muestra los logs del servicio."""
    if LOG_FILE.exists():
        content = LOG_FILE.read_text().splitlines()
        for line in content[-lines:]:
            safe = escape(line)
            if "ERROR" in line:
                console.print(f"[red]{safe}[/red]", highlight=False)
            elif "WARNING" in line:
                console.print(f"[yellow]{safe}[/yellow]", highlight=False)
            elif "INFO" in line:
                console.print(f"[dim]{safe}[/dim]", highlight=False)
            else:
                console.print(safe, highlight=False)
    else:
        console.print("[yellow]No hay logs disponibles aún.[/yellow]")


@main.command("projects")
@click.option("--add", "add_name", metavar="NOMBRE", help="Agregar proyecto manualmente")
@click.option("--remove", "remove_name", metavar="NOMBRE", help="Eliminar proyecto")
def projects_cmd(add_name: str | None, remove_name: str | None):
    """Gestiona los proyectos de clasificación."""
    from .config import add_project

    config = load_config()
    projects: list[str] = config.get("projects", [])

    if add_name:
        add_project(add_name)
        console.print(f"[green]✅ Proyecto agregado: {add_name}[/green]")
        return

    if remove_name:
        if remove_name in projects:
            projects.remove(remove_name)
            config["projects"] = projects
            save_config(config)
            console.print(f"[yellow]🗑️  Proyecto eliminado: {remove_name}[/yellow]")
        else:
            console.print(f"[red]Proyecto no encontrado: {remove_name}[/red]")
        return

    if not projects:
        console.print("[dim]No hay proyectos aprobados aún. La IA los sugerirá conforme clasifique archivos.[/dim]")
    else:
        table = Table(title="Proyectos aprobados", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Proyecto")
        for i, p in enumerate(projects, 1):
            table.add_row(str(i), p)
        console.print(table)


# Comando interno para el daemon (no mostrar en ayuda)
@main.command("_run-daemon", hidden=True)
def run_daemon():
    """Comando interno: inicia el proceso daemon (usado por launchd/systemd)."""
    from .watcher import start_watcher

    _setup_logging(verbose=False)
    config = load_config()
    start_watcher(config, foreground=False)


def _check_ollama(config: dict) -> None:
    """Verifica que Ollama esté instalado y corriendo."""
    import httpx

    base_url = config["ollama"]["base_url"]
    model = config["ollama"]["model"]

    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if any(model in m for m in models):
            console.print(f"[green]✅ Ollama activo — modelo '{model}' disponible[/green]")
        else:
            console.print(f"[yellow]⚠️  Ollama activo pero el modelo '{model}' no está descargado.[/yellow]")
            console.print(f"   Ejecuta: [cyan]ollama pull {model}[/cyan]")
    except Exception:
        console.print("[red]⚠️  Ollama no está corriendo.[/red]")
        console.print("   Instala Ollama desde [link=https://ollama.ai]https://ollama.ai[/link]")
        console.print(f"   Luego ejecuta: [cyan]ollama pull {model}[/cyan]")


if __name__ == "__main__":
    main()
