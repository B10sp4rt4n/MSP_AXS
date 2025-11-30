import os
import re
from pathlib import Path
import aiofiles
from ..core.config import settings


_FILENAME_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]")


def _secure_filename(name: str) -> str:
    # Remove path separators and disallowed chars
    name = os.path.basename(name)
    name = _FILENAME_SANITIZE_RE.sub("_", name)
    # Prevent empty names
    return name or "file.bin"


async def save_file(uploaded_bytes: bytes, filename: str) -> str:
    folder = Path(settings.UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = _secure_filename(filename)
    dest = folder / safe_name
    async with aiofiles.open(dest, "wb") as f:
        await f.write(uploaded_bytes)
    return str(dest)


def guardar_archivo(filename: str, content: bytes) -> str:
    """Guardar contenido binario de forma síncrona y devolver la ruta.

    - Sanitiza el nombre para evitar path traversal.
    - Usa `UPLOAD_DIR` desde settings.
    """
    folder = Path(settings.UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = _secure_filename(filename)
    dest = folder / safe_name
    with open(dest, "wb") as f:
        f.write(content)
    return str(dest)
