import os
from pathlib import Path
import aiofiles


async def save_file(uploaded_bytes: bytes, filename: str, folder: str = "uploads") -> str:
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)
    dest = path / filename
    async with aiofiles.open(dest, "wb") as f:
        await f.write(uploaded_bytes)
    return str(dest)
