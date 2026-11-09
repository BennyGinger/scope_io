"""Generic input revision references; no workflow or filename conventions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from scope_io.metadata.models import ImageMetadata


def input_reference(path: Path, metadata: ImageMetadata, output_directory: Path) -> dict[str, Any]:
    """
    Record the actual input revision using a portable relative path.
    """
    return {"artifact_path": Path(os.path.relpath(path.resolve(), output_directory.resolve())).as_posix(),
            "artifact_type": metadata.artifact.artifact_type,
            "created_at": metadata.artifact.created_at,
            "external": metadata.artifact.artifact_type is None}
