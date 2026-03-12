[![PyPI version](https://img.shields.io/pypi/v/downloads-organizer)](https://pypi.org/project/downloads-organizer/)
[![Python versions](https://img.shields.io/pypi/pyversions/downloads-organizer)](https://pypi.org/project/downloads-organizer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/jarsa/downloads-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/jarsa/downloads-organizer/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/pypi/dm/downloads-organizer)](https://pypi.org/project/downloads-organizer/)

# Downloads Organizer

Smart downloads folder organizer powered by **local AI (Ollama)**. Compatible with **macOS** and **Linux**. Installs with `pipx` and runs as a system service.

Your files never leave your machine — all AI classification happens locally via Ollama.

---

## Demo

```
~/Downloads/
├── 📥 Recién Descargado/      ← files from today
└── 📁 Organizado/
    ├── 🔴 Urgente/
    │   ├── Trabajo/
    │   │   └── documento/
    │   └── Finanzas/
    │       └── hoja_de_calculo/
    ├── 🟡 Normal/
    │   └── Personal/
    │       └── imagen/
    └── 📦 Archivo/
```

---

## Requirements

- Python ≥ 3.10
- [pipx](https://pipx.pypa.io/) — to install the CLI
- [Ollama](https://ollama.ai) — local AI engine

---

## Installation

### macOS

```bash
# 1. Install Ollama
brew install ollama
ollama serve &
ollama pull llama3.2

# 2. Install pipx (if needed)
brew install pipx
pipx ensurepath

# 3. Install Downloads Organizer
pipx install downloads-organizer

# 4. Enable system service
dorg install
```

### Linux

```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2

# 2. Install pipx (if needed)
pip install pipx --user && pipx ensurepath

# 3. Install Downloads Organizer
pipx install downloads-organizer

# 4. Enable systemd service
dorg install
```

---

## Usage

| Command | Description |
|---------|-------------|
| `dorg install` | Install and enable system service |
| `dorg uninstall` | Remove system service |
| `dorg status` | Service status + statistics |
| `dorg classify` | Classify pending files now |
| `dorg watch` | Start in foreground (debug mode) |
| `dorg logs` | View service logs |
| `dorg logs -n 200` | View last N log lines |
| `dorg config` | Edit configuration file |
| `dorg config --set ollama.model=mistral` | Change Ollama model |
| `dorg projects` | List approved projects |
| `dorg projects --add Trabajo` | Add project manually |

---

## Configuration

File: `~/.config/downloads-organizer/config.yaml`

```yaml
downloads_folder: ~/Downloads
recent_folder_name: Recién Descargado   # staging folder for new files
organized_folder_name: Organizado        # destination for classified files
classify_time: "06:00"                   # daily classification time

ollama:
  base_url: http://localhost:11434
  model: llama3.2
  timeout: 60
  confidence_threshold: 0.65             # below this → ask user

projects:                                # approved project names
  - Trabajo
  - Personal
  - Finanzas
  - Estudio
```

---

## Recommended Ollama Models

| Model | Size | Speed | Quality | Best for |
|-------|------|-------|---------|----------|
| `llama3.2` | 2 GB | Fast | Good | Default, everyday use |
| `mistral` | 4 GB | Medium | Very good | More nuanced classification |
| `phi3` | 2 GB | Fast | Good | Low-RAM machines |
| `gemma2` | 5 GB | Slow | Excellent | Best accuracy |

Change model:
```bash
ollama pull mistral
dorg config --set ollama.model=mistral
```

---

## How It Works

```
New file detected
      │
      ▼
[watchdog event]
      │
      ▼
_should_move()? ──No──► ignore
      │
     Yes
      │
      ▼
wait for file ready (download complete)
      │
      ▼
move → Recién Descargado/
+ native notification
      │
      ▼
      (daily at 06:00)
      │
      ▼
[Ollama classification]
      │
      ├─ confidence ≥ 0.65 + known project
      │         └─► move automatically
      │
      ├─ confidence < 0.65
      │         └─► show interactive dialog
      │
      └─ new project suggested
                └─► ask user to approve/rename/reject
                          └─► move to Organizado/
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, commit conventions, and the pull request process.

---

## License

MIT — see [LICENSE](LICENSE).
Copyright (c) 2025 [Jarsa Sistemas](https://jarsa.com.mx)
