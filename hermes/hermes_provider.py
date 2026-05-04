import json
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    id: str = ""

@dataclass
class ChatResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)

class HermesProvider:
    def __init__(self, host: str, model: str, timeout: int = 300):
        self.host = host.rstrip('/')
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True,
    ) -> ChatResponse:
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        full_content = ""
        tool_calls = []
        finish_reason = ""
        usage = {}

        try:
            # We use stream=True even for non-streaming response to handle potentially large JSON
            with requests.post(url, json=payload, stream=stream, timeout=self.timeout) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text}")
                
                if stream:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        msg = data.get("message", {})
                        
                        content = msg.get("content", "")
                        if content:
                            full_content += content
                        
                        t_calls = msg.get("tool_calls", [])
                        for tc in t_calls:
                            fn = tc.get("function", {})
                            tool_calls.append(ToolCall(
                                name=fn.get("name", ""),
                                arguments=fn.get("arguments", {}),
                                id=""
                            ))
                        
                        if data.get("done"):
                            finish_reason = data.get("done_reason", "stop")
                            usage = {
                                "total_duration": data.get("total_duration"),
                                "load_duration": data.get("load_duration"),
                                "prompt_eval_count": data.get("prompt_eval_count"),
                                "eval_count": data.get("eval_count"),
                            }
                            break
                else:
                    data = resp.json()
                    msg = data.get("message", {})
                    full_content = msg.get("content", "")
                    t_calls = msg.get("tool_calls", [])
                    for tc in t_calls:
                        fn = tc.get("function", {})
                        tool_calls.append(ToolCall(
                            name=fn.get("name", ""),
                            arguments=fn.get("arguments", {}),
                            id=""
                        ))
                    finish_reason = data.get("done_reason", "stop")
                    usage = {
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                        "prompt_eval_count": data.get("prompt_eval_count"),
                        "eval_count": data.get("eval_count"),
                    }
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to connect to Ollama at {self.host}: {e}")

        return ChatResponse(
            content=full_content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage
        )
