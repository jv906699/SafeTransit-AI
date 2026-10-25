
import os
import unittest
from unittest.mock import patch

from src.ollama_client import OllamaClient


class TestOllamaClientConfig(unittest.TestCase):
    def test_default_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            client = OllamaClient()

        self.assertEqual(
            client.base_url,
            "http://localhost:11434",
        )
        self.assertEqual(
            client.model,
            "qwen2.5-coder:7b-instruct",
        )
        self.assertEqual(client.timeout, 180)

    def test_environment_variable_overrides(self):
        env = {
            "OLLAMA_BASE_URL": "http://example.com:11434/",
            "OLLAMA_MODEL": "test-model",
            "OLLAMA_TIMEOUT": "90",
        }

        with patch.dict(os.environ, env, clear=True):
            client = OllamaClient()

        self.assertEqual(
            client.base_url,
            "http://example.com:11434",
        )
        self.assertEqual(client.model, "test-model")
        self.assertEqual(client.timeout, 90)

    def test_explicit_arguments_override_environment(self):
        env = {
            "OLLAMA_BASE_URL": "http://environment.example",
            "OLLAMA_MODEL": "environment-model",
            "OLLAMA_TIMEOUT": "90",
        }

        with patch.dict(os.environ, env, clear=True):
            client = OllamaClient(
                base_url="http://explicit.example/",
                model="explicit-model",
                timeout=45,
            )

        self.assertEqual(
            client.base_url,
            "http://explicit.example",
        )
        self.assertEqual(client.model, "explicit-model")
        self.assertEqual(client.timeout, 45)


if __name__ == "__main__":
    unittest.main()
