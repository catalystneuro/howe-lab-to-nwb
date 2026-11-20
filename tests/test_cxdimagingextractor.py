"""Tests of the sampling frequency and the frame times of the CxdImagingExtractor."""

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from howe_lab_to_nwb.vu2024.extractors.cxdimagingextractor import CxdImagingExtractor

# Frame times of a movie where two excitation wavelengths alternate at 36 frames per second with some jitter.
NUM_FRAMES = 12
FRAME_TIMES = np.arange(NUM_FRAMES) / 36.0 + np.linspace(0.0, 0.004, NUM_FRAMES) ** 2
TIME_INCREMENT = 1 / 36.0


def test_frame_times_from_file_are_kept(make_cxd_file):
    """The frame times read from the file must not be reset by the initialization of the base class."""
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)

    extractor = CxdImagingExtractor(file_path=file_path)

    assert extractor.has_time_vector()
    assert_array_equal(extractor.frame_to_time(frames=np.arange(NUM_FRAMES)), FRAME_TIMES)


def test_sampling_frequency_from_file(make_cxd_file):
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)

    extractor = CxdImagingExtractor(file_path=file_path)

    assert extractor.get_sampling_frequency() == pytest.approx(36.0)
    assert extractor.get_num_frames() == NUM_FRAMES


@pytest.mark.parametrize(
    "frame_indices",
    [
        [0, 2, 4, 6, 8, 10],  # the first of two alternating wavelengths
        [1, 3, 5, 7, 9, 11],  # the second of two alternating wavelengths
        [2, 3, 4, 5, 6, 7, 8],  # a range of frames of a file with one wavelength
    ],
)
def test_frame_indices_select_frames_and_frame_times(make_cxd_file, frame_indices):
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)

    extractor = CxdImagingExtractor(file_path=file_path, frame_indices=frame_indices, sampling_frequency=18.0)

    assert extractor.get_num_frames() == len(frame_indices)
    assert_array_equal(extractor.frame_to_time(frames=np.arange(len(frame_indices))), FRAME_TIMES[frame_indices])
    assert_array_equal(extractor.get_video()[:, 0, 0], frame_indices)


@pytest.mark.parametrize("sampling_frequency", [18.0, 36.0])
def test_sampling_frequency_with_frame_indices_is_the_given_value(make_cxd_file, sampling_frequency):
    """The extractor must not change the sampling frequency on its own when 'frame_indices' is used."""
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)

    extractor = CxdImagingExtractor(
        file_path=file_path, frame_indices=[0, 2, 4, 6, 8, 10], sampling_frequency=sampling_frequency
    )

    assert extractor.get_sampling_frequency() == sampling_frequency


def test_frame_indices_without_sampling_frequency_raises(make_cxd_file):
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)

    with pytest.raises(ValueError, match="'sampling_frequency' argument when 'frame_indices' is used"):
        CxdImagingExtractor(file_path=file_path, frame_indices=[0, 2, 4, 6, 8, 10])


def test_missing_sampling_frequency_raises(make_cxd_file):
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=None)

    with pytest.raises(ValueError, match="Sampling frequency is not found in the metadata"):
        CxdImagingExtractor(file_path=file_path)


@pytest.mark.parametrize("sampling_frequency", [0.0, -1.0])
def test_sampling_frequency_must_be_positive(make_cxd_file, sampling_frequency):
    file_path = make_cxd_file(delta_ts=list(FRAME_TIMES), time_increment=TIME_INCREMENT)

    with pytest.raises(ValueError, match="The sampling frequency must be positive"):
        CxdImagingExtractor(file_path=file_path, sampling_frequency=sampling_frequency)


@pytest.mark.parametrize(
    "delta_ts, reason",
    [
        ([None] * NUM_FRAMES, "some frames have no time"),
        ([0.0] * NUM_FRAMES, "do not increase"),
        (list(FRAME_TIMES[:-1]) + [0.0], "do not increase"),
        (list(FRAME_TIMES[:-1]) + [None], "some frames have no time"),
    ],
)
@pytest.mark.parametrize("frame_indices", [None, [1, 3, 5, 7, 9, 11]])
def test_unusable_frame_times_warn_and_fall_back_to_the_sampling_frequency(
    make_cxd_file, delta_ts, reason, frame_indices
):
    file_path = make_cxd_file(delta_ts=delta_ts, time_increment=TIME_INCREMENT)

    with pytest.warns(UserWarning, match=f"frame times in the file are not used because .*{reason}"):
        extractor = CxdImagingExtractor(file_path=file_path, frame_indices=frame_indices, sampling_frequency=18.0)

    assert not extractor.has_time_vector()
    num_frames = extractor.get_num_frames()
    assert_array_equal(extractor.frame_to_time(frames=np.arange(num_frames)), np.arange(num_frames) / 18.0)
