from scope_io.metadata.models import ImageMetadata
from scope_io.metadata.payload import assemble_payload


def test_build_payload_preserves_existing_source_channel_identity_when_not_overridden():
    base = ImageMetadata().with_artifact(
        source_channel_indices=[0, 2],
        artifact_channel_indices=[0, 2],
    )

    out = assemble_payload(base)

    assert out.artifact.source_channel_indices == [0, 2]
    assert out.artifact.artifact_channel_indices == [0, 2]


def test_build_payload_sets_source_channel_identity_when_provided():
    base = ImageMetadata()

    out = assemble_payload(
        base,
        source_channel_indices=[0, 1, 2],
        artifact_channel_indices=[1, 2],)

    assert out.artifact.source_channel_indices == [0, 1, 2]
    assert out.artifact.artifact_channel_indices == [1, 2]


def test_build_payload_keeps_unrelated_existing_artifact_fields():
    base = ImageMetadata().with_artifact(
        axes="TZCYX", channel_labels=["GFP", "RFP"])

    out = assemble_payload(base, artifact_type="image")

    assert out.artifact.axes == "TZCYX"
    assert out.artifact.channel_labels == ["GFP", "RFP"]
    assert out.artifact.channel_count == 2
    assert out.artifact.artifact_type == "image"
