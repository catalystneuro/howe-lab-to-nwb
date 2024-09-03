from pathlib import Path
from typing import Union
from warnings import warn

import pandas as pd
from nwbinspector import inspect_nwbfile, format_messages, save_report
from tqdm import tqdm

from howe_lab_to_nwb.vu2024 import single_wavelength_session_to_nwb


def convert_all_single_wavelength_sessions(
    data_table_path: Union[str, Path],
    folder_path: Union[str, Path],
    nwbfile_folder_path: Union[str, Path],
    subject_ids: list = None,
    stub_test: bool = False,
    overwrite: bool = False,
):
    """
    Convert all single-wavelength excitation sessions from the Vu 2024 dataset to NWB format.

    Parameters
    ----------
    data_table_path : FilePathType
        The path to the XLSX file containing info for all the sessions.
    folder_path : FolderPathType
        The root folder path to search for the filenames in the data table.
    nwbfile_folder_path : FolderPathType
        The folder path to save the NWB files.
    subject_ids : list, optional
        The list of subjects to convert, default is None.
    stub_test : bool, optional
        Whether to run the conversion as a stub test.
        When set to True, write only a subset of the data for each session.
        When set to False, write the entire data for each session.
    overwrite : bool, optional
        Whether to overwrite existing NWB files, default is False.

    """
    from howe_lab_to_nwb.vu2024.utils._data_utils import (
        _get_subject_metadata_from_dataframe,
        _get_ttl_stream_name_from_file_path,
        _get_indicator_from_aav_string,
    )

    data_table_dict = pd.read_excel(data_table_path, sheet_name=["Sessions", "Mice"])
    data_table = data_table_dict["Sessions"]

    if subject_ids is not None:
        filtered_data_table = data_table[data_table["Mouse"].isin(subject_ids)]
        if filtered_data_table.empty:
            raise ValueError(f"No sessions found for the provided subject IDs: {subject_ids}.")
    else:
        filtered_data_table = data_table

    subjects_table = data_table_dict["Mice"].astype(str)

    folder_path = Path(folder_path)

    total_file_paths = len(filtered_data_table)
    progress_bar = tqdm(
        filtered_data_table.iterrows(),
        desc=f"Converting {total_file_paths} sessions to NWB ...",
        position=0,
        total=total_file_paths,
        dynamic_ncols=True,
    )

    for row_ind, row in progress_bar:
        subject_id = row["Mouse"]
        date = row["Date (YYYYMMDD)"]
        subject_metadata = _get_subject_metadata_from_dataframe(subject_id=subject_id, data_table=subjects_table)

        subject_id = str(subject_id).replace("-", "")
        subject_folder_path = folder_path / subject_id

        behavior_file_name = row["Raw behavior file"]
        ttl_file_paths = list(subject_folder_path.rglob(behavior_file_name))
        if not len(ttl_file_paths):
            warn(f"Raw behavior file not found: '{behavior_file_name}'. Skipping session.")
            progress_bar.update(1)
            continue
        else:
            ttl_file_path = ttl_file_paths[0]

        session_folder_path = ttl_file_paths[0].parent

        imaging_file_paths = list(session_folder_path.glob("*.cxd"))
        if not len(imaging_file_paths):
            warn(f"No .cxd files found in '{session_folder_path}'.")
            progress_bar.update(1)
            continue
        else:
            imaging_file_path = imaging_file_paths[0]

        processed_behavior_file_name = row["Processed behavior file"]
        processed_behavior_file_path = session_folder_path / processed_behavior_file_name
        if not processed_behavior_file_path.exists():
            warn(f"The processed behavior file '{processed_behavior_file_path}' does not exist. Skipping session.")
            progress_bar.update(1)
            continue

        fiber_photometry_file_pattern = "*_MC_ROIs*.mat"
        fiber_photometry_file_paths = list(session_folder_path.glob(fiber_photometry_file_pattern))
        if not len(fiber_photometry_file_paths):
            warn(f"No fiber photometry files found in '{session_folder_path}'. Skipping session.")
            progress_bar.update(1)
            continue
        else:
            fiber_photometry_file_path = fiber_photometry_file_paths[0]

        motion_corrected_file_path = None
        motion_corrected_file_paths = list(session_folder_path.glob("*.tif"))
        if len(motion_corrected_file_paths):
            motion_corrected_file_path = motion_corrected_file_paths[0]

        fiber_locations_file_path = session_folder_path.parent / f"{subject_id}_fiber_locations.xlsx"
        if not fiber_locations_file_path.exists():
            warn(f"Fiber locations file '{fiber_locations_file_path}' does not exist. Skipping session.")
            progress_bar.update(1)
            continue

        aav_string = row["Relevant injected sensor"]
        indicator = _get_indicator_from_aav_string(aav_string)
        excitation_wavelength_in_nm = row["LED excitation wavelength (nm)"]
        ttl_stream_name = _get_ttl_stream_name_from_file_path(processed_behavior_file_name)

        nwbfile_path = nwbfile_folder_path / f"{subject_id}-{session_folder_path.name}.nwb"
        if stub_test:
            nwbfile_path = nwbfile_folder_path / f"stub-{subject_id}-{session_folder_path.name}.nwb"
        if nwbfile_path.exists() and not overwrite:
            progress_bar.update(1)
            continue

        progress_bar.set_description(
            f"Converting subject '{subject_id}' session '{session_folder_path.name}' session to NWB ..."
        )
        single_wavelength_session_to_nwb(
            raw_imaging_file_path=imaging_file_path,
            motion_corrected_imaging_file_path=motion_corrected_file_path,
            raw_fiber_photometry_file_path=fiber_photometry_file_path,
            fiber_locations_file_path=fiber_locations_file_path,
            excitation_wavelength_in_nm=excitation_wavelength_in_nm,
            indicator=indicator,
            ttl_file_path=ttl_file_path,
            ttl_stream_name=ttl_stream_name,
            behavior_file_path=processed_behavior_file_path,
            nwbfile_path=nwbfile_path,
            subject_metadata=subject_metadata,
            stub_test=stub_test,
        )

        results = list(inspect_nwbfile(nwbfile_path=nwbfile_path))
        report_path = nwbfile_folder_path / f"{subject_id}-{session_folder_path.name}_nwbinspector_result.txt"
        if not report_path.exists():
            save_report(
                report_file_path=report_path,
                formatted_messages=format_messages(
                    results,
                    levels=["importance", "file_path"],
                ),
            )

        progress_bar.update(1)


if __name__ == "__main__":
    # Parameters for conversion

    # The path to the XLSX file containing info for all the sessions
    data_table_excel_file_path = Path("/Volumes/T9/Howe/data table.xlsx")

    # The list of subjects to convert
    # When subject_ids is set to None, all subjects will be converted assuming the single-wavelength excitation setup
    subject_ids = ["DL18", "DL20", "DL21", "DL23", "DL27", "DL29", "DL30", "DL15"]

    # The root folder path to search for the filenames in the data table
    folder_path = Path("/Volumes/T9/Howe")

    # The folder path to save the NWB files
    nwbfile_folder_path = Path("/Volumes/T9/Howe/001084")
    if not nwbfile_folder_path.exists():
        nwbfile_folder_path.mkdir(exist_ok=True)

    # Whether to overwrite existing NWB files, default is False
    overwrite = False

    # Whether to run the conversion as a stub test
    # When set to True, write only a subset of the data for each session
    # When set to False, write the entire data for each session
    stub_test = False

    convert_all_single_wavelength_sessions(
        data_table_path=data_table_excel_file_path,
        folder_path=folder_path,
        nwbfile_folder_path=nwbfile_folder_path,
        subject_ids=subject_ids,
        stub_test=stub_test,
        overwrite=overwrite,
    )
