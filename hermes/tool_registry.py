import json
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional
from .hermes_provider import ToolCall

@dataclass
class ToolResult:
    status: str  # "success", "failed", "skipped"
    content: str  # Typically a JSON string of the result
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    requires_auth: bool = True
    dry_run_safe: bool = False

    def to_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self.tools[tool.name] = tool

    def get_schema_list(self) -> List[Dict[str, Any]]:
        return [tool.to_schema() for tool in self.tools.values()]

    def dispatch(self, call: ToolCall) -> ToolResult:
        if call.name not in self.tools:
            return ToolResult(
                status="failed",
                content=f"Tool '{call.name}' not found in registry."
            )
        
        tool = self.tools[call.name]
        try:
            # The handler is expected to return a dict or ToolResult
            result = tool.handler(**call.arguments)
            
            if isinstance(result, ToolResult):
                return result
            
            # If handler returns a dict, wrap it in ToolResult
            if isinstance(result, dict):
                return ToolResult(
                    status=result.get("status", "success"),
                    content=json.dumps(result),
                    metadata=result
                )
            
            # Fallback for other return types
            return ToolResult(
                status="success",
                content=str(result),
                metadata={"raw_result": result}
            )
            
        except Exception as e:
            return ToolResult(
                status="failed",
                content=f"Error executing tool '{call.name}': {str(e)}"
            )
