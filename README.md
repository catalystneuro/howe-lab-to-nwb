# howe-lab-to-nwb
NWB conversion scripts for Howe lab data to the [Neurodata Without Borders](https://nwb-overview.readthedocs.io/) data format.


## Installation from Github
We recommend installing this package directly from Github. This option has the advantage that the source code can be modifed if you need to amend some of the code we originally provided to adapt to future experimental differences.
To install the conversion from GitHub you will need to use `git` ([installation instructions](https://github.com/git-guides/install-git)). We also recommend the installation of `conda` ([installation instructions](https://docs.conda.io/en/latest/miniconda.html)) as it contains
all the required machinery in a single and simple install.

From a terminal (note that conda should install one in your system) you can do the following:

```
git clone https://github.com/catalystneuro/howe-lab-to-nwb
cd howe-lab-to-nwb
conda env create --file make_env.yml
conda activate howe-lab-to-nwb-env
```

This creates a [conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html) which isolates the conversion code from your system libraries.  We recommend that you run all your conversion related tasks and analysis from the created environment in order to minimize issues related to package dependencies.

Alternatively, if you want to avoid conda altogether (for example if you use another virtual environment tool) you can install the repository with the following commands using only pip:

```
git clone https://github.com/catalystneuro/howe-lab-to-nwb
cd howe-lab-to-nwb
pip install -e .
```

Note:
both of the methods above install the repository in [editable mode](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs).

## Repository structure
Each conversion is organized in a directory of its own in the `src` directory:

    howe-lab-to-nwb/
    ├── LICENSE
    ├── make_env.yml
    ├── pyproject.toml
    ├── README.md
    ├── requirements.txt
    ├── setup.py
    └── src
        ├── howe_lab_to_nwb
        │   ├── vu2024
        │       ├── extractors
        │       │   ├── bioformats_utils.py
        │       │   ├── cxdimagingextractor.py
        │       │   └── __init__.py
        │       ├── interfaces
        │       │   ├── cxdimaginginterface.py
        │       │   ├── tiffimaginginterface.py
        │       │   ├── vu2024_behaviorinterface.py
        │       │   ├── vu2024_fiberphotometryinterface.py
        │       │   ├── vu2024_segmentationinterface.py
        │       │   └── __init__.py
        │       ├── metadata
        │       │   ├── vu2024_fiber_photometry_metadata.yaml
        │       │   ├── vu2024_general_metadata.yaml
        │       │   ├── vu2024_ophys_metadata.yaml
        │       ├── tutorials
        │       │   └── vu2024_tutorial.ipynb
        │       ├── utils
        │       │   ├── add_fiber_photometry.py
        │       │   └── __init__.py
        │       ├── vu2024_convert_dual_wavelength_session.py
        │       ├── vu2024_convert_single_wavelength_session.py
        │       ├── vu2024_notes.md
        │       ├── vu2024_requirements.txt
        │       ├── vu2024nwbconverter.py
        │       └── __init__.py
        │   └── another_conversion
        └── __init__.py

 For example, for the conversion `vu2024` you can find a directory located in `src/howe-lab-to-nwb/vu2024`. Inside each conversion directory you can find the following files:

* `vu2024_convert_dual_wavelength_session.py`: this script defines the function to convert a dual-wavelength session of the conversion.
* `vu2024_convert_single_wavelength_session.py`: this script defines the function to convert a single-wavelength session of the conversion.
* `vu2024_requirements.txt`: dependencies specific to this conversion.
* `vu2024_metadata.yml`: metadata in yaml format for this specific conversion.
* `vu2024behaviorinterface.py`: the behavior interface. Usually ad-hoc for each conversion.
* `vu2024nwbconverter.py`: the place where the `NWBConverter` class is defined.
* `vu2024_notes.md`: notes and comments concerning this specific conversion.
* `extractors/`: directory containing the imaging extractor class for this specific conversion.
* `interfaces/`: directory containing the interface classes for this specific conversion.
* `metadata/`: directory containing the metadata files for this specific conversion.
* `tutorials/`: directory containing tutorials for this specific conversion.
* `utils/`: directory containing utility functions for this specific conversion.

### Notes on the conversion

The conversion notes is located in `src/howe-lab-to-nwb/vu2024/vu2024_notes.md`. This file contains information about the expected file structure and the conversion process.

### Running a specific conversion

To run a specific conversion, you might need to install first some conversion specific dependencies that are located in each conversion directory:
```
pip install -r src/howe_lab_to_nwb/vu2024/vu2024_requirements.txt
```

To convert a single-wavelength session, you can run the following command:
```
python src/howe_lab_to_nwb/vu2024/vu2024_convert_single_wavelength_session.py
```
To convert all single-wavelength sessions in a directory, you can run the following command:
```
python src/howe_lab_to_nwb/vu2024/vu2024_convert_all_single_wavelength_sessions.py
```

To convert a dual-wavelength session, you can run the following command:
```
python src/howe_lab_to_nwb/vu2024/vu2024_convert_dual_wavelength_session.py
```
To convert all dual-wavelength sessions in a directory, you can run the following command:
```
python src/howe_lab_to_nwb/vu2024/vu2024_convert_all_dual_wavelength_sessions.py
```

## NWB tutorials

The `tutorials` directory contains Jupyter notebooks that demonstrate how to use the NWB files generated by the conversion scripts.
The notebooks are located in the `src/howe-lab-to-nwb/vu2024/tutorials` directory.

You might need to install `jupyter` before running the notebooks:

```
pip install jupyter
cd src/howe-lab-to-nwb/vu2024/tutorials
jupyter lab
```
