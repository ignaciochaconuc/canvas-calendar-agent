"""Cliente pequeño y de solo lectura para la API REST de Canvas."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests


class CanvasError(Exception):
    """Error comprensible al comunicarse con Canvas."""


class CanvasClient:
    """Cliente básico autenticado mediante un token de acceso de Canvas."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 15.0,
        session: requests.Session | None = None,
    ) -> None:
        base_url = base_url.strip().rstrip("/")
        parsed_url = urlparse(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise CanvasError("CANVAS_BASE_URL debe ser una URL HTTP(S) válida.")
        if parsed_url.username or parsed_url.password:
            raise CanvasError("CANVAS_BASE_URL no debe contener credenciales.")
        if not token.strip():
            raise CanvasError("CANVAS_TOKEN no está configurado.")

        self.base_url = base_url
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token.strip()}", "Accept": "application/json"}
        )

    def get_active_courses(self) -> list[dict[str, Any]]:
        """Obtiene todos los cursos activos visibles para el usuario actual."""
        url: str | None = f"{self.base_url}/api/v1/courses"
        params: dict[str, Any] | None = {
            "enrollment_state": "active",
            "per_page": 100,
        }
        courses: list[dict[str, Any]] = []

        while url:
            response = self._get(url, params=params)
            params = None
            try:
                payload = response.json()
            except ValueError as exc:
                raise CanvasError("Canvas devolvió una respuesta que no es JSON.") from exc

            if not isinstance(payload, list):
                raise CanvasError("Canvas devolvió un formato inesperado para los cursos.")
            if not all(isinstance(course, dict) for course in payload):
                raise CanvasError("Canvas devolvió un curso con formato inesperado.")

            courses.extend(payload)
            url = response.links.get("next", {}).get("url")
            if url:
                next_url = urlparse(url)
                base = urlparse(self.base_url)
                if (next_url.scheme, next_url.netloc) != (base.scheme, base.netloc):
                    raise CanvasError("Canvas devolvió un enlace de paginación inesperado.")

        return courses

    def _get(
        self, url: str, *, params: dict[str, Any] | None = None
    ) -> requests.Response:
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.ConnectionError as exc:
            raise CanvasError(
                "No fue posible conectar con Canvas. Revisa la URL y tu conexión."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise CanvasError("La conexión con Canvas superó el tiempo de espera.") from exc
        except requests.exceptions.RequestException as exc:
            raise CanvasError("Ocurrió un error al comunicarse con Canvas.") from exc

        if response.status_code in {401, 403}:
            raise CanvasError("Canvas rechazó el token. Revisa CANVAS_TOKEN.")
        if response.status_code == 404:
            raise CanvasError("Canvas no encontró el recurso. Revisa CANVAS_BASE_URL.")
        if not response.ok:
            raise CanvasError(f"Canvas respondió con un error HTTP {response.status_code}.")
        return response
