"""Caché local de descargas; no contiene secretos y está excluida de Git."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


class FileCache:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, file: dict[str, Any]) -> Path:
        identity = "|".join(str(file.get(key, "")) for key in ("id", "updated_at", "size"))
        digest = hashlib.sha256(identity.encode()).hexdigest()[:16]
        name = str(file.get("display_name") or file.get("filename") or "")
        extension = Path(name).suffix.lower() if Path(name).suffix.lower() in {".pdf", ".xlsx", ".xls"} else ".bin"
        return self.root / f"{file.get('id', 'file')}-{digest}{extension}"

    def get(self, file: dict[str, Any]) -> Path | None:
        path = self.path_for(file)
        return path if path.is_file() else None
