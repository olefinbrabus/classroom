import os
from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse, Response
from starlette.routing import Route
from starlette_admin.contrib.sqla import Admin
from starlette_admin.fields import BaseField
from starlette.exceptions import HTTPException

from database.engine import PROJECT_ROOT
from database.models import UploadedFile

TEXT_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-yaml",
    "text/csv",
    "text/html",
    "text/markdown",
    "text/plain",
    "text/xml",
}


def is_image_content_type(content_type: str | None) -> bool:
    return bool(content_type and content_type.startswith("image/"))


def is_text_content_type(content_type: str | None) -> bool:
    return bool(
        content_type
        and (content_type.startswith("text/") or content_type in TEXT_CONTENT_TYPES)
    )


def get_upload_root() -> Path:
    return Path(os.environ.get("CLASSROOM_UPLOAD_ROOT", PROJECT_ROOT / "uploads")).resolve()


def resolve_uploaded_file_path(storage_path: str) -> Path:
    upload_root = get_upload_root()
    path = Path(storage_path)
    resolved_path = path.resolve() if path.is_absolute() else (upload_root / path).resolve()

    if not resolved_path.is_relative_to(upload_root):
        raise HTTPException(status_code=404, detail="File not found")
    return resolved_path


async def uploaded_file_preview(request: Request):
    uploaded_file = await request.state.session.get(
        UploadedFile,
        int(request.path_params["file_id"]),
    )
    if uploaded_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    if uploaded_file.content is not None:
        return Response(
            uploaded_file.content,
            media_type=uploaded_file.content_type,
            headers={
                "Content-Disposition": f'inline; filename="{uploaded_file.filename}"'
            },
        )

    file_path = resolve_uploaded_file_path(uploaded_file.storage_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type=uploaded_file.content_type,
        filename=uploaded_file.filename,
        content_disposition_type="inline",
    )


def add_uploaded_file_preview_route(admin: Admin) -> None:
    admin.routes.append(
        Route(
            "/uploaded-files/{file_id:int}/preview",
            uploaded_file_preview,
            methods=["GET"],
            name="uploaded-file-preview",
        )
    )


class UploadedFilePreviewField(BaseField):
    def __init__(self, name: str = "preview", label: str = "Preview") -> None:
        super().__init__(
            name=name,
            label=label,
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
            searchable=False,
            orderable=False,
            display_template="displays/uploaded_file_preview.html",
        )

    async def parse_obj(self, request: Request, obj: UploadedFile):
        content_type = obj.content_type or ""
        route_name = request.app.state.ROUTE_NAME
        return {
            "url": str(
                request.url_for(
                    f"{route_name}:uploaded-file-preview",
                    file_id=obj.id,
                )
            ),
            "filename": obj.filename,
            "content_type": content_type,
            "is_image": is_image_content_type(content_type),
            "is_text": is_text_content_type(content_type),
        }
