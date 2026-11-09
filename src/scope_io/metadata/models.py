from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Self, Sequence
from scope_io.readers._types import Zproj, validate_axes


@dataclass(slots=True, frozen=True)
class ArtifactMeta:
    """
    Describe an image artifact independently of its producing application.
    """
    artifact_type: str | None = None
    created_by: str | None = None
    version: str | None = None
    derived_from: str | list[dict[str, Any]] | None = None
    created_at: str | None = None
    axes: str | None = None
    channel_labels: list[str] | None = None
    source_channel_indices: list[int] = field(default_factory=list)
    artifact_channel_indices: list[int] = field(default_factory=list)
    z_projection: Zproj = None

    def __post_init__(self) -> None:
        """
        Validate and normalize the initialized fields.
        """
        if self.axes is not None:
            validate_axes(self.axes)

    @property
    def channel_count(self) -> int | None:
        """
        Return the number of channels in the artifact, if available.
        """
        if self.channel_labels is not None:
            return len(self.channel_labels)
        return None


    def to_dict(self) -> dict[str, Any]:
        """
        To dict.
        """
        return {
            "artifact_type": self.artifact_type,
            "created_by": self.created_by,
            "version": self.version,
            "derived_from": self.derived_from,
            "created_at": self.created_at,
            "axes": self.axes,
            "channel_labels": self.channel_labels,
            "source_channel_indices": self.source_channel_indices,
            "artifact_channel_indices": self.artifact_channel_indices,
            "z_projection": self.z_projection,
        }


@dataclass(slots=True, frozen=True)
class ImageMetadata:
    """
    Pair portable image artifact metadata with application-owned custom metadata.
    """
    artifact: ArtifactMeta = field(default_factory=ArtifactMeta)
    custom_metadata: Mapping[str, Any] = field(default_factory=dict)

    def new_revision(self, inputs: Sequence[Mapping[str, Any]] = ()) -> Self:
        """
        Create data revision provenance; ordinary metadata replacements preserve it.
        """
        return replace(self, artifact=replace(self.artifact,
                                             created_at=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                                             derived_from=[dict(item) for item in inputs],
                                             ))


    @classmethod
    def from_dict(cls, payload_dict: Mapping[str, Any]) -> Self:
        """
        Read neutral artifact metadata or the historical fits_io representation.
        """
        artifact_meta = ArtifactMeta(**_artifact_fields(payload_dict))

        custom_metadata = payload_dict.get("custom_metadata", {})
        if not isinstance(custom_metadata, Mapping):
            custom_metadata = {}
        return cls(artifact=artifact_meta, custom_metadata=custom_metadata)


    def dump(self) -> dict[str, Any]:
        """
        Convert the ImageMetadata to a dictionary suitable for serialization or storage.
        """
        payload: dict[str, Any] = {}
        if self.artifact is not None:
            payload['artifact'] = self.artifact.to_dict()
        if self.custom_metadata:
            payload["custom_metadata"] = dict(self.custom_metadata)
        return payload


    def to_info_payload(self) -> dict[str, Any]:
        """
        Convert the ImageMetadata to a dictionary suitable for InfoSummary.
        """
        return {"artifact": self.artifact.to_dict(), **dict(self.custom_metadata),}


    def with_artifact(self,
                    *,
                    artifact_type: str | None = None,
                    created_by: str | None = None,
                    version: str | None = None,
                    derived_from: str | list[dict[str, Any]] | None = None,
                    axes: str | None = None,
                    channel_labels: Sequence[str] | None = None,
                    source_channel_indices: Sequence[int] | None = None,
                    artifact_channel_indices: Sequence[int] | None = None,
                    z_projection: Zproj = None,
                    ) -> Self:
        """
        Update artifact metadata, retaining each field whose argument is None.
        """
        return replace(self,
            artifact=replace(self.artifact,
                            artifact_type=artifact_type if artifact_type is not None else self.artifact.artifact_type,
                            created_by=created_by if created_by is not None else self.artifact.created_by,
                            version=version if version is not None else self.artifact.version,
                            derived_from=derived_from if derived_from is not None else self.artifact.derived_from,
                            axes=axes if axes is not None else self.artifact.axes,
                            channel_labels=list(channel_labels) if channel_labels is not None else self.artifact.channel_labels,
                            source_channel_indices=list(source_channel_indices) if source_channel_indices is not None else self.artifact.source_channel_indices,
                            artifact_channel_indices=list(artifact_channel_indices) if artifact_channel_indices is not None else self.artifact.artifact_channel_indices,
                            z_projection=z_projection if z_projection is not None else self.artifact.z_projection,
                            )
    )

    def with_custom_metadata(self, custom_metadata: Mapping[str, Any] | None) -> Self:
        """
        Return a new ImageMetadata instance with updated custom metadata. If custom_metadata is None, it will be set to an empty dictionary.
        """
        if custom_metadata is None:
            return self

        merged = dict(self.custom_metadata)
        merged.update(custom_metadata)
        return replace(self, custom_metadata=merged)


def _artifact_fields(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    Accept either metadata key and reject conflicting duplicate representations.
    """
    if 'artifact' in payload and 'fits_io' in payload and payload['artifact'] != payload['fits_io']:
        raise ValueError('Conflicting artifact and legacy fits_io metadata fields.')
    fields = payload.get('artifact', payload.get('fits_io', {}))
    if not isinstance(fields, Mapping):
        raise TypeError('Artifact metadata must be a mapping.')
    return fields


