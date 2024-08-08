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

    def temporally_align_data_interfaces(self):
        if self.aligned:
            return
        imaging = self.data_interface_objects["Imaging"]
        fiber_photometry = self.data_interface_objects["FiberPhotometry"]
        # Use the timestamps from the fiber photometry interface for the imaging data
        # The timestamps from the fiber photometry data is from the TTL signals
        fiber_photometry_timestamps = fiber_photometry.get_timestamps()

        if imaging.source_data["frame_indices"] is not None:
            # we must fix the timestamps for fiber photometry
            frame_indices = imaging.source_data["frame_indices"]
            fiber_photometry_timestamps = fiber_photometry_timestamps[frame_indices]
            fiber_photometry.set_aligned_timestamps(aligned_timestamps=fiber_photometry_timestamps)
        imaging.set_aligned_timestamps(aligned_timestamps=fiber_photometry_timestamps)

        video_interfaces = [self.data_interface_objects[key] for key in self.data_interface_objects if "Video" in key]
        for video_interface in video_interfaces:
            video_file_path = video_interface.source_data["file_paths"][0]
            if any(part in video_file_path for part in ["body", "top"]):
                ttl_stream_name = "ttlIn3"
            elif any(part in video_file_path for part in ["lick", "face", "side"]):
                ttl_stream_name = "ttlIn4"
            else:
                raise ValueError(f"Could not determine TTL stream for video file {video_file_path}.")

            ttl_file_path = fiber_photometry.source_data["ttl_file_path"]
            ttl_data = read_mat(filename=ttl_file_path)
            rising_frames = get_rising_frames_from_ttl(trace=ttl_data[ttl_stream_name])
            video_timestamps = ttl_data["timestamp"][rising_frames]
            if len(video_timestamps) > len(fiber_photometry_timestamps):
                video_timestamps = video_timestamps[: len(fiber_photometry_timestamps)]
            video_interface.set_aligned_timestamps(aligned_timestamps=[video_timestamps])

        self.aligned = True

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata, conversion_options: Optional[dict] = None) -> None:
        self.temporally_align_data_interfaces()
        # set custom description for the 'ophys' processing module
        _ = get_module(
            nwbfile=nwbfile, name="ophys", description="Constains the processed imaging and fiber photometry data."
        )
        return super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)
