"""Primary NWBConverter class for this dataset."""

from neuroconv import NWBConverter

from howe_lab_to_nwb.vu2024.interfaces import Vu2024FiberPhotometryInterface, CxdImagingInterface


class Vu2024NWBConverter(NWBConverter):
    """Primary conversion class for the Vu 2024 fiber photometry dataset."""

    data_interface_classes = dict(
        Imaging=CxdImagingInterface,
        FiberPhotometry=Vu2024FiberPhotometryInterface,
    )

    def get_metadata_schema(self) -> dict:

        metadata_schema = super().get_metadata_schema()
        # To allow FiberPhotometry in Ophys metadata
        metadata_schema["properties"]["Ophys"].update(
            additionalProperties=True,
        )

        return metadata_schema
