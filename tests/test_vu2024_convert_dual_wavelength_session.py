"""Tests of the sampling frequency that the dual-wavelength conversion passes for each excitation wavelength."""

import numpy as np
import pytest

from howe_lab_to_nwb.vu2024 import vu2024_convert_dual_wavelength_session
from howe_lab_to_nwb.vu2024.vu2024_convert_dual_wavelength_session import dual_wavelength_session_to_nwb

from conftest import make_ome_metadata

NUM_FRAMES = 12


@pytest.fixture
def single_wavelength_calls(monkeypatch):
    """Replace the reading of the source files and record the arguments passed for each excitation wavelength."""
    calls = []

    def fake_single_wavelength_session_to_nwb(**kwargs):
        calls.append(kwargs)

    def fake_read_mat(file_path) -> dict:
        # MATLAB indexing starts at 1. The first wavelength has the odd frame numbers and the second the even ones.
        first_frame_number = 1 if "ttlIn1" in str(file_path) else 2
        orig_frame_numbers = np.arange(first_frame_number, NUM_FRAMES + 1, 2)
        return dict(orig_frame_numbers=orig_frame_numbers, timestamp=100.0 + orig_frame_numbers / 36.0)

    def fake_extract_ome_metadata(file_path):
        return make_ome_metadata(delta_ts=list(np.arange(NUM_FRAMES) / 36.0), time_increment=1 / 36.0)

    module = vu2024_convert_dual_wavelength_session
    monkeypatch.setattr(module, "single_wavelength_session_to_nwb", fake_single_wavelength_session_to_nwb)
    monkeypatch.setattr(module, "read_mat", fake_read_mat)
    monkeypatch.setattr(module, "extract_ome_metadata", fake_extract_ome_metadata)

    return calls


def convert_session(raw_imaging_file_paths: list, **kwargs):
    dual_wavelength_session_to_nwb(
        raw_imaging_file_paths=raw_imaging_file_paths,
        fiber_photometry_file_paths=["first_ROIs.mat", "second_ROIs.mat"],
        fiber_locations_file_path="fiber_locations.xlsx",
        excitation_wavelengths_in_nm=[470, 415],
        indicators=["dLight1.3b", "dLight1.3b"],
        ttl_file_path="behavior.mat",
        ttl_stream_names=["ttlIn1", "ttlIn1"],
        nwbfile_path="session.nwb",
        behavior_file_paths=["behavior_ttlIn1_movie1.mat", "behavior_ttlIn2_movie1.mat"],
        **kwargs,
    )


def test_wavelengths_in_the_same_file_get_half_of_the_sampling_frequency_of_the_file(single_wavelength_calls):
    convert_session(raw_imaging_file_paths=["movie.cxd", "movie.cxd"])

    first_call, second_call = single_wavelength_calls
    assert first_call["sampling_frequency"] == pytest.approx(18.0)
    assert second_call["sampling_frequency"] == pytest.approx(18.0)
    assert first_call["frame_indices"] == [0, 2, 4, 6, 8, 10]
    assert second_call["frame_indices"] == [1, 3, 5, 7, 9, 11]


def test_wavelengths_in_the_same_file_use_the_given_sampling_frequency(single_wavelength_calls):
    convert_session(raw_imaging_file_paths=["movie.cxd", "movie.cxd"], sampling_frequency=11.0)

    first_call, second_call = single_wavelength_calls
    assert first_call["sampling_frequency"] == 11.0
    assert second_call["sampling_frequency"] == 11.0


def test_wavelengths_in_separate_files_use_the_sampling_frequency_of_each_file(single_wavelength_calls):
    convert_session(raw_imaging_file_paths=["first_movie.cxd", "second_movie.cxd"])

    first_call, second_call = single_wavelength_calls
    assert first_call["sampling_frequency"] is None
    assert second_call["sampling_frequency"] is None
    assert first_call["frame_indices"] is None
    assert second_call["frame_indices"] is None
