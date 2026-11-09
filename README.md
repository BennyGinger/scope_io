# ScopeIO

`scope-io` is a standalone microscopy image I/O library. It presents ND2
and TIFF microscopy data through one `ScopeIO` façade, keeps axis and channel
identity explicit, and writes ImageJ-compatible TIFF files with portable artifact
metadata embedded in them. It does not depend on the FITS application.

```python
from scope_io import ScopeIO

image = ScopeIO.from_path("experiment.nd2")
result = image.get_channel("GFP", z_projection="max")

print(result.array.shape, result.axes)
```

The façade supports full-array and channel reads, series splitting, Z
projection, channel selection and reconstruction, channel-aware mask merging,
conversion preparation, and artifact saving. Channel labels are always tied to
their original source indices so that derived files remain traceable even when
only a subset of channels is exported.

Channel labels determine ImageJ LUT colours, for example GFP is green and DAPI
is blue. Unrecognised labels use grayscale without suppressing known colours
in other channels. Single-channel TIFFs also carry a TIFF colour map so ImageJ
restores their LUT when opening them, including files with embedded overlays.

`image.channel_colors` (also `image.reader.channel_colors`) exposes original
ND2/NIS display colors as RGB hex strings in source-channel order. Unknown or
black colors are `None`; missing or misaligned channel metadata returns `None`
for the whole palette. TIFF readers expose the terminal RGB color of each cached
ImageJ LUT through the same property. Missing or misaligned LUTs return `None`;
invalid or black channel colors remain unknown. No image pixels are read.

`image.get_plane(frame_index=0, channel=0, z_index=0)` reads a YX plane from
ND2 or TIFF without loading the full stack. Choose an ND2 position or TIFF
series with `ScopeIO.from_path(path, series_idx=1)` (zero-based). ND2 reads one
acquisition frame, which contains its channels, and returns an independent copy
of the selected channel before closing the file's memory map.

`resolve_channel_selection()` keeps supplied labels and fills blank labels from
ND2 color names, then `C1`, `C2`, etc. Repeated color defaults become `green_1`,
`green_2`, etc. A nonempty label list with the wrong count warns and uses generic
names for every channel. Source colors do not override label-based output LUTs:
an explicitly labeled `RFP` channel is saved with a red LUT even if its ND2
display color is green.

`save_array(..., crop_xy=(x0, y0, x1, y1))` applies an exclusive XY pixel crop
across every other dimension, using the array's axes metadata. It preserves
channel identity, artifact/custom metadata, pixel calibration, and timing, and adds
the source shape, bounds, and offset to `spatial_crops` metadata. ImageJ spatial
origins are adjusted for the crop. Serialized annotations can be supplied with
`imagej_overlays`; the caller must first clip/shift them into crop coordinates.
Use `compression="none"` for overlay hyperstacks opened with ImageJ's native
TIFF opener.

## Metadata and the 3.0 API

The Python package is `scope_io`; its distribution is `scope-io`. Version 3.0
renames the former `fits_io` API:

| Previous name | New name |
| --- | --- |
| `from fits_io import FitsIO` | `from scope_io import ScopeIO` |
| `FitsIOMeta` | `ImageMetadata` (also exported at package level) |
| `metadata.fits_io` | `metadata.artifact` |
| `metadata.with_fitsio(...)` | `metadata.with_artifact(...)` |
| `fitsio_metadata=` in the writer API | `image_metadata=` |
| `FITS_TAG` | `ARTIFACT_METADATA_TAG` (still TIFF tag 65000) |

```python
from scope_io import ImageMetadata

metadata = ImageMetadata().with_artifact(axes="YX", channel_labels=["GFP"])
assert metadata.dump()["artifact"]["axes"] == "YX"
```

Readers accept both the historical serialized `fits_io` key and the neutral
`artifact` key. New writes emit only `artifact`. Matching duplicate keys are
accepted; conflicting duplicate keys raise an error instead of discarding
provenance. Historical producer names, revisions and application-owned custom
metadata are retained. Reading a legacy file does not modify it.

There is no `fits_io` import shim or old Python API alias: consumers must update
their imports and API calls. Old application versions that only understand the
serialized `fits_io` key need updating before using newly written files. Existing
files do not need a bulk migration. The stale, nonfunctional `fits-io` CLI entry
point has been removed; ScopeIO is a Python library.

The default output filename is now `array.tif`. Callers can continue supplying
their own names. ScopeIO does not rename workflow output files or folders.

## Application boundary

An application such as FITS decides which artifact a workflow step requires and
where its result belongs. ScopeIO performs the actual reads and writes and carries provenance,
axis information, calibration, and custom metadata across those operations.
Processing modules can therefore receive arrays rather than file paths.

## Development checks

From this repository, run `uv run --group dev pytest` and
`uv run --group dev pyright`. Build distributions with `uv build`.
