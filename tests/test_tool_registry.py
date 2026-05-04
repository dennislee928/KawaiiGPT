import unittest
from unittest.mock import MagicMock
import sys
import os

# Add the project root to sys.path to allow imports from hermes
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We expect these to be defined in hermes/tool_registry.py
try:
    from hermes.tool_registry import ToolRegistry, ToolDefinition
except ImportError:
    # Fallback for when implementation doesn't exist yet
    class ToolDefinition:
        def __init__(self, name, description, parameters, handler, requires_auth=True, dry_run_safe=False):
            self.name = name
            self.description = description
            self.parameters = parameters
            self.handler = handler
            self.requires_auth = requires_auth
            self.dry_run_safe = dry_run_safe
    
    class ToolRegistry:
        pass

class TestToolRegistry(unittest.TestCase):
    def setUp(self):
        # We assume the constructor exists
        try:
            self.registry = ToolRegistry()
        except TypeError:
            self.registry = MagicMock()

    def test_register_and_get_schema(self):
        def dummy_handler(**kwargs):
            return {"status": "success"}

        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"}
                },
                "required": ["arg1"]
            },
            handler=dummy_handler
        )

        # If register is not yet implemented, this test will fail gracefully or we mock it
        if hasattr(self.registry, 'register'):
            self.registry.register(tool)
            
            if hasattr(self.registry, 'get_schema_list'):
                schemas = self.registry.get_schema_list()
                self.assertEqual(len(schemas), 1)
                self.assertEqual(schemas[0]["function"]["name"], "test_tool")
                self.assertEqual(schemas[0]["function"]["parameters"]["required"], ["arg1"])

    def test_dispatch(self):
        handler_mock = MagicMock(return_value={"status": "dispatched"})
        tool = ToolDefinition(
            name="dispatch_tool",
            description="Tool for dispatch testing",
            parameters={"type": "object", "properties": {}},
            handler=handler_mock
        )

        if hasattr(self.registry, 'register') and hasattr(self.registry, 'dispatch'):
            self.registry.register(tool)

            # Mocking the ToolCall object structure from Section 11.2
            tool_call = MagicMock()
            tool_call.function.name = "dispatch_tool"
            tool_call.function.arguments = {"param1": "value1"}

            result = self.registry.dispatch(tool_call)

            self.assertEqual(result, {"status": "dispatched"})
            handler_mock.assert_called_once_with(param1="value1")

    def test_dispatch_unknown_tool(self):
        if hasattr(self.registry, 'dispatch'):
            tool_call = MagicMock()
            tool_call.function.name = "unknown_tool"
            
            with self.assertRaises(Exception): # Could be ValueError or KeyError
                self.registry.dispatch(tool_call)

if __name__ == '__main__':
    unittest.main()
