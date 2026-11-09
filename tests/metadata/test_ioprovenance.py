from scope_io.metadata.codec import ARTIFACT_METADATA_TAG


def test_fits_tag_constant_is_stable():
    assert ARTIFACT_METADATA_TAG == 65000
