import threading

import numpy as np

from ImageMixer.services.transform_explorer.actions import build_operation_registry
from ImageMixer.services.transform_explorer.complex_helpers import (
    fft2c,
    ifft2c,
    image_to_gray_float,
    normalize_component,
    numpy_to_base64,
)
from ImageMixer.services.transform_explorer.validators import sanitize_apply_request


class TransformExplorerController:
    def __init__(self):
        self.registry = build_operation_registry()

        self.source_spatial = None
        self.source_frequency = None
        self.transformed_spatial = None
        self.transformed_frequency = None

        self._task_lock = threading.Lock()
        self._thread = None
        self._cancel_event = threading.Event()
        self._active_task_id = 0

        self._is_processing = False
        self._progress = 0
        self._latest_error = None

    def _is_task_cancelled(self, task_id: int, cancel_event: threading.Event) -> bool:
        return cancel_event.is_set() or task_id != self._active_task_id

    def _set_progress(self, task_id: int, value: int):
        if task_id == self._active_task_id:
            self._progress = value

    def _ensure_loaded(self):
        if self.source_spatial is None:
            raise ValueError("No source image loaded")

    def load_source(self, image_data: np.ndarray):
        gray = image_to_gray_float(image_data)
        spatial = gray.astype(np.complex128)
        frequency = fft2c(spatial)

        with self._task_lock:
            self.source_spatial = spatial
            self.source_frequency = frequency
            self.transformed_spatial = spatial.copy()
            self.transformed_frequency = frequency.copy()
            self._latest_error = None
            self._is_processing = False
            self._progress = 100

    def list_operations(self) -> list[dict]:
        ops = []
        for spec in self.registry.values():
            ops.append(
                {
                    "id": spec.operation_id,
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                }
            )
        return ops

    def _apply_worker(self, task_id: int, cancel_event: threading.Event, payload: dict):
        try:
            self._set_progress(task_id, 5)
            self._ensure_loaded()
            if self._is_task_cancelled(task_id, cancel_event):
                return

            operation_id, domain, params = sanitize_apply_request(payload, self.registry)
            operation = self.registry[operation_id]

            self._set_progress(task_id, 20)
            if domain == "spatial":
                result_spatial = operation.apply_spatial(self.source_spatial.copy(), params)
                if self._is_task_cancelled(task_id, cancel_event):
                    return

                self._set_progress(task_id, 60)
                result_frequency = fft2c(result_spatial)
            else:
                result_frequency = operation.apply_frequency(self.source_frequency.copy(), params)
                if self._is_task_cancelled(task_id, cancel_event):
                    return

                self._set_progress(task_id, 60)
                result_spatial = ifft2c(result_frequency)

            if self._is_task_cancelled(task_id, cancel_event):
                return

            self._set_progress(task_id, 85)
            if task_id == self._active_task_id:
                self.transformed_spatial = result_spatial
                self.transformed_frequency = result_frequency

            self._set_progress(task_id, 100)
        except Exception as exc:
            if task_id == self._active_task_id:
                self._latest_error = str(exc)
        finally:
            if task_id == self._active_task_id:
                self._is_processing = False

    def start_apply_async(self, payload: dict) -> int:
        with self._task_lock:
            self._cancel_event.set()
            self._cancel_event = threading.Event()
            self._active_task_id += 1
            task_id = self._active_task_id

            self._progress = 0
            self._latest_error = None
            self._is_processing = True

            self._thread = threading.Thread(
                target=self._apply_worker,
                args=(task_id, self._cancel_event, payload),
                daemon=True,
            )
            self._thread.start()

            return task_id

    def cancel(self):
        with self._task_lock:
            self._cancel_event.set()
            self._active_task_id += 1
            self._is_processing = False
            self._progress = 0

    def get_status(self) -> dict:
        return {
            "is_processing": self._is_processing,
            "progress": self._progress,
            "error": self._latest_error,
            "active_task_id": self._active_task_id,
        }

    def _encode_components(self, data: np.ndarray, is_frequency: bool) -> dict:
        mag_data = np.abs(data)
        if is_frequency:
            mag_data = np.log1p(mag_data)

        mag_min = float(np.min(mag_data))
        mag_max = float(np.max(mag_data))

        if not is_frequency:
            real_data = np.real(data)
            imag_data = np.imag(data)

            # Use the real part's peak magnitude as the shared scale for both
            # components so that zero is always mid-grey (128) and real/imag
            # are directly comparable on the same axis.
            scale = max(float(np.max(np.abs(real_data))), 1e-12)
            real_img = np.clip((real_data / (2.0 * scale)) * 255 + 128, 0, 255).astype(np.uint8)
            imag_img = np.clip((imag_data / (2.0 * scale)) * 255 + 128, 0, 255).astype(np.uint8)
        else:
            real_img = normalize_component(data, "real", log_magnitude=False)
            imag_img = normalize_component(data, "imaginary", log_magnitude=False)

        return {
            "magnitude": numpy_to_base64(
                normalize_component(
                    data,
                    "magnitude",
                    log_magnitude=is_frequency,
                    normalize_min=mag_min,
                    normalize_max=mag_max,
                )
            ),
            "phase": numpy_to_base64(normalize_component(data, "phase", log_magnitude=False)),
            "real": numpy_to_base64(real_img),
            "imaginary": numpy_to_base64(imag_img),
        }

    def _encode_components_with_reference(self, data: np.ndarray, reference: np.ndarray, is_frequency: bool) -> dict:
        ref_mag = np.abs(reference)
        if is_frequency:
            ref_mag = np.log1p(ref_mag)

        mag_min = float(np.min(ref_mag))
        mag_max = float(np.max(ref_mag))

        if not is_frequency:
            real_data = np.real(data)
            imag_data = np.imag(data)

            # Anchor scale to the *reference* real peak so that:
            #   - zero is always mid-grey (128) regardless of phase rotation
            #   - real and imaginary are on the same axis
            #   - a pure pi/2 phase rotation shows: real=flat grey, imag=normal image
            #   - a tiny imaginary residual stays near mid-grey instead of self-normalising
            scale = max(float(np.max(np.abs(np.real(reference)))), 1e-12)
            real_img = np.clip((real_data / (2.0 * scale)) * 255 + 128, 0, 255).astype(np.uint8)
            imag_img = np.clip((imag_data / (2.0 * scale)) * 255 + 128, 0, 255).astype(np.uint8)
        else:
            real_img = normalize_component(data, "real", log_magnitude=False)
            imag_img = normalize_component(data, "imaginary", log_magnitude=False)

        return {
            "magnitude": numpy_to_base64(
                normalize_component(
                    data,
                    "magnitude",
                    log_magnitude=is_frequency,
                    normalize_min=mag_min,
                    normalize_max=mag_max,
                )
            ),
            "phase": numpy_to_base64(normalize_component(data, "phase", log_magnitude=False)),
            "real": numpy_to_base64(real_img),
            "imaginary": numpy_to_base64(imag_img),
        }

    def get_meta(self) -> dict:
        if self.source_spatial is None:
            return {"source_shape": None}

        h, w = self.source_spatial.shape
        return {
            "source_shape": {
                "height": int(h),
                "width": int(w),
            }
        }

    def get_viewports(self) -> dict:
        if self.source_spatial is None:
            return {
                "spatial_original": None,
                "spatial_transformed": None,
                "frequency_original": None,
                "frequency_transformed": None,
            }

        return {
            "spatial_original": self._encode_components(self.source_spatial, is_frequency=False),
            "spatial_transformed": self._encode_components_with_reference(
                self.transformed_spatial,
                self.source_spatial,
                is_frequency=False,
            ),
            "frequency_original": self._encode_components(self.source_frequency, is_frequency=True),
            "frequency_transformed": self._encode_components_with_reference(
                self.transformed_frequency,
                self.source_frequency,
                is_frequency=True,
            ),
        }