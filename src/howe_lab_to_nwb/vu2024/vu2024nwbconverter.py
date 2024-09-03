"""Primary NWBConverter class for this dataset."""
from typing import Optional

from neuroconv import NWBConverter
from neuroconv.datainterfaces import TiffImagingInterface, VideoInterface
from neuroconv.tools import get_module
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl
from neuroconv.utils import DeepDict
from pymatreader import read_mat
from pynwb import NWBFile

from howe_lab_to_nwb.vu2024.interfaces import (
    CxdImagingInterface,
    Vu2024FiberPhotometryInterface,
    Vu2024BehaviorInterface,
    Vu2024SegmentationInterface,
    Vu2024TiffImagingInterface,
)


class Vu2024NWBConverter(NWBConverter):
    """Primary conversion class for the Vu 2024 fiber photometry dataset."""

    aligned = False

    data_interface_classes = dict(
        Imaging=CxdImagingInterface,
        ProcessedImaging=Vu2024TiffImagingInterface,
        FiberPhotometry=Vu2024FiberPhotometryInterface,
        Behavior=Vu2024BehaviorInterface,
        Segmentation=Vu2024SegmentationInterface,
        Video1=VideoInterface,
        Video2=VideoInterface,
    )

    def get_metadata_schema(self) -> dict:

        metadata_schema = super().get_metadata_schema()
        # To allow FiberPhotometry in Ophys metadata
        metadata_schema["properties"]["Ophys"].update(
            additionalProperties=True,
        )

        return metadata_schema

    def temporally_align_data_interfaces(self, aligned_starting_time: Optional[float] = None) -> None:
        if self.aligned:
            return
        imaging = self.data_interface_objects["Imaging"]
        fiber_photometry = self.data_interface_objects["FiberPhotometry"]

        has_behavior = "Behavior" in self.data_interface_objects
        # Align the starting time of the imaging data to the starting time of the behavior data (aligned timestamps)
        if has_behavior and aligned_starting_time is None:
            behavior = self.data_interface_objects["Behavior"]
            behavior_timestamps = behavior.get_timestamps()
            aligned_starting_time = behavior_timestamps[0]

        # Align the starting time of the imaging data to the starting time of the behavior data
        imaging.set_aligned_starting_time(aligned_starting_time=aligned_starting_time)

        # Use the aligned timestamps to override the timestamps in the fiber photometry data
        aligned_timestamps = imaging.get_timestamps()
        fiber_photometry.set_aligned_timestamps(aligned_timestamps=aligned_timestamps)

        if "ProcessedImaging" in self.data_interface_objects:
            processed_imaging = self.data_interface_objects["ProcessedImaging"]
            processed_imaging.set_aligned_timestamps(aligned_timestamps=aligned_timestamps)

        video_interfaces = [self.data_interface_objects[key] for key in self.data_interface_objects if "Video" in key]
        for video_interface in video_interfaces:
            video_file_path = video_interface.source_data["file_paths"][0]
            if any(part in video_file_path for part in ["body", "top", "video1"]):
                ttl_stream_name = "ttlIn3"
            elif any(part in video_file_path for part in ["lick", "face", "side", "video2"]):
                ttl_stream_name = "ttlIn4"
            else:
                raise ValueError(f"Could not determine TTL stream for video file {video_file_path}.")

            ttl_file_path = fiber_photometry.source_data["ttl_file_path"]
            ttl_data = read_mat(filename=ttl_file_path)
            rising_frames = get_rising_frames_from_ttl(trace=ttl_data[ttl_stream_name])
            video_timestamps = ttl_data["timestamp"][rising_frames]
            if len(video_timestamps) > len(aligned_timestamps):
                video_timestamps = video_timestamps[: len(aligned_timestamps)]
            video_interface.set_aligned_timestamps(aligned_timestamps=[video_timestamps])

        self.aligned = True

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata,
        conversion_options: Optional[dict] = None,
        aligned_starting_time: Optional[float] = None,
    ) -> None:
        self.temporally_align_data_interfaces(aligned_starting_time=aligned_starting_time)
        # set custom description for the 'ophys' processing module
        _ = get_module(
            nwbfile=nwbfile, name="ophys", description="Constains the processed imaging and fiber photometry data."
        )
        return super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)
