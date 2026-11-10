"""Atomic private-metadata replacement without decoding or changing image pixels."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import tifffile
from pathlib import Path
from scope_io.metadata.codec import ARTIFACT_METADATA_TAG
from scope_io.metadata.models import ImageMetadata
from scope_io.metadata.imageJ_meta import InfoSummary
from scope_io.writers.core import _replace_with_retry


def rewrite_metadata(path: Path, metadata: ImageMetadata, *, output_path: Path | None = None) -> Path:
    """
    Replace the private TIFF metadata atomically, preserving encoded pixel data.
    """
    target = output_path or path
    fd, name = tempfile.mkstemp(dir=target.parent, suffix=target.suffix)
    os.close(fd)
    temporary = Path(name)
    try:
        shutil.copy2(path, temporary)
        with tifffile.TiffFile(temporary, mode="r+") as tif:
            tag = tif.pages.first.tags.get(ARTIFACT_METADATA_TAG)
            if tag is None:
                raise ValueError("This TIFF has no private metadata tag to update.")
            tag.overwrite(json.dumps(metadata.dump(), ensure_ascii=False).encode())
        # Reopen after an append: tifffile caches file size and may otherwise
        # grow an old end-of-file tag across the newly appended private payload.
        with tifffile.TiffFile(temporary, mode='r+') as tif:
            imagej = tif.imagej_metadata
            if imagej is not None and 'Info' in imagej:
                imagej['Info'] = InfoSummary(metadata.to_info_payload()).render(delimiter_levels=2)
                for code, dtype, count, value, write_once in tifffile.imagej_metadata_tag(imagej, tif.byteorder):
                    existing = tif.pages.first.tags.get(code)
                    if existing is not None:
                        existing.overwrite(value, dtype=dtype)
        _replace_with_retry(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
