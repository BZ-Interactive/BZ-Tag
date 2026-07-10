from __future__ import annotations

from pathlib import Path

from mutagen.id3 import ID3, APIC, ID3NoHeaderError

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

SUPPORTED_EXTENSIONS = set(MIME_MAP.keys())


def detect_mime(image_path: Path) -> str | None:
    return MIME_MAP.get(image_path.suffix.lower())


def embed_cover(mp3_path: Path, image_path: Path) -> None:
    """Read an image file and embed it as cover art in the given MP3."""
    mime = detect_mime(image_path)
    if not mime:
        raise ValueError(f"Unsupported image format: {image_path.suffix}")

    data = image_path.read_bytes()

    try:
        audio = ID3(mp3_path)
    except ID3NoHeaderError:
        audio = ID3()

    audio.delall("APIC")
    audio["APIC"] = APIC(
        encoding=3,
        mime=mime,
        type=3,
        desc="Cover",
        data=data,
    )
    audio.save(mp3_path)


def remove_cover(mp3_path: Path) -> None:
    """Remove cover art from an MP3 file."""
    try:
        audio = ID3(mp3_path)
        audio.delall("APIC")
        audio.save(mp3_path)
    except ID3NoHeaderError:
        pass


def get_cover_data(mp3_path: Path) -> tuple[bytes, str] | None:
    """Extract cover art data and mime type from an MP3 file."""
    try:
        audio = ID3(mp3_path)
    except ID3NoHeaderError:
        return None

    for key in audio:
        if key.startswith("APIC"):
            pic = audio[key]
            return pic.data, pic.mime
    return None


def save_cover(mp3_path: Path, output_path: Path) -> Path | None:
    """Extract cover art from MP3 and save to file. Returns path or None."""
    result = get_cover_data(mp3_path)
    if not result:
        return None

    data, mime = result
    ext = mime.split("/")[-1].replace("jpeg", "jpg")
    if not ext.startswith("."):
        ext = f".{ext}"

    out = output_path.with_suffix(ext)
    out.write_bytes(data)
    return out
