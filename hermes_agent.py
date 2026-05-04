import sys
import os
import json
import yaml
import time
import uuid
import subprocess
import requests
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, ValidationError
from colorama import init, Fore, Style
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

# Add current dir to sys.path to allow imports from pentest/common
sys.path.append(str(Path(__file__).resolve().parent))
try:
    from pentest.common.result_schema import ModuleResult, Finding
    from pentest.common import auth_check
except ImportError:
    # Fallback if imports fail (should not happen in this environment)
    class Finding(BaseModel):
        severity: str
        title: str
        description: str
        host: Optional[str] = None
        port: Optional[int] = None
        evidence: Optional[str] = None
    class ModuleResult(BaseModel):
        module: str
        started_at: datetime
        finished_at: datetime
        target_scope: List[str]
        findings: List[Finding] = []
        def summary(self) -> dict:
            return {"module": self.module, "findings": [f.model_dump() for f in self.findings]}

# --- Configuration ---

DEFAULT_CONFIG = {
    "hermes": {
        "ollama_host": "http://localhost:11434",
        "model": "hermes3:8b",
        "max_iterations": 10,
        "stream": True,
        "timeout_seconds": 300
    },
    "agent": {
        "system_prompt_path": "hermes/prompts/system.txt",
        "max_context_tokens": 8192,
        "dry_run": False
    },
    "memory": {
        "session_dir": "hermes_sessions",
        "max_transcript_turns": 100
    },
    "tools": {
        "enabled": [
            "run_vulnerability_scan", "run_network_scan", "run_web_app_test",
            "run_sqli_test", "run_xss_test", "run_file_inclusion_test",
            "run_web_service_test", "get_workflow_status", "read_latest_findings",
            "list_available_modules", "generate_analyst_report", "reset_session"
        ],
        "pentest_workflow_path": "pentest/workflow.yaml",
        "pentest_root": "pentest/"
    }
}

class Config:
    def __init__(self, path: str = "hermes_config.yaml"):
        self.data = DEFAULT_CONFIG.copy()
        if Path(path).exists():
            with open(path, "r") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    self._deep_update(self.data, user_config)
        
        # Override with env vars
        if os.getenv("OLLAMA_HOST"):
            self.data["hermes"]["ollama_host"] = os.getenv("OLLAMA_HOST")
        if os.getenv("HERMES_MODEL"):
            self.data["hermes"]["model"] = os.getenv("HERMES_MODEL")
        if os.getenv("HERMES_DRY_RUN") == "1":
            self.data["agent"]["dry_run"] = True

    def _deep_update(self, base, update):
        for k, v in update.items():
            if isinstance(v, dict) and k in base:
                self._deep_update(base[k], v)
            else:
                base[k] = v

    def __getitem__(self, key):
        return self.data[key]

# --- Models & Responses ---

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class ChatResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"

# --- Provider ---

class HermesProvider:
    def __init__(self, host: str, model: str, timeout: int = 300):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def pull_model(self):
        print(f"{Fore.CYAN}[Hermes]{Style.RESET_ALL} Checking model {self.model}...")
        resp = requests.get(f"{self.host}/api/tags")
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            if self.model in models or f"{self.model}:latest" in models:
                print(f"{Fore.CYAN}[Hermes]{Style.RESET_ALL} Model {self.model} is ready.")
                return
        
        print(f"{Fore.CYAN}[Hermes]{Style.RESET_ALL} Pulling model {self.model} (this may take a while)...")
        resp = requests.post(f"{self.host}/api/pull", json={"name": self.model}, stream=True)
        for line in resp.iter_lines():
            if line:
                status = json.loads(line)
                if "status" in status:
                    print(f"\r{Fore.CYAN}[Hermes]{Style.RESET_ALL} {status['status']}... ", end="")
        print("\nDone.")

    def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> ChatResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": 8192}
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            message = data.get("message", {})
            
            tool_calls = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    f = tc.get("function", {})
                    tool_calls.append(ToolCall(
                        id=str(uuid.uuid4()),
                        name=f.get("name"),
                        arguments=f.get("arguments", {})
                    ))
            
            return ChatResponse(
                content=message.get("content", ""),
                tool_calls=tool_calls,
                finish_reason=data.get("done_reason", "stop")
            )
        except Exception as e:
            return ChatResponse(content=f"Error connecting to Ollama: {e}", finish_reason="error")

# --- Memory ---

class SessionMemory:
    def __init__(self, session_dir: str):
        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.base_dir = Path(session_dir) / self.session_id
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_path = self.base_dir / "transcript.jsonl"
        self.findings_path = self.base_dir / "findings_index.json"
        self.findings = []
        
        # Create .gitignore in sessions dir if not exists
        gitignore = Path(session_dir) / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n!.gitignore\n")

    def append_turn(self, role: str, content: str, tool_calls: Optional[List[ToolCall]] = None, tool_result: Optional[str] = None, tool_call_id: Optional[str] = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content
        }
        if tool_calls:
            entry["tool_calls"] = [{"name": tc.name, "args": tc.arguments} for tc in tool_calls]
        if tool_result:
            entry["tool_result"] = tool_result
        if tool_call_id:
            entry["tool_call_id"] = tool_call_id
            
        with open(self.transcript_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def append_findings(self, new_findings: List[Dict]):
        self.findings.extend(new_findings)
        with open(self.findings_path, "w", encoding="utf-8") as f:
            json.dump(self.findings, f, indent=2)

# --- Tool Registry ---

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, description: str, parameters: Dict, handler: Callable):
        self.tools[name] = {
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            },
            "handler": handler
        }

    def get_schemas(self) -> List[Dict]:
        return [t["schema"] for t in self.tools.values()]

    def dispatch(self, name: str, args: Dict) -> Any:
        if name not in self.tools:
            return {"status": "error", "message": f"Tool {name} not found"}
        return self.tools[name]["handler"](**args)

# --- Pentest Tools ---

def get_tool_handler(config: Config, memory: SessionMemory):
    pentest_root = Path(config["tools"]["pentest_root"])
    
    def run_module_tool(module_name: str, **kwargs):
        if config["agent"]["dry_run"]:
            return {"status": "success", "message": f"Dry-run: would run {module_name} with {kwargs}", "findings": []}
        
        module_path = pentest_root / module_name
        if not module_path.exists():
            return {"status": "error", "message": f"Module {module_name} not found at {module_path}"}
        
        # Prepare targets
        targets = kwargs.get("targets", [])
        operator = kwargs.get("operator", "HermesAgent")
        engagement_ref = kwargs.get("engagement_ref", f"HERMES-{memory.session_id}")
        
        # Create temp config patch
        original_config_path = module_path / "config.yaml"
        temp_config_path = module_path / f"config.hermes.{uuid.uuid4()}.yaml"
        
        try:
            with open(original_config_path, "r") as f:
                mod_cfg = yaml.safe_load(f)
            
            mod_cfg["target_scope"] = targets if isinstance(targets, list) else [targets]
            mod_cfg["authorization"]["operator"] = operator
            mod_cfg["authorization"]["engagement_ref"] = engagement_ref
            
            # Additional args for specific modules
            if "ports" in kwargs and "nmap" in str(mod_cfg.get("meta", {}).get("description", "")).lower():
                mod_cfg["options"] = mod_cfg.get("options", {})
                mod_cfg["options"]["ports"] = kwargs["ports"]

            with open(temp_config_path, "w") as f:
                yaml.dump(mod_cfg, f)
            
            # Run module via run-pentest.py wrapper logic (calling run.py directly is easier here)
            # We must override the config path. Most modules read 'config.yaml' in their cwd.
            # So we swap files temporarily.
            backup_config = module_path / "config.yaml.bak"
            shutil_move = lambda src, dst: Path(src).replace(dst)
            
            shutil_move(original_config_path, backup_config)
            shutil_move(temp_config_path, original_config_path)
            
            try:
                print(f"{Fore.YELLOW}[Agent]{Style.RESET_ALL} Executing {module_name}...")
                result = subprocess.run([sys.executable, "run.py"], cwd=module_path, capture_output=True, text=True)
                
                # Collect findings
                output_dir = module_path / mod_cfg.get("output", {}).get("dir", "results")
                summaries = sorted(output_dir.glob("summary*.json"), key=lambda p: p.stat().st_mtime)
                if summaries:
                    res = ModuleResult.from_json(str(summaries[-1]))
                    memory.append_findings(res.summary()["findings"])
                    return res.summary()
                else:
                    return {"status": "error", "message": f"Module {module_name} finished but no summary found. Exit code: {result.returncode}", "stdout": result.stdout, "stderr": result.stderr}
            finally:
                # Restore original config
                shutil_move(original_config_path, temp_config_path)
                shutil_move(backup_config, original_config_path)
                if temp_config_path.exists(): temp_config_path.unlink()
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return run_module_tool

# --- Agent ---

class Agent:
    def __init__(self, provider: HermesProvider, registry: ToolRegistry, memory: SessionMemory, config: Config):
        self.provider = provider
        self.registry = registry
        self.memory = memory
        self.config = config
        self.messages = []
        self._init_system_prompt()

    def _init_system_prompt(self):
        prompt_path = Path(self.config["agent"]["system_prompt_path"])
        if prompt_path.exists():
            content = prompt_path.read_text()
        else:
            content = (
                "You are a security-focused AI agent embedded in KawaiiGPT.\n"
                "You have access to authorized penetration testing tools.\n"
                "Before running ANY tool, verify the engagement authorization is in scope.\n"
                "Always explain what you are about to do BEFORE calling a tool.\n"
                "After receiving tool results, summarize findings clearly for the operator.\n"
                "Use structured JSON tool calls only — never hallucinate tool names.\n"
                "Available tools: " + ", ".join(self.registry.tools.keys())
            )
        self.messages.append({"role": "system", "content": content})

    def run(self, user_input: str):
        self.messages.append({"role": "user", "content": user_input})
        self.memory.append_turn("user", user_input)
        
        for i in range(self.config["hermes"]["max_iterations"]):
            print(f"{Fore.CYAN}[Hermes]{Style.RESET_ALL} Thinking... (Iteration {i+1})")
            response = self.provider.chat(self.messages, tools=self.registry.get_schemas())
            
            if response.finish_reason == "error":
                print(f"{Fore.RED}Error: {response.content}{Style.RESET_ALL}")
                break

            if response.content:
                print(f"\n{Fore.GREEN}Hermes:{Style.RESET_ALL} {response.content}\n")
                self.messages.append({"role": "assistant", "content": response.content})
                self.memory.append_turn("assistant", response.content)

            if not response.tool_calls:
                break

            for tc in response.tool_calls:
                print(f"{Fore.YELLOW}[Agent]{Style.RESET_ALL} Calling tool: {tc.name}({tc.arguments})")
                result = self.registry.dispatch(tc.name, tc.arguments)
                result_str = json.dumps(result)
                
                # Append to messages for next turn
                self.messages.append({
                    "role": "tool",
                    "content": result_str,
                    "tool_call_id": tc.id,
                    "name": tc.name
                })
                self.memory.append_turn("tool", "", tool_result=result_str, tool_call_id=tc.id)
                
                # Brief summary of result
                if isinstance(result, dict) and "total_findings" in result:
                    print(f"{Fore.MAGENTA}[Result]{Style.RESET_ALL} {result['module']} finished with {result['total_findings']} findings.")

        print(f"{Fore.CYAN}[Hermes]{Style.RESET_ALL} Turn complete.")

# --- CLI ---

def main():
    init()
    print(f"""{Fore.MAGENTA}
  _  __                     _ _  _____ _____ _______ 
 | |/ /                    (_|_)/ ____|  __ \__   __|
 | ' / __ ___      ____ _ _ _ | |  __| |__) | | |   
 |  < / _` \ \ /\ / / _` | | | | | |_ |  ___/  | |   
 | . \ (_| |\ V  V / (_| | | | | |__| | |      | |   
 |_|\_\__,_| \_/\_/ \__,_|_|_| |\_____|_|      |_|   
                            _/ |                     
                           |__/  Hermes Agent v1.0
{Style.RESET_ALL}""")

    config = Config()
    provider = HermesProvider(config["hermes"]["ollama_host"], config["hermes"]["model"])
    
    try:
        provider.pull_model()
    except Exception as e:
        print(f"{Fore.RED}Could not connect to Ollama: {e}{Style.RESET_ALL}")
        print("Make sure Ollama is running.")
        sys.exit(1)

    memory = SessionMemory(config["memory"]["session_dir"])
    registry = ToolRegistry()
    handler = get_tool_handler(config, memory)

    # Register tools
    registry.register(
        "run_vulnerability_scan",
        "Run an authenticated Nmap vulnerability scan against one or more targets.",
        {
            "type": "object",
            "properties": {
                "targets": {"type": "array", "items": {"type": "string"}, "description": "IP addresses or hostnames to scan."},
                "operator": {"type": "string", "description": "Authorized operator name."},
                "engagement_ref": {"type": "string", "description": "Engagement reference (e.g. ENG-001)."},
                "ports": {"type": "string", "description": "Port range (e.g. '1-1024').", "default": "1-1024"}
            },
            "required": ["targets", "operator", "engagement_ref"]
        },
        lambda **kwargs: handler("01-VulnerabilityScanning", **kwargs)
    )
    
    registry.register(
        "run_network_scan",
        "Run a network discovery scan to find live hosts and open ports.",
        {
            "type": "object",
            "properties": {
                "targets": {"type": "array", "items": {"type": "string"}},
                "operator": {"type": "string"},
                "engagement_ref": {"type": "string"}
            },
            "required": ["targets", "operator", "engagement_ref"]
        },
        lambda **kwargs: handler("02-NetworkScanning", **kwargs)
    )

    registry.register(
        "run_web_app_test",
        "Run a web application security test using ZAP.",
        {
            "type": "object",
            "properties": {
                "targets": {"type": "array", "items": {"type": "string"}, "description": "URLs to test."},
                "operator": {"type": "string"},
                "engagement_ref": {"type": "string"}
            },
            "required": ["targets", "operator", "engagement_ref"]
        },
        lambda **kwargs: handler("03-WebApplicationTesting", **kwargs)
    )

    registry.register(
        "list_available_modules",
        "List all available pentest modules.",
        {"type": "object", "properties": {}},
        lambda: {"status": "success", "modules": ["01-VulnerabilityScanning", "02-NetworkScanning", "03-WebApplicationTesting", "04-SQLInjectionTesting", "05-XSSTesting"]}
    )

    agent = Agent(provider, registry, memory, config)

    session = PromptSession(history=FileHistory(".hermes_history"))

    print(f"\n{Fore.GREEN}Session ID: {memory.session_id}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Model: {config['hermes']['model']}{Style.RESET_ALL}")
    if config["agent"]["dry_run"]:
        print(f"{Fore.YELLOW}DRY-RUN MODE ENABLED{Style.RESET_ALL}")
    print("Type your request or 'help' for commands. 'exit' to quit.\n")

    while True:
        try:
            user_input = session.prompt(f"{Fore.BLUE}Operator>{Style.RESET_ALL} ")
            if not user_input.strip(): continue
            
            cmd = user_input.strip().lower()
            if cmd in ("exit", "quit", "q"):
                break
            elif cmd == "help":
                print("\nCommands:")
                print("  exit / quit : End session")
                print("  reset       : Clear conversation context")
                print("  status      : Show agent status")
                print("  tools       : List available tools")
                print("  dry-run on  : Enable dry-run mode")
                print("  dry-run off : Disable dry-run mode")
                print("\nOtherwise, just type your request in natural language.\n")
                continue
            elif cmd == "reset":
                agent.messages = [agent.messages[0]]
                print("Conversation context cleared.")
                continue
            elif cmd == "status":
                print(f"Model: {config['hermes']['model']}")
                print(f"Session: {memory.session_id}")
                print(f"History: {len(agent.messages)} messages")
                continue
            elif cmd == "tools":
                for name, t in registry.tools.items():
                    print(f"- {name}: {t['schema']['function']['description']}")
                continue
            elif cmd == "dry-run on":
                config.data["agent"]["dry_run"] = True
                print("Dry-run mode enabled.")
                continue
            elif cmd == "dry-run off":
                config.data["agent"]["dry_run"] = False
                print("Dry-run mode disabled.")
                continue

            agent.run(user_input)
            
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

    print("\nGoodbye!")

if __name__ == "__main__":
    main()
