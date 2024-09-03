# Notes concerning the vu2024 conversion

## Dataset notes

Based on the [manuscript](https://doi.org/10.1016/j.neuron.2023.12.011) provided by the lab, this dataset contains fiber
photometry recordings from multi-fiber arrays implanted in the striatum in mice running on a treadmill while receiving
either visual (blue LED) or auditory (12 kHz tone) stimuli at random intervals (4–40 s). Some sessions may include water
reward delivery, where a water spout mounted on a post delivered water rewards (9 μL) at random time intervals
(randomly drawn from a 5-30s uniform distribution) through a water spout and solenoid valve gated electronically.
Licking was monitored by a capacitive touch circuit connected to the spout.

### From protocol.io

The dataset was collected using the following protocol: [dx.doi.org/10.17504/protocols.io.bp2l6xyrklqe/v1](dx.doi.org/10.17504/protocols.io.bp2l6xyrklqe/v1)

#### Fiber array imaging

Fiber bundle imaging for head-fixed experiments was performed with a custom microscope.

Imaging data was acquired using HCImage Live (Hamamatsu) and saved as a .CXD (movie) file. Single wavelength excitation
(470nm, 405nm, 415nm, and 570nm) and emission was performed with continuous, internally triggered imaging at 30Hz.
For dual-wavelength excitation and emission, two LEDs were triggered by 5V digital TTL pulses which alternated at
either 11Hz (30ms exposure) or 18Hz (20ms exposure). To synchronize each LED with the appropriate camera
(e.g. 470nm LED excitation to green emission camera), the LED trigger pulses were sent in parallel(and decreased to 3.3V
via a pulldown circuit) to the cameras to trigger exposure timing. The timing and duration of digital pulses were
controlled by custom MATLAB software through a programmable digital acquisition card (“NIDAQ”, National Instruments PCIe
6343 ). Voltage pulses were sent back from the cameras to the NIDAQ card after exposure of each frame to confirm proper
camera triggering and to align imaging data with behavior data.

#### Behavior data

Behavioral data is collected at 2kHz via a programmable digital acquisition card (NIDAQ, National Instruments PCIe 6343) controlled via custom MATLAB programs.
TTL pulses sent from the imaging cameras enable syncing of behavioral recordings with neural, i.e., imaging, data (see split_and_bin_grid_behav_files.m).
The resulting "binned" behavioral data measures have one datapoint (calculated via averaging, and for binary variables, subsequently rounded) corresponding to one frame of the recorded neural data movie.

### Preprocessing steps

All neural data were preprocessed using the scripts in https://github.com/HoweLab/MultifiberProcessing

1. Raw neural data are acquired as movies and have filetype .cxd
2. These movies are converted to .tif, and then motion-corrected.
3. Fluorescence is extracted from ROIs corresponding to fiber tops, and delta-F-over-F is calculated.

### Folder structure

The dataset is organized in the following way:

    ExperimentFolder/
    ├── DL18
    │   ├── 211110
    │   │   ├── GridDL-18_<date>_<time>_ttlIn1_movie1.mat
    │   │   ├── GridDL-18_<date>_<time>.mat
    │   │   ├── Data00217_crop_MC_ROIs.mat
    │   │   ├── DL18-lick-<date>-0000.avi
    │   │   ├── DL18-body-<date>-0000.avi
    │   │   ├── DL18-lick-<date>-0000.csv
    │   │   ├── Data00217.cxd
    │   │   └── Data00217_MC.tif
    │   └── DL18_fiber_locations.xlsx
    ├── DL19
    ├── DL30
    ├── UG21
    └── data table.xlsx

The `ExperimentFolder` contains subfolders for each animal. Each animal folder contains subfolders for each session.

- `GridDL-18_<date>_<time>.mat`: contains the raw behavioral data and the TTL pulses from the imaging cameras
- `GridDL-18_<date>_<time>_ttlIn1_movie1.mat`: contains the preprocessed behavioral data (downsampled to match the sampling rate of the imaging data)
  The fields in the .mat files are:
  * mouse: the name of the file
  * starttime: the timestamp of the beginning of the recording
  * timestamp: the time (s) elapsed since the start of the recording
  * ballSensor1_x: raw voltage reflecting the magnitude of the x-velocity coming from optical mouse sensor placed behind the mouse on the ball treadmill
  * ballSensor1_y: raw voltage reflecting the magnitude of the y-velocity coming from optical mouse sensor placed behind the mouse on the ball treadmill
  * ballSensor1_xsign: the sign (direction) of the x-velocity coming from optical mouse sensor placed behind the mouse on the ball treadmill
  * ballSensor1_ysign: the sign (direction) of the y-velocity coming from optical mouse sensor placed behind the mouse on
  * ballSensor2_x: raw voltage reflecting the magnitude of the x-velocity coming from optical mouse sensor placed to the side of the mouse on the ball treadmill
  * ballSensor2_y: raw voltage reflecting the magnitude of the y-velocity coming from optical mouse sensor placed to the side of the mouse on the ball treadmill
  * ballSensor2_xsign: the sign (direction) of the x-velocity coming from optical mouse sensor placed to the side of the mouse on the ball treadmill
  * ballSensor2_ysign: the sign (direction) of the y-velocity coming from optical mouse sensor placed to the side of the mouse on the ball treadmill
  * ballYaw: conversion to yaw velocity; see ball2xy.m
  * ballPitch: conversion to pitch velocity; see ball2xy.m
  * ballRoll: conversion to roll velocity; see ball2xy.m
  * reward: (binary) reward trigger
  * lick: (binary) lick touch sensor
  * ttlOut: (binary) TTLs sent from the program (user determined)
  * ttlIn1: (binary) TTLs coming in from neural imaging camera #1 (if applicable)
  * ttlIn2: (binary) TTLs coming in from neural imaging camera #2 (if applicable)
  * ttlIn470: (binary) duplicate of TTLs sent to trigger 470nm LED (if applicable)
  * ttlIn1_x_ttlIn470: (binary) the product of ttlIn1 and ttlIn470
  * ttlIn3: TTLs coming in from behavioral camera #1 (if applicable)
  * ttlIn4: TTLs coming in from behavioral camera #2 (if applicable)
- `Data00217.cxd`: the raw imaging data
- `Data00217_MC.tif`: the motion-corrected imaging data (not all sessions have this file)
- `Data00217_crop_MC_ROIs.mat`: contains the fluorescence data extracted from the ROIs
   The fields in the .mat files are:
   * ROIs: the centers of the ROIs
   * datapath: the path to the associated .tif file
   * snapshot: a snapshot of a frame from the .tif movie
   * radius: the radius of the ROIs
   * ROImasks: an m x n x p matrix of p binary ROI masks
   * FtoFcWindow: the window used to calculate baseline
   * F: the extracted raw fluorescence
   * Fc: the calculated ΔF/F
   * Fc_baseline: the calculated baseline
   * Fc_center: the calculated center, which becomes 0
- `DL18-lick-<date>-0000.avi` and `DL18-body-<date>-0000.avi`: videos of the mouse licking and running on the treadmill
   If "body", "top", "video1" is in the name of the file, then the corresponding TTL pulse is `ttlIn3`.
   If lick", "face", "side", "video2" is in the name of the file, then the corresponding TTL pulse is `ttlIn4`.
- `DL18_fiber_locations.xlsx`: contains the stereotactic coordinates of the fiber tips and the brain area they were implanted in

## Run conversion for a single session

First install the conversion specific dependencies:

```bash
cd src/howe_lab_to_nwb/vu2024
pip install -r vu2024_requirements.txt
```

### Convert a single-wavelength session

To convert a single-wavelength session, you can do in Python:

```python
from howe_lab_to_nwb.vu2024.vu2024_convert_single_wavelength_session import  single_wavelength_session_to_nwb
single_wavelength_session_to_nwb(
        raw_imaging_file_path="Data00217.cxd",
        raw_fiber_photometry_file_path="Data00217_crop_MC_ROIs.mat",
        ttl_file_path="GridDL-18_<date>_<time>.mat",
        ttl_stream_name="ttlIn1",
        fiber_locations_file_path="DL18_fiber_locations.xlsx",
        excitation_wavelength_in_nm=470,
        indicator="dLight1.3b",
        motion_corrected_imaging_file_path="Data00217_MC.tif",  # can be None
        behavior_file_path="GridDL-18_<date>_<time>_ttlIn1_movie1.mat",
        nwbfile_path="sub-DL18-ses-211110.nwb",
    )
```

#### Conversion parameters

The `single_wavelength_session_to_nwb` functions takes the following parameters:

- `raw_imaging_file_path`: The path to the .cxd file containing the raw imaging data.
- `raw_fiber_photometry_file_path`: The path to the .mat file containing the raw fiber photometry data.
- `ttl_file_path`: The path to the .mat file containing the TTL signals.
- `ttl_stream_name`: The name of the TTL stream for the imaging camera (e.g. 'ttlIn1').
- `fiber_locations_file_path`: The path to the .xlsx file containing the fiber locations.
- `excitation_wavelength_in_nm`: The excitation wavelength in nm.
- `indicator`: The name of the indicator used for the fiber photometry recording.
- `motion_corrected_imaging_file_path`: The path to the .tif file containing the motion corrected imaging data. (optional)
- `behavior_file_path`: The path to the processed behavior file.
- `nwbfile_path`: The path to the output NWB file.
- `stub_test`: if True, only a small subset of the data is converted (default: False).

### Convert all single-wavelength sessions

To convert all single-wavelength sessions, you can do in Python:

```python
from howe_lab_to_nwb.vu2024.vu2024_convert_all_single_wavelength_sessions import convert_all_single_wavelength_sessions
convert_all_single_wavelength_sessions(
        data_table_path="data table.xlsx",
        folder_path="ExperimentFolder",
        nwbfile_folder_path="nwbfiles",
        subject_ids=["DL18", "DL20", "DL21", "DL23", "DL27", "DL29", "DL30", "DL15"],
        stub_test=False,
        overwrite=False,
    )
```

#### Conversion parameters

The `convert_all_single_wavelength_sessions` function takes the following parameters:

- `data_table_path`: The path to the XLSX file containing info for all the sessions. (required)
- `folder_path`: The root folder path to search for the filenames in the data table. (required)
- `nwbfile_folder_path`: The folder path to save the NWB files. (required)
- `subject_ids`: The list of subject IDs to convert. (optional)
- `stub_test`: if True, only a small subset of the data is converted (default: False).
- `overwrite`: if True, overwrite existing NWB files (default: False).


### Convert dual-wavelength sessions

To convert a single dual-wavelength session, you can do in Python:

```python
from howe_lab_to_nwb.vu2024.vu2024_convert_dual_wavelength_session import dual_wavelength_session_to_nwb
dual_wavelength_session_to_nwb(
        raw_imaging_file_paths=["Data113.cxd", "R600_AP9_117.cxd"],
        fiber_photometry_file_paths=["Data113_crop_MC_ROIs_new.mat", "R600_AP9_117_crop_MC_ROIs_new.mat"],
        ttl_file_path="chatdat600_AP9_470_570_2021.08.21_10.48.07.mat",
        ttl_stream_names=["ttlIn1", "ttlIn2"],
        fiber_locations_file_path="Grid9_fiber_locations.xlsx",
        excitation_wavelengths_in_nm=[470, 570],
        indicators=["Ach3.0", "jRGECO1a"],
        behavior_file_paths=["chatdat600_AP9_470_570_2021.08.21_10.48.07_aligned_ttlIn1_movie1.mat",
                             "chatdat600_AP9_470_570_2021.08.21_10.48.07_aligned_ttlIn2_movie1.mat"],
        nwbfile_path="sub-Grid9_ses-210821.nwb",
    )
```

To convert all dual-wavelength sessions, you can do in Python:
```python
from howe_lab_to_nwb.vu2024.vu2024_convert_all_dual_wavelength_sessions import convert_all_dual_wavelength_sessions
convert_all_dual_wavelength_sessions(
        data_table_path="data table.xlsx",
        folder_path="ExperimentFolder",
        nwbfile_folder_path="nwbfiles",
        subject_ids=["Grid9", "842", "DL31", "DL32"],
        stub_test=False,
        overwrite=False,
    )
```

#### Conversion parameters

The `convert_all_dual_wavelength_sessions` function takes the following parameters:

- `data_table_path`: The path to the XLSX file containing info for all the sessions. (required)
- `folder_path`: The root folder path to search for the filenames in the data table. (required)
- `nwbfile_folder_path`: The folder path to save the NWB files. (required)
- `subject_ids`: The list of subject IDs to convert. (required)
- `stub_test`: if True, only a small subset of the data is converted (default: False).
- `overwrite`: if True, overwrite existing NWB files (default: False).
