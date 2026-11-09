"""Read historical files without modifying them and write neutral artifact metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import tifffile
from numpy.typing import NDArray

from scope_io import ImageMetadata, ScopeIO
from scope_io.metadata.codec import ARTIFACT_METADATA_TAG
from scope_io.writers.metadata_update import rewrite_metadata


def _historical_payload() -> dict[str, Any]:
    """
    Represent metadata written by the original library, including producer history.
    """
    return {'fits_io': {'artifact_type': 'image_raw', 'axes': 'TCYX',
                        'channel_labels': ['GFP', 'RFP'], 'source_channel_indices': [1, 4],
                        'artifact_channel_indices': [1, 4], 'created_by': 'fits-io',
                        'version': '2.2.0', 'created_at': '2026-11-01T09:00:00+00:00',
                        'derived_from': [{'artifact_path': '../original.nd2', 'external': True}]},
            'custom_metadata': {'experiment': 'historical run',
                                'steps': {'convert': {'created_by': 'fits-io', 'version': '2.2.0'}}}}


def _write_fixture(path: Path, payload: dict[str, Any]) -> NDArray[np.float32]:
    """
    Write a compressed historical TIFF with signed pixels, calibration and overlays.
    """
    pixels = np.linspace(-12.5, 100.25, 2 * 2 * 8 * 9, dtype=np.float32).reshape(2, 2, 8, 9)
    raw = json.dumps(payload).encode('utf-8')
    tifffile.imwrite(path, pixels, imagej=True, compression='zlib', resolution=(2.0, 4.0),
                     metadata={'axes': 'TCYX', 'finterval': 2.5, 'unit': 'micron',
                               'Overlays': [b'preserved serialized ROI']},
                     extratags=[(65000, 'B', len(raw), raw, True)],
                     )
    return pixels


def _stored_payload(path: Path) -> dict[str, Any]:
    """
    Read the actual on-disk private payload independently of ScopeIO's model.
    """
    with tifffile.TiffFile(path) as tif:
        return json.loads(tif.pages.first.tags[65000].value)


def _encoded_pixels(path: Path) -> list[bytes]:
    """
    Collect encoded pixel segments to detect recompression during metadata replacement.
    """
    result: list[bytes] = []
    with tifffile.TiffFile(path) as tif, path.open('rb') as stream:
        for page in tif.pages:
            for offset, count in zip(page.dataoffsets, page.databytecounts, strict=True):
                stream.seek(offset)
                result.append(stream.read(count))
    return result


def test_legacy_payload_normalises_to_neutral_key_without_changing_history() -> None:
    """
    Deserialization preserves historical identity and emits only the new schema key.
    """
    historical = _historical_payload()
    metadata = ImageMetadata.from_dict(historical)
    assert metadata.artifact.created_by == 'fits-io'
    assert metadata.artifact.version == '2.2.0'
    assert metadata.artifact.created_at == historical['fits_io']['created_at']
    assert metadata.artifact.derived_from == historical['fits_io']['derived_from']
    assert metadata.custom_metadata == historical['custom_metadata']
    assert metadata.dump() == {'artifact': metadata.artifact.to_dict(),
                               'custom_metadata': historical['custom_metadata']}
    assert 'fits_io' not in metadata.to_info_payload()
    assert ImageMetadata.from_dict(metadata.dump()) == metadata
    assert 'artifact' not in historical


@pytest.mark.parametrize('key', ['fits_io', 'artifact'])
def test_old_and_new_tiffs_round_trip_without_altering_originals(tmp_path: Path, key: str) -> None:
    """
    Both schemas retain signed pixels, channel identity, calibration and provenance.
    """
    payload = _historical_payload()
    if key == 'artifact':
        payload['artifact'] = payload.pop('fits_io')
    source = tmp_path / 'source.tif'
    pixels = _write_fixture(source, payload)
    before = source.read_bytes()
    image = ScopeIO.from_path(source)
    assert source.read_bytes() == before
    np.testing.assert_array_equal(image.get_array().array, pixels)
    assert image.axes == 'TCYX'
    assert image.reader.resolution == (0.5, 0.25)
    assert image.reader.interval == 2.5
    output = image.save_array(pixels, metadata=image.metadata, output_path=tmp_path / 'roundtrip.tif',
                              imagej_overlays=[b'preserved serialized ROI'])
    assert source.read_bytes() == before
    restored = ScopeIO.from_path(output)
    np.testing.assert_array_equal(restored.get_array().array, pixels)
    assert restored.get_array().array.dtype == np.float32
    assert restored.metadata == image.metadata
    assert restored.reader.resolution == image.reader.resolution
    assert restored.reader.interval == image.reader.interval
    assert restored.metadata.artifact.source_channel_indices == [1, 4]
    stored = _stored_payload(output)
    assert 'artifact' in stored and 'fits_io' not in stored
    with tifffile.TiffFile(output) as tif:
        assert tif.imagej_metadata is not None
        assert tif.imagej_metadata['Overlays'] == b'preserved serialized ROI'
        assert 'artifact' in tif.imagej_metadata['Info']


def test_metadata_only_rewrite_preserves_encoded_pixels_and_revision(tmp_path: Path) -> None:
    """
    Explicit metadata replacement changes the key without decoding or revising pixels.
    """
    source = tmp_path / 'historical.tif'
    pixels = _write_fixture(source, _historical_payload())
    metadata = ScopeIO.from_path(source).metadata
    encoded = _encoded_pixels(source)
    rewrite_metadata(source, metadata)
    assert _encoded_pixels(source) == encoded
    assert ScopeIO.from_path(source).metadata == metadata
    np.testing.assert_array_equal(tifffile.imread(source), pixels)
    assert 'artifact' in _stored_payload(source)
    assert 'fits_io' not in _stored_payload(source)
    with tifffile.TiffFile(source) as tif:
        assert tif.imagej_metadata is not None
        assert tif.imagej_metadata['Overlays'] == b'preserved serialized ROI'


def test_matching_dual_keys_are_accepted_and_written_once() -> None:
    """
    A transitional duplicate is harmless only when both representations agree.
    """
    payload = _historical_payload()
    payload['artifact'] = dict(payload['fits_io'])
    metadata = ImageMetadata.from_dict(payload)
    assert metadata.artifact.axes == 'TCYX'
    assert 'fits_io' not in metadata.dump()


def test_conflicting_dual_keys_fail_before_metadata_can_be_lost(tmp_path: Path) -> None:
    """
    Readers must not silently replace ambiguous lineage with an empty payload.
    """
    payload = _historical_payload()
    payload['artifact'] = {**payload['fits_io'], 'created_by': 'different-producer'}
    with pytest.raises(ValueError, match='Conflicting'):
        ImageMetadata.from_dict(payload)
    source = tmp_path / 'ambiguous.tif'
    _write_fixture(source, payload)
    before = source.read_bytes()
    with pytest.raises(ValueError, match='Conflicting'):
        ScopeIO.from_path(source)
    assert source.read_bytes() == before


@pytest.mark.parametrize('key', ['fits_io', 'artifact'])
def test_invalid_artifact_mapping_is_rejected(key: str) -> None:
    """
    Invalid metadata is reported rather than converted into an empty artifact.
    """
    with pytest.raises(TypeError, match='must be a mapping'):
        ImageMetadata.from_dict({key: 'not a mapping'})


def test_new_revision_retains_producer_and_custom_history() -> None:
    """
    A new data revision changes lineage while ordinary metadata updates do not.
    """
    historical = ImageMetadata.from_dict(_historical_payload())
    updated = historical.with_artifact(channel_labels=['Green', 'Red'])
    assert updated.artifact.created_at == historical.artifact.created_at
    revision = updated.new_revision([{'artifact_path': 'input.tif', 'created_at': 'previous'}])
    assert revision.artifact.created_at != historical.artifact.created_at
    assert revision.artifact.created_by == 'fits-io'
    assert revision.custom_metadata == historical.custom_metadata
    assert ARTIFACT_METADATA_TAG == 65000
