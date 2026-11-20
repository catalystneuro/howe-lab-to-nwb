"""Tests of the temporal alignment of the Vu2024NWBConverter."""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from howe_lab_to_nwb.vu2024 import Vu2024NWBConverter
from howe_lab_to_nwb.vu2024.interfaces import CxdImagingInterface

# Frame times of a movie where two excitation wavelengths alternate at 36 frames per second with some jitter.
NUM_FRAMES = 12
FRAME_TIMES = np.arange(NUM_FRAMES) / 36.0 + np.linspace(0.0, 0.004, NUM_FRAMES) ** 2
TIME_INCREMENT = 1 / 36.0


class TimestampsInterface:
    """Stands in for the behavior and fiber photometry interfaces, which only hold timestamps in the alignment."""

    def __init__(self, timestamps=None):
        self._timestamps = timestamps

    def get_timestamps(self) -> np.ndarray:
        return self._timestamps

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.array(aligned_timestamps)


def make_converter(imaging_interface: CxdImagingInterface, behavior_timestamps: np.ndarray = None):
    converter = Vu2024NWBConverter.__new__(Vu2024NWBConverter)
    converter.data_interface_objects = dict(Imaging=imaging_interface, FiberPhotometry=TimestampsInterface())
    if behavior_timestamps is not None:
        converter.data_interface_objects.update(Behavior=TimestampsInterface(timestamps=behavior_timestamps))
    return converter


@pytest.mark.parametrize("frame_indices", [None, [0, 2, 4, 6, 8, 10], [1, 3, 5, 7, 9, 11]])
def test_imaging_and_fiber_photometry_use_the_frame_times_of_the_file(make_cxd_file, frame_indices):
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)
    sampling_frequency = None if frame_indices is None else 18.0
    imaging_interface = CxdImagingInterface(
        file_path=file_path, frame_indices=frame_indices, sampling_frequency=sampling_frequency
    )
    behavior_timestamps = 100.0 + np.arange(NUM_FRAMES) / 18.0
    converter = make_converter(imaging_interface=imaging_interface, behavior_timestamps=behavior_timestamps)

    converter.temporally_align_data_interfaces()

    frame_times = FRAME_TIMES if frame_indices is None else FRAME_TIMES[frame_indices]
    expected_timestamps = frame_times - frame_times[0] + behavior_timestamps[0]
    assert expected_timestamps[0] == behavior_timestamps[0]
    assert_allclose(imaging_interface.get_timestamps(), expected_timestamps, rtol=0, atol=1e-12)
    fiber_photometry_timestamps = converter.data_interface_objects["FiberPhotometry"].get_timestamps()
    assert_allclose(fiber_photometry_timestamps, expected_timestamps, rtol=0, atol=1e-12)


def test_aligned_starting_time_argument_sets_the_time_of_the_first_frame(make_cxd_file):
    """The second wavelength of a dual-wavelength session has no behavior interface and gets its starting time."""
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)
    frame_indices = [1, 3, 5, 7, 9, 11]
    imaging_interface = CxdImagingInterface(file_path=file_path, frame_indices=frame_indices, sampling_frequency=18.0)
    converter = make_converter(imaging_interface=imaging_interface)

    converter.temporally_align_data_interfaces(aligned_starting_time=50.0)

    expected_timestamps = FRAME_TIMES[frame_indices] - FRAME_TIMES[frame_indices[0]] + 50.0
    assert_allclose(imaging_interface.get_timestamps(), expected_timestamps, rtol=0, atol=1e-12)
    fiber_photometry_timestamps = converter.data_interface_objects["FiberPhotometry"].get_timestamps()
    assert_allclose(fiber_photometry_timestamps, expected_timestamps, rtol=0, atol=1e-12)


def test_without_frame_times_the_sampling_frequency_of_the_wavelength_is_used(make_cxd_file):
    file_path = make_cxd_file(delta_ts=[None] * NUM_FRAMES, time_increment=TIME_INCREMENT)
    frame_indices = [0, 2, 4, 6, 8, 10]
    with pytest.warns(UserWarning, match="frame times in the file are not used"):
        imaging_interface = CxdImagingInterface(
            file_path=file_path, frame_indices=frame_indices, sampling_frequency=18.0
        )
    converter = make_converter(imaging_interface=imaging_interface)

    converter.temporally_align_data_interfaces(aligned_starting_time=50.0)

    expected_timestamps = 50.0 + np.arange(len(frame_indices)) / 18.0
    assert_allclose(imaging_interface.get_timestamps(), expected_timestamps, rtol=0, atol=1e-12)
    fiber_photometry_timestamps = converter.data_interface_objects["FiberPhotometry"].get_timestamps()
    assert_allclose(fiber_photometry_timestamps, expected_timestamps, rtol=0, atol=1e-12)


def test_one_photon_series_is_written_with_the_frame_times(make_cxd_file):
    from datetime import datetime, timezone

    from pynwb import NWBFile

    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)
    frame_indices = [1, 3, 5, 7, 9, 11]
    imaging_interface = CxdImagingInterface(file_path=file_path, frame_indices=frame_indices, sampling_frequency=18.0)
    converter = make_converter(imaging_interface=imaging_interface)
    converter.temporally_align_data_interfaces(aligned_starting_time=50.0)

    nwbfile = NWBFile(
        session_description="test",
        identifier="test",
        session_start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    imaging_interface.add_to_nwbfile(
        nwbfile=nwbfile, metadata=imaging_interface.get_metadata(), photon_series_type="OnePhotonSeries"
    )

    one_photon_series = nwbfile.acquisition["OnePhotonSeries"]
    expected_timestamps = FRAME_TIMES[frame_indices] - FRAME_TIMES[frame_indices[0]] + 50.0
    assert one_photon_series.rate is None
    assert_allclose(one_photon_series.timestamps, expected_timestamps, rtol=0, atol=1e-12)
