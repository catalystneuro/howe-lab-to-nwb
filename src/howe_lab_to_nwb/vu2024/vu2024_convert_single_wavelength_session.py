"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union, Optional, List

from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update
from pynwb import NWBFile

from howe_lab_to_nwb.vu2024 import Vu2024NWBConverter
from howe_lab_to_nwb.vu2024.extractors.bioformats_utils import extract_ome_metadata, parse_ome_metadata
from howe_lab_to_nwb.vu2024.utils import get_fiber_locations, update_ophys_metadata, update_fiber_photometry_metadata


def single_wavelength_session_to_nwb(
    raw_imaging_file_path: Union[str, Path],
    raw_fiber_photometry_file_path: Union[str, Path],
    fiber_locations_file_path: Union[str, Path],
    excitation_wavelength_in_nm: int,
    indicator: str,
    ttl_file_path: Union[str, Path],
    ttl_stream_name: str,
    motion_corrected_imaging_file_path: Optional[Union[str, Path]] = None,
    frame_indices: Optional[List[int]] = None,
    nwbfile_path: Optional[Union[str, Path]] = None,
    nwbfile: Optional[NWBFile] = None,
    sampling_frequency: float = None,
    stub_test: bool = False,
) -> NWBFile:
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
        The excitation wavelength in nm for the fiber photometry.
    indicator : str
        The indicator used for the fiber photometry.
    ttl_file_path : Union[str, Path]
        The path to the .mat file containing the TTL signals.
    ttl_stream_name : str
        The name of the TTL stream (e.g. 'ttlIn1').
    motion_corrected_imaging_file_path : Union[str, Path], optional
        The path to the .tif file containing the motion corrected imaging data.
    frame_indices : List[int], optional
        The list of frame indices to extract from the raw imaging data. If None, all frames will be extracted.
    nwbfile_path : Union[str, Path], optional
        The path to the NWB file to write. If None, the NWBFile object will be returned.
    nwbfile : NWBFile, optional
        An in-memory NWBFile object to add the data to. If None, a new NWBFile object will be created.
    sampling_frequency : float, optional
        The sampling frequency of the data. If None, the sampling frequency will be read from the .cxd file.
        If missing from the file, the sampling frequency must be provided.
    stub_test : bool, optional
        Whether to run the conversion as a stub test.
    """

    source_data = dict()
    conversion_options = dict()

    # Add raw imaging data
    if raw_imaging_file_path is not None:
        imaging_source_data = dict(file_path=str(raw_imaging_file_path), frame_indices=frame_indices)
        if sampling_frequency is not None:
            imaging_source_data.update(sampling_frequency=sampling_frequency)
        source_data.update(dict(Imaging=imaging_source_data))
        conversion_options.update(dict(Imaging=dict(stub_test=stub_test, photon_series_index=0)))

    # Add raw fiber photometry
    source_data.update(
        dict(
            FiberPhotometry=dict(
                file_path=str(raw_fiber_photometry_file_path),
                ttl_file_path=str(ttl_file_path),
                ttl_stream_name=ttl_stream_name,
            )
        )
    )
    conversion_options.update(dict(FiberPhotometry=dict(stub_test=stub_test)))

    # Add motion corrected imaging data
    if motion_corrected_imaging_file_path is not None:
        # We need the sampling frequency from the raw imaging data
        if sampling_frequency is None:
            ome_metadata = extract_ome_metadata(file_path=raw_imaging_file_path)
            parsed_metadata = parse_ome_metadata(metadata=ome_metadata)
            sampling_frequency = parsed_metadata["sampling_frequency"]
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

    ophys_metadata = load_dict_from_file(Path(__file__).parent / "metadata" / "vu2024_ophys_metadata.yaml")
    metadata = dict_deep_update(metadata, ophys_metadata)

    # Load the default metadata for fiber photometry
    fiber_photometry_metadata = load_dict_from_file(
        Path(__file__).parent / "metadata" / "vu2024_fiber_photometry_metadata.yaml"
    )
    # Update metadata with the excitation wavelength and indicator
    excitation_wavelength_to_photon_series_name = {
        470: "Green",
        405: "GreenIsosbestic",
        570: "Red",
    }

    name_suffix = excitation_wavelength_to_photon_series_name[excitation_wavelength_in_nm]
    fiber_photometry_response_series_name = f"FiberPhotometryResponseSeries{name_suffix}"
    updated_fiber_photometry_metadata = update_fiber_photometry_metadata(
        metadata=fiber_photometry_metadata,
        fiber_photometry_response_series_name=fiber_photometry_response_series_name,
        excitation_wavelength_in_nm=excitation_wavelength_in_nm,
        indicator=indicator,
    )
    metadata = dict_deep_update(metadata, updated_fiber_photometry_metadata)

    # Update metadata with the excitation wavelength and indicator
    metadata = update_ophys_metadata(
        metadata=metadata,
        two_photon_series_name=f"TwoPhotonSeries{name_suffix}",
        excitation_wavelength_in_nm=excitation_wavelength_in_nm,
        indicator=indicator,
    )

    if nwbfile is None:
        nwbfile = converter.create_nwbfile(metadata=metadata, conversion_options=conversion_options)
    else:
        converter.add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)

    if nwbfile_path is None:
        return nwbfile

    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        nwbfile=nwbfile,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=True,
    )


if __name__ == "__main__":

    # Parameters for conversion
    raw_imaging_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/Data00217.cxd")
    raw_fiber_photometry_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/Data00217_crop_MC_ROIs.mat")
    ttl_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/GridDL-18_2021.11.10_16.12.31.mat")
    ttl_stream_name = "ttlIn1"
    fiber_locations_file_path = Path("/Volumes/t7-ssd/Howe/DL18/DL18_fiber_locations.xlsx")
    motion_corrected_imaging_file_path = Path("/Volumes/t7-ssd/Howe/DL18/211110/Data00217_crop_MC.tif")

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
        ttl_stream_name=ttl_stream_name,
        fiber_locations_file_path=fiber_locations_file_path,
        excitation_wavelength_in_nm=excitation_wavelength_in_nm,
        indicator=indicator,
        motion_corrected_imaging_file_path=motion_corrected_imaging_file_path,
        nwbfile_path=nwbfile_path,
        sampling_frequency=sampling_frequency,
        stub_test=stub_test,
    )
