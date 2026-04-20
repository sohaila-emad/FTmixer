from dataclasses import dataclass
from typing import Callable

import numpy as np

from ImageMixer.services.transform_explorer.complex_helpers import (
    build_convolution_kernel,
    convolve_complex,
    repeat_fourier_transform,
    rotate_complex,
    stretch_complex,
    stretch_complex_inverse,
)


ArrayOp = Callable[[np.ndarray, dict], np.ndarray]


@dataclass
class OperationSpec:
    operation_id: str
    name: str
    description: str
    parameters: list[dict]
    apply_spatial: ArrayOp
    apply_frequency: ArrayOp


def _shift(image: np.ndarray, params: dict) -> np.ndarray:
    shift_x = int(params.get("shift_x", 0))
    shift_y = int(params.get("shift_y", 0))
    return np.roll(np.roll(image, shift_y, axis=0), shift_x, axis=1)


def _complex_exponential(image: np.ndarray, params: dict) -> np.ndarray:
    h, w = image.shape

    # Coordinates normalized to [-0.5, 0.5] so omega is image-size independent
    xx, yy = np.meshgrid(
        np.linspace(-0.5, 0.5, w, endpoint=False),
        np.linspace(-0.5, 0.5, h, endpoint=False),
    )

    omega_x = float(params.get("omega_x", 0.0))
    omega_y = float(params.get("omega_y", 0.0))
    phase = float(params.get("phase", 0.0))
    amplitude = float(params.get("amplitude", 1.0))

    phase_map = 2.0 * np.pi * (omega_x * xx + omega_y * yy) + phase
    multiplier = amplitude * np.exp(1j * phase_map)
    return image * multiplier


def _complex_exponential_spatial(image: np.ndarray, params: dict) -> np.ndarray:
    return _complex_exponential(image, params)


def _stretch(image: np.ndarray, params: dict) -> np.ndarray:
    scale_x = max(1e-6, float(params.get("scale_x", 1.0)))
    scale_y = max(1e-6, float(params.get("scale_y", 1.0)))
    return stretch_complex(image, scale_x, scale_y)


def _stretch_theorem_spatial(image: np.ndarray, params: dict) -> np.ndarray:
    """Stretch in spatial domain: direct scaling by user-specified factors."""
    scale_x = max(1e-6, float(params.get("scale_x", 1.0)))
    scale_y = max(1e-6, float(params.get("scale_y", 1.0)))
    return stretch_complex(image, scale_x, scale_y)


def _stretch_theorem_frequency(image: np.ndarray, params: dict) -> np.ndarray:
    """Stretch in frequency domain: inverse scaling by 1/a with amplitude 1/|a|²."""
    scale_x = max(1e-6, float(params.get("scale_x", 1.0)))
    scale_y = max(1e-6, float(params.get("scale_y", 1.0)))
    return stretch_complex_inverse(image, scale_x, scale_y)


def _mirror_impl(image: np.ndarray, params: dict, conjugate: bool = False) -> np.ndarray:
    """Mirror/flip operation with optional conjugation for frequency domain.
    
    Args:
        image: Complex array to mirror
        params: Contains 'axis' and 'direction' parameters
        conjugate: If True, conjugate the flipped content before concatenating (for frequency domain)
    """
    axis = str(params.get("axis", "horizontal"))
    direction = str(params.get("direction", "positive"))

    output = image

    if axis in ("horizontal", "both"):
        flipped = np.flipud(output)
        if conjugate:
            flipped = np.conj(flipped)
        if direction == "positive":
            output = np.concatenate([output, flipped], axis=0)
        elif direction == "negative":
            output = np.concatenate([flipped, output], axis=0)
        else:
            output = np.concatenate([flipped, output, flipped], axis=0)

    if axis in ("vertical", "both"):
        flipped = np.fliplr(output)
        if conjugate:
            flipped = np.conj(flipped)
        if direction == "positive":
            output = np.concatenate([output, flipped], axis=1)
        elif direction == "negative":
            output = np.concatenate([flipped, output], axis=1)
        else:
            output = np.concatenate([flipped, output, flipped], axis=1)

    return output


def _mirror(image: np.ndarray, params: dict) -> np.ndarray:
    """Mirror in spatial domain: flip without conjugation."""
    return _mirror_impl(image, params, conjugate=False)


def _mirror_frequency(image: np.ndarray, params: dict) -> np.ndarray:
    """Mirror in frequency domain: flip with conjugation (Fourier property)."""
    return _mirror_impl(image, params, conjugate=True)


def _even_odd(image: np.ndarray, params: dict) -> np.ndarray:
    mode = str(params.get("mode", "even"))
    axis = str(params.get("axis", "both"))

    result = image.copy()

    if axis in ("x", "both"):
        mirror_x = np.fliplr(result)
        if mode == "even":
            result = 0.5 * (result + mirror_x)
        else:
            result = 0.5 * (result - mirror_x)

    if axis in ("y", "both"):
        mirror_y = np.flipud(result)
        if mode == "even":
            result = 0.5 * (result + mirror_y)
        else:
            result = 0.5 * (result - mirror_y)

    return result


def _rotate(image: np.ndarray, params: dict) -> np.ndarray:
    angle = int(params.get("angle", 0))
    auto_fit = bool(params.get("auto_fit", True))
    return rotate_complex(image, float(angle), auto_fit=auto_fit)


def _differentiate(image: np.ndarray, params: dict) -> np.ndarray:
    axis = str(params.get("axis", "both"))
    order = max(1, int(params.get("order", 1)))

    result = image.copy()
    for _ in range(order):
        if axis == "x":
            result = np.gradient(result, axis=1)
        elif axis == "y":
            result = np.gradient(result, axis=0)
        else:
            dx = np.gradient(result, axis=1)
            dy = np.gradient(result, axis=0)
            result = dx + dy

    return result


def _integrate(image: np.ndarray, params: dict) -> np.ndarray:
    axis = str(params.get("axis", "both"))

    if axis == "x":
        return np.cumsum(image, axis=1)
    if axis == "y":
        return np.cumsum(image, axis=0)

    return np.cumsum(np.cumsum(image, axis=0), axis=1)


def _window_multiply(image: np.ndarray, params: dict) -> np.ndarray:
    window_type = str(params.get("window_type", "rectangular"))
    kernel = build_convolution_kernel(window_type, params)
    step_size = max(1, int(params.get("step_size", 1)))
    return convolve_complex(image, kernel, step_size)


def _fourier_repeat(image: np.ndarray, params: dict) -> np.ndarray:
    count = max(0, int(params.get("count", 1)))
    return repeat_fourier_transform(image, count)


def _operation_specs() -> list[OperationSpec]:
    base_window_params = [
        {"id": "window_type", "label": "Window Type", "type": "select", "options": ["rectangular", "gaussian", "hamming", "hanning"], "default": "rectangular"},
        {"id": "kernel_width", "label": "Kernel Width", "type": "int", "min": 1, "max": 1000, "step": 2, "default": 31},
        {"id": "kernel_height", "label": "Kernel Height", "type": "int", "min": 1, "max": 1000, "step": 2, "default": 31},
        {"id": "step_size", "label": "Step Size", "type": "int", "min": 1, "max": 1000, "step": 1, "default": 1},
        {"id": "sigma_x", "label": "Gaussian Sigma X", "type": "number", "min": 0.1, "max": 100.0, "step": 0.1, "default": 3.0, "windowTypes": ["gaussian"]},
        {"id": "sigma_y", "label": "Gaussian Sigma Y", "type": "number", "min": 0.1, "max": 100.0, "step": 0.1, "default": 3.0, "windowTypes": ["gaussian"]},
        {"id": "hamming_offset", "label": "Hamming Offset", "type": "number", "min": 0.0, "max": 1.0, "step": 0.01, "default": 0.54, "windowTypes": ["hamming"]},
    ]

    return [
        OperationSpec(
            operation_id="shift",
            name="Shift",
            description="Translate image by x/y offsets.",
            parameters=[
                {"id": "shift_x", "label": "Shift X", "type": "int", "min": -1024, "max": 1024, "step": 1, "default": 0},
                {"id": "shift_y", "label": "Shift Y", "type": "int", "min": -1024, "max": 1024, "step": 1, "default": 0},
            ],
            apply_spatial=_shift,
            apply_frequency=_shift,
        ),
        OperationSpec(
            operation_id="complex_exponential",
            name="Multiply By Complex Exponential",
            description="Multiply by A * exp(j * 2pi * (wx*x + wy*y) + phase). Coords normalised to [-0.5, 0.5].",
            parameters=[
                {"id": "amplitude", "label": "Amplitude", "type": "number", "min": 0.0, "max": 1000.0, "step": 0.01, "default": 1.0},
                {"id": "omega_x", "label": "Omega X (cycles/image)", "type": "number", "min": -100.0, "max": 100.0, "step": 0.01, "default": 0.0},
                {"id": "omega_y", "label": "Omega Y (cycles/image)", "type": "number", "min": -100.0, "max": 100.0, "step": 0.01, "default": 0.0},
                {"id": "phase", "label": "Phase (radians)", "type": "number", "min": -6.283185, "max": 6.283185, "step": 0.01, "default": 0.0},
            ],
            apply_spatial=_complex_exponential_spatial,
            apply_frequency=_complex_exponential,
        ),
        OperationSpec(
            operation_id="stretch",
            name="Stretch",
            description="Scale image by fractional or integer factors.",
            parameters=[
                {"id": "scale_x", "label": "Scale X", "type": "number", "min": 0.00001, "max": 1000.0, "step": 0.01, "default": 1.0},
                {"id": "scale_y", "label": "Scale Y", "type": "number", "min": 0.00001, "max": 1000.0, "step": 0.01, "default": 1.0},
            ],
            apply_spatial=_stretch,
            apply_frequency=_stretch,
        ),
        OperationSpec(
            operation_id="stretch_theorem",
            name="Stretch (Scaling Theorem)",
            description="Fourier scaling/similarity theorem: spatial scales by a, frequency by 1/a with amplitude 1/|a|².",
            parameters=[
                {"id": "scale_x", "label": "Scale X", "type": "number", "min": 0.00001, "max": 1000.0, "step": 0.01, "default": 1.0},
                {"id": "scale_y", "label": "Scale Y", "type": "number", "min": 0.00001, "max": 1000.0, "step": 0.01, "default": 1.0},
            ],
            apply_spatial=_stretch_theorem_spatial,
            apply_frequency=_stretch_theorem_frequency,
        ),
        OperationSpec(
            operation_id="mirror",
            name="Mirror / Symmetry Duplication",
            description="Duplicate mirrored content by axis and direction. Frequency domain applies conjugation per Fourier properties.",
            parameters=[
                {"id": "axis", "label": "Axis", "type": "select", "options": ["horizontal", "vertical", "both"], "default": "horizontal"},
                {"id": "direction", "label": "Direction", "type": "select", "options": ["positive", "negative", "both"], "default": "positive"},
            ],
            apply_spatial=_mirror,
            apply_frequency=_mirror_frequency,
        ),
        OperationSpec(
            operation_id="even_odd",
            name="Make Even/Odd",
            description="Construct even or odd image around center.",
            parameters=[
                {"id": "mode", "label": "Mode", "type": "select", "options": ["even", "odd"], "default": "even"},
                {"id": "axis", "label": "Axis", "type": "select", "options": ["x", "y", "both"], "default": "both"},
            ],
            apply_spatial=_even_odd,
            apply_frequency=_even_odd,
        ),
        OperationSpec(
            operation_id="rotate",
            name="Rotate",
            description="Rotate 0..360 degrees with auto-fit canvas.",
            parameters=[
                {"id": "angle", "label": "Angle", "type": "int", "min": 0, "max": 360, "step": 1, "default": 0},
                {"id": "auto_fit", "label": "Auto Fit", "type": "bool", "default": True},
            ],
            apply_spatial=_rotate,
            apply_frequency=_rotate,
        ),
        OperationSpec(
            operation_id="differentiate",
            name="Differentiate",
            description="Differentiate image along x/y/both.",
            parameters=[
                {"id": "axis", "label": "Axis", "type": "select", "options": ["x", "y", "both"], "default": "both"},
                {"id": "order", "label": "Order", "type": "int", "min": 1, "max": 3, "step": 1, "default": 1},
            ],
            apply_spatial=_differentiate,
            apply_frequency=_differentiate,
        ),
        OperationSpec(
            operation_id="integrate",
            name="Integrate",
            description="Integrate image along x/y/both.",
            parameters=[
                {"id": "axis", "label": "Axis", "type": "select", "options": ["x", "y", "both"], "default": "both"},
            ],
            apply_spatial=_integrate,
            apply_frequency=_integrate,
        ),
        OperationSpec(
            operation_id="window_multiply",
            name="Multiply By 2D Window",
            description="Apply sliding-window convolution using rectangular/gaussian/hamming/hanning kernel.",
            parameters=base_window_params,
            apply_spatial=_window_multiply,
            apply_frequency=_window_multiply,
        ),
        OperationSpec(
            operation_id="fourier_repeat",
            name="Repeated Fourier",
            description="Apply Fourier transform multiple times.",
            parameters=[
                {"id": "count", "label": "Count", "type": "int", "min": 1, "max": 12, "step": 1, "default": 1},
            ],
            apply_spatial=_fourier_repeat,
            apply_frequency=_fourier_repeat,
        ),
    ]


def build_operation_registry() -> dict[str, OperationSpec]:
    specs = _operation_specs()
    return {spec.operation_id: spec for spec in specs}