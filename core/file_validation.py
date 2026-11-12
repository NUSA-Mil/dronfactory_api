import uuid
from typing import Tuple
from fastapi import UploadFile
from core.exceptions import BadRequestException

ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm"
}

IMAGE_MAGIC_BYTES = [
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"RIFF", ".webp")
]

VIDEO_MAGIC_BYTES = [
    (b"\x1a\x45\xdf\xa3", ".webm"),
]

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
CHUNK_SIZE = 8192  # 8 KB


async def validate_and_save_image(file: UploadFile) -> Tuple[bytes, str]:
    """[Исправление 2]: Потоковое чтение файла для предотвращения OOM DoS"""
    if not file.filename:
        raise BadRequestException("Файл не имеет имени")

    header = await file.read(12)
    await file.seek(0)

    is_valid_magic = any(header.startswith(magic) for magic, _ in IMAGE_MAGIC_BYTES)
    if not is_valid_magic or file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise BadRequestException("Файл не является валидным изображением (JPG, PNG, WebP)")

    # Чтение файлового потока чанками
    content_chunks = []
    total_size = 0

    while chunk := await file.read(CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > MAX_IMAGE_SIZE_BYTES:
            raise BadRequestException("Размер изображения превышает лимит 10 МБ")
        content_chunks.append(chunk)

    content = b"".join(content_chunks)
    ext = ALLOWED_IMAGE_MIME_TYPES.get(file.content_type, ".jpg")
    random_filename = f"{uuid.uuid4()}{ext}"

    return content, random_filename


async def validate_and_save_video(file: UploadFile) -> Tuple[bytes, str]:
    """[Исправление 2]: Потоковое чтение видеофайла (100MB лимит)"""
    if not file.filename:
        raise BadRequestException("Файл не имеет имени")

    header = await file.read(12)
    await file.seek(0)

    is_mp4_magic = len(header) >= 8 and header[4:8] == b"ftyp"
    is_webm_magic = any(header.startswith(magic) for magic, _ in VIDEO_MAGIC_BYTES)

    if not (is_mp4_magic or is_webm_magic) or file.content_type not in ALLOWED_VIDEO_MIME_TYPES:
        raise BadRequestException("Файл не является валидным видеофайлом (MP4, WebM)")

    content_chunks = []
    total_size = 0

    while chunk := await file.read(CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > MAX_VIDEO_SIZE_BYTES:
            raise BadRequestException("Размер видеофайла превышает лимит 100 МБ")
        content_chunks.append(chunk)

    content = b"".join(content_chunks)
    ext = ALLOWED_VIDEO_MIME_TYPES.get(file.content_type, ".mp4")
    random_filename = f"{uuid.uuid4()}{ext}"

    return content, random_filename