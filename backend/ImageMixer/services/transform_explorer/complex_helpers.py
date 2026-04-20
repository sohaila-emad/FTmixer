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


def stretch_complex(image: np.ndarray, scale_x: float, scale_y: float) -> np.ndarray:
    h, w = image.shape
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0

    matrix = np.array(
        [
            [scale_x, 0.0, (1.0 - scale_x) * cx],
            [0.0, scale_y, (1.0 - scale_y) * cy],
        ],
        dtype=np.float64,
    )

    real = cv2.warpAffine(
        np.real(image),
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    imag = cv2.warpAffine(
        np.imag(image),
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return real + 1j * imag


def stretch_complex_inverse(image: np.ndarray, scale_x: float, scale_y: float) -> np.ndarray:
    """
    Inverse stretch for frequency domain: applies scaling/similarity theorem.
    When spatial domain scales by a, frequency domain scales by 1/a with amplitude 1/|a|².
    
    Args:
        image: Complex-valued array (typically frequency domain data)
        scale_x: User-specified scale factor (will be inverted)
        scale_y: User-specified scale factor (will be inverted)
    
    Returns:
        Transformed complex array with inverse geometric scaling and amplitude correction.
    """
    h, w = image.shape
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    
    # Invert the scale factors for the other domain
    inv_scale_x = 1.0 / scale_x
    inv_scale_y = 1.0 / scale_y
    
    # Affine transformation with inverse scales
    matrix = np.array(
        [
            [inv_scale_x, 0.0, (1.0 - inv_scale_x) * cx],
            [0.0, inv_scale_y, (1.0 - inv_scale_y) * cy],
        ],
        dtype=np.float64,
    )
    
    # Apply transformation to real and imaginary parts
    real = cv2.warpAffine(
        np.real(image),
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    imag = cv2.warpAffine(
        np.imag(image),
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    
    result = real + 1j * imag
    
    # Apply amplitude scaling: 1 / (|scale_x| * |scale_y|) per Fourier scaling theorem
    amplitude_factor = 1.0 / (abs(scale_x) * abs(scale_y))
    result = result * amplitude_factor
    
    return result


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


def _ensure_odd(value: int) -> int:
    n = max(1, int(value))
    if n % 2 == 0:
        n += 1
    return n


def _custom_hamming(length: int, offset: float) -> np.ndarray:
    n = np.arange(length, dtype=np.float64)
    if length <= 1:
        return np.ones((1,), dtype=np.float64)
    return offset - (1.0 - offset) * np.cos((2.0 * np.pi * n) / (length - 1))


def build_convolution_kernel(kind: str, params: dict) -> np.ndarray:
    kernel_w = _ensure_odd(int(params.get("kernel_width", 31)))
    kernel_h = _ensure_odd(int(params.get("kernel_height", 31)))

    if kind == "rectangular":
        kernel = np.ones((kernel_h, kernel_w), dtype=np.float64)
    elif kind == "gaussian":
        sigma_x = max(1e-6, float(params.get("sigma_x", 3.0)))
        sigma_y = max(1e-6, float(params.get("sigma_y", 3.0)))
        gx = cv2.getGaussianKernel(kernel_w, sigma_x)
        gy = cv2.getGaussianKernel(kernel_h, sigma_y)
        kernel = gy @ gx.T
    elif kind == "hanning":
        wy = np.hanning(kernel_h) if kernel_h > 1 else np.ones((1,), dtype=np.float64)
        wx = np.hanning(kernel_w) if kernel_w > 1 else np.ones((1,), dtype=np.float64)
        kernel = np.outer(wy, wx)
    elif kind == "hamming":
        offset = float(params.get("hamming_offset", 0.54))
        offset = max(0.0, min(1.0, offset))
        wy = _custom_hamming(kernel_h, offset)
        wx = _custom_hamming(kernel_w, offset)
        kernel = np.outer(wy, wx)
    else:
        raise ValueError(f"Unsupported window type: {kind}")

    total = float(np.sum(kernel))
    if abs(total) < 1e-12:
        return kernel
    return kernel / total


def convolve_complex(image: np.ndarray, kernel: np.ndarray, step_size: int) -> np.ndarray:
    real = cv2.filter2D(np.real(image), ddepth=-1, kernel=kernel, borderType=cv2.BORDER_REFLECT)
    imag = cv2.filter2D(np.imag(image), ddepth=-1, kernel=kernel, borderType=cv2.BORDER_REFLECT)
    result = real + 1j * imag

    step = max(1, int(step_size))
    if step == 1:
        return result

    h, w = result.shape
    sampled = result[::step, ::step]
    up_real = cv2.resize(np.real(sampled), (w, h), interpolation=cv2.INTER_NEAREST)
    up_imag = cv2.resize(np.imag(sampled), (w, h), interpolation=cv2.INTER_NEAREST)
    return up_real + 1j * up_imag


def normalize_component(
    component: np.ndarray,
    component_name: str,
    log_magnitude: bool,
    normalize_min: float | None = None,
    normalize_max: float | None = None,
) -> np.ndarray:
    name = component_name.lower()

    if name == "magnitude":
        data = np.abs(component)
        if log_magnitude:
            data = np.log1p(data)
    elif name == "phase":
        if np.allclose(component, 0, atol=1e-8):
            return np.full(component.shape, 128, dtype=np.uint8)
        data = np.angle(component)
        data = ((data + np.pi) / (2.0 * np.pi)) * 255.0
        return np.clip(data, 0, 255).astype(np.uint8)
    elif name == "real":
        data = np.real(component)
        d_min, d_max = np.min(data), np.max(data)
        if d_max - d_min < 1e-12:
            return np.full_like(data, 128, dtype=np.uint8)
        norm = (data - d_min) * (255.0 / (d_max - d_min))
        return np.clip(norm, 0, 255).astype(np.uint8)
    elif name == "imaginary":
        data = np.imag(component)
        d_min, d_max = np.min(data), np.max(data)
        if d_max - d_min < 1e-12:
            return np.full_like(data, 128, dtype=np.uint8)
        norm = (data - d_min) * (255.0 / (d_max - d_min))
        return np.clip(norm, 0, 255).astype(np.uint8)
    else:
        raise ValueError(f"Unsupported component: {component_name}")

    if normalize_min is None or normalize_max is None:
        min_v = np.min(data)
        max_v = np.max(data)
    else:
        min_v = float(normalize_min)
        max_v = float(normalize_max)
    if max_v - min_v < 1e-12:
        return np.full(data.shape, 128, dtype=np.uint8)

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