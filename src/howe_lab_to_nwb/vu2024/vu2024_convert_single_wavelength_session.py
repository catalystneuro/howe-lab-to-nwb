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
    nwbfile_path: Union[str, Path],
    sampling_frequency: float = None,
    stub_test: bool = False,
):
    """
    Convert a session of data to NWB format.

    Parameters
    ----------
    raw_fiber_photometry_file_path : Union[str, Path]
        The path to the .mat file containing the raw fiber photometry data.
    fiber_locations_file_path : Union[str, Path]
        The path to the .xlsx file containing the fiber locations.
    ttl_file_path : Union[str, Path]
        The path to the .mat file containing the TTL signals.
    sampling_frequency : float, optional
        The sampling frequency of the data. If None, the sampling frequency will be read from the .cxd file.
        If missing from the file, the sampling frequency must be provided.
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

    # Add ROI segmentation
    accepted_list = [fiber_ind for fiber_ind, fiber in enumerate(fiber_locations_metadata) if fiber["location"] != ""]
    roi_source_data = dict(
        file_path=str(raw_fiber_photometry_file_path),
        sampling_frequency=sampling_frequency,
        accepted_list=accepted_list,
    )
    source_data.update(dict(Segmentation=roi_source_data))
    conversion_options.update(dict(Segmentation=dict(stub_test=stub_test)))

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

    # The sampling frequency of the raw imaging data must be provided when it cannot be extracted from the .cxd file
    sampling_frequency = None

    excitation_wavelength_in_nm = 470
    indicator = "dLight1.3b"

    nwbfile_path = Path("/Volumes/t7-ssd/Howe/nwbfiles/ROIs_GridDL-18_211110.nwb")
    stub_test = True

    single_wavelength_session_to_nwb(
        raw_imaging_file_path=raw_imaging_file_path,
        raw_fiber_photometry_file_path=raw_fiber_photometry_file_path,
        ttl_file_path=ttl_file_path,
        fiber_locations_file_path=fiber_locations_file_path,
        excitation_wavelength_in_nm=excitation_wavelength_in_nm,
        indicator=indicator,
        motion_corrected_imaging_file_path=motion_corrected_imaging_file_path,
        nwbfile_path=nwbfile_path,
        sampling_frequency=sampling_frequency,
        stub_test=stub_test,
    )
