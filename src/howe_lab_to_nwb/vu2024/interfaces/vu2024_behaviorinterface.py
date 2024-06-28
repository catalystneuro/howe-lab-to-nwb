from typing import Optional

import numpy as np
import pandas as pd
from neuroconv import BaseTemporalAlignmentInterface
from neuroconv.tools import get_module
from neuroconv.utils import FilePathType, get_base_schema, get_schema_from_hdmf_class
from pymatreader import read_mat
from pynwb import NWBFile, TimeSeries
from pynwb.epoch import TimeIntervals


class Vu2024BehaviorInterface(BaseTemporalAlignmentInterface):
    """
    Interface for reading the processed behavior data from .mat files from the Howe Lab.
    """

    display_name = "Vu2024Behavior"
    associated_suffixes = (".mat",)
    info = "Interface for behavior data (.mat) from the Howe Lab."

    def __init__(
        self,
        file_path: FilePathType,
        verbose: bool = True,
    ):
        """
        DataInterface for reading the processed behavior data from .mat files from the Howe Lab.

        Parameters
        ----------
        file_path : FilePathType
            Path to the .mat file that contains the fiber photometry data.
        verbose : bool, default: True
            controls verbosity.
        """

        super().__init__(file_path=file_path, verbose=verbose)
        self._timestamps = None

    def get_original_timestamps(self) -> np.ndarray:
        filename = self.source_data["file_path"]
        behavior_data = read_mat(filename=filename)
        if "timestamp" not in behavior_data:
            raise ValueError(f"Expected 'timestamp' is not in '{filename}'.")
        timestamps = behavior_data["timestamp"]

        return timestamps

    def get_timestamps(self, stub_test: bool = False) -> np.ndarray:
        timestamps = self._timestamps if self._timestamps is not None else self.get_original_timestamps()
        if stub_test:
            return timestamps[:6000]
        return timestamps

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.array(aligned_timestamps)

    def get_metadata_schema(self) -> dict:
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Behavior"] = get_base_schema(tag="Behavior")
        time_series_schema = get_schema_from_hdmf_class(TimeSeries)
        metadata_schema["properties"]["Behavior"].update(
            required=["TimeSeries", "TimeIntervals"],
            properties=dict(
                TimeSeries=dict(
                    type="array",
                    minItems=1,
                    items=time_series_schema,
                ),
                TimeIntervals=dict(
                    type="object",
                    required=["name", "description"],
                    properties=dict(
                        name=dict(type="string"),
                        description=dict(type="string"),
                    ),
                ),
            ),
        )
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()

        metadata["Behavior"] = dict(
            TimeSeries=[
                dict(
                    name="AngularVelocity",
                    description="The angular velocity from yaw (rotational) velocity converted to radians/s.",
                    unit="radians/s",
                ),
                dict(
                    name="Velocity",
                    description="Velocity for the roll and pitch (x, y) measured in m/s.",
                    unit="m/s",
                ),
            ],
            TimeIntervals=dict(
                name="TimeIntervals",
                description="The onset times of the events (licking, tone, light or reward delivery).",
            ),
        )

        return metadata

    def add_velocity_signals(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        ball_diameter_in_meters: float = None,
        stub_test: Optional[bool] = False,
    ) -> None:
        """
        Add the velocity signals (yaw (z) velocity and the roll and pitch (x, y)) to the NWBFile.
        The yaw velocity is converted to radians/s using the calculation provided from the Howe Lab.
        The roll and pitch velocities are in m/s.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWBFile to which the velocity signals will be added.
        metadata : dict
            Metadata for the velocity signals.
        ball_diameter_in_meters : float, optional
            The diameter of the ball in meters, optional.
            Used to convert the yaw velocity from m/s to radians/s, when not specified default value is 0.2032.
            Reference: https://zenodo.org/records/10272874 from ball2xy.m
        stub_test : bool, optional
            Whether to run a stub test, by default False.
        """

        end_frame = 6000 if stub_test else None

        behavior_metadata = metadata["Behavior"]
        time_series_metadata = behavior_metadata["TimeSeries"]

        behavior_data = read_mat(filename=self.source_data["file_path"])
        timestamps = self.get_timestamps(stub_test=stub_test)

        behavior = get_module(
            nwbfile,
            name="behavior",
            description="Contains the velocity signals from two optical mouse sensors (Logitech G203 mice with hard plastic shells removed).",
        )

        # ballYaw is in m/s convert to radians/s using their code
        # https://zenodo.org/records/10272874 ball2xy.m
        angular_velocity_metadata = time_series_metadata[0]
        yaw_in_meters = behavior_data["ballYaw"][:end_frame]
        ball_diameter_in_meters = ball_diameter_in_meters or 0.2032
        yaw_in_radians = yaw_in_meters / (np.pi * ball_diameter_in_meters) * 2 * np.pi

        velocity_z = TimeSeries(
            **angular_velocity_metadata,
            data=yaw_in_radians,
            timestamps=timestamps,
        )
        behavior.add(velocity_z)

        velocity_metadata = time_series_metadata[1]
        velocity_in_meters = np.column_stack((behavior_data["ballRoll"], behavior_data["ballPitch"]))
        velocity_in_meters = velocity_in_meters[:end_frame]
        velocity_xy = TimeSeries(
            **velocity_metadata,
            data=velocity_in_meters,
            timestamps=velocity_z,
        )
        behavior.add(velocity_xy)

    def _get_start_end_times(self, binary_event_data: np.ndarray):

        timestamps = self.get_timestamps()
        ones_indices = np.where(binary_event_data == 1)[0]
        if not len(ones_indices):
            return [], []

        # Calculate the differences between consecutive indices
        diff = np.diff(ones_indices)

        # Find where the difference is not 1
        ends = np.where(diff != 1)[0]

        # The start of an interval is one index after the end of the previous interval
        starts = ends + 1

        # Handle the case for the first interval
        starts = np.insert(starts, 0, 0)

        # Handle the case for the last interval
        ends = np.append(ends, len(ones_indices) - 1)

        # Return the start and end times of the intervals
        start_times = timestamps[ones_indices[starts]]
        end_times = timestamps[ones_indices[ends]]

        return start_times, end_times

    def add_binary_signals(self, nwbfile: NWBFile, metadata: dict):
        behavior_data = read_mat(filename=self.source_data["file_path"])

        events_metadata = metadata["Behavior"]["TimeIntervals"]

        event_name_mapping = dict(
            lick="Lick",
            reward="Reward",
            stimulus_led="Light",
            stimulus_sound="Tone",
        )

        event_dfs = []
        for event_name in ["lick", "reward", "stimulus_led", "stimulus_sound"]:
            start_times, end_times = self._get_start_end_times(binary_event_data=behavior_data[event_name])
            if not len(start_times):
                continue

            event_dfs.append(
                pd.DataFrame(
                    {
                        "start_time": start_times,
                        "stop_time": end_times,
                        "event_type": event_name_mapping[event_name],
                    }
                )
            )

        if not len(event_dfs):
            return

        events = TimeIntervals(**events_metadata)
        events.add_column(
            name="event_type",
            description="The type of event (licking, light, tone or reward delivery).",
        )

        event_df = pd.concat(event_dfs)
        event_df = event_df.sort_values(by="start_time")
        event_df = event_df.reset_index(drop=True)
        for row_ind, row in event_df.iterrows():
            events.add_interval(
                start_time=row["start_time"],
                stop_time=row["stop_time"],
                event_type=row["event_type"],
                id=row_ind,
            )

        behavior = get_module(nwbfile, name="behavior")
        behavior.add(events)

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: Optional[bool] = False,
        ball_diameter_in_meters: Optional[float] = None,
    ) -> None:

        self.add_velocity_signals(
            nwbfile=nwbfile,
            metadata=metadata,
            stub_test=stub_test,
            ball_diameter_in_meters=ball_diameter_in_meters,
        )
        self.add_binary_signals(nwbfile=nwbfile, metadata=metadata)
