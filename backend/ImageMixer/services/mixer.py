import numpy as np
from typing import Callable, Optional

from ImageMixer.services.modes_enum import ComponentMode, MixMode, RegionMode


class FFTImageMixer:
    def __init__(self):
        self.current_mode = MixMode.MAGNITUDE_PHASE
        self.image_component_modes = [
            ComponentMode.MAGNITUDE,
            ComponentMode.MAGNITUDE,
            ComponentMode.MAGNITUDE,
            ComponentMode.MAGNITUDE,
        ]

    def set_mix_mode(self, mode: MixMode):
        self.current_mode = mode

    def set_image_component_mode(self, image_index: int, mode: ComponentMode):
        self.image_component_modes[image_index] = mode

    def _mask_region(self, fft_image: np.ndarray, region_mode: RegionMode, boundaries: list[int]) -> np.ndarray:
        if region_mode == RegionMode.FULL:
            return fft_image

        left, top, right, bottom = boundaries
        h, w = fft_image.shape

        left = max(0, min(int(left), w - 1))
        top = max(0, min(int(top), h - 1))
        right = max(left + 1, min(int(right), w - 1))
        bottom = max(top + 1, min(int(bottom), h - 1))

        if region_mode == RegionMode.INNER:
            mask = np.zeros_like(fft_image, dtype=np.float64)
            mask[top : bottom + 1, left : right + 1] = 1.0
        else:
            mask = np.ones_like(fft_image, dtype=np.float64)
            mask[top : bottom + 1, left : right + 1] = 0.0

        return fft_image * mask

    def _empty_mix_result(self, images) -> np.ndarray:
        for image in images:
            if image.loaded:
                return np.zeros_like(image.get_image_for_mixing(), dtype=np.float64)
        return np.zeros((1, 1), dtype=np.float64)

    def mix(
        self,
        images,
        weights: list[float],
        boundaries: list[int],
        global_region_mode: RegionMode,
        image_region_modes: Optional[list[RegionMode]] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> np.ndarray:
        if image_region_modes is None:
            image_region_modes = [RegionMode.INNER, RegionMode.INNER, RegionMode.INNER, RegionMode.INNER]

        active_indices = [
            idx for idx, image in enumerate(images)
            if image.loaded and weights[idx] > 0
        ]
        total_steps = max(1, len(active_indices))
        processed_steps = 0

        def report_progress():
            if progress_callback is not None:
                progress_callback(min(1.0, processed_steps / float(total_steps)))

        if self.current_mode == MixMode.MAGNITUDE_PHASE:
            mag_sum = None
            phase_sum = None

            for idx, image in enumerate(images):
                if not image.loaded:
                    continue
                w = weights[idx]
                if w == 0:
                    continue

                region_mode = (
                    image_region_modes[idx]
                    if global_region_mode == RegionMode.INNER_OUTER
                    else global_region_mode
                )
                fft_region = self._mask_region(image.get_mix_fft(), region_mode, boundaries)

                mag = np.abs(fft_region)
                phase = np.angle(fft_region)

                selected = self.image_component_modes[idx]
                if selected == ComponentMode.MAGNITUDE:
                    mag_sum = mag * w if mag_sum is None else mag_sum + (mag * w)
                elif selected == ComponentMode.PHASE:
                    phase_sum = phase * w if phase_sum is None else phase_sum + (phase * w)

                processed_steps += 1
                report_progress()

            if mag_sum is None and phase_sum is None:
                return self._empty_mix_result(images)

            if mag_sum is None:
                mag_sum = np.ones_like(phase_sum)
            if phase_sum is None:
                phase_sum = np.zeros_like(mag_sum)

            mixed_fft = mag_sum * np.exp(1j * phase_sum)
        else:
            real_sum = None
            imag_sum = None

            for idx, image in enumerate(images):
                if not image.loaded:
                    continue
                w = weights[idx]
                if w == 0:
                    continue

                region_mode = (
                    image_region_modes[idx]
                    if global_region_mode == RegionMode.INNER_OUTER
                    else global_region_mode
                )
                fft_region = self._mask_region(image.get_mix_fft(), region_mode, boundaries)
                real = np.real(fft_region)
                imag = np.imag(fft_region)

                selected = self.image_component_modes[idx]
                if selected == ComponentMode.REAL:
                    real_sum = real * w if real_sum is None else real_sum + (real * w)
                elif selected == ComponentMode.IMAGINARY:
                    imag_sum = imag * w if imag_sum is None else imag_sum + (imag * w)

                processed_steps += 1
                report_progress()

            if real_sum is None and imag_sum is None:
                return self._empty_mix_result(images)

            if real_sum is None:
                real_sum = np.zeros_like(imag_sum)
            if imag_sum is None:
                imag_sum = np.zeros_like(real_sum)

            mixed_fft = real_sum + 1j * imag_sum

        inv = np.fft.ifft2(np.fft.ifftshift(mixed_fft))
        return inv.real
