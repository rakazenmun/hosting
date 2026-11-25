import stat
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Asset, Deployment

MAX_SIZE = settings.WNBASE_SITE_LIMIT_MIB * 1024 * 1024
MAX_FILES = settings.WNBASE_SITE_FILE_LIMIT
TYPES = {
    ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".cjs": "text/javascript; charset=utf-8", ".wasm": "application/wasm",
    ".json": "application/json", ".map": "application/json",
    ".webmanifest": "application/manifest+json", ".xml": "application/xml",
    ".txt": "text/plain; charset=utf-8", ".md": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8", ".vtt": "text/vtt; charset=utf-8",
    ".pdf": "application/pdf",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".ico": "image/x-icon",
    ".svg": "image/svg+xml", ".avif": "image/avif", ".bmp": "image/bmp",
    ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf", ".otf": "font/otf",
    ".mp4": "video/mp4", ".webm": "video/webm", ".ogv": "video/ogg",
    ".mov": "video/quicktime", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
    ".ogg": "audio/ogg", ".opus": "audio/ogg", ".wav": "audio/wav", ".flac": "audio/flac",
    ".gltf": "model/gltf+json", ".glb": "model/gltf-binary", ".bin": "application/octet-stream",
}
TOOLING_FILES = {
    "cname", "readme.md", "license", "license.md", "package.json",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
}
TOOLING_CONFIGS = ("next.config.", "vite.config.", "postcss.config.", "tailwind.config.", "eslint.config.")



def assets_from_zip(upload):
    if upload.size > MAX_SIZE:
        raise ValidationError(f"The ZIP must be {settings.WNBASE_SITE_LIMIT_MIB} MiB or smaller.")
    try:
        with ZipFile(upload) as archive:
            files = {}
            total = 0
            for item in archive.infolist():
                if item.is_dir():
                    continue
                path = item.filename
                parts = path.split("/")
                filename = parts[-1].lower()
                if any(
                    part == "__MACOSX" or part == "node_modules" or
                    (part.startswith(".") and part not in (".", ".."))
                    for part in parts
                ):
                    continue
                if filename in TOOLING_FILES or filename.startswith(TOOLING_CONFIGS):
                    continue
                if (
                    len(path) > 240 or "\\" in path or any(part in ("", ".", "..") for part in path.split("/"))
                    or any(ord(char) < 32 for char in path)
                    or stat.S_ISLNK(item.external_attr >> 16)
                    or PurePosixPath(path).suffix.lower() not in TYPES or path in files
                ):
                    if PurePosixPath(path).suffix.lower() in {".tsx", ".ts", ".jsx", ".vue", ".svelte"}:
                        raise ValidationError(f"{path[:100]} is source code. Build or export the site and upload the output folder.")
                    raise ValidationError(f"Unsupported file path or file type: {path[:100]}")
                total += item.file_size
                if total > MAX_SIZE or len(files) >= MAX_FILES:
                    raise ValidationError(f"Use at most {MAX_FILES} files and {settings.WNBASE_SITE_LIMIT_MIB} MiB of extracted content.")
                files[path] = archive.read(item)
    except (BadZipFile, RuntimeError, NotImplementedError, OSError) as exc:
        raise ValidationError("Upload a readable ZIP file.") from exc
    if "index.html" not in files and files:
        folder = next(iter(files)).split("/", 1)[0] + "/"
        if folder + "index.html" in files and all(path.startswith(folder) for path in files):
            files = {path[len(folder):]: content for path, content in files.items()}
    if "index.html" not in files:
        raise ValidationError("Put index.html at the root of the ZIP.")
    return files


@transaction.atomic
def publish(site, files):
    site = type(site).objects.select_for_update().get(pk=site.pk)
    if site.suspended:
        raise ValidationError("This site has been suspended.")
    release = Deployment.objects.create(site=site, size=sum(map(len, files.values())))
    Asset.objects.bulk_create(
        Asset(deployment=release, path=path, content=content) for path, content in files.items()
    )
    site.live = release
    site.save(update_fields=["live"])
    older = list(site.deployments.values_list("pk", flat=True)[3:])
    site.deployments.filter(pk__in=older).delete()
    return release
