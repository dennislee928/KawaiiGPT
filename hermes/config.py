import os
import yaml
from pathlib import Path
from typing import Any, Dict

# Default configuration matching §6.9 of the integration plan
DEFAULT_CONFIG = {
    "hermes": {
        "ollama_host": "http://localhost:11434",
        "model": "hermes3:8b",
        "max_iterations": 10,
        "stream": True,
        "timeout_seconds": 300,
    },
    "agent": {
        "system_prompt_path": "hermes/prompts/system.txt",
        "max_context_tokens": 8192,
        "dry_run": False,
    },
    "memory": {
        "session_dir": "hermes_sessions",
        "max_transcript_turns": 100,
    },
    "tools": {
        "enabled": [
            "run_vulnerability_scan",
            "run_network_scan",
            "run_web_app_test",
            "run_sqli_test",
            "run_xss_test",
            "run_file_inclusion_test",
            "run_web_service_test",
            "get_workflow_status",
            "read_latest_findings",
            "list_available_modules",
            "generate_analyst_report",
            "reset_session"
        ],
        "pentest_workflow_path": "pentest/workflow.yaml",
        "pentest_root": "pentest/",
    }
}

def load_config(config_path: str = "hermes_config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file, with environment variable overrides.
    """
    config = DEFAULT_CONFIG.copy()
    
    # Load from YAML if it exists
    path = Path(config_path)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # Simple one-level deep merge for sections
                    for section, values in user_config.items():
                        if isinstance(values, dict) and section in config:
                            config[section].update(values)
                        else:
                            config[section] = values
        except Exception as e:
            print(f"\033[33mWarning: Failed to load {config_path}: {e}. Using defaults.\033[0m")
                        
    # Override with environment variables (Phase 1 support)
    if os.environ.get("OLLAMA_HOST"):
        config["hermes"]["ollama_host"] = os.environ.get("OLLAMA_HOST")
    
    if os.environ.get("HERMES_MODEL"):
        config["hermes"]["model"] = os.environ.get("HERMES_MODEL")
    
    if os.environ.get("HERMES_MAX_ITERATIONS"):
        try:
            config["hermes"]["max_iterations"] = int(os.environ.get("HERMES_MAX_ITERATIONS"))
        except ValueError:
            pass

    if os.environ.get("HERMES_DRY_RUN"):
        config["agent"]["dry_run"] = os.environ.get("HERMES_DRY_RUN") == "1"
        
    if os.environ.get("HERMES_SESSION_DIR"):
        config["memory"]["session_dir"] = os.environ.get("HERMES_SESSION_DIR")
        
    return config
