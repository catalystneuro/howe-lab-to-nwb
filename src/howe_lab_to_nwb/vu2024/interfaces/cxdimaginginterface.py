from typing import Literal

from neuroconv.datainterfaces.ophys.baseimagingextractorinterface import BaseImagingExtractorInterface
from neuroconv.utils import FilePathType, DeepDict

from howe_lab_to_nwb.vu2024.extractors.cxdimagingextractor import CxdImagingExtractor


class CxdImagingInterface(BaseImagingExtractorInterface):
    """
    Interface for reading Hamamatsu Photonics imaging data from .cxd files.
    """

    display_name = "CXD Imaging"
    associated_suffixes = (".cxd",)
    info = "Interface for Hamamatsu Photonics CXD files."

    Extractor = CxdImagingExtractor

    def __init__(
        self,
        file_path: FilePathType,
        channel_name: str = None,
        plane_name: str = None,
        sampling_frequency: float = None,
        verbose: bool = True,
    ):
        """
        DataInterface for reading Hamamatsu Photonics imaging data from .cxd files.

        Parameters
        ----------
        file_path : FilePathType
            Path to the CXD file.
        channel_name : str, optional
            The name of the channel for this extractor.
        plane_name : str, optional
            The name of the plane for this extractor.
        sampling_frequency : float, optional
            The sampling frequency of the data. If None, the sampling frequency will be read from the file.
            If missing from the file, the sampling frequency must be provided.
        verbose : bool, default: True
            controls verbosity.
        """
        super().__init__(
            file_path=file_path,
            channel_name=channel_name,
            plane_name=plane_name,
            sampling_frequency=sampling_frequency,
            verbose=verbose,
        )

    def get_metadata(
        self, photon_series_type: Literal["OnePhotonSeries", "TwoPhotonSeries"] = "TwoPhotonSeries"
    ) -> DeepDict:
        metadata = super().get_metadata(photon_series_type=photon_series_type)

        device_name = "HamamatsuMicroscope"
        metadata["Ophys"]["Device"][0].update(
            name=device_name,
            manufacturer="Hamamatsu Photonics",
        )
        optical_channel_name = "OpticalChannel"  # TODO: add better channel name
        imaging_plane_metadata = metadata["Ophys"]["ImagingPlane"][0]
        optical_channel_metadata = imaging_plane_metadata["optical_channel"][0]
        optical_channel_metadata.update(name=optical_channel_name)
        imaging_plane_metadata.update(
            device=device_name,
            optical_channel=[optical_channel_metadata],
        )

        return metadata
