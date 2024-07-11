import numpy as np
from pymatreader import read_mat
from roiextractors import SegmentationExtractor


class Vu2024SegmentationExtractor(SegmentationExtractor):
    extractor_name = "Vu2024Segmentation"

    def __init__(self, file_path: str, sampling_frequency: float, accepted_list: list[int] = None):
        """
        Create a Vu2024SegmentationExtractor instance from a .mat file that contains the ROI locations and image masks.
        """
        super().__init__()
        self.file_path = file_path

        data = read_mat(file_path)

        self._image_masks = data["ROImasks"]  # e.g. shape of (378, 381, 103) height, width, num_rois
        self._num_rows, self._num_columns, self._num_rois = self._image_masks.shape
        self._image_size = (self._num_rows, self._num_columns)
        self._num_frames = data["F"].shape[0]

        self._roi_locations = data["ROIs"].transpose()  # e.g. shape of (103, 2) num_rois, (x, y)

        if accepted_list is None:
            accepted_list = list(range(self._num_rois))
        self._accepted_list = accepted_list
        self._rejected_list = [i for i in range(self._num_rois) if i not in self._accepted_list]

        self._sampling_frequency = sampling_frequency
        self._times = None

    def get_num_frames(self) -> int:
        return self._num_frames

    def get_accepted_list(self) -> list[int]:
        return self._accepted_list

    def get_rejected_list(self) -> list[int]:
        return self._rejected_list

    def get_image_size(self) -> tuple[int, int]:
        return self._image_size

    def get_roi_ids(self) -> list:
        return list(range(self.get_num_rois()))

    def get_num_rois(self) -> int:
        return self._num_rois

    def get_roi_locations(self, roi_ids=None) -> np.ndarray:
        if roi_ids is None:
            return self._roi_locations
        else:
            return self._roi_locations[roi_ids]

    def get_roi_image_masks(self, roi_ids=None) -> np.ndarray:
        if roi_ids is None:
            return self._image_masks
        else:
            return self._image_masks[:, :, roi_ids]
