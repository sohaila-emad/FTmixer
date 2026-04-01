import threading

import cv2
import numpy as np

from ImageMixer.services.custom_image import CustomImage
from ImageMixer.services.mixer import FFTImageMixer
from ImageMixer.services.modes_enum import ComponentMode, MixMode, RegionMode


class MixerController:
    def __init__(self):
        self.images = [CustomImage(), CustomImage(), CustomImage(), CustomImage()]
        self.outputs = [None, None]
        self.weights = [0.0, 0.0, 0.0, 0.0]
        self.roi = [0, 0, 100, 100]

        self.mixer = FFTImageMixer()

        self._task_lock = threading.Lock()
        self._thread = None
        self._cancel_event = threading.Event()
        self._active_task_id = 0

        self._is_mixing = False
        self._progress = 0
        self._latest_error = None

    def _is_task_cancelled(self, task_id: int, cancel_event: threading.Event) -> bool:
        return cancel_event.is_set() or task_id != self._active_task_id

    def _set_progress(self, task_id: int, value: int):
        if task_id == self._active_task_id:
            self._progress = value

    def add_image(self, image_data: np.ndarray, image_index: int):
        self.images[image_index] = CustomImage(image_data)

    def set_roi(self, boundaries: list[int]):
        self.roi = [int(v) for v in boundaries]

    def set_mix_mode(self, mode: MixMode):
        self.mixer.set_mix_mode(mode)

    def set_image_component_mode(self, image_index: int, mode: ComponentMode):
        self.mixer.set_image_component_mode(image_index, mode)

    def set_weights(self, weights: list[float]):
        self.weights = [float(v) for v in weights]

    def _get_min_size(self):
        loaded = [img for img in self.images if img.loaded]
        if not loaded:
            return None

        heights = [img.get_image_for_mixing().shape[0] for img in loaded]
        widths = [img.get_image_for_mixing().shape[1] for img in loaded]
        return min(heights), min(widths)

    def update_image_processing(self):
        min_size = self._get_min_size()
        if min_size is None:
            return

        h, w = min_size
        for image in self.images:
            if image.loaded:
                image.resize(h, w)

    def adjust_brightness_contrast(self, image_index: int, brightness: float, contrast: float):
        self.images[image_index].adjust_brightness_contrast(brightness, contrast)

    def reset_brightness_contrast(self, image_index: int):
        self.images[image_index].reset_brightness_contrast()

    def _mix_worker(
        self,
        task_id: int,
        cancel_event: threading.Event,
        output_viewer: int,
        region_mode: RegionMode,
        image_region_modes: list[RegionMode],
    ):
        try:
            self._set_progress(task_id, 5)
            self.update_image_processing()
            if self._is_task_cancelled(task_id, cancel_event):
                return

            loaded_count = sum(1 for image in self.images if image.loaded)
            if loaded_count == 0:
                if task_id == self._active_task_id:
                    self.outputs[output_viewer] = None
                    self._set_progress(task_id, 100)
                return

            self._set_progress(task_id, 20)
            normalized = [v / 100.0 for v in self.weights]

            if sum(normalized) == 0:
                if task_id == self._active_task_id:
                    self.outputs[output_viewer] = None
                    self._set_progress(task_id, 100)
                return

            mixed = self.mixer.mix(self.images, normalized, self.roi, region_mode, image_region_modes)
            if self._is_task_cancelled(task_id, cancel_event):
                return

            self._set_progress(task_id, 75)
            if task_id == self._active_task_id:
                if np.max(np.abs(mixed)) < 1e-10:
                    self.outputs[output_viewer] = None
                else:
                    normalized_img = cv2.normalize(mixed, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                    self.outputs[output_viewer] = normalized_img

            self._set_progress(task_id, 100)
        except Exception as exc:
            if task_id == self._active_task_id:
                self._latest_error = str(exc)
        finally:
            if task_id == self._active_task_id:
                self._is_mixing = False

    def start_mixing_async(
        self,
        output_viewer: int,
        region_mode: RegionMode,
        image_region_modes: list[RegionMode],
    ):
        with self._task_lock:
            self._cancel_event.set()
            self._cancel_event = threading.Event()
            self._active_task_id += 1
            task_id = self._active_task_id

            self._progress = 0
            self._latest_error = None
            self._is_mixing = True

            self._thread = threading.Thread(
                target=self._mix_worker,
                args=(task_id, self._cancel_event, output_viewer, region_mode, image_region_modes),
                daemon=True,
            )
            self._thread.start()

    def cancel_mixing(self):
        with self._task_lock:
            self._cancel_event.set()
            self._active_task_id += 1
            self._is_mixing = False
            self._progress = 0

    def get_status(self):
        return {
            "is_mixing": self._is_mixing,
            "progress": self._progress,
            "error": self._latest_error,
        }

    def get_output(self, output_viewer: int):
        return self.outputs[output_viewer]
