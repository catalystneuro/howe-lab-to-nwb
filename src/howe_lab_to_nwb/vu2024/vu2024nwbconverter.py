"""Primary NWBConverter class for this dataset."""

from neuroconv import NWBConverter
from neuroconv.datainterfaces import TiffImagingInterface
from neuroconv.utils import DeepDict

from howe_lab_to_nwb.vu2024.interfaces import Vu2024FiberPhotometryInterface, CxdImagingInterface


class Vu2024NWBConverter(NWBConverter):
    """Primary conversion class for the Vu 2024 fiber photometry dataset."""

    data_interface_classes = dict(
        Imaging=CxdImagingInterface,
        ProcessedImaging=TiffImagingInterface,
        FiberPhotometry=Vu2024FiberPhotometryInterface,
    )

    def get_metadata_schema(self) -> dict:

        metadata_schema = super().get_metadata_schema()
        # To allow FiberPhotometry in Ophys metadata
        metadata_schema["properties"]["Ophys"].update(
            additionalProperties=True,
        )

        return metadata_schema

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        # Overwrite the Ophys imaging metadata with the metadata from the CxdImagingInterface
        imaging_interface_metadata = self.data_interface_objects["Imaging"].get_metadata()
        metadata["Ophys"]["Device"] = imaging_interface_metadata["Ophys"]["Device"]
        metadata["Ophys"]["ImagingPlane"] = imaging_interface_metadata["Ophys"]["ImagingPlane"]
        metadata["Ophys"]["TwoPhotonSeries"] = imaging_interface_metadata["Ophys"]["TwoPhotonSeries"]

        return metadata

    def temporally_align_data_interfaces(self):
        imaging = self.data_interface_objects["Imaging"]
        fiber_photometry = self.data_interface_objects["FiberPhotometry"]
        # Use the timestamps from the fiber photometry interface for the imaging data
        # The timestamps from the fiber photometry data is from the TTL signals
        fiber_photometry_timestamps = fiber_photometry.get_timestamps()
        imaging.set_aligned_timestamps(aligned_timestamps=fiber_photometry_timestamps)
