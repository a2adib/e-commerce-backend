from abc import ABC, abstractmethod
import os
from fastapi import UploadFile
from src.config import settings
from src.common.utils import generate_public_id


class StorageService(ABC):
    @abstractmethod
    async def upload_file(self, file: UploadFile, folder: str = "products") -> str:
        """Uploads a file and returns its URL."""
        pass


class LocalStorageService(StorageService):
    def __init__(self, base_dir: str = settings.STORAGE_DIR, base_url: str = settings.BASE_URL):
        self.base_dir = base_dir
        self.base_url = base_url

    async def upload_file(self, file: UploadFile, folder: str = "products") -> str:
        target_dir = os.path.join(self.base_dir, folder)
        os.makedirs(target_dir, exist_ok=True)

        ext = os.path.splitext(file.filename or "")[1]
        if not ext:
            ext = ".jpg"
        filename = f"{generate_public_id(12)}{ext}"
        filepath = os.path.join(target_dir, filename)

        content = await file.read()
        with open(filepath, "wb") as out_file:
            out_file.write(content)

        return f"{self.base_url}/uploads/{folder}/{filename}"


def get_storage_service() -> StorageService:
    return LocalStorageService()
