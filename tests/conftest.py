"""Fixtures that stand in for a .cxd file, so that the tests run without Java, Bio-Formats and the lab's data."""

import dask.array as da
import numpy as np
import pytest
from ome_types import OME
from ome_types.model import Channel, Image, Pixels, Plane


def make_ome_metadata(delta_ts: list, time_increment: float = None) -> OME:
    """Make the OME metadata of a movie with one channel, one plane and one frame for each value in 'delta_ts'."""
    num_frames = len(delta_ts)
    pixels = Pixels(
        dimension_order="XYZCT",
        type="uint16",
        size_x=4,
        size_y=3,
        size_z=1,
        size_c=1,
        size_t=num_frames,
        time_increment=time_increment,
        channels=[Channel(id="Channel:0:0")],
        planes=[Plane(the_z=0, the_c=0, the_t=frame, delta_t=delta_t) for frame, delta_t in enumerate(delta_ts)],
    )
    return OME(images=[Image(pixels=pixels)])


@pytest.fixture
def make_cxd_file(tmp_path, monkeypatch):
    """
    Return a function that makes a stand-in .cxd file and returns its path.

    The reading of the OME metadata and of the video is replaced. The value of every pixel of a frame is the index of
    the frame in the file.
    """
    ome_metadata_per_file = dict()

    def fake_extract_ome_metadata(file_path) -> OME:
        return ome_metadata_per_file[str(file_path)]

    class FakeBioFile:
        def __init__(self, file_path):
            self.ome_metadata = ome_metadata_per_file[str(file_path)]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def to_dask(self) -> da.Array:
            pixels = self.ome_metadata.images[0].pixels
            frames = np.arange(pixels.size_t, dtype="uint16")
            video = np.broadcast_to(
                frames[:, None, None, None, None],
                (pixels.size_t, pixels.size_c, pixels.size_z, pixels.size_y, pixels.size_x),
            )
            return da.from_array(video)

    monkeypatch.setenv("JAVA_HOME", str(tmp_path))
    monkeypatch.setattr(
        "howe_lab_to_nwb.vu2024.extractors.bioformats_utils.extract_ome_metadata", fake_extract_ome_metadata
    )
    monkeypatch.setattr("aicsimageio.readers.bioformats_reader.BioFile", FakeBioFile)

    def _make_cxd_file(delta_ts: list, time_increment: float = None, name: str = "movie.cxd") -> str:
        file_path = tmp_path / name
        file_path.touch()
        ome_metadata_per_file[str(file_path)] = make_ome_metadata(delta_ts=delta_ts, time_increment=time_increment)
        return str(file_path)

    return _make_cxd_file
