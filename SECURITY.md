# Security Policy

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues by emailing **hola@jarsa.com.mx**. Include as much detail as possible:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

We will respond within 5 business days and coordinate a fix and disclosure timeline with you.

## Privacy & Data

Downloads Organizer is designed with privacy as a core principle:

- **All AI classification runs locally** via [Ollama](https://ollama.ai). No file names, contents, or metadata are ever sent to external servers.
- Configuration is stored locally at `~/.config/downloads-organizer/`.
- Logs are stored locally at the platform's standard log directory.
- The only network connection made is to `http://localhost:11434` (Ollama's local API).
