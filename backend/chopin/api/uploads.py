"""Bounded, durable upload staging with cleanup on failure."""

import os
import uuid

MAX_IMPORT = 50 * 1024 * 1024


async def save_upload(file, folder, suffix):
    target = folder / (uuid.uuid4().hex + suffix)
    size = 0
    try:
        with target.open("xb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_IMPORT:
                    raise ValueError("Import exceeds the 50 MiB safety limit")
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        if not size:
            raise ValueError("File is empty")
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
