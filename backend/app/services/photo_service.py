"""PhotoService — 현장 사진 업로드 (CONTRACT §4-9).

jpg/png/webp · 파일당 10MB · 요청당 최대 5장.
저장 전에 **EXIF 를 제거**하고(촬영 위치·기기 정보가 그대로 남는 것을 막는다)
**320px 썸네일**을 함께 만든다. 원본과 썸네일은 `backend/uploads/` 아래에 둔다.

파트명은 `files` 이며 배열이다. 한 요청에 여러 장이 오므로, 개수 초과는 전체를 거절하고
(409) 형식·용량 위반도 저장 전에 걸러 부분 저장이 남지 않게 한다.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.models import User, WorkRequestPhoto
from app.repositories.work_request_repo import WorkRequestRepository

#: content-type → 저장 포맷·확장자
FORMATS = {
    "image/jpeg": ("JPEG", ".jpg"),
    "image/png": ("PNG", ".png"),
    "image/webp": ("WEBP", ".webp"),
}


class PhotoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkRequestRepository(db)
        self.settings = get_settings()

    def list(self, wr_id: str, current: User) -> list[WorkRequestPhoto]:
        from app.services.work_request_service import WorkRequestService

        WorkRequestService(self.db).get_for(wr_id, current)  # 404 · 403 게이트
        return self.repo.photos_for(wr_id)

    def upload(self, wr_id: str, uploads: list[tuple[str | None, str | None, bytes]], current: User) -> list[WorkRequestPhoto]:
        from app.services.work_request_service import WorkRequestService

        service = WorkRequestService(self.db)
        wr = service.get_for(wr_id, current)
        service.assert_owner(wr, current)

        if not uploads:
            raise AppError(
                ErrorCode.VALIDATION_FAILED,
                "업로드할 파일이 없습니다",
                [{"field": "files", "message": "필수 항목"}],
            )

        existing = self.repo.count_photos(wr.id)
        limit = self.settings.max_photos_per_request
        if existing + len(uploads) > limit:
            raise AppError(
                ErrorCode.PHOTO_LIMIT_EXCEEDED,
                f"사진은 요청당 최대 {limit}장입니다 (현재 {existing}장)",
            )

        # 검증을 먼저 전부 끝내고 나서 저장한다 — 일부만 저장되는 상태를 만들지 않는다
        prepared = [self._prepare(name, content_type, data) for name, content_type, data in uploads]

        directory: Path = self.settings.uploads_dir
        directory.mkdir(parents=True, exist_ok=True)
        saved: list[WorkRequestPhoto] = []
        for file_name, suffix, original_bytes, thumb_bytes in prepared:
            photo = WorkRequestPhoto(
                work_request_id=wr.id,
                file_name=file_name,
                size=len(original_bytes),
                storage_key="",
                thumbnail_key="",
                uploaded_at=datetime.now(timezone.utc),
            )
            self.db.add(photo)
            self.db.flush()  # UUID PK 를 얻어 파일명에 쓴다
            photo.storage_key = f"{wr.id}/{photo.id}{suffix}"
            photo.thumbnail_key = f"{wr.id}/{photo.id}_thumb{suffix}"
            (directory / wr.id).mkdir(parents=True, exist_ok=True)
            (directory / photo.storage_key).write_bytes(original_bytes)
            (directory / photo.thumbnail_key).write_bytes(thumb_bytes)
            saved.append(photo)

        self.db.commit()
        for photo in saved:
            self.db.refresh(photo)
        return saved

    def _prepare(self, file_name: str | None, content_type: str | None, data: bytes) -> tuple[str, str, bytes, bytes]:
        """형식·용량을 검사하고 EXIF 를 제거한 원본과 썸네일 바이트를 만든다."""
        if content_type not in FORMATS:
            raise AppError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                f"지원하지 않는 파일 형식입니다: {content_type or 'unknown'} (jpg·png·webp)",
                [{"field": "files", "message": "jpg · png · webp 만 허용"}],
            )
        if not data:
            raise AppError(
                ErrorCode.VALIDATION_FAILED,
                "빈 파일은 업로드할 수 없습니다",
                [{"field": "files", "message": "빈 파일"}],
            )
        if len(data) > self.settings.max_upload_bytes:
            limit_mb = self.settings.max_upload_bytes / (1024 * 1024)
            raise AppError(ErrorCode.FILE_TOO_LARGE, f"파일 용량이 상한을 초과했습니다 (파일당 최대 {limit_mb:.0f}MB)")

        pillow_format, suffix = FORMATS[content_type]
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                stripped = self._strip_exif(image, pillow_format)
                thumbnail = self._thumbnail(image, pillow_format)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise AppError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "이미지를 읽을 수 없습니다. 손상되었거나 형식이 맞지 않습니다",
                [{"field": "files", "message": "이미지 디코딩 실패"}],
            ) from exc

        safe_name = Path(file_name or "photo").name or "photo"
        return safe_name, suffix, stripped, thumbnail

    @staticmethod
    def _normalize(image: Image.Image, pillow_format: str) -> Image.Image:
        """JPEG 는 알파를 지원하지 않으므로 RGB 로 맞춘다."""
        if pillow_format == "JPEG" and image.mode not in {"RGB", "L"}:
            return image.convert("RGB")
        return image

    def _strip_exif(self, image: Image.Image, pillow_format: str) -> bytes:
        """픽셀만 새 이미지로 옮겨 담아 EXIF·ICC 등 부가 메타데이터를 떨어뜨린다."""
        source = self._normalize(image, pillow_format)
        clean = Image.new(source.mode, source.size)
        clean.paste(source)  # 픽셀만 옮긴다 — info/exif 는 따라오지 않는다
        buffer = io.BytesIO()
        clean.save(buffer, format=pillow_format)
        return buffer.getvalue()

    def _thumbnail(self, image: Image.Image, pillow_format: str) -> bytes:
        source = self._normalize(image, pillow_format).copy()
        side = self.settings.thumbnail_px
        source.thumbnail((side, side))
        clean = Image.new(source.mode, source.size)
        clean.paste(source)
        buffer = io.BytesIO()
        clean.save(buffer, format=pillow_format)
        return buffer.getvalue()


#: `/uploads` 정적 마운트가 서빙하는 경로 접두어 (main.py 참조)
UPLOADS_URL_PREFIX = "/uploads"


def photo_to_schema(photo: WorkRequestPhoto) -> dict:
    return {
        "id": photo.id,
        "photoId": photo.id,
        "workRequestId": photo.work_request_id,
        "fileName": photo.file_name,
        "size": photo.size,
        "storageKey": photo.storage_key,
        "thumbnailKey": photo.thumbnail_key,
        "originalUrl": f"{UPLOADS_URL_PREFIX}/{photo.storage_key}",
        "thumbnailUrl": f"{UPLOADS_URL_PREFIX}/{photo.thumbnail_key}",
        "uploadedAt": photo.uploaded_at,
    }
