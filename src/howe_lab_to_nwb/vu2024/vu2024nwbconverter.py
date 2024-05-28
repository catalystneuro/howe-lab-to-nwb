"""Primary NWBConverter class for this dataset."""

from neuroconv import NWBConverter

from howe_lab_to_nwb.vu2024.interfaces import Vu2024FiberPhotometryInterface


class Vu2024NWBConverter(NWBConverter):
    """Primary conversion class for the Vu 2024 fiber photometry dataset."""

    data_interface_classes = dict(
        FiberPhotometry=Vu2024FiberPhotometryInterface,
    )
