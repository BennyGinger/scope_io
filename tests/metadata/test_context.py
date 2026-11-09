from scope_io.metadata.models import ImageMetadata
from scope_io.metadata.payload import assemble_payload


def test_build_payload_sets_requested_artifact_fields():
    base = ImageMetadata()
    out = assemble_payload(
        base,
        axes="TCYX",
        channel_labels=["GFP", "RFP"],
        source_channel_indices=[0, 2],
        artifact_channel_indices=[0, 2],
        z_projection="max",
    )

    assert out.artifact.axes == "TCYX"
    assert out.artifact.channel_labels == ["GFP", "RFP"]
    assert out.artifact.channel_count == 2
    assert out.artifact.source_channel_indices == [0, 2]
    assert out.artifact.artifact_channel_indices == [0, 2]
    assert out.artifact.z_projection == "max"


def test_build_payload_merges_custom_metadata_when_provided():
    base = ImageMetadata(custom_metadata={"legacy": 1})
    out = assemble_payload(base, custom_metadata={"run_id": 7})

    assert out.custom_metadata == {"legacy": 1, "run_id": 7}


def test_build_payload_preserves_base_custom_metadata_when_custom_missing():
    base = ImageMetadata(custom_metadata={"legacy": "keep"})
    out = assemble_payload(base)

    assert out.custom_metadata == {"legacy": "keep"}
