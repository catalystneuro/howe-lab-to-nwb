from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
from neuroconv import BaseTemporalAlignmentInterface
from neuroconv.tools import get_module
from neuroconv.utils import get_base_schema, get_schema_from_hdmf_class
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
        file_path: Union[str, Path],
        verbose: bool = True,
    ):
        """
        DataInterface for reading the processed behavior data from .mat files from the Howe Lab.

        Parameters
        ----------
        file_path : str or Path
            Path to the .mat file that contains the "binned" behavior data.
            ("*ttlIn1_movie1.mat" files)
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
                description="Mice were presented with either visual (blue LED) or auditory (12 kHz tone) stimuli at random intervals (4–40 s). For experiments with water reward delivery, a water spout mounted on a post delivered water rewards (9 μL, Figure 1B) at random time intervals (randomly drawn from a 5-30s uniform distribution) through a water spout and solenoid valve gated electronically. Licking was monitored by a capacitive touch circuit connected to the spout.",
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

    def add_binary_signals(self, nwbfile: NWBFile, metadata: dict):
        """
        Add the binary signals (licking, light, tone, and reward delivery) to the NWBFile.
        The onset and offset times are determined by the changes in the binary signals.
        # Reference for calculation: https://zenodo.org/records/10272874 salientStim_getTrialTimes.m
        """
        behavior_data = read_mat(filename=self.source_data["file_path"])
        timestamps = self.get_timestamps()

        events_metadata = metadata["Behavior"]["TimeIntervals"]

        event_name_mapping = dict(
            stimulus_led="Light",
            stimulus_led2="Light",
            stimulus_sound="Tone",
            lick="Lick",
            reward="Reward",
        )

        event_dfs = []
        for event_name in event_name_mapping.keys():
            if event_name not in behavior_data:
                continue

            event_data = behavior_data[event_name].astype(int)

            # Find the indices where stimulus_led changes from 0 to 1 (stimulus on)
            stim_on = np.where(np.diff(event_data) == 1)[0] + 1
            if not len(stim_on):
                continue

            # Find the indices where stimulus_led changes from 1 to 0 (stimulus off)
            stim_off = np.where(np.diff(event_data) == -1)[0] + 1

            # Sort the indices to ensure they are in order
            stim_on = sorted(stim_on)
            stim_off = sorted(stim_off)

            # Adjust for mismatches
            if stim_off[0] < stim_on[0]:
                stim_off = stim_off[1:]
            if stim_on[-1] > stim_off[-1]:
                stim_on = stim_on[:-1]

            event_dfs.append(
                pd.DataFrame(
                    {
                        "start_time": timestamps[stim_on],
                        "stop_time": timestamps[stim_off],
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
