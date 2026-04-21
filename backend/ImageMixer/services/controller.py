import threading
import time

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

        self._size_policy = "smallest"
        self._keep_aspect_ratio = False
        self._fixed_size = (512, 512)

        self._simulate_bottleneck = False
        self._bottleneck_seconds = 0.0

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

    def _get_target_size(self):
        loaded = [img for img in self.images if img.loaded]
        if not loaded:
            return None

        if self._size_policy == "fixed":
            return self._fixed_size

        source_sizes = [img.get_source_size() for img in loaded]

        # Keep a real source aspect ratio by selecting one source size, instead of
        # combining min/max height and width from different images.
        if self._size_policy == "largest":
            return max(source_sizes, key=lambda size: size[0] * size[1])
        return min(source_sizes, key=lambda size: size[0] * size[1])

    def set_image_sizing(
        self,
        policy: str,
        keep_aspect_ratio: bool,
        fixed_width: int | None = None,
        fixed_height: int | None = None,
    ):
        normalized = str(policy).lower().strip()
        if normalized not in ("smallest", "largest", "fixed"):
            raise ValueError("policy must be one of smallest, largest, fixed")

        if normalized == "fixed":
            if fixed_width is None or fixed_height is None:
                raise ValueError("fixed width and height are required for fixed policy")
            if fixed_width <= 0 or fixed_height <= 0:
                raise ValueError("fixed width and height must be positive")
            self._fixed_size = (int(fixed_height), int(fixed_width))

        self._size_policy = normalized
        self._keep_aspect_ratio = bool(keep_aspect_ratio)

    def set_processing_options(self, simulate_bottleneck: bool, bottleneck_seconds: float):
        seconds = float(bottleneck_seconds)
        if seconds < 0.0:
            raise ValueError("bottleneck_seconds must be non-negative")
        self._simulate_bottleneck = bool(simulate_bottleneck)
        self._bottleneck_seconds = seconds

    def update_image_processing(self):
        target_size = self._get_target_size()
        if target_size is None:
            return

        h, w = target_size
        for image in self.images:
            if image.loaded:
                image.resize(h, w, keep_aspect_ratio=self._keep_aspect_ratio)

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

            if self._simulate_bottleneck and self._bottleneck_seconds > 0.0:
                steps = max(1, int(round(self._bottleneck_seconds / 0.1)))
                sleep_interval = self._bottleneck_seconds / float(steps)
                for step in range(steps):
                    if self._is_task_cancelled(task_id, cancel_event):
                        return
                    time.sleep(sleep_interval)
                    simulated = 20 + int(((step + 1) * 30) / steps)
                    self._set_progress(task_id, simulated)

            normalized = [v / 100.0 for v in self.weights]

            if sum(normalized) == 0:
                if task_id == self._active_task_id:
                    self.outputs[output_viewer] = None
                    self._set_progress(task_id, 100)
                return

            mixed = self.mixer.mix(
                self.images,
                normalized,
                self.roi,
                region_mode,
                image_region_modes,
                progress_callback=lambda fraction: self._set_progress(task_id, 50 + int(fraction * 25)),
            )
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

    def get_sizing_config(self):
        return {
            "policy": self._size_policy,
            "keep_aspect_ratio": self._keep_aspect_ratio,
            "fixed_width": self._fixed_size[1],
            "fixed_height": self._fixed_size[0],
        }

    def get_processing_options(self):
        return {
            "simulate_bottleneck": self._simulate_bottleneck,
            "bottleneck_seconds": self._bottleneck_seconds,
        }

    def get_output(self, output_viewer: int):
        return self.outputs[output_viewer]
