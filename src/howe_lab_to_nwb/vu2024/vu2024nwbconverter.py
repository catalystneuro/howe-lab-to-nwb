"""Primary NWBConverter class for this dataset."""

from neuroconv import NWBConverter
from neuroconv.datainterfaces import TiffImagingInterface, VideoInterface
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl
from neuroconv.utils import DeepDict
from pymatreader import read_mat

from howe_lab_to_nwb.vu2024.interfaces import (
    CxdImagingInterface,
    Vu2024FiberPhotometryInterface,
    Vu2024BehaviorInterface,
)


class Vu2024NWBConverter(NWBConverter):
    """Primary conversion class for the Vu 2024 fiber photometry dataset."""

    data_interface_classes = dict(
        Imaging=CxdImagingInterface,
        ProcessedImaging=TiffImagingInterface,
        FiberPhotometry=Vu2024FiberPhotometryInterface,
        Behavior=Vu2024BehaviorInterface,
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

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        # Overwrite the Ophys imaging metadata with the metadata from the CxdImagingInterface
        imaging_interface_metadata = self.data_interface_objects["Imaging"].get_metadata()
        metadata["Ophys"]["Device"] = imaging_interface_metadata["Ophys"]["Device"]
        metadata["Ophys"]["ImagingPlane"] = imaging_interface_metadata["Ophys"]["ImagingPlane"]
        metadata["Ophys"]["TwoPhotonSeries"] = imaging_interface_metadata["Ophys"]["TwoPhotonSeries"]

        return metadata

    def temporally_align_data_interfaces(self):
        imaging = self.data_interface_objects["Imaging"]
        fiber_photometry = self.data_interface_objects["FiberPhotometry"]
        # Use the timestamps from the fiber photometry interface for the imaging data
        # The timestamps from the fiber photometry data is from the TTL signals
        fiber_photometry_timestamps = fiber_photometry.get_timestamps()
        imaging.set_aligned_timestamps(aligned_timestamps=fiber_photometry_timestamps)

        video_interfaces = [self.data_interface_objects[key] for key in self.data_interface_objects if "Video" in key]
        # TODO: need to know which TTL stream to use for each video interface
        ttl_stream_names = ["ttlIn3", "ttlIn4"]
        for video_interface, ttl_stream_name in zip(video_interfaces, ttl_stream_names):
            video_timestamps = video_interface.get_timestamps()
            ttl_file_path = fiber_photometry.source_data["ttl_file_path"]
            ttl_data = read_mat(filename=ttl_file_path)
            first_ttl_frame = get_rising_frames_from_ttl(trace=ttl_data[ttl_stream_name])[0]
            video_interface.set_aligned_segment_starting_times(
                aligned_segment_starting_times=[video_timestamps[0][first_ttl_frame]]
            )
