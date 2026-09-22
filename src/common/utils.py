import io
import secrets
import string


def generate_public_id(length: int = 11) -> str:
    """Generates a secure, random 11-character public ID."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def compress_and_upload_image(file_bytes: bytes, original_filename: str, folder: str = "products") -> str:
    """
    Compresses an image to WebP format and uploads it to Firebase Storage if available.
    """
    try:
        from PIL import Image
        from firebase_admin import storage

        img = Image.open(io.BytesIO(file_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        output_buffer = io.BytesIO()
        img.save(output_buffer, format="WEBP", quality=80)
        output_buffer.seek(0)

        bucket = storage.bucket()
        safe_filename = f"{generate_public_id(8)}.webp"
        destination_path = f"{folder}/{safe_filename}"
        blob = bucket.blob(destination_path)
        blob.upload_from_file(output_buffer, content_type="image/webp")
        blob.make_public()
        return blob.public_url
    except Exception:
        return f"/uploads/{folder}/{generate_public_id(8)}.webp"