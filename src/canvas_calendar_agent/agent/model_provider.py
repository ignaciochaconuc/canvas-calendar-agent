"""Construcción aislada del backend de modelo para el Agents SDK."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

import requests
from agents import OpenAIChatCompletionsModel, set_tracing_disabled
from openai import AsyncOpenAI

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
OLLAMA_DUMMY_API_KEY = "ollama"


class ModelProviderError(ValueError):
    """Configuración o disponibilidad inválida del proveedor de modelo."""


def selected_provider(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return env.get("MODEL_PROVIDER", "ollama").strip().lower()


def build_model(
    environ: Mapping[str, str] | None = None,
    *,
    client_factory: Callable[..., Any] = AsyncOpenAI,
    tracing_configurer: Callable[[bool], None] = set_tracing_disabled,
) -> Any:
    """Crea el modelo configurado sin filtrar detalles al resto del agente."""
    env = os.environ if environ is None else environ
    provider = selected_provider(env)

    if provider == "ollama":
        base_url = env.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).strip()
        model_name = env.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
        if not base_url or not model_name:
            raise ModelProviderError("OLLAMA_BASE_URL y OLLAMA_MODEL no pueden estar vacíos.")
        tracing_configurer(True)
        client = client_factory(base_url=base_url, api_key=OLLAMA_DUMMY_API_KEY)
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    if provider == "openai":
        api_key = env.get("OPENAI_API_KEY", "").strip()
        model_name = env.get("OPENAI_MODEL", "").strip()
        if not api_key:
            raise ModelProviderError(
                "OPENAI_API_KEY es obligatoria cuando MODEL_PROVIDER=openai."
            )
        if not model_name:
            raise ModelProviderError(
                "OPENAI_MODEL es obligatorio cuando MODEL_PROVIDER=openai."
            )
        tracing_configurer(False)
        return model_name

    raise ModelProviderError(
        f"MODEL_PROVIDER desconocido: {provider!r}. Usa 'ollama' u 'openai'."
    )


def check_model_available(
    environ: Mapping[str, str] | None = None,
    *,
    http_get: Callable[..., Any] = requests.get,
) -> None:
    """Comprueba de antemano que Ollama responda y tenga el modelo configurado."""
    env = os.environ if environ is None else environ
    if selected_provider(env) != "ollama":
        return
    base_url = env.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
    model_name = env.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
    try:
        response = http_get(f"{base_url}/models", timeout=5)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.ConnectionError as exc:
        raise ModelProviderError(
            f"No se pudo conectar con Ollama en {base_url}. "
            "Instálalo e inicia el servicio antes de ejecutar el agente."
        ) from exc
    except (requests.exceptions.RequestException, ValueError) as exc:
        raise ModelProviderError(
            f"Ollama respondió incorrectamente en {base_url}: {exc}"
        ) from exc

    available = {
        item.get("id") for item in payload.get("data", []) if isinstance(item, dict)
    }
    if model_name not in available:
        raise ModelProviderError(
            f"El modelo {model_name!r} no está instalado en Ollama. "
            f"Ejecuta: ollama pull {model_name}"
        )
