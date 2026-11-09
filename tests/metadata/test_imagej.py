import json

from scope_io.metadata.tiff_meta import assemble_tiff_metadata
from scope_io.metadata.models import ImageMetadata
from scope_io.metadata.codec import ARTIFACT_METADATA_TAG


def _make_payload() -> ImageMetadata:
    return ImageMetadata().with_artifact(
        version="x",
        axes="TZCYX",
        channel_labels=["GFP", "mCherry"],
        z_projection=None,
    ).with_custom_metadata({"existing": "data"})


def test_build_tiff_metadata_basic_fields():
    payload = _make_payload()
    out = assemble_tiff_metadata(payload, interval=11.0, resolution=(0.5, 0.25))

    assert out.imagej_meta["axes"] == "TZCYX"
    assert out.imagej_meta["finterval"] == 11.0
    assert out.imagej_meta["Labels"] == ["GFP", "mCherry"]
    assert out.imagej_meta["unit"] == "micron"
    assert out.resolution == (2.0, 4.0)


def test_build_tiff_metadata_encodes_payload_in_extratags():
    payload = ImageMetadata().with_artifact(
        version="x",
        axes="TZCYX",
        channel_labels=["GFP", "mCherry"],
        z_projection="mean",
        source_channel_indices=[0, 1],
        artifact_channel_indices=[0, 1],
    ).with_custom_metadata({"param": "value"})
    out = assemble_tiff_metadata(payload, interval=11.0, resolution=(0.5, 0.25))

    assert out.extratags is not None
    tag, dtype, count, raw, writeonce = out.extratags[0]
    assert tag == ARTIFACT_METADATA_TAG
    assert dtype == "B"
    assert count == len(raw)
    assert writeonce is True
    decoded = json.loads(raw.decode("utf-8"))
    assert decoded["artifact"]["z_projection"] == "mean"
    assert decoded["custom_metadata"]["param"] == "value"
