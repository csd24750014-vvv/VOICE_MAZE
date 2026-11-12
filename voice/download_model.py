"""Download and safely install the small English Vosk model once."""

import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

import config

_MODEL_NAME = "vosk-model-small-en-us-0.15"
_MODEL_URL = f"https://alphacephei.com/vosk/models/{_MODEL_NAME}.zip"
_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
_MAX_EXTRACTED_BYTES = 250 * 1024 * 1024


def main() -> None:
    """Download the official model archive and install it beside the assets."""
    target = config.VOICE_MODEL_DIR
    if (target / "am" / "final.mdl").is_file():
        print(f"Offline voice model is already installed at: {target}")
        return
    if target.exists():
        raise FileExistsError(
            f"The model directory exists but is incomplete: {target}. "
            "Move or remove that directory, then run this command again."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".vosk-model-",
        dir=target.parent,
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        archive_path = temporary_root / "model.zip"
        extracted_root = temporary_root / "extracted"
        extracted_root.mkdir()

        print("Downloading the approximately 40 MB offline English model...")
        _download_archive(archive_path)
        _extract_model(archive_path, extracted_root)
        model_source = extracted_root / _MODEL_NAME
        if not (model_source / "am" / "final.mdl").is_file():
            raise ValueError("The downloaded archive does not contain a valid Vosk model.")
        model_source.replace(target)
    print(f"Offline voice model installed at: {target}")


def _download_archive(destination: Path) -> None:
    """Stream the fixed HTTPS model archive while enforcing a size limit."""
    request = urllib.request.Request(
        _MODEL_URL,
        headers={"User-Agent": "VoiceMaze/1.0 offline-model-installer"},
    )
    downloaded = 0
    with urllib.request.urlopen(request, timeout=60) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > _MAX_DOWNLOAD_BYTES:
            raise ValueError("The model archive is larger than the allowed download size.")
        with destination.open("wb") as archive_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > _MAX_DOWNLOAD_BYTES:
                    raise ValueError("The model archive exceeded the allowed download size.")
                archive_file.write(chunk)
    if downloaded == 0:
        raise ValueError("The model download was empty.")


def _extract_model(archive_path: Path, destination: Path) -> None:
    """Extract only regular files under the expected model directory."""
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        extracted_size = sum(entry.file_size for entry in entries)
        if extracted_size > _MAX_EXTRACTED_BYTES:
            raise ValueError("The extracted model exceeds the allowed size.")
        for entry in entries:
            archive_pathname = PurePosixPath(entry.filename.replace("\\", "/"))
            if (
                archive_pathname.is_absolute()
                or not archive_pathname.parts
                or archive_pathname.parts[0] != _MODEL_NAME
                or any(part in {"", ".", ".."} for part in archive_pathname.parts)
            ):
                raise ValueError("The model archive contains an unsafe file path.")
            mode = (entry.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise ValueError("The model archive contains an unsupported symbolic link.")

            output_path = destination.joinpath(*archive_pathname.parts)
            if entry.is_dir():
                output_path.mkdir(parents=True, exist_ok=True)
                continue
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, output_path.open("wb") as output:
                shutil.copyfileobj(source, output)


if __name__ == "__main__":
    main()
