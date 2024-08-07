from typing import Literal

from neuroconv.datainterfaces import TiffImagingInterface
from neuroconv.utils import FilePathType, DeepDict


class Vu2024TiffImagingInterface(TiffImagingInterface):
    """Interface for adding the motion corrected imaging data from the Vu 2024 dataset."""

    display_name = "TIFF Imaging"
    associated_suffixes = (".tif", ".tiff")
    info = "Interface for multi-page TIFF files."

    ExtractorName = "TiffImagingExtractor"

    @classmethod
    def get_source_schema(cls) -> dict:
        source_schema = super().get_source_schema()
        source_schema["properties"]["file_path"]["description"] = "Path to Tiff file."
        return source_schema

    def __init__(
        self,
        file_path: FilePathType,
        sampling_frequency: float,
        verbose: bool = True,
        photon_series_type: Literal["OnePhotonSeries", "TwoPhotonSeries"] = "OnePhotonSeries",
    ):
        """
        Initialize reading of TIFF file.

        Parameters
        ----------
        file_path : FilePathType
        sampling_frequency : float
        verbose : bool, default: True
        photon_series_type : {'OnePhotonSeries', 'TwoPhotonSeries'}, default: "TwoPhotonSeries"
        """
        super().__init__(
            file_path=file_path,
            sampling_frequency=sampling_frequency,
            verbose=verbose,
            photon_series_type=photon_series_type,
        )

    def get_metadata(
        self, photon_series_type: Literal["OnePhotonSeries", "TwoPhotonSeries"] = "OnePhotonSeries"
    ) -> DeepDict:
        # Override the default metadata to correctly set the metadata for this experiment
        metadata = super().get_metadata(photon_series_type=photon_series_type)

        device_name = "HamamatsuMicroscope"
        metadata["Ophys"]["Device"][0].update(name=device_name)
        optical_channel_name = "OpticalChannel"
        imaging_plane_metadata = metadata["Ophys"]["ImagingPlane"][0]
        optical_channel_metadata = imaging_plane_metadata["optical_channel"][0]
        optical_channel_metadata.update(name=optical_channel_name)
        imaging_plane_metadata.update(
            device=device_name,
            optical_channel=[optical_channel_metadata],
        )

        one_photon_series_metadata = metadata["Ophys"]["OnePhotonSeries"][0]
        one_photon_series_metadata.update(
            name="OnePhotonSeriesMotionCorrected",
        )

        return metadata
