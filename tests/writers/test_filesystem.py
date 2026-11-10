# tests/test_writer.py
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import pytest
from scope_io.readers.protocol import ImageReader

from scope_io.writers.filesystem import (
    _ends_with_s_number,
    build_output_path,
    create_save_path,
    get_save_dir,
)

# -----------------------------
# Filesystem tests (unchanged)
# -----------------------------

def test_build_output_path_joins_series_dir_and_save_name(tmp_path: Path, dummy_reader: ImageReader) -> None:
    """
    Create an output under the input's own series directory.
    """
    source_dir = tmp_path / "input"
    reader = replace(dummy_reader, img_path=source_dir / "sample.tif", series_idx=0)

    out = build_output_path(reader, save_name="masks.tif")
    assert out == source_dir / "sample_s1" / "masks.tif"
    assert out.parent.is_dir()


@pytest.mark.parametrize("bad_save_name", ["", None])
def test_build_output_path_rejects_bad_save_name(tmp_path: Path, bad_save_name: object, dummy_reader: ImageReader) -> None:
    """
    Reject empty output names before creating a destination.
    """
    reader = replace(dummy_reader, img_path=tmp_path / "sample.tif", series_idx=0)

    with pytest.raises(ValueError):
        build_output_path(reader, save_name=bad_save_name)  # type: ignore[arg-type]


def test_get_save_dir_resolves_s1_for_single_series(tmp_path: Path, dummy_reader: ImageReader) -> None:
    """
    Resolve the first series without creating its folder.
    """
    input_path = tmp_path / "input" / "my_image.tif"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(b"")

    reader = replace(dummy_reader, img_path=input_path, series_idx=0)
    expected_dir = input_path.parent / "my_image_s1"
    assert get_save_dir(reader) == expected_dir
    assert not expected_dir.exists()


def test_get_save_dir_resolves_one_folder_per_series(tmp_path: Path, dummy_reader: ImageReader) -> None:
    """
    Keep series destinations distinct for a shared acquisition.
    """
    input_path = tmp_path / "data" / "sample.nd2"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(b"")

    readers = [replace(dummy_reader, img_path=input_path, series_idx=i) for i in range(3)]
    assert [get_save_dir(reader) for reader in readers] == [
        input_path.parent / "sample_s1",
        input_path.parent / "sample_s2",
        input_path.parent / "sample_s3",
    ]

# Test the regex helper
def test_ends_with_s_number_valid() -> None:
    """Test valid _sN patterns."""
    assert _ends_with_s_number("experiment_s1")
    assert _ends_with_s_number("experiment_s01")
    assert _ends_with_s_number("experiment_s123")
    assert _ends_with_s_number("my_data_s5")

def test_ends_with_s_number_invalid() -> None:
    """Test invalid patterns that should NOT match."""
    assert not _ends_with_s_number("experiment")
    assert not _ends_with_s_number("experiment_s")
    assert not _ends_with_s_number("experiment_s1234")  # Too many digits (max 3)
    assert not _ends_with_s_number("experiments1")  # No underscore
    assert not _ends_with_s_number("experiment_s1a")  # Has letter after
    assert not _ends_with_s_number("experiment_s1_extra")  # Has more after

# Test get_save_dirs with an existing series directory
def test_get_save_dirs_already_series_file(tmp_path: Path, dummy_reader: ImageReader) -> None:
    """
    Keep the parent when the input is already inside a series directory.
    """
    series_dir = tmp_path / "experiment_s1"
    series_dir.mkdir(parents=True)
    input_path = series_dir / "array.tif"
    input_path.write_bytes(b"")

    directory = get_save_dir(replace(dummy_reader, img_path=input_path, series_idx=0))
    assert directory == series_dir

def test_create_save_path_uses_directory_or_file_parent(tmp_path: Path) -> None:
    assert create_save_path(tmp_path, "result.tif") == tmp_path / "result.tif"
    source = tmp_path / "source.tif"
    assert create_save_path(source, "result.tif") == tmp_path / "result.tif"
