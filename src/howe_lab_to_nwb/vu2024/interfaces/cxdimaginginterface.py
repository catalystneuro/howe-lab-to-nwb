from pathlib import Path
from typing import Literal, Union

from neuroconv.datainterfaces.ophys.baseimagingextractorinterface import BaseImagingExtractorInterface

from howe_lab_to_nwb.vu2024.extractors.cxdimagingextractor import CxdImagingExtractor


class CxdImagingInterface(BaseImagingExtractorInterface):
    """
    Interface for reading Hamamatsu Photonics imaging data from .cxd files.
    """

    display_name = "CXD Imaging"
    associated_suffixes = (".cxd",)
    info = "Interface for Hamamatsu Photonics CXD files."

    Extractor = CxdImagingExtractor

    @classmethod
    def get_source_schema(cls) -> dict:
        source_schema = super().get_source_schema()
        source_schema["properties"]["frame_indices"].update(type=["array", "null"])
        return source_schema

    def __init__(
        self,
        file_path: Union[str, Path],
        channel_name: str = None,
        plane_name: str = None,
        sampling_frequency: float = None,
        frame_indices: list = None,
        verbose: bool = True,
    ):
        """
        DataInterface for reading Hamamatsu Photonics imaging data from .cxd files.

        Parameters
        ----------
        file_path : str or Path
            Path to the CXD file.
        channel_name : str, optional
            The name of the channel for this extractor.
        plane_name : str, optional
            The name of the plane for this extractor.
        sampling_frequency : float, optional
            The sampling frequency of the data. If None, the sampling frequency will be read from the file.
            If missing from the file, the sampling frequency must be provided.
        frame_indices : list, optional
            List of frame indices to extract. If None, all frames will be extracted.
        verbose : bool, default: True
            controls verbosity.
        """
        super().__init__(
            file_path=file_path,
            channel_name=channel_name,
            plane_name=plane_name,
            sampling_frequency=sampling_frequency,
            frame_indices=frame_indices,
            verbose=verbose,
        )

    def get_metadata(
        self, photon_series_type: Literal["OnePhotonSeries", "TwoPhotonSeries"] = "OnePhotonSeries"
    ) -> dict:
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

        return metadata
