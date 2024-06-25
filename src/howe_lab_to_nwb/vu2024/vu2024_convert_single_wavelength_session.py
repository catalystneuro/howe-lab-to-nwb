"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union

from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update

from howe_lab_to_nwb.vu2024 import Vu2024NWBConverter
from howe_lab_to_nwb.vu2024.extractors.bioformats_utils import extract_ome_metadata, parse_ome_metadata
from howe_lab_to_nwb.vu2024.utils import get_fiber_locations
from howe_lab_to_nwb.vu2024.utils.add_fiber_photometry import update_fiber_photometry_metadata


def single_wavelength_session_to_nwb(
    raw_imaging_file_path: Union[str, Path],
    raw_fiber_photometry_file_path: Union[str, Path],
    fiber_locations_file_path: Union[str, Path],
    excitation_wavelength_in_nm: int,
    indicator: str,
    ttl_file_path: Union[str, Path],
    motion_corrected_imaging_file_path: Union[str, Path],
    behavior_file_path: Union[str, Path],
    nwbfile_path: Union[str, Path],
    sampling_frequency: float = None,
    stub_test: bool = False,
):
    """
    Convert a session of data to NWB format.

    Parameters
    ----------
    raw_imaging_file_path : Union[str, Path]
        The path to the .cxd file containing the raw imaging data.
    raw_fiber_photometry_file_path : Union[str, Path]
        The path to the .mat file containing the raw fiber photometry data.
    fiber_locations_file_path : Union[str, Path]
        The path to the .xlsx file containing the fiber locations.
    excitation_wavelength_in_nm : int
        The excitation wavelength in nm.
    indicator : str
        The name of the indicator used for the fiber photometry recording.
    ttl_file_path : Union[str, Path]
        The path to the .mat file containing the TTL signals.
    motion_corrected_imaging_file_path : Union[str, Path]
        The path to the .tif file containing the motion corrected imaging data.
    behavior_file_path : Union[str, Path]
        The path to the .mat file containing the processed behavior data.
    nwbfile_path : Union[str, Path]
        The path to the NWB file to be created.
    sampling_frequency : float, optional
        The sampling frequency of the data. If None, the sampling frequency will be read from the .cxd file.
        If missing from the file, the sampling frequency must be provided.
    stub_test : bool, optional
        Whether to run a stub test, by default False.
    """

    raw_fiber_photometry_file_path = Path(raw_fiber_photometry_file_path)

    source_data = dict()
    conversion_options = dict()

    # Add raw imaging data
    imaging_source_data = dict(file_path=str(raw_imaging_file_path))
    if sampling_frequency is not None:
        imaging_source_data.update(sampling_frequency=sampling_frequency)
    source_data.update(dict(Imaging=imaging_source_data))

    # Add raw fiber photometry
    source_data.update(
        dict(
            FiberPhotometry=dict(
                file_path=str(raw_fiber_photometry_file_path),
                ttl_file_path=str(ttl_file_path),
            )
        )
    )
    conversion_options.update(dict(FiberPhotometry=dict(stub_test=stub_test)))
    conversion_options.update(dict(Imaging=dict(stub_test=stub_test, photon_series_index=0)))

    # We need the sampling frequency from the raw imaging data
    if sampling_frequency is None:
        ome_metadata = extract_ome_metadata(file_path=raw_imaging_file_path)
        parsed_metadata = parse_ome_metadata(metadata=ome_metadata)
        sampling_frequency = parsed_metadata["sampling_frequency"]

    # Add motion corrected imaging data
    source_data.update(
        dict(
            ProcessedImaging=dict(
                file_path=str(motion_corrected_imaging_file_path), sampling_frequency=sampling_frequency
            )
        )
    )
    conversion_options.update(
        dict(ProcessedImaging=dict(stub_test=stub_test, photon_series_index=1, parent_container="processing/ophys"))
    )

    # Add fiber locations
    fiber_locations_metadata = get_fiber_locations(fiber_locations_file_path)
    conversion_options.update(
        dict(FiberPhotometry=dict(stub_test=stub_test, fiber_locations_metadata=fiber_locations_metadata))
    )

    # Add behavior
    source_data.update(dict(Behavior=dict(file_path=str(behavior_file_path))))
    conversion_options.update(dict(Behavior=dict(stub_test=stub_test)))

    # Add behavior camera recording (optional)
    subject_id = raw_fiber_photometry_file_path.parent.parent.name
    behavior_avi_file_paths = list(raw_fiber_photometry_file_path.parent.glob(f"{subject_id}*.avi"))
    for avi_file_ind, behavior_avi_file_path in enumerate(behavior_avi_file_paths):
        video_key = f"Video{avi_file_ind + 1}"
        source_data.update(
            {
                video_key: dict(
                    file_paths=[str(behavior_avi_file_path)],
                    metadata_key_name=video_key,
                )
            }
        )
        conversion_options.update({video_key: dict(stub_test=stub_test)})

    converter = Vu2024NWBConverter(source_data=source_data)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    session_start_time = metadata["NWBFile"]["session_start_time"]
    tzinfo = tz.gettz("US/Eastern")
    metadata["NWBFile"].update(session_start_time=session_start_time.replace(tzinfo=tzinfo))

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "metadata" / "vu2024_general_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    fiber_photometry_metadata = load_dict_from_file(
        Path(__file__).parent / "metadata" / "vu2024_fiber_photometry_metadata.yaml"
    )
    fiber_photometry_metadata = update_fiber_photometry_metadata(
        metadata=fiber_photometry_metadata,
        excitation_wavelength_in_nm=excitation_wavelength_in_nm,
        indicator=indicator,
    )

    metadata = dict_deep_update(metadata, fiber_photometry_metadata)

    ophys_metadata = load_dict_from_file(Path(__file__).parent / "metadata" / "vu2024_ophys_metadata.yaml")
    metadata = dict_deep_update(metadata, ophys_metadata)

    # Run conversion
    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":

    # Parameters for conversion
    raw_imaging_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/Data00217.cxd")
    raw_fiber_photometry_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/Data00217_crop_MC_ROIs.mat")
    ttl_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/GridDL-18_2021.11.10_16.12.31.mat")
    fiber_locations_file_path = Path("/Volumes/t7-ssd/Howe/DL18/DL18_fiber_locations.xlsx")
    motion_corrected_imaging_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/Data00217_crop_MC.tif")
    behavior_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/GridDL-18_2021.11.10_16.12.31_ttlIn1_movie1.mat")

    # The sampling frequency of the raw imaging data must be provided when it cannot be extracted from the .cxd file
    sampling_frequency = None

    excitation_wavelength_in_nm = 470
    indicator = "dLight1.3b"

    nwbfile_path = Path("/Volumes/t7-ssd/Howe/nwbfiles/GridDL-18_211110.nwb")
    stub_test = True

    single_wavelength_session_to_nwb(
        raw_imaging_file_path=raw_imaging_file_path,
        raw_fiber_photometry_file_path=raw_fiber_photometry_file_path,
        ttl_file_path=ttl_file_path,
        fiber_locations_file_path=fiber_locations_file_path,
        excitation_wavelength_in_nm=excitation_wavelength_in_nm,
        indicator=indicator,
        motion_corrected_imaging_file_path=motion_corrected_imaging_file_path,
        behavior_file_path=behavior_file_path,
        nwbfile_path=nwbfile_path,
        sampling_frequency=sampling_frequency,
        stub_test=stub_test,
    )
