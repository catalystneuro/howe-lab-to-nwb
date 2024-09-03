from pathlib import Path
from typing import Union
from warnings import warn

import pandas as pd
from nwbinspector import inspect_nwbfile, format_messages, save_report
from tqdm import tqdm

from howe_lab_to_nwb.vu2024.vu2024_convert_dual_wavelength_session import dual_wavelength_session_to_nwb


def convert_all_dual_wavelength_sessions(
    data_table_path: Union[str, Path],
    folder_path: Union[str, Path],
    nwbfile_folder_path: Union[str, Path],
    subject_ids: list,
    stub_test: bool = False,
    overwrite: bool = False,
):
    """
    Convert all dual-wavelength excitation sessions from the Vu 2024 dataset to NWB format.

    Parameters
    ----------
    data_table_path : str or Path
        The path to the XLSX file containing info for all the sessions.
    folder_path : str or Path
        The root folder path to search for the filenames in the data table.
    nwbfile_folder_path : str or Path
        The folder path to save the NWB files.
    subject_ids : list
        The list of subjects to convert.
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

    filtered_data_table = data_table[data_table["Mouse"].astype(str).isin(subject_ids)]
    if filtered_data_table.empty:
        raise ValueError(f"No sessions found for the provided subject IDs: {subject_ids}.")

    subjects_table = data_table_dict["Mice"].astype(str)

    folder_path = Path(folder_path)

    columns_to_group = ["Mouse", "Date (YYYYMMDD)"]
    total_file_paths = filtered_data_table.groupby(columns_to_group).count().shape[0]
    progress_bar = tqdm(
        filtered_data_table.groupby(columns_to_group),
        desc=f"Converting {total_file_paths} sessions to NWB ...",
        position=0,
        total=total_file_paths,
        dynamic_ncols=True,
    )

    for (subject_id, date), table in progress_bar:
        subject_metadata = _get_subject_metadata_from_dataframe(subject_id=subject_id, data_table=subjects_table)

        subject_id = str(subject_id).replace("-", "")
        subject_folder_path = folder_path / subject_id

        behavior_file_name = table["Raw behavior file"].values[0]
        ttl_file_paths = list(subject_folder_path.rglob(behavior_file_name))
        if not len(ttl_file_paths):
            warn(f"Raw behavior file not found: '{behavior_file_name}'. Skipping session.")
            progress_bar.update(1)
            continue

        session_folder_path = ttl_file_paths[0].parent

        imaging_file_paths = [session_folder_path / file_path for file_path in table["Raw imaging file"]]
        processed_behavior_file_paths = [
            session_folder_path / file_path for file_path in table["Processed behavior file"]
        ]
        fiber_photometry_file_paths = [
            session_folder_path / file_path for file_path in table["Processed photometry data"]
        ]

        if len(set(imaging_file_paths)) == 1:
            imaging_file_name = imaging_file_paths[0].stem
            motion_corrected_file_paths = list(session_folder_path.glob(f"{imaging_file_name}*.tif"))

        else:
            motion_corrected_file_paths = []
            for imaging_file_path in imaging_file_paths:
                imaging_file_name = imaging_file_path.stem
                files = list(session_folder_path.glob(f"{imaging_file_name}*.tif"))
                motion_corrected_file_paths.extend(files)
        if not len(motion_corrected_file_paths):
            motion_corrected_file_paths = [None] * len(imaging_file_paths)

        if len(motion_corrected_file_paths) != len(imaging_file_paths):
            raise ValueError("The number of motion corrected imaging files must match the number of raw imaging files.")

        fiber_locations_file_path = session_folder_path.parent / f"{subject_id}_fiber_locations.xlsx"
        if not fiber_locations_file_path.exists():
            warn(f"Fiber locations file '{fiber_locations_file_path}' does not exist. Skipping session.")
            progress_bar.update(1)
            continue

        indicators = [_get_indicator_from_aav_string(aav_string) for aav_string in table["Relevant injected sensor"]]
        excitation_wavelengths_in_nm = [
            excitation_wavelength for excitation_wavelength in table["LED excitation wavelength (nm)"]
        ]
        ttl_stream_names = [
            _get_ttl_stream_name_from_file_path(processed_behavior_file_name)
            for processed_behavior_file_name in processed_behavior_file_paths
        ]

        nwbfile_path = nwbfile_folder_path / f"{subject_id}-{date}.nwb"
        if stub_test:
            nwbfile_path = nwbfile_folder_path / f"stub-{subject_id}-{date}.nwb"
        if nwbfile_path.exists() and not overwrite:
            progress_bar.update(1)
            continue

        progress_bar.set_description(f"Converting subject '{subject_id}' session '{date}' session to NWB ...")
        dual_wavelength_session_to_nwb(
            raw_imaging_file_paths=imaging_file_paths,
            motion_corrected_imaging_file_paths=motion_corrected_file_paths,
            fiber_photometry_file_paths=fiber_photometry_file_paths,
            fiber_locations_file_path=fiber_locations_file_path,
            excitation_wavelengths_in_nm=excitation_wavelengths_in_nm,
            indicators=indicators,
            ttl_file_path=ttl_file_paths[0],
            ttl_stream_names=ttl_stream_names,
            behavior_file_paths=processed_behavior_file_paths,
            nwbfile_path=nwbfile_path,
            subject_metadata=subject_metadata,
        )

        results = list(inspect_nwbfile(nwbfile_path=nwbfile_path))
        report_path = nwbfile_folder_path / f"{subject_id}-{date}_nwbinspector_result.txt"
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
    subject_ids = ["Grid9", "842", "DL31", "DL32"]

    # The root folder path to search for the filenames in the data table
    folder_path = Path("/Volumes/T9/Howe")

    # The folder path to save the NWB files
    nwbfile_folder_path = Path("/Volumes/T9/Howe/nwbfiles")
    if not nwbfile_folder_path.exists():
        nwbfile_folder_path.mkdir(exist_ok=True)

    # Whether to overwrite existing NWB files, default is False
    overwrite = True

    # Whether to run the conversion as a stub test
    # When set to True, write only a subset of the data for each session
    # When set to False, write the entire data for each session
    stub_test = False

    convert_all_dual_wavelength_sessions(
        data_table_path=data_table_excel_file_path,
        folder_path=folder_path,
        nwbfile_folder_path=nwbfile_folder_path,
        subject_ids=subject_ids,
        stub_test=stub_test,
        overwrite=overwrite,
    )
