import re
from datetime import datetime

import pandas as pd


def _get_subject_metadata_from_dataframe(subject_id: str, data_table: pd.DataFrame) -> dict:
    """
    Returns the subject metadata from the data table.

    Parameters
    ----------
    subject_id : str
        The identifier of the subject (e.g. 'DL18').
    data_table : pd.DataFrame
        The data table containing the subject metadata:
        Required columns: 'MouseID', 'Date of Birth'
        Optional columns: 'Sex', 'Genotype', 'Strain'
    """
    if "MouseID" not in data_table.columns:
        raise ValueError(f"The 'MouseID' column is missing from the data table.")
    mouse_id_without_dashes = data_table["MouseID"].map(lambda x: x.replace("-", ""))
    mouse_metadata = data_table.loc[mouse_id_without_dashes == str(subject_id)]
    if mouse_metadata.empty:
        raise ValueError(f"Metadata for '{subject_id}' not found.")

    mouse_metadata = mouse_metadata.to_dict(orient="records")[0]
    date_of_birth = datetime.strptime(mouse_metadata["Date of Birth"], "%Y-%m-%d")
    return dict(
        Subject=dict(
            subject_id=mouse_metadata["MouseID"],
            date_of_birth=date_of_birth,
            sex=mouse_metadata["Sex"] if "Sex" in mouse_metadata else "U",
            genotype=mouse_metadata["Genotype"] if "Genotype" in mouse_metadata else None,
            strain=mouse_metadata["Strain"] if "Strain" in mouse_metadata else None,
            species="Mus musculus",
        ),
    )


def _get_ttl_stream_name_from_file_path(file_path: str) -> str:
    """
    Returns the TTL stream name from the file path.

    Parameters
    ----------
    file_path : str
        The file path containing the TTL stream name (e.g. 'ttlIn1', 'ttlIn2').
    """
    pattern = re.compile(r"(ttlIn1|ttlIn2)")
    # Search for the pattern in the provided string
    match = pattern.search(str(file_path))
    ttl_stream_name = match.group(0) if match else None
    if ttl_stream_name is None:
        raise ValueError(f"TTL stream name (ttlIn1, ttlIn2) not found in '{file_path}'.")

    return ttl_stream_name


def _get_indicator_from_aav_string(aav_string: str) -> str:
    """
    Returns the indicator from the AAV string.

    Parameters
    ----------
    aav_string : str
        The AAV string containing the indicator (e.g. 'pAAV-CAG-dLight1.3b (AAV5)' -> 'dLight1.3b').
    """
    pattern = re.compile(r"(dLight1\.3b|GCaMP7f|Ach3\.0|jRGECO1a|tdTomato|rDA3m)")
    # Search for the pattern in the provided string
    match = pattern.search(aav_string)
    # If a match is found, return the matched string; otherwise, return None
    indicator = match.group(0) if match else None
    if indicator is None:
        raise ValueError(
            f"Indicator (dLight1.3b, GCaMP7f, Ach3.0, jRGECO1a, tdTomato, rDA3m) not found in {aav_string}."
        )

    return indicator
