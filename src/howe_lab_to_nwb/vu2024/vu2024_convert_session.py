"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union

from dateutil import tz
from neuroconv.utils import load_dict_from_file, dict_deep_update

from howe_lab_to_nwb.vu2024 import Vu2024NWBConverter
from howe_lab_to_nwb.vu2024.utils import get_fiber_locations


def session_to_nwb(
    raw_imaging_file_path: Union[str, Path],
    raw_fiber_photometry_file_path: Union[str, Path],
    fiber_locations_file_path: Union[str, Path],
    ttl_file_path: Union[str, Path],
    nwbfile_path: Union[str, Path],
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
    """

    raw_fiber_photometry_file_path = Path(raw_fiber_photometry_file_path)

    source_data = dict()
    conversion_options = dict()

    # Add raw imaging data
    source_data.update(dict(Imaging=dict(file_path=str(raw_imaging_file_path))))
    conversion_options.update(dict(Imaging=dict(stub_test=stub_test)))

    # Add raw fiber photometry
    source_data.update(
        dict(
            FiberPhotometry=dict(
                file_path=str(raw_fiber_photometry_file_path),
                ttl_file_path=str(ttl_file_path),
            )
        )
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

    fiber_photometry_metadata = load_dict_from_file(
        Path(__file__).parent / "metadata" / "vu2024_fiber_photometry_metadata.yaml"
    )

    metadata = dict_deep_update(metadata, fiber_photometry_metadata)

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
    nwbfile_path = Path("/Volumes/t7-ssd/Howe/nwbfiles/GridDL-18_211110.nwb")
    stub_test = True

    session_to_nwb(
        raw_imaging_file_path=raw_imaging_file_path,
        raw_fiber_photometry_file_path=raw_fiber_photometry_file_path,
        ttl_file_path=ttl_file_path,
        fiber_locations_file_path=fiber_locations_file_path,
        nwbfile_path=nwbfile_path,
        stub_test=stub_test,
    )
