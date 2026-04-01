import base64
from dataclasses import dataclass

import cv2
import numpy as np


def image_to_gray_float(image: np.ndarray) -> np.ndarray:
    if image is None:
        raise ValueError("image cannot be None")

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if gray.dtype != np.float64:
        gray = gray.astype(np.float64)

    return gray


def fft2c(spatial: np.ndarray) -> np.ndarray:
    return np.fft.fftshift(np.fft.fft2(spatial))


def ifft2c(frequency: np.ndarray) -> np.ndarray:
    return np.fft.ifft2(np.fft.ifftshift(frequency))


def repeat_fourier_transform(data: np.ndarray, count: int) -> np.ndarray:
    result = data.copy()
    for _ in range(max(0, int(count))):
        result = np.fft.fftshift(np.fft.fft2(result))
    return result


def resize_complex(image: np.ndarray, width: int, height: int) -> np.ndarray:
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")

    real = cv2.resize(np.real(image), (width, height), interpolation=cv2.INTER_LINEAR)
    imag = cv2.resize(np.imag(image), (width, height), interpolation=cv2.INTER_LINEAR)
    return real + 1j * imag


def rotate_complex(image: np.ndarray, angle_degrees: float, auto_fit: bool = True) -> np.ndarray:
    h, w = image.shape
    center = (w / 2.0, h / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)

    if auto_fit:
        cos_v = abs(matrix[0, 0])
        sin_v = abs(matrix[0, 1])
        new_w = int((h * sin_v) + (w * cos_v))
        new_h = int((h * cos_v) + (w * sin_v))

        matrix[0, 2] += (new_w / 2.0) - center[0]
        matrix[1, 2] += (new_h / 2.0) - center[1]
    else:
        new_w = w
        new_h = h

    real = cv2.warpAffine(np.real(image), matrix, (new_w, new_h), flags=cv2.INTER_LINEAR)
    imag = cv2.warpAffine(np.imag(image), matrix, (new_w, new_h), flags=cv2.INTER_LINEAR)
    return real + 1j * imag


def build_window(shape: tuple[int, int], kind: str, params: dict) -> np.ndarray:
    h, w = shape
    width_ratio = float(params.get("width_ratio", 1.0))
    height_ratio = float(params.get("height_ratio", 1.0))
    center_x_ratio = float(params.get("center_x_ratio", 0.5))
    center_y_ratio = float(params.get("center_y_ratio", 0.5))

    patch_w = max(1, min(w, int(round(w * width_ratio))))
    patch_h = max(1, min(h, int(round(h * height_ratio))))

    center_x = int(round((w - 1) * center_x_ratio))
    center_y = int(round((h - 1) * center_y_ratio))

    left = max(0, min(w - patch_w, center_x - patch_w // 2))
    top = max(0, min(h - patch_h, center_y - patch_h // 2))

    full = np.zeros((h, w), dtype=np.float64)

    if kind == "rectangular":
        patch = np.ones((patch_h, patch_w), dtype=np.float64)
    elif kind == "gaussian":
        sigma_x = max(1e-6, float(params.get("sigma_x", 0.2)))
        sigma_y = max(1e-6, float(params.get("sigma_y", 0.2)))
        x = np.linspace(-1.0, 1.0, patch_w)
        y = np.linspace(-1.0, 1.0, patch_h)
        xx, yy = np.meshgrid(x, y)
        patch = np.exp(-0.5 * ((xx / sigma_x) ** 2 + (yy / sigma_y) ** 2))
    elif kind == "hamming":
        wy = np.hamming(patch_h)
        wx = np.hamming(patch_w)
        patch = np.outer(wy, wx)
    elif kind == "hanning":
        wy = np.hanning(patch_h)
        wx = np.hanning(patch_w)
        patch = np.outer(wy, wx)
    else:
        raise ValueError(f"Unsupported window type: {kind}")

    full[top : top + patch_h, left : left + patch_w] = patch
    return full


def normalize_component(component: np.ndarray, component_name: str, log_magnitude: bool) -> np.ndarray:
    name = component_name.lower()

    if name == "magnitude":
        data = np.abs(component)
        if log_magnitude:
            data = np.log1p(data)
    elif name == "phase":
        data = np.angle(component)
        data = ((data + np.pi) / (2.0 * np.pi)) * 255.0
        return np.clip(data, 0, 255).astype(np.uint8)
    elif name == "real":
        data = np.real(component)
    elif name == "imaginary":
        data = np.imag(component)
    else:
        raise ValueError(f"Unsupported component: {component_name}")

    min_v = np.min(data)
    max_v = np.max(data)
    if max_v - min_v < 1e-12:
        return np.zeros_like(data, dtype=np.uint8)

    norm = (data - min_v) * (255.0 / (max_v - min_v))
    return np.clip(norm, 0, 255).astype(np.uint8)


def numpy_to_base64(image: np.ndarray) -> str:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Failed to encode image")
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


@dataclass
class ViewportBundle:
    spatial_original: dict
    spatial_transformed: dict
    frequency_original: dict
    frequency_transformed: dict


def pack_viewport_components(spatial: np.ndarray, frequency: np.ndarray) -> dict:
    return {
        "magnitude": numpy_to_base64(normalize_component(spatial, "magnitude", log_magnitude=False)),
        "phase": numpy_to_base64(normalize_component(spatial, "phase", log_magnitude=False)),
        "real": numpy_to_base64(normalize_component(spatial, "real", log_magnitude=False)),
        "imaginary": numpy_to_base64(normalize_component(spatial, "imaginary", log_magnitude=False)),
        "frequency": {
            "magnitude": numpy_to_base64(normalize_component(frequency, "magnitude", log_magnitude=True)),
            "phase": numpy_to_base64(normalize_component(frequency, "phase", log_magnitude=False)),
            "real": numpy_to_base64(normalize_component(frequency, "real", log_magnitude=False)),
            "imaginary": numpy_to_base64(normalize_component(frequency, "imaginary", log_magnitude=False)),
        },
    }
