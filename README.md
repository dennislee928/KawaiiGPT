# KawaiiGPT

KawaiiGPT is a terminal-based AI chat application with support for multiple providers, plus a separate `pentest/` framework for authorized security assessment workflows.

This repository is maintained by [dennislee928](https://github.com/dennislee928). The original project attribution in the repository points to MrSanZz and states the work is free for any use case with no warranty.

<div align="center">
  <img src="kawaii.svg" width="50%" alt="KawaiiGPT logo" />
</div>

![KawaiiGPT screenshot](.Assets/%E8%9E%A2%E5%B9%95%E6%93%B7%E5%8F%96%E7%95%AB%E9%9D%A2%202026-04-30%20140541.png)

## What Is Here

- `chat.py`: interactive CLI chat client
- `docker-compose.yml`: local Ollama + chat stack
- `pentest/`: orchestrated penetration testing framework with per-module runners and aggregate reporting
- `use_case.md`: bilingual project notes on legitimate use cases, risks, and guardrails

## Chat App

The chat client auto-detects the backend from environment variables:

| Priority | Variable | Provider | Default Model |
|---|---|---|---|
| 1 | `ANTHROPIC_API_KEY` | Anthropic Claude | `claude-opus-4-7` |
| 2 | `GROQ_API_KEY` | Groq | `llama-3.3-70b-versatile` |
| 3 | neither set | Ollama at `http://localhost:11434` | `llama3.2` |

Optional overrides:

- `ANTHROPIC_MODEL`
- `GROQ_MODEL`
- `OLLAMA_HOST`
- `OLLAMA_MODEL`

### Quick Start

#### Option 1: Groq

```powershell
pip install -r requirements.txt
$env:GROQ_API_KEY = "gsk_..."
python chat.py
```

```bash
pip install -r requirements.txt
export GROQ_API_KEY="gsk_..."
python chat.py
```

#### Option 2: Ollama in Docker

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker-compose up
docker attach kawaiigpt-chat-1
```

On first run, Ollama downloads the selected model. By default the stack uses `llama3.2`.

To switch models:

```bash
OLLAMA_MODEL=mistral docker-compose up
```

While the stack is running:

```bash
docker-compose ps
docker logs -f kawaiigpt-ollama-1
docker-compose down
```

#### Option 3: Ollama without Docker

1. Install [Ollama](https://ollama.com/download).
2. Pull a model and start the chat client:

```bash
ollama pull llama3.2
python chat.py
```

#### Option 4: Anthropic Claude

```powershell
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python chat.py
```

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python chat.py
```

### Chat Commands

| Command | Action |
|---|---|
| `exit`, `quit`, `q` | Quit |
| `reset` | Clear the in-memory conversation |
| `help` | Show the built-in command help |
| Up arrow | Recall previous inputs via prompt history |

## Hermes Agent (Autonomous Mode)

The Hermes Agent is an autonomous execution mode powered by **NousResearch Hermes 3**. It can reason about complex pentest requests, plan its own actions, and execute tools from the pentest framework automatically.

### Quick Start (Hermes)

1. **Pull the model**:
   ```bash
   ollama pull hermes3:8b
   ```
2. **Start the agent**:
   ```bash
   python hermes_agent.py
   ```

### Using with Docker

```bash
docker-compose up hermes-agent
docker attach kawaiigpt-hermes-agent-1
```

The agent will automatically pull `hermes3:8b` on startup when running via Docker Compose.

### Agent Capabilities

- **Autonomous Planning**: Turn high-level goals into a sequence of tool calls.
- **Tool Use**: Direct access to 10+ pentest modules.
- **Analyst Reporting**: Automatically synthesizes raw JSON findings into a Markdown analyst report.
- **Session Memory**: Persistent transcript and finding history under `hermes_sessions/`.

### Configuration

The agent is configured via `hermes_config.yaml`. Key settings:
- `HERMES_MODEL`: Default is `hermes3:8b`. Use `hermes3:70b` for higher quality reasoning.
- `HERMES_DRY_RUN`: Set to `1` to test agent logic without executing real scans.

## Installation

### Windows

```powershell
git clone https://github.com/dennislee928/KawaiiGPT
cd KawaiiGPT
pip install -r requirements.txt
python chat.py
```

### Linux / macOS

```bash
git clone https://github.com/dennislee928/KawaiiGPT
cd KawaiiGPT
pip install -r requirements.txt
python chat.py
```

## Docker Notes

The Compose stack starts:

- `ollama` on port `11434`
- `chat`, configured to talk to the Ollama service by default

To use Groq or Anthropic inside Docker, adjust the `chat` service environment in `docker-compose.yml` and remove `OLLAMA_HOST` when switching away from Ollama.

## Pentest Framework

The `pentest/` directory contains a workflow-driven assessment framework with shared utilities, per-module runners, and aggregate report generation.

Key entrypoints:

- `pentest/workflow.yaml`: module list, dependencies, and enabled/disabled state
- `pentest/run-pentest.py`: validates configs, resolves dependency order, runs enabled modules, and writes aggregate JSON/HTML reports
- `pentest/common/`: shared authorization checks, result schema helpers, and report templating

The default workflow currently enables `01`, `02`, `03`, `04`, `05`, `07`, `09`, and `10`. Module `06-PasswordCracking` is disabled by default because it requires operator-supplied hash material and wordlists. Module `08-BluetoothWiFiScanning` is disabled by default because it requires a Linux host plus compatible wireless/Bluetooth hardware.

### Safety and Authorization

The pentest framework is intended only for authorized engagements. Before a module can run successfully, its `config.yaml` must be populated with real authorization metadata such as the operator name, engagement reference, and non-empty target scope. Placeholder values are rejected by the orchestrator and module-level checks.

The orchestrator follows dependency order from `pentest/workflow.yaml`, writes aggregate reports to `pentest/reports/`, and defaults `continue_on_error` to `false`.

`07-SocialEngineeringTesting` is review-only template generation. It does not send emails, track users, or collect credentials.

Example dry run:

```bash
python pentest/run-pentest.py --dry-run
```

Run specific modules by name:

```bash
python pentest/run-pentest.py --module 02-NetworkScanning --module 03-WebApplicationTesting
```

Reports are collected under `pentest/reports/`.

Current verification is limited to structure and smoke checks. Full end-to-end scans are not validated until real authorization data, target scope, and required runtime environments are provided.

## Repository Files

| File | Purpose |
|---|---|
| `chat.py` | Main multi-provider chat interface |
| `hermes_agent.py` | Autonomous agent CLI entrypoint |
| `hermes_config.yaml` | Hermes agent configuration |
| `docker-compose.yml` | Ollama + chat + hermes-agent stack |
| `Dockerfile` | Container image for the chat app |
| `Dockerfile.hermes` | Container image for the Hermes agent |
| `requirements.txt` | Core Python dependencies |
| `requirements-hermes.txt` | Additional Hermes-specific dependencies |
| `use_case.md` | Use cases, risks, and guardrails |
| `kawai.py` | Original KawaiiGPT script |
| `install.py` | Original installer |

## Recommended Free Models

| Model | Provider | Good For |
|---|---|---|
| `llama3.2` | Ollama / Groq | General chat |
| `llama-3.3-70b-versatile` | Groq | Complex reasoning |
| `mistral` | Ollama | Lightweight local use |
| `gemma2` | Ollama | Open model alternative |
| `deepseek-r1:8b` | Ollama | Reasoning-oriented tasks |

## License

Free for any use case. No warranty.
