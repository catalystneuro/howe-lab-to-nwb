"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union, List

from pymatreader import read_mat

from howe_lab_to_nwb.vu2024 import single_wavelength_session_to_nwb


def dual_wavelength_session_to_nwb(
    raw_imaging_file_paths: List[Union[str, Path]],
    fiber_photometry_file_paths: List[Union[str, Path]],
    fiber_locations_file_path: Union[str, Path],
    excitation_wavelengths_in_nm: List[int],
    indicators: List[str],
    ttl_file_path: Union[str, Path],
    ttl_stream_names: List[str],
    nwbfile_path: Union[str, Path],
    behavior_file_paths: List[Union[str, Path]] = None,
    motion_corrected_imaging_file_paths: List[Union[str, Path]] = None,
    subject_metadata: dict = None,
    stub_test: bool = False,
):
    """
    Convert a session of data to NWB format.

    Parameters
    ----------
    raw_imaging_file_paths : List[Union[str, Path]]
        The list of paths to the .cxd files containing the raw imaging data.
    fiber_photometry_file_paths : List[Union[str, Path]]
        The list of paths to the .mat files containing the raw fiber photometry data.
    fiber_locations_file_path : Union[str, Path]
        The path to the .xlsx file containing the fiber locations.
    excitation_wavelengths_in_nm : List[int]
        The excitation wavelengths in nm for each imaging modality.
    indicators : List[str]
        The indicators used for each imaging modality.
    ttl_file_path : Union[str, Path]
        The path to the .mat file containing the TTL signals.
    ttl_stream_names : List[str]
        The names of the TTL streams.
    nwbfile_path : Union[str, Path]
        The path to the NWB file to write.
    behavior_file_paths : List[Union[str, Path]], optional
        The list of paths to the .mat files containing the processed behavior data.
    motion_corrected_imaging_file_paths : List[Union[str, Path]], optional
        The list of paths to the .tif files containing the motion corrected imaging data.
    subject_metadata : dict, optional
        The metadata for the subject.
    stub_test : bool, optional
        Whether to run the conversion as a stub test.
    """

    if motion_corrected_imaging_file_paths is None:
        motion_corrected_imaging_file_paths = [None] * len(raw_imaging_file_paths)

    first_frame_indices, second_frame_indices = None, None
    second_behavior_data = read_mat(behavior_file_paths[1])
    if len(set(raw_imaging_file_paths)) != len(raw_imaging_file_paths):
        # we need the frame_indices for the imaging data
        if len(behavior_file_paths) != len(raw_imaging_file_paths):
            raise ValueError("The number of behavior file paths must match the number of imaging files.")
        first_behavior_data = read_mat(behavior_file_paths[0])
        if "orig_frame_numbers" not in first_behavior_data:
            raise ValueError(f"Expected 'orig_frame_numbers' is not in '{behavior_file_paths[0]}'.")
        first_frame_indices = list(first_behavior_data["orig_frame_numbers"] - 1)  # MATLAB indexing starts at 1
        second_frame_indices = list(second_behavior_data["orig_frame_numbers"] - 1)  # MATLAB indexing starts at 1

    # Add data from the first excitation wavelength
    nwbfile = single_wavelength_session_to_nwb(
        raw_imaging_file_path=raw_imaging_file_paths[0],
        frame_indices=first_frame_indices,
        raw_fiber_photometry_file_path=fiber_photometry_file_paths[0],
        fiber_locations_file_path=fiber_locations_file_path,
        excitation_wavelength_in_nm=excitation_wavelengths_in_nm[0],
        indicator=indicators[0],
        ttl_file_path=ttl_file_path,
        ttl_stream_name=ttl_stream_names[0],
        motion_corrected_imaging_file_path=motion_corrected_imaging_file_paths[0],
        behavior_file_path=behavior_file_paths[0],
        subject_metadata=subject_metadata,
        excitation_mode="dual-wavelength",
        stub_test=stub_test,
    )

    second_frame_starting_time = second_behavior_data["timestamp"][0]
    # Add data from the second excitation wavelength and write to NWB file
    single_wavelength_session_to_nwb(
        raw_imaging_file_path=raw_imaging_file_paths[1],
        frame_indices=second_frame_indices,
        aligned_starting_time=second_frame_starting_time,
        raw_fiber_photometry_file_path=fiber_photometry_file_paths[1],
        fiber_locations_file_path=fiber_locations_file_path,
        excitation_wavelength_in_nm=excitation_wavelengths_in_nm[1],
        indicator=indicators[1],
        ttl_file_path=ttl_file_path,
        ttl_stream_name=ttl_stream_names[1],
        motion_corrected_imaging_file_path=motion_corrected_imaging_file_paths[1],
        nwbfile=nwbfile,
        nwbfile_path=nwbfile_path,
        excitation_mode="dual-wavelength",
        stub_test=stub_test,
    )


if __name__ == "__main__":
    # Parameters for conversion
    subject_folder_path = Path("/Volumes/t7-ssd/Howe/Grid9")
    session_folder_path = subject_folder_path / "210821"

    imaging_file_paths = [
        session_folder_path / "Data113.cxd",
        session_folder_path / "R600_AP9_117.cxd",
    ]

    fiber_photometry_file_paths = [
        session_folder_path / "Data113_crop_MC_ROIs_new.mat",
        session_folder_path / "R600_AP9_117_crop_MC_ROIs_new.mat",
    ]

    behavior_file_paths = [
        session_folder_path / "chatdat600_AP9_470_570_2021.08.21_10.48.07_aligned_ttlIn1_movie1.mat",
        session_folder_path / "chatdat600_AP9_470_570_2021.08.21_10.48.07_aligned_ttlIn2_movie1.mat",
    ]

    ttl_file_path = session_folder_path / "chatdat600_AP9_470_570_2021.08.21_10.48.07.mat"
    ttl_stream_names = ["ttlIn1", "ttlIn2"]

    fiber_locations_file_path = subject_folder_path / "Grid9_fiber_locations.xlsx"

    excitation_wavelengths_in_nm = [470, 570]
    indicators = ["Ach3.0", "jRGECO1a"]

    nwbfile_path = Path("/Volumes/t7-ssd/Howe/nwbfiles/Grid9_210821.nwb")
    stub_test = False

    dual_wavelength_session_to_nwb(
        raw_imaging_file_paths=imaging_file_paths,
        fiber_photometry_file_paths=fiber_photometry_file_paths,
        ttl_file_path=ttl_file_path,
        ttl_stream_names=ttl_stream_names,
        fiber_locations_file_path=fiber_locations_file_path,
        excitation_wavelengths_in_nm=excitation_wavelengths_in_nm,
        indicators=indicators,
        behavior_file_paths=behavior_file_paths,
        nwbfile_path=nwbfile_path,
        stub_test=stub_test,
    )
