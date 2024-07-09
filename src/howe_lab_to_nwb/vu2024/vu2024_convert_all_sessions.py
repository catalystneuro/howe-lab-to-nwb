import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from neuroconv.utils import FilePathType, FolderPathType
from nwbinspector import inspect_all
from nwbinspector.inspector_tools import save_report, format_messages
from tqdm import tqdm

from howe_lab_to_nwb.vu2024.vu2024_convert_dual_wavelength_session import (
    dual_wavelength_session_to_nwb,
    single_wavelength_session_to_nwb,
)


def convert_all_sessions(
    data_table_path: FilePathType,
    folder_path: FolderPathType,
    nwbfile_folder_path: FolderPathType,
    stub_test: bool = False,
    overwrite: bool = False,
):
    """
    Convert all sessions from the Vu 2024 dataset to NWB format.

    Parameters
    ----------
    data_table_path : FilePathType
        The path to the XLSX file containing info for all the sessions.
    folder_path : FolderPathType
        The root folder path to search for the filenames in the data table.
    nwbfile_folder_path : FolderPathType
        The folder path to save the NWB files.
    stub_test : bool, optional
        Whether to run the conversion as a stub test.
        When set to True, write only a subset of the data for each session.
        When set to False, write the entire data for each session.
    overwrite : bool, optional
        Whether to overwrite existing NWB files, default is False.

    """

    data_table_dict = pd.read_excel(data_table_path, sheet_name=["Sessions", "Mice"])
    data_table = data_table_dict["Sessions"]
    subjects_table = data_table_dict["Mice"].astype(str)

    folder_path = Path(folder_path)

    columns_to_group = ["Mouse", "Date (YYYYMMDD)"]
    total_file_paths = data_table.groupby(columns_to_group).count().shape[0]
    progress_bar = tqdm(
        data_table.groupby(columns_to_group),
        desc=f"Converting {total_file_paths} sessions to NWB ...",
        position=0,
        total=total_file_paths,
        dynamic_ncols=True,
    )

    for (subject_id, date), table in progress_bar:
        experiment_type = "single-wavelength" if len(table) == 1 else "dual-wavelength"

        mouse_metadata = subjects_table.loc[subjects_table["MouseID"] == str(subject_id)]
        mouse_metadata = mouse_metadata.to_dict(orient="records")[0]
        date_of_birth = datetime.strptime(mouse_metadata["Date of Birth"], "%Y-%m-%d")
        subject_metadata = dict(
            Subject=dict(
                subject_id=mouse_metadata["MouseID"],
                date_of_birth=date_of_birth,
                sex=mouse_metadata["Sex"],
                genotype=mouse_metadata["Genotype"],
                strain=mouse_metadata["Strain"],
                species="Mus musculus",
            ),
        )

        subject_id = str(subject_id).replace("-", "")
        subject_folder_path = folder_path / subject_id

        behavior_file_name = table["Raw behavior file"].values[0]
        ttl_file_paths = list(subject_folder_path.rglob(behavior_file_name))
        if not len(ttl_file_paths):
            raise FileNotFoundError(f"Behavior file not found: {behavior_file_name}")

        session_folder_path = ttl_file_paths[0].parent

        imaging_file_paths = list(session_folder_path.glob("*.cxd"))
        if not len(imaging_file_paths):
            raise FileNotFoundError(f"No .cxd files found in {session_folder_path}")

        ttl_stream_names = []
        behavior_file_paths = []
        for processed_behavior_file_name in table["Processed behavior file"]:
            pattern = re.compile(r"(ttlIn1|ttlIn2)")
            # Search for the pattern in the provided string
            match = pattern.search(processed_behavior_file_name)
            ttl_stream_name = match.group(0) if match else None
            if ttl_stream_name is None:
                raise ValueError(f"TTL stream name (ttlIn1, ttlIn2) not found in {processed_behavior_file_name}")
            ttl_stream_names.append(ttl_stream_name)

            behavior_file_paths.append(session_folder_path / processed_behavior_file_name)

        fiber_photometry_file_paths = list(session_folder_path.glob("*_ROIs*.mat"))

        ttl_file_path = imaging_file_paths[0].parent / table["Raw behavior file"].values[0]

        ttl_stream_names = []
        behavior_file_paths = []
        for processed_behavior_file_name in table["Processed behavior file"]:
            pattern = re.compile(r"(ttlIn1|ttlIn2)")
            match = pattern.search(processed_behavior_file_name)
            ttl_stream_name = match.group(0) if match else None
            if ttl_stream_name is None:
                raise ValueError(f"TTL stream name (ttlIn1, ttlIn2) not found in {processed_behavior_file_name}")
            ttl_stream_names.append(ttl_stream_name)

            behavior_file_paths.append(imaging_file_paths[0].parent / processed_behavior_file_name)

        if len(imaging_file_paths) < len(table):
            # In this case we have dual wavelength imaging data in the same file
            # We will use the frame indices in dual_wavelength_session_to_nwb to determine which excitation wavelength the frame belongs to
            imaging_file_paths = imaging_file_paths * len(table)
        motion_corrected_file_paths = list(session_folder_path.glob("*.tif"))
        if not len(motion_corrected_file_paths):
            motion_corrected_file_paths = [None] * len(imaging_file_paths)
        if len(motion_corrected_file_paths) != len(imaging_file_paths):
            raise ValueError("The number of motion corrected imaging files must match the number of raw imaging files.")

        fiber_locations_file_path = imaging_file_paths[0].parent.parent / f"{subject_id}_fiber_locations.xlsx"
        if not fiber_locations_file_path.exists():
            raise FileNotFoundError(f"Fiber locations file not found: {fiber_locations_file_path}")

        excitation_wavelengths_in_nm = table["LED excitation wavelength (nm)"].values
        indicators = []
        for aav_string in table["Relevant injected sensor"].values:
            pattern = re.compile(r"(dLight1\.3b|GCaMP7f|Ach3\.0|jRGECO1a)")
            # Search for the pattern in the provided string
            match = pattern.search(aav_string)
            # If a match is found, return the matched string; otherwise, return None
            indicator = match.group(0) if match else None
            if indicator is None:
                raise ValueError(f"Indicator (dLight1.3b, GCaMP7f, Ach3.0, jRGECO1a) not found in {aav_string}")
            indicators.append(indicator)

        nwbfile_path = nwbfile_folder_path / f"{subject_id}-{date}.nwb"
        if nwbfile_path.exists() and not overwrite:
            progress_bar.update(1)
            continue

        progress_bar.set_description(f"Converting subject '{subject_id}' session '{date}' session to NWB ...")
        if experiment_type == "dual-wavelength":
            dual_wavelength_session_to_nwb(
                raw_imaging_file_paths=imaging_file_paths,
                motion_corrected_imaging_file_paths=motion_corrected_file_paths,
                fiber_photometry_file_paths=fiber_photometry_file_paths,
                fiber_locations_file_path=fiber_locations_file_path,
                excitation_wavelengths_in_nm=excitation_wavelengths_in_nm,
                indicators=indicators,
                ttl_file_path=ttl_file_path,
                ttl_stream_names=ttl_stream_names,
                behavior_file_paths=behavior_file_paths,
                nwbfile_path=nwbfile_path,
                subject_metadata=subject_metadata,
                stub_test=stub_test,
            )
        elif experiment_type == "single-wavelength":
            single_wavelength_session_to_nwb(
                raw_imaging_file_path=imaging_file_paths[0],
                motion_corrected_imaging_file_path=motion_corrected_file_paths[0],
                raw_fiber_photometry_file_path=fiber_photometry_file_paths[0],
                fiber_locations_file_path=fiber_locations_file_path,
                excitation_wavelength_in_nm=excitation_wavelengths_in_nm[0],
                indicator=indicators[0],
                ttl_file_path=ttl_file_path,
                ttl_stream_name=ttl_stream_names[0],
                behavior_file_path=behavior_file_paths[0],
                nwbfile_path=nwbfile_path,
                subject_metadata=subject_metadata,
                stub_test=stub_test,
            )
        progress_bar.update(1)

    report_path = nwbfile_folder_path / "inspector_result.txt"
    if not report_path.exists():
        results = list(inspect_all(path=nwbfile_folder_path))
        save_report(
            report_file_path=report_path,
            formatted_messages=format_messages(
                results,
                levels=["importance", "file_path"],
            ),
        )


if __name__ == "__main__":
    # Parameters for conversion

    # The path to the XLSX file containing info for all the sessions
    data_table_excel_file_path = Path("/Volumes/t7-ssd/Howe/data table.xlsx")

    # The root folder path to search for the filenames in the data table
    folder_path = Path("/Volumes/t7-ssd/Howe")

    # The folder path to save the NWB files
    nwbfile_folder_path = Path("/Volumes/t7-ssd/Howe/nwbfiles")

    # Whether to overwrite existing NWB files, default is False
    overwrite = True

    # Whether to run the conversion as a stub test
    # When set to True, write only a subset of the data for each session
    # When set to False, write the entire data for each session
    stub_test = True

    convert_all_sessions(
        data_table_path=data_table_excel_file_path,
        folder_path=folder_path,
        nwbfile_folder_path=nwbfile_folder_path,
        stub_test=stub_test,
        overwrite=overwrite,
    )
