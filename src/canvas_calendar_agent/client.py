"""Cliente pequeño y de solo lectura para la API REST de Canvas."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests


class CanvasError(Exception):
    """Error comprensible al comunicarse con Canvas."""


class CanvasClient:
    """Cliente de exploración autenticado mediante un token de Canvas."""

    def __init__(self, base_url: str, token: str, *, timeout: float = 15.0,
                 session: requests.Session | None = None) -> None:
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
        """Obtiene cursos con matrícula activa, no necesariamente del periodo actual."""
        return self._get_paginated("/api/v1/courses", params={
            "enrollment_state": "active", "include[]": "term", "per_page": 100,
        })

    def get_assignments(self, course_id: int) -> list[dict[str, Any]]:
        """Devuelve tareas visibles, incluidas descripción, fechas y entrega."""
        return self._get_paginated(f"/api/v1/courses/{course_id}/assignments")

    def get_modules(self, course_id: int) -> list[dict[str, Any]]:
        """Devuelve módulos y sus items visibles."""
        modules = self._get_paginated(
            f"/api/v1/courses/{course_id}/modules",
            params={"include[]": ["items", "content_details"], "per_page": 100},
        )
        for module in modules:
            if module.get("items") is None:
                module["items"] = self._get_paginated(
                    f"/api/v1/courses/{course_id}/modules/{module['id']}/items",
                    params={"include[]": "content_details", "per_page": 100},
                )
        return modules

    def get_pages(self, course_id: int) -> list[dict[str, Any]]:
        """Devuelve páginas visibles, incluido su cuerpo cuando Canvas lo permite."""
        return self._get_paginated(
            f"/api/v1/courses/{course_id}/pages", params={"include[]": "body"}
        )

    def get_files(self, course_id: int) -> list[dict[str, Any]]:
        """Devuelve metadatos de archivos, sin descargar su contenido."""
        return self._get_paginated(f"/api/v1/courses/{course_id}/files")

    def get_calendar_events(self, course_id: int) -> list[dict[str, Any]]:
        """Devuelve todos los eventos de calendario visibles del curso."""
        return self._get_paginated("/api/v1/calendar_events", params={
            "context_codes[]": f"course_{course_id}", "type": "event",
            "all_events": "true", "per_page": 100,
        })

    def get_course_details(self, course_id: int) -> dict[str, Any]:
        """Devuelve detalles del curso, incluidos syllabus y periodo."""
        return self._get_json_object(
            f"/api/v1/courses/{course_id}",
            params={"include[]": ["syllabus_body", "term"]},
        )

    def get_announcements(self, course_id: int) -> list[dict[str, Any]]:
        """Devuelve los anuncios visibles del curso."""
        return self._get_paginated("/api/v1/announcements", params={
            "context_codes[]": f"course_{course_id}", "active_only": "false",
            "latest_only": "false", "start_date": "2000-01-01",
            "end_date": "2100-01-01", "per_page": 100,
        })

    def _get_paginated(self, path: str, *,
                       params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Recorre de forma segura cualquier listado paginado de Canvas."""
        url: str | None = self._api_url(path)
        request_params = dict(params or {})
        request_params.setdefault("per_page", 100)
        results: list[dict[str, Any]] = []
        while url:
            response = self._get(url, params=request_params)
            request_params = None
            payload = self._response_json(response)
            if not isinstance(payload, list) or not all(
                isinstance(item, dict) for item in payload
            ):
                raise CanvasError("Canvas devolvió un listado con formato inesperado.")
            results.extend(payload)
            url = response.links.get("next", {}).get("url")
            if url:
                self._validate_same_origin(url)
        return results

    def _get_json_object(self, path: str, *,
                         params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._get(self._api_url(path), params=params)
        payload = self._response_json(response)
        if not isinstance(payload, dict):
            raise CanvasError("Canvas devolvió un objeto con formato inesperado.")
        return payload

    def _api_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _validate_same_origin(self, url: str) -> None:
        candidate, base = urlparse(url), urlparse(self.base_url)
        if (candidate.scheme, candidate.netloc) != (base.scheme, base.netloc):
            raise CanvasError("Canvas devolvió un enlace de paginación inesperado.")

    @staticmethod
    def _response_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise CanvasError("Canvas devolvió una respuesta que no es JSON.") from exc

    def _get(self, url: str, *,
             params: dict[str, Any] | None = None) -> requests.Response:
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
            raise CanvasError("Canvas rechazó el token o no autorizó este recurso.")
        if response.status_code == 404:
            raise CanvasError("Canvas no encontró el recurso solicitado.")
        if not response.ok:
            raise CanvasError(f"Canvas respondió con un error HTTP {response.status_code}.")
        return response
