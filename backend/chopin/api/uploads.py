"""Bounded, durable upload staging with cleanup on failure."""

from ..platform.files import LOCAL_FILES

MAX_IMPORT = 50 * 1024 * 1024


async def save_upload(file, folder, suffix, *, files=LOCAL_FILES):
    target = None
    size = 0
    try:
        target = files.temporary_path(folder, prefix="upload-", suffix=suffix)
        with target.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_IMPORT:
                    raise ValueError("Import exceeds the 50 MiB safety limit")
                out.write(chunk)
            files.sync(out)
        if not size:
            raise ValueError("File is empty")
        files.sync_directory(folder)
        return target
    except Exception:
        if target is not None:
            target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
