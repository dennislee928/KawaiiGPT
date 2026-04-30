# KawaiiGPT

> Modified and maintained by [dennislee928](https://github.com/dennislee928).
> Original project by MrSanZz — license declared free for any use case, no warranty.

## ref to https://gbhackers.com/kawaiigpt-a-free-wormgpt-clone-powered/

<div align="center">
    <img src="kawaii.svg" width="50%" />
</div>

A terminal AI chat interface that works with multiple LLM providers — including free and fully local options.

## Use Cases / 使用情境

See `use_case.md` for a bilingual (EN/繁中) overview of legitimate use cases, risks, and recommended guardrails.

---

## Quick Start

### Option 1 — Groq (free API, fastest)

1. Get a free API key at [console.groq.com](https://console.groq.com)
2. Run:

```powershell
# Windows
pip install -r requirements.txt
$env:GROQ_API_KEY = "gsk_..."
python chat.py
```

```bash
# Linux / macOS
pip install -r requirements.txt
export GROQ_API_KEY="gsk_..."
python chat.py
```

### Option 2 — Ollama in Docker (free, fully local, no API key)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker-compose up
# In a second terminal:
docker attach kawaiigpt-chat-1
```

First run downloads Ollama and pulls `llama3.2` (~2 GB). Subsequent starts are instant.

### Option 3 — Ollama without Docker

1. Install Ollama from [ollama.com](https://ollama.com/download)
2. Run:

```bash
ollama pull llama3.2
python chat.py
```

### Option 4 — Claude (Anthropic API, paid)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python chat.py
```

---

## Provider Auto-Detection

`chat.py` picks the backend automatically based on which environment variable is set:

| Priority | Variable | Provider | Cost |
|---|---|---|---|
| 1 | `ANTHROPIC_API_KEY` | Claude (Anthropic) | Paid |
| 2 | `GROQ_API_KEY` | Groq | Free tier |
| 3 | *(neither set)* | Ollama at `localhost:11434` | Free / local |

---

## Docker Architecture

```
docker-compose up
│
├── ollama (port 11434)
│     └── runs llama3.2 locally, free
│
└── chat
      └── chat.py → talks to Ollama via HTTP
```

To switch the Docker stack to a different model:

```bash
OLLAMA_MODEL=mistral docker-compose up
```

To use Groq inside Docker instead of Ollama, edit `docker-compose.yml`:

```yaml
environment:
  - GROQ_API_KEY=gsk_...
  # remove OLLAMA_HOST
```

```bash
#Useful commands while the stack is running:

  # See what's running
  docker-compose ps

  # Watch ollama logs separately
  docker logs -f kawaiigpt-ollama-1

  # Detach from chat WITHOUT stopping it
  # (press)  Ctrl+P  then  Ctrl+Q

  # Stop everything cleanly
  docker-compose down

  # Stop but keep downloaded models for next time
  docker-compose down   # (models are in the 'ollama_data' volume, not deleted)

  To switch models (e.g. Mistral instead of Llama):

  docker-compose down
  $env:OLLAMA_MODEL = "mistral"
  docker-compose up

  Once llama3.2 finishes downloading you're fully offline — no API keys, no internet needed for future sessions. The model lives in the kawaiigpt_ollama_data Docker volume and persists 
  across restarts.
```

---

## Chat Commands

| Command | Action |
|---|---|
| `exit` / `quit` | Quit |
| `reset` | Clear conversation history |
| `help` | Show commands |
| Up arrow | Recall previous inputs |

---

## Installation (Windows)

```powershell
git clone https://github.com/dennislee928/KawaiiGPT
cd KawaiiGPT
pip install -r requirements.txt
python chat.py
```

## Installation (Linux / macOS)

```bash
git clone https://github.com/dennislee928/KawaiiGPT
cd KawaiiGPT
pip install -r requirements.txt
python chat.py
```

---

## Files

| File | Purpose |
|---|---|
| `chat.py` | Main chat interface — multi-provider |
| `docker-compose.yml` | Ollama + chat stack |
| `Dockerfile` | Container definition for chat app |
| `requirements.txt` | Python dependencies |
| `use_case.md` | Use cases, risks, and guardrails (EN/繁中) |
| `kawai.py` | Original KawaiiGPT script (Linux/Android) |
| `install.py` | Original installer (Linux/Android/Termux) |

---

## Recommended Free Models

| Model | Provider | Good for |
|---|---|---|
| `llama3.2` | Ollama / Groq | General chat |
| `llama-3.3-70b-versatile` | Groq | Complex reasoning |
| `mistral` | Ollama | Fast, lightweight |
| `gemma2` | Ollama | Google's open model |
| `deepseek-r1:8b` | Ollama | Reasoning tasks |

---

## License

Free for any use case. No warranty.
