from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np
from neuroconv import BaseTemporalAlignmentInterface
from neuroconv.tools.signal_processing import get_rising_frames_from_ttl
from pymatreader import read_mat
from pynwb import NWBFile

from howe_lab_to_nwb.vu2024.utils import add_fiber_photometry_series
from howe_lab_to_nwb.vu2024.utils.add_fiber_photometry import add_fiber_photometry_table


class Vu2024FiberPhotometryInterface(BaseTemporalAlignmentInterface):
    """
    Interface for reading fiber photometry data from .mat files from the Howe Lab.
    """

    display_name = "Vu2024FiberPhotometry"
    associated_suffixes = (".mat",)
    info = "Interface for fiber photometry data (.mat) from the Howe Lab."

    def __init__(
        self,
        file_path: Union[str, Path],
        ttl_file_path: Union[str, Path],
        ttl_stream_name: str,
        verbose: bool = True,
    ):
        """
        DataInterface for reading fiber photometry data from .mat files from the Howe Lab.

        Parameters
        ----------
        file_path : str or Path
            Path to the .mat file that contains the fiber photometry data.
        ttl_file_path : str or Path
            Path to the .mat file that contains the TTL signals.
        ttl_stream_name : str, optional
            Name of the TTL stream to extract from the TTL signals. Default is 'ttlIn1'.
        verbose : bool, default: True
            controls verbosity.
        """
        file_path = Path(file_path)
        assert file_path.exists(), f"The file that contains the fiber photometry data '{file_path}' does not exist."
        assert file_path.suffix == ".mat", f"Expected .mat file, got {file_path.suffix}."

        super().__init__(
            file_path=file_path, ttl_file_path=ttl_file_path, ttl_stream_name=ttl_stream_name, verbose=verbose
        )

        ttl_file_path = Path(ttl_file_path)
        assert ttl_file_path.exists(), f"The file that contains the TTL signals '{file_path}' does not exist."
        assert ttl_file_path.suffix == ".mat", f"Expected .mat file, got {ttl_file_path.suffix}."
        ttl_data = read_mat(filename=str(ttl_file_path))

        if "starttime" not in ttl_data:
            raise ValueError(f"Expected 'starttime' is not in '{ttl_file_path}'.")
        self._start_time = ttl_data["starttime"]
        self._timestamps = None

    def get_original_timestamps(self) -> np.ndarray:
        filename = self.source_data["ttl_file_path"]
        ttl_stream_name = self.source_data["ttl_stream_name"]
        ttl_data = read_mat(filename=filename)
        rising_frames = get_rising_frames_from_ttl(trace=ttl_data[ttl_stream_name])
        timestamps = ttl_data["timestamp"]

        return timestamps[rising_frames]

    def get_timestamps(self, stub_test: bool = False) -> np.ndarray:
        timestamps = self._timestamps if self._timestamps is not None else self.get_original_timestamps()
        if stub_test:
            return timestamps[:100]
        return timestamps

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.array(aligned_timestamps)

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        expected_date_format = "%d-%b-%Y %H:%M:%S"
        session_start_time = datetime.strptime(self._start_time, expected_date_format)
        metadata["NWBFile"]["session_start_time"] = session_start_time

        return metadata

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        fiber_locations_metadata: list,
        stub_test: Optional[bool] = False,
    ) -> None:

        fiber_photometry_data = read_mat(filename=self.source_data["file_path"])
        timestamps = self.get_timestamps(stub_test=stub_test)

        additional_device_metadata = metadata["Ophys"]["FiberPhotometry"]["Devices"]
        for device_metadata in additional_device_metadata:
            if device_metadata["name"] not in nwbfile.devices:
                nwbfile.create_device(**device_metadata)

        if "F" not in fiber_photometry_data:
            raise ValueError(f"Expected raw fluorescence 'F' is not in '{self.source_data['file_path']}'.")
        raw_fluorescence = fiber_photometry_data["F"]
        data_to_add = raw_fluorescence if not stub_test else raw_fluorescence[:100]

        add_fiber_photometry_table(nwbfile=nwbfile, metadata=metadata)
        fiber_photometry_table = nwbfile.lab_meta_data["FiberPhotometry"].fiber_photometry_table
        fiber_table_region = list(np.array(range(data_to_add.shape[1])) + len(fiber_photometry_table))

        if len(fiber_locations_metadata) != data_to_add.shape[1]:
            raise ValueError(
                f"Number of fiber locations ({len(fiber_locations_metadata)}) does not match the number of fibers "
                f"({data_to_add.shape[1]})."
            )
        fluorescence_metadata = metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"][0]
        fiber_photometry_series_name = fluorescence_metadata["name"]
        # Add raw fiber photometry data to NWBFile
        add_fiber_photometry_series(
            nwbfile=nwbfile,
            metadata=metadata,
            data=data_to_add,
            timestamps=timestamps,
            fiber_photometry_series_name=fiber_photometry_series_name,
            fiber_locations_metadata=fiber_locations_metadata,
            table_region=fiber_table_region,
        )

        # Add baseline fluorescence data to NWBFile
        if "F_baseline" in fiber_photometry_data:
            baseline_fluorescence = fiber_photometry_data["F_baseline"]
            baseline_data_to_add = baseline_fluorescence if not stub_test else baseline_fluorescence[:100]
            fluorescence_metadata = deepcopy(metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"][0])
            fiber_photometry_series_name = f"Baseline{fluorescence_metadata['name']}"
            description = fluorescence_metadata["description"]
            description = description.replace("Raw", "Baseline")
            fluorescence_metadata.update(
                name=fiber_photometry_series_name,
                description=description,
            )
            metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"].append(fluorescence_metadata)
            add_fiber_photometry_series(
                nwbfile=nwbfile,
                metadata=metadata,
                data=baseline_data_to_add,
                timestamps=timestamps,
                fiber_photometry_series_name=fiber_photometry_series_name,
                fiber_locations_metadata=fiber_locations_metadata,
                table_region=fiber_table_region,
                parent_container="processing/ophys",
            )

        # Add baseline corrected fluorescence data to NWBFile
        if "Fc" in fiber_photometry_data:
            corrected_fluorescence = fiber_photometry_data["Fc"]
            corrected_data_to_add = corrected_fluorescence if not stub_test else corrected_fluorescence[:100]
            fluorescence_metadata = deepcopy(metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"][0])
            fiber_photometry_series_name = f"DfOverF{fluorescence_metadata['name']}"
            description = fluorescence_metadata["description"]
            description = description.replace("Raw", "Baseline corrected (DF/F)")
            fluorescence_metadata.update(
                name=fiber_photometry_series_name,
                description=description,
            )
            metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"].append(fluorescence_metadata)

            add_fiber_photometry_series(
                nwbfile=nwbfile,
                metadata=metadata,
                data=corrected_data_to_add,
                timestamps=timestamps,
                fiber_photometry_series_name=fiber_photometry_series_name,
                fiber_locations_metadata=fiber_locations_metadata,
                table_region=fiber_table_region,
                parent_container="processing/ophys",
            )
