import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from database.engine import PROJECT_ROOT

CHUNK_SIZE = 1024 * 1024


def get_upload_root() -> Path:
    return Path(os.environ.get("CLASSROOM_UPLOAD_ROOT", PROJECT_ROOT / "uploads")).resolve()


def clean_filename(filename: str | None) -> str:
    name = Path(filename or "upload.bin").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "upload.bin"


async def save_upload_file(file: UploadFile, owner_id: int) -> tuple[str, int]:
    upload_root = get_upload_root()
    relative_dir = Path(f"user-{owner_id}")
    target_dir = upload_root / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}_{clean_filename(file.filename)}"
    relative_path = relative_dir / filename
    target_path = (upload_root / relative_path).resolve()

    if not target_path.is_relative_to(upload_root):
        raise ValueError("Invalid upload path")

    size = 0
    with target_path.open("wb") as output:
        while chunk := await file.read(CHUNK_SIZE):
            size += len(chunk)
            output.write(chunk)

    return relative_path.as_posix(), size
