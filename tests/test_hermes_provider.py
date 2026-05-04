import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the project root to sys.path to allow imports from hermes
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We expect these to be defined in hermes/hermes_provider.py
try:
    from hermes.hermes_provider import HermesProvider, ChatResponse
except ImportError:
    # Fallback for when implementation doesn't exist yet so tests can be written
    class ChatResponse:
        def __init__(self, content, tool_calls, finish_reason, usage):
            self.content = content
            self.tool_calls = tool_calls
            self.finish_reason = finish_reason
            self.usage = usage
    
    class HermesProvider:
        pass

class TestHermesProvider(unittest.TestCase):
    def setUp(self):
        self.host = "http://localhost:11434"
        self.model = "hermes3:8b"
        self.provider = HermesProvider(self.host, self.model)

    @patch('requests.post')
    def test_chat_happy_path(self, mock_post):
        # Mock successful Ollama response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "Hello! I am ready to help.",
                "tool_calls": []
            },
            "done": True,
            "total_duration": 1000,
            "load_duration": 100,
            "sample_count": 50,
            "sample_duration": 200,
            "prompt_eval_count": 10,
            "prompt_eval_duration": 300,
            "eval_count": 40,
            "eval_duration": 400
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        response = self.provider.chat(messages, stream=False)

        self.assertEqual(response.content, "Hello! I am ready to help.")
        self.assertEqual(len(response.tool_calls), 0)
        self.assertEqual(response.finish_reason, "stop")

    @patch('requests.post')
    def test_chat_tool_call(self, mock_post):
        # Mock Ollama response with tool call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "run_vulnerability_scan",
                            "arguments": {
                                "targets": ["192.168.1.10"],
                                "operator": "Alice",
                                "engagement_ref": "ENG-2026-001"
                            }
                        }
                    }
                ]
            },
            "done": True
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Scan 192.168.1.10"}]
        tools = [{"type": "function", "function": {"name": "run_vulnerability_scan"}}]
        response = self.provider.chat(messages, tools=tools, stream=False)

        self.assertEqual(len(response.tool_calls), 1)
        # Check tool call structure (assuming attribute access or dict-like)
        tool_call = response.tool_calls[0]
        if hasattr(tool_call, 'function'):
            self.assertEqual(tool_call.function.name, "run_vulnerability_scan")
            self.assertEqual(tool_call.function.arguments["targets"], ["192.168.1.10"])
        else:
            self.assertEqual(tool_call["function"]["name"], "run_vulnerability_scan")

    @patch('requests.post')
    def test_chat_error_recovery(self, mock_post):
        # Test retry on 500 error
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        mock_response_error.raise_for_status.side_effect = Exception("Internal Server Error")
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "message": {"role": "assistant", "content": "Success after retry"},
            "done": True
        }
        
        # We need to configure the provider to have a small retry delay or mock time.sleep
        mock_post.side_effect = [mock_response_error, mock_response_success]

        with patch('time.sleep', return_value=None):
            messages = [{"role": "user", "content": "Test retry"}]
            response = self.provider.chat(messages, stream=False)

            self.assertEqual(response.content, "Success after retry")
            self.assertGreaterEqual(mock_post.call_count, 2)

if __name__ == '__main__':
    unittest.main()
