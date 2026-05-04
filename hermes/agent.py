import json
from typing import List, Dict, Any, Optional
from .hermes_provider import HermesProvider, ToolCall
from .tool_registry import ToolRegistry, ToolResult

class Agent:
    def __init__(
        self,
        provider: HermesProvider,
        registry: ToolRegistry,
        system_prompt: str,
        max_iterations: int = 10,
        stream: bool = True
    ):
        self.provider = provider
        self.registry = registry
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.stream = stream

    def run(self, user_input: str, history: List[Dict[str, Any]] = None) -> str:
        """
        Runs the ReAct loop for a given user input.
        Returns the final assistant response text.
        """
        # Start with system prompt
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add history if any
        if history:
            messages.extend(history)
            
        # Add current user input
        messages.append({"role": "user", "content": user_input})

        for i in range(self.max_iterations):
            # 1. THINK: Send current state to Hermes
            response = self.provider.chat(
                messages=messages,
                tools=self.registry.get_schema_list(),
                stream=self.stream
            )

            # 2. Add assistant's response (text and/or tool calls) to messages
            assistant_msg = {"role": "assistant", "content": response.content}
            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments
                        }
                    } for tc in response.tool_calls
                ]
            
            messages.append(assistant_msg)

            # Display assistant text if any (for UX)
            if response.content:
                print(f"\033[36mHermes:\033[0m {response.content}")

            if not response.tool_calls:
                # If no tool calls, this iteration is the final answer
                return response.content

            # 3. ACT: Execute each tool call
            for tc in response.tool_calls:
                print(f"\033[33m[Agent]: Executing {tc.name}({json.dumps(tc.arguments)})...\033[0m")
                
                result = self.registry.dispatch(tc)
                
                # 4. OBSERVE: Add tool output to history
                # Note: Ollama uses 'role': 'tool' for results
                messages.append({
                    "role": "tool",
                    "content": result.content
                })
                
                if result.status == "failed":
                    print(f"\033[31m[Agent]: Tool '{tc.name}' failed.\033[0m")
                else:
                    print(f"\033[32m[Agent]: Tool '{tc.name}' returned success.\033[0m")

        # Fallback if loop ends without a terminal response
        error_msg = f"Agent reached max iterations ({self.max_iterations}) without resolving."
        print(f"\033[31m{error_msg}\033[0m")
        return "I've reached my maximum reasoning steps. Here is the latest state of the engagement."
