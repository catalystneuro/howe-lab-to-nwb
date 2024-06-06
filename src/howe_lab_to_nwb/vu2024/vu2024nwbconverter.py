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
