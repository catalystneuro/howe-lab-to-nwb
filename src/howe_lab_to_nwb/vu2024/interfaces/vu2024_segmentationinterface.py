from neuroconv.datainterfaces.ophys.basesegmentationextractorinterface import BaseSegmentationExtractorInterface
from neuroconv.utils import FilePathType

from howe_lab_to_nwb.vu2024.extractors.vu2024_segmentationextractor import Vu2024SegmentationExtractor


class Vu2024SegmentationInterface(BaseSegmentationExtractorInterface):
    """The interface for reading the ROI masks and locations from custom .mat files from the Howe Lab."""

    display_name = "Vu2024 Segmentation"
    associated_suffixes = (".mat",)
    info = "Interface for Vu2024 segmentation data."

    Extractor = Vu2024SegmentationExtractor

    def __init__(
        self, file_path: FilePathType, sampling_frequency: float, accepted_list: list = None, verbose: bool = True
    ):
        """
        DataInterface for reading ROI masks and locations from custom .mat files from the Howe Lab.

        Parameters
        ----------
        file_path : FilePathType
            Path to the .mat file that contains the ROI masks and locations.
        sampling_frequency : float
            The sampling frequency of the data.
        accepted_list : list, optional
            A list of the accepted ROIs.
        verbose : bool, default: True
            controls verbosity.
        """
        super().__init__(file_path=file_path, sampling_frequency=sampling_frequency, accepted_list=accepted_list)
        self.verbose = verbose

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        device_name = "HamamatsuMicroscope"
        metadata["Ophys"]["Device"][0].update(name=device_name)
        return metadata
