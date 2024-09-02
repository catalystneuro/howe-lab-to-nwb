import os
from pathlib import Path
from typing import List, Tuple

import aicsimageio
import numpy as np
from neuroconv.utils import FilePathType
from roiextractors import ImagingExtractor
from roiextractors.extraction_tools import DtypeType


class CxdImagingExtractor(ImagingExtractor):
    """Imaging extractor for reading Hamamatsu Photonics imaging data from .cxd files."""

    extractor_name = "CxdImaging"

    @classmethod
    def get_available_channels(cls, file_path) -> List[str]:
        """Get the available channel names from a CXD file produced by Hamamatsu Photonics.

        Parameters
        ----------
        file_path : PathType
            Path to the Bio-Formats file.

        Returns
        -------
        channel_names: list
            List of channel names.
        """
        from .bioformats_utils import extract_ome_metadata, parse_ome_metadata

        ome_metadata = extract_ome_metadata(file_path=file_path)
        parsed_metadata = parse_ome_metadata(metadata=ome_metadata)
        channel_names = parsed_metadata["channel_names"]
        return channel_names

    @classmethod
    def get_available_planes(cls, file_path):
        """Get the available plane names from a CXD file produced by Hamamatsu Photonics.

        Parameters
        ----------
        file_path : PathType
            Path to the Bio-Formats file.

        Returns
        -------
        plane_names: list
            List of plane names.
        """
        from .bioformats_utils import extract_ome_metadata, parse_ome_metadata

        ome_metadata = extract_ome_metadata(file_path=file_path)
        parsed_metadata = parse_ome_metadata(metadata=ome_metadata)
        num_planes = parsed_metadata["num_planes"]
        plane_names = [f"{i}" for i in range(num_planes)]
        return plane_names

    def __init__(
        self,
        file_path: FilePathType,
        channel_name: str = None,
        plane_name: str = None,
        sampling_frequency: float = None,
        frame_indices: List[int] = None,
    ):
        r"""
        Create a CxdImagingExtractor instance from a CXD file produced by Hamamatsu Photonics.

        This extractor requires `bioformats_jar` to be installed in the environment,
        and requires the java executable to be available on the path (or via the JAVA_HOME environment variable),
        along with the mvn executable.

        If you are using conda, you can install with `conda install -c conda-forge bioformats_jar`.
        Note: you may need to reactivate your conda environment after installing.
        If you are still getting a JVMNotFoundException, try:
        # mac and linux:
        `export JAVA_HOME=$CONDA_PREFIX`

        # windows:
        `set JAVA_HOME=%CONDA_PREFIX%\\Library`

        Parameters
        ----------
        file_path : PathType
            Path to the CXD file.
        channel_name : str
            The name of the channel for this extractor. (default=None)
        plane_name : str
            The name of the plane for this extractor. (default=None)
        sampling_frequency : float
            The sampling frequency of the imaging data. (default=None)
            Has to be provided manually if not found in the metadata.
        frame_indices : list, optional
            List of frame indices to extract. If None, all frames will be extracted. (default=None)
        """
        from .bioformats_utils import extract_ome_metadata, parse_ome_metadata

        if ".cxd" not in Path(file_path).suffixes:
            raise ValueError("The file suffix must be .cxd!")

        if "JAVA_HOME" not in os.environ:
            conda_home = os.environ.get("CONDA_PREFIX")
            os.environ["JAVA_HOME"] = conda_home

        self.ome_metadata = extract_ome_metadata(file_path=file_path)
        parsed_metadata = parse_ome_metadata(metadata=self.ome_metadata)

        self._num_frames = parsed_metadata["num_frames"]
        self._num_channels = parsed_metadata["num_channels"]
        self._num_planes = parsed_metadata["num_planes"]
        self._num_rows = parsed_metadata["num_rows"]
        self._num_columns = parsed_metadata["num_columns"]
        self._dtype = parsed_metadata["dtype"]
        self._sampling_frequency = parsed_metadata["sampling_frequency"]
        # When the cxd file contains both channels (dual-wavelength excitation), the sampling frequency should be halved.
        if frame_indices is not None:
            self._sampling_frequency = self._sampling_frequency / 2
        self._channel_names = parsed_metadata["channel_names"]
        self._plane_names = [f"{i}" for i in range(self._num_planes)]

        if channel_name is None:
            if self._num_channels > 1:
                raise ValueError(
                    "More than one channel is detected! Please specify which channel you wish to load "
                    "with the `channel_name` argument. To see which channels are available, use "
                    "`CxdImagingExtractor.get_available_channels(file_path=...)`"
                )
            channel_name = self._channel_names[0]

        if channel_name not in self._channel_names:
            raise ValueError(
                f"The selected channel '{channel_name}' is not a valid channel name."
                f" The available channel names are: {self._channel_names}."
            )
        self.channel_index = self._channel_names.index(channel_name)

        if plane_name is None:
            if self._num_planes > 1:
                raise ValueError(
                    "More than one plane is detected! Please specify which plane you wish to load "
                    "with the `plane_name` argument. To see which planes are available, use "
                    "`CxdImagingExtractor.get_available_planes(file_path=...)`"
                )
            plane_name = self._plane_names[0]

        if plane_name not in self._plane_names:
            raise ValueError(
                f"The selected plane '{plane_name}' is not a valid plane name."
                f" The available plane names are: {self._plane_names}."
            )
        self.plane_index = self._plane_names.index(plane_name)

        if self._sampling_frequency is None:
            if sampling_frequency is None:
                raise ValueError(
                    "Sampling frequency is not found in the metadata. Please provide it manually with the 'sampling_frequency' argument."
                )
            self._sampling_frequency = sampling_frequency

        pixels_metadata = self.ome_metadata.images[0].pixels
        timestamps = [plane.delta_t for plane in pixels_metadata.planes]
        if np.any(timestamps):
            self._times = np.array(timestamps)

        with aicsimageio.readers.bioformats_reader.BioFile(file_path) as reader:
            self._video = reader.to_dask()

        if frame_indices is not None:
            assert len(frame_indices) > 0, "frame_indices must be a non-empty list."
            assert (
                len(frame_indices) <= self._num_frames
            ), "frame_indices must be less than or equal to the number of frames."
            self._video = self._video[frame_indices, ...]
            self._times = self._times[frame_indices]
            self._num_frames = len(frame_indices)

        super().__init__(file_path=file_path, channel_name=channel_name, plane_name=plane_name)

    def get_channel_names(self) -> list:
        return self._channel_names

    def get_dtype(self) -> DtypeType:
        return self._dtype

    def get_image_size(self) -> Tuple[int, int]:
        return self._num_rows, self._num_columns

    def get_num_channels(self) -> int:
        return self._num_channels

    def get_num_frames(self) -> int:
        return self._num_frames

    def get_sampling_frequency(self):
        return self._sampling_frequency

    def get_video(self, start_frame=None, end_frame=None, channel: int = 0) -> np.ndarray:
        video = self._video[start_frame:end_frame, self.channel_index, self.plane_index, ...]

        return video.compute()
