import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canvas_calendar_agent.agent.model_provider import (
    OLLAMA_DUMMY_API_KEY,
    ModelProviderError,
    build_model,
    check_model_available,
)


class ModelProviderTests(unittest.TestCase):
    @patch("canvas_calendar_agent.agent.model_provider.OpenAIChatCompletionsModel")
    def test_ollama_uses_configured_url_model_and_no_openai_key(self, model_class):
        client_factory = Mock(return_value=Mock())
        tracing = Mock()
        env = {
            "MODEL_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://localhost:9999/v1",
            "OLLAMA_MODEL": "qwen-test:8b",
        }
        result = build_model(
            env, client_factory=client_factory, tracing_configurer=tracing
        )
        client_factory.assert_called_once_with(
            base_url="http://localhost:9999/v1", api_key="ollama"
        )
        model_class.assert_called_once_with(
            model="qwen-test:8b", openai_client=client_factory.return_value
        )
        tracing.assert_called_once_with(True)
        self.assertIs(result, model_class.return_value)
        self.assertNotIn("OPENAI_API_KEY", env)

    def test_ollama_dummy_key_is_public_constant(self):
        self.assertEqual(OLLAMA_DUMMY_API_KEY, "ollama")

    def test_openai_requires_api_key(self):
        with self.assertRaisesRegex(ModelProviderError, "OPENAI_API_KEY"):
            build_model(
                {"MODEL_PROVIDER": "openai", "OPENAI_MODEL": "example-model"},
                tracing_configurer=Mock(),
            )

    def test_openai_uses_configured_model_and_enables_tracing(self):
        tracing = Mock()
        model = build_model(
            {
                "MODEL_PROVIDER": "openai",
                "OPENAI_MODEL": "example-model",
                "OPENAI_API_KEY": "test-only-key",
            },
            tracing_configurer=tracing,
        )
        self.assertEqual(model, "example-model")
        tracing.assert_called_once_with(False)

    def test_unknown_provider_has_clear_error(self):
        with self.assertRaisesRegex(ModelProviderError, "desconocido"):
            build_model({"MODEL_PROVIDER": "unknown"}, tracing_configurer=Mock())

    def test_availability_check_reports_missing_model(self):
        response = Mock()
        response.json.return_value = {"data": [{"id": "other-model"}]}
        with self.assertRaisesRegex(ModelProviderError, "ollama pull qwen3:8b"):
            check_model_available(
                {"MODEL_PROVIDER": "ollama", "OLLAMA_MODEL": "qwen3:8b"},
                http_get=Mock(return_value=response),
            )
        response.raise_for_status.assert_called_once()

    def test_availability_check_accepts_installed_model(self):
        response = Mock()
        response.json.return_value = {"data": [{"id": "qwen3:8b"}]}
        check_model_available(
            {"MODEL_PROVIDER": "ollama", "OLLAMA_MODEL": "qwen3:8b"},
            http_get=Mock(return_value=response),
        )


if __name__ == "__main__":
    unittest.main()
