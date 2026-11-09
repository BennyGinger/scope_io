"""Library identity and historical producer versions survive package renaming."""

from importlib.metadata import PackageNotFoundError

import pytest
from scope_io import ImageMetadata
from scope_io.metadata import payload


def test_default_producer_version_looks_up_scope_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    A fresh payload must use the new distribution name for installed version lookup.
    """
    requested: list[str] = []

    def version(distribution: str) -> str:
        """
        Record the distribution whose version the writer requests.
        """
        requested.append(distribution)
        return '3.0.0'

    monkeypatch.setattr(payload, 'version', version)
    metadata = payload.assemble_payload(ImageMetadata(), axes='YX')
    assert requested == ['scope-io']
    assert metadata.artifact.version == '3.0.0'


def test_uninstalled_historical_producer_keeps_recorded_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    A legacy producer need not remain installed to retain its recorded version.
    """
    def missing(distribution: str) -> str:
        """
        Model a standalone installation where the old library is absent.
        """
        raise PackageNotFoundError(distribution)

    monkeypatch.setattr(payload, 'version', missing)
    original = ImageMetadata().with_artifact(created_by='fits-io', version='2.2.0')
    metadata = payload.assemble_payload(original, axes='YX')
    assert metadata.artifact.created_by == 'fits-io'
    assert metadata.artifact.version == '2.2.0'
    changed = payload.assemble_payload(original, created_by='another-producer')
    assert changed.artifact.created_by == 'another-producer'
    assert changed.artifact.version == 'unknown'
