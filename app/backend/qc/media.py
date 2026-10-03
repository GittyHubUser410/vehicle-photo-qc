import hashlib
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_BATCH_BYTES = 1024 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 50_000_000
FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
EXIF_KEYS = {
    271: "camera_make",
    272: "camera_model",
    36867: "capture_time",
    33434: "exposure_time",
    33437: "aperture",
    34855: "iso",
    37386: "focal_length",
    42036: "lens",
    274: "orientation",
}


def prepare_image(upload, photo_id: str, data: Path):
    """Validate bytes, preserve original, make an EXIF-oriented thumbnail. Caller owns cleanup."""
    temp = data / "tmp" / photo_id
    sha = hashlib.sha256()
    size = 0
    paths = [temp]
    try:
        with temp.open("wb") as handle:
            while block := upload.file.read(1024 * 1024):
                size += len(block)
                if size > MAX_FILE_BYTES:
                    raise ValueError("Each image must be 25 MB or smaller.")
                sha.update(block)
                handle.write(block)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(temp) as im:
                fmt = im.format
                if fmt not in FORMATS:
                    raise ValueError("Use JPEG, PNG, or WebP images. Export HEIC photos as JPEG first.")
                im.verify()
            with Image.open(temp) as im:
                exif = im.getexif()
                meta = {name: str(exif[key])[:250] for key, name in EXIF_KEYS.items() if key in exif}
                # Capture/lens values are commonly in the nested EXIF IFD.
                try:
                    nested = exif.get_ifd(34665)
                    meta.update(
                        {name: str(nested[key])[:250] for key, name in EXIF_KEYS.items() if key in nested}
                    )
                except (KeyError, TypeError, ValueError):
                    pass
                oriented = ImageOps.exif_transpose(im).convert("RGB")
                width, height = oriented.size
                if min(width, height) < 32:
                    raise ValueError("Images must be at least 32 × 32 pixels.")
                original_key = f"originals/{photo_id[:2]}/{photo_id}{FORMATS[fmt]}"
                thumbnail_key = f"thumbnails/{photo_id[:2]}/{photo_id}.jpg"
                for key in (original_key, thumbnail_key):
                    (data / key).parent.mkdir(parents=True, exist_ok=True)
                    paths.append(data / key)
                oriented.thumbnail((720, 540))
                oriented.save(data / thumbnail_key, "JPEG", quality=84)
        temp.replace(data / original_key)
        return dict(
            original_key=original_key,
            thumbnail_key=thumbnail_key,
            sha256=sha.hexdigest(),
            width=width,
            height=height,
            byte_size=size,
            exif=meta,
        ), paths
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        for path in paths:
            path.unlink(missing_ok=True)
        raise ValueError(str(exc) or "Unreadable image") from exc


def resolved_file(data: Path, key: str) -> Path:
    path = (data / key).resolve()
    if not path.is_relative_to(data.resolve()) or not path.is_file():
        raise FileNotFoundError(key)
    return path
