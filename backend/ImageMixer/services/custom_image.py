import cv2
import numpy as np


class CustomImage:
    def __init__(self, image=None):
        self.loaded = False
        self._source_gray = None
        self._mix_image = None

        self._display_brightness = 0.0
        self._display_contrast = 0.0

        self._mix_fft = None
        self._display_fft = None

        if image is not None:
            self.set_source(image)

    def set_source(self, image: np.ndarray):
        if image is None:
            raise ValueError("image cannot be None")

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if gray.dtype != np.uint8:
            gray = np.clip(gray, 0, 255).astype(np.uint8)

        self._source_gray = gray
        self._mix_image = gray.copy()
        self.loaded = True
        self._invalidate_fft_cache()
        self._compute_mix_fft()

    def _invalidate_fft_cache(self):
        self._mix_fft = None
        self._display_fft = None

    def resize(self, height: int, width: int, keep_aspect_ratio: bool = False):
        if not self.loaded:
            return
        if height <= 0 or width <= 0:
            raise ValueError("height and width must be positive")

        if not keep_aspect_ratio:
            interpolation = cv2.INTER_AREA if (height < self._source_gray.shape[0] or width < self._source_gray.shape[1]) else cv2.INTER_LINEAR
            self._mix_image = cv2.resize(self._source_gray, (width, height), interpolation=interpolation)
        else:
            src_h, src_w = self._source_gray.shape[:2]
            scale = min(width / float(src_w), height / float(src_h))
            new_w = max(1, int(round(src_w * scale)))
            new_h = max(1, int(round(src_h * scale)))
            interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            resized = cv2.resize(self._source_gray, (new_w, new_h), interpolation=interpolation)

            canvas = np.zeros((height, width), dtype=np.uint8)
            top = (height - new_h) // 2
            left = (width - new_w) // 2
            canvas[top : top + new_h, left : left + new_w] = resized
            self._mix_image = canvas

        self._invalidate_fft_cache()
        self._compute_mix_fft()

    def _compute_mix_fft(self):
        if not self.loaded:
            return
        self._mix_fft = np.fft.fftshift(np.fft.fft2(self._mix_image))

    def _compute_display_fft(self):
        if not self.loaded:
            return
        display = self.get_display_image()
        self._display_fft = np.fft.fftshift(np.fft.fft2(display))

    def adjust_brightness_contrast(self, brightness: float, contrast: float):
        self._display_brightness = float(brightness)
        self._display_contrast = float(contrast)
        self._display_fft = None

    def reset_brightness_contrast(self):
        self._display_brightness = 0.0
        self._display_contrast = 0.0
        self._display_fft = None

    def get_display_image(self) -> np.ndarray:
        if not self.loaded:
            raise ValueError("image is not loaded")

        alpha = max(0.1, 1.0 + self._display_contrast)
        beta = self._display_brightness
        return cv2.convertScaleAbs(self._mix_image, alpha=alpha, beta=beta)

    def get_image_for_mixing(self) -> np.ndarray:
        if not self.loaded:
            raise ValueError("image is not loaded")
        return self._mix_image

    def get_mix_fft(self) -> np.ndarray:
        if self._mix_fft is None:
            self._compute_mix_fft()
        return self._mix_fft

    def get_display_fft(self) -> np.ndarray:
        if self._display_fft is None:
            self._compute_display_fft()
        return self._display_fft

    def get_component(self, component_type: str, display_fft: bool = True) -> np.ndarray:
        source_fft = self.get_display_fft() if display_fft else self.get_mix_fft()
        name = component_type.lower()

        if name == "magnitude":
            return np.abs(source_fft)
        if name == "phase":
            return np.angle(source_fft)
        if name == "real":
            return np.real(source_fft)
        if name == "imaginary":
            return np.imag(source_fft)

        raise ValueError(f"Unsupported component type: {component_type}")
