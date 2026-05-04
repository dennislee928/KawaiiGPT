import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PENTEST_ROOT = PROJECT_ROOT / "pentest"
WORKFLOW_PATH = PENTEST_ROOT / "workflow.yaml"

def list_available_modules() -> Dict[str, Any]:
    """List all modules defined in workflow.yaml with their status and descriptions."""
    if not WORKFLOW_PATH.exists():
        return {"error": "workflow.yaml not found"}
    
    with open(WORKFLOW_PATH, "r") as f:
        workflow = yaml.safe_load(f)
    
    modules = workflow.get("modules", [])
    return {
        "status": "success",
        "modules": modules
    }

def get_workflow_status() -> Dict[str, Any]:
    """Return the entire workflow.yaml content."""
    if not WORKFLOW_PATH.exists():
        return {"error": "workflow.yaml not found"}
    
    with open(WORKFLOW_PATH, "r") as f:
        workflow = yaml.safe_load(f)
    
    return {
        "status": "success",
        "workflow": workflow
    }

def read_latest_findings(module_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Read the latest summary JSON for a specific module or all modules.
    Returns normalized findings.
    """
    if not WORKFLOW_PATH.exists():
        return {"error": "workflow.yaml not found"}
    
    with open(WORKFLOW_PATH, "r") as f:
        workflow = yaml.safe_load(f)
    
    modules = workflow.get("modules", [])
    results = {}

    for m in modules:
        name = m["name"]
        if module_name and name != module_name:
            continue
        
        module_dir = PENTEST_ROOT / m["path"]
        # In a real scenario, we'd need to know the output dir from module's config
        # For simplicity, we check common locations or assume 'results'
        output_dir = module_dir / "results"
        if not output_dir.exists():
            # Try to read config.yaml to find output dir
            config_path = module_dir / "config.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f)
                output_dir = module_dir / cfg.get("output", {}).get("dir", "results")

        if output_dir.exists():
            summaries = sorted(output_dir.glob("summary*.json"), key=lambda p: p.stat().st_mtime)
            if summaries:
                with open(summaries[-1], "r") as f:
                    results[name] = json.load(f)

    return {
        "status": "success",
        "results": results
    }

def reset_session() -> Dict[str, Any]:
    """
    Clears in-memory messages. 
    Note: The actual clearing happens in the Agent loop, this tool just returns a signal.
    """
    return {
        "status": "success",
        "action": "reset_session",
        "message": "Session reset requested."
    }

def generate_analyst_report(session_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Trigger the analyst report generation.
    Note: This is usually wired to ResultAnalyst.analyze() in the registry/agent.
    """
    return {
        "status": "success",
        "action": "generate_analyst_report",
        "findings_count": len(session_findings)
    }
