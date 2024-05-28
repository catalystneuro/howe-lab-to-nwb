from copy import deepcopy
from pathlib import Path

import pandas as pd
from neuroconv.utils import FilePathType, DeepDict


def process_extra_metadata(
    file_path: FilePathType,
    metadata: dict,
):
    """
    Process the extra metadata from the .xlsx file.

    Parameters
    ----------
    file_path : FilePathType
        The path to the fiber locations xlsx file.
    metadata : dict
        The metadata dictionary to update with the extra metadata.
    """

    extra_metadata = deepcopy(metadata)
    assert Path(file_path).exists(), f"File {file_path} does not exist."
    fiber_locations = pd.read_excel(file_path)
    fiber_locations.replace(to_replace={pd.NA: None}, inplace=True)

    # todo: how to determine which one to use?
    default_optical_fibers_metadata = extra_metadata["Ophys"]["FiberPhotometry"]["OpticalFibers"][0]
    default_fiber_name = default_optical_fibers_metadata["name"]

    optical_fibers_to_add = []
    for roi_ind, row in fiber_locations.iterrows():
        coordinates = [row["fiber_bottom_AP"], row["fiber_bottom_ML"], row["fiber_bottom_DV"]]
        default_optical_fibers_metadata.update(
            name=default_fiber_name + f"-{row['ROI']}",
            # todo: sometimes allen label is not specified but ccf and fp labels are, what should be the location in this case?
            # TODO: rename to brain_area
            location=row["allen_label_abbrev"] if row["allen_label_abbrev"] else "unknown",
            coordinates=coordinates,
            # ccf_label=row["ccf_label"],
            # fp_label=row["fp_label"],
        )
        optical_fibers_to_add.append(deepcopy(default_optical_fibers_metadata))

    # Overriding the default optical fibers metadata with the new ones
    extra_metadata["Ophys"]["FiberPhotometry"]["OpticalFibers"] = optical_fibers_to_add
    extra_metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"][0].update(
        optical_fiber=optical_fibers_to_add,
    )

    return extra_metadata
