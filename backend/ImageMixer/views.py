import cv2
import numpy as np
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ImageMixer.serializers import (
    BrightnessContrastSerializer,
    ImageSizingSerializer,
    ImageIndexSerializer,
    ImageUploadSerializer,
    MixRequestSerializer,
    ProcessingOptionsSerializer,
    SetImageModeSerializer,
    SetMixingModeSerializer,
    numpy_to_base64,
)
from ImageMixer.services.controller import MixerController
from ImageMixer.services.modes_enum import ComponentMode, MixMode, RegionMode
from ImageMixer.services.transform_explorer.controller import TransformExplorerController

controller = MixerController()
transform_controller = TransformExplorerController()


def image_to_numpy(image_file):
    image_bytes = image_file.read()
    array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image file")
    return image


def normalize_component(component_type: str, comp: np.ndarray) -> np.ndarray:
    name = component_type.lower()
    processed = comp
    if name == "magnitude":
        processed = np.log1p(np.abs(comp))

    min_v = np.min(processed)
    max_v = np.max(processed)
    if max_v - min_v < 1e-12:
        return np.zeros_like(processed, dtype=np.uint8)

    norm = ((processed - min_v) * (255.0 / (max_v - min_v))).astype(np.uint8)
    return norm


def collect_display_images() -> list[str | None]:
    images_data = []
    for image in controller.images:
        if image.loaded:
            images_data.append(numpy_to_base64(image.get_display_image()))
        else:
            images_data.append(None)
    return images_data


@api_view(["POST"])
def upload_image(request):
    serializer = ImageUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    image_file = serializer.validated_data["image"]
    image_index = serializer.validated_data["image_index"]

    try:
        image_data = image_to_numpy(image_file)
        controller.add_image(image_data, image_index)
        controller.update_image_processing()

        image = controller.images[image_index]
        image_base64 = numpy_to_base64(image.get_display_image())

        return Response(
            {
                "success": True,
                "image_index": image_index,
                "image_data": image_base64,
                "images_data": collect_display_images(),
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def get_image(request, image_index):
    if not (0 <= int(image_index) < 4):
        return Response({"error": "Invalid image index"}, status=status.HTTP_400_BAD_REQUEST)

    image = controller.images[int(image_index)]
    if not image.loaded:
        return Response({"error": "Image not loaded"}, status=status.HTTP_400_BAD_REQUEST)

    image_base64 = numpy_to_base64(image.get_display_image())
    return Response(
        {
            "success": True,
            "image_index": int(image_index),
            "image_data": image_base64,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def get_image_component(request, image_index, component_type):
    if not (0 <= int(image_index) < 4):
        return Response({"error": "Invalid image index"}, status=status.HTTP_400_BAD_REQUEST)

    image = controller.images[int(image_index)]
    if not image.loaded:
        return Response({"error": "Image not loaded"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        comp = image.get_component(component_type, display_fft=True).T
        normalized = normalize_component(component_type, comp)
        image_base64 = numpy_to_base64(normalized)

        return Response(
            {
                "success": True,
                "image_index": int(image_index),
                "component_type": component_type,
                "image_data": image_base64,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def mix_images(request):
    serializer = MixRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        weights = serializer.validated_data["weights"]
        boundaries = serializer.validated_data["boundaries"]
        region_mode = RegionMode[serializer.validated_data["region_mode"].upper()]
        image_region_modes = [
            RegionMode[item.upper()] for item in serializer.validated_data["image_region_modes"]
        ]
        output_viewer = serializer.validated_data["output_viewer"]
        mix_mode = MixMode[serializer.validated_data["current_mode"].upper()]

        controller.set_weights(weights)
        controller.set_roi(boundaries)
        controller.set_mix_mode(mix_mode)
        controller.start_mixing_async(output_viewer, region_mode, image_region_modes)

        return Response(
            {
                "success": True,
                "status": "started",
                "output_viewer": output_viewer,
            },
            status=status.HTTP_200_OK,
        )
    except KeyError as exc:
        return Response(
            {"success": False, "error": f"Invalid mode value: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as exc:
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def get_mix_status(request):
    return Response({"success": True, **controller.get_status()}, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_mix_result(request):
    output_viewer = int(request.query_params.get("output_viewer", 0))
    if output_viewer not in (0, 1):
        return Response({"success": False, "error": "Invalid output_viewer"}, status=status.HTTP_400_BAD_REQUEST)

    result = controller.get_output(output_viewer)
    image_data = None if result is None else numpy_to_base64(result)

    return Response({"success": True, "image_data": image_data}, status=status.HTTP_200_OK)


@api_view(["POST"])
def cancel_mixing(request):
    controller.cancel_mixing()
    return Response({"success": True, "message": "Cancellation requested"}, status=status.HTTP_200_OK)


@api_view(["POST"])
def adjust_brightness_contrast(request):
    serializer = BrightnessContrastSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    image_index = serializer.validated_data["image_index"]
    brightness = serializer.validated_data["brightness"]
    contrast = serializer.validated_data["contrast"]
    include_image = serializer.validated_data.get("include_image", True)

    try:
        controller.adjust_brightness_contrast(image_index, brightness, contrast)

        payload = {"success": True, "image_index": image_index}
        if include_image:
            image = controller.images[image_index]
            payload["image_data"] = numpy_to_base64(image.get_display_image())

        return Response(
            payload,
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def reset_brightness_contrast(request):
    serializer = ImageIndexSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    image_index = serializer.validated_data["image_index"]

    try:
        controller.reset_brightness_contrast(image_index)
        image = controller.images[image_index]
        image_base64 = numpy_to_base64(image.get_display_image())
        return Response(
            {"success": True, "image_index": image_index, "image_data": image_base64},
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def set_image_mode(request):
    serializer = SetImageModeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    image_index = serializer.validated_data["image_index"]
    mode_str = serializer.validated_data["mode"].upper()

    try:
        mode = ComponentMode[mode_str]
        controller.set_image_component_mode(image_index, mode)
        return Response({"success": True}, status=status.HTTP_200_OK)
    except KeyError:
        return Response({"success": False, "error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def set_mixing_mode(request):
    serializer = SetMixingModeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    mode_str = serializer.validated_data["mode"].upper()

    try:
        mode = MixMode[mode_str]
        controller.set_mix_mode(mode)
        return Response({"success": True}, status=status.HTTP_200_OK)
    except KeyError:
        return Response({"success": False, "error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def set_image_sizing(request):
    serializer = ImageSizingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        apply_now = serializer.validated_data.get("apply_now", True)
        controller.set_image_sizing(
            policy=serializer.validated_data["policy"],
            keep_aspect_ratio=serializer.validated_data.get("keep_aspect_ratio", False),
            fixed_width=serializer.validated_data.get("fixed_width"),
            fixed_height=serializer.validated_data.get("fixed_height"),
        )
        images_data = None
        if apply_now:
            controller.update_image_processing()
            images_data = collect_display_images()

        return Response(
            {
                "success": True,
                "sizing": controller.get_sizing_config(),
                "images_data": images_data,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
def set_processing_options(request):
    serializer = ProcessingOptionsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        controller.set_processing_options(
            simulate_bottleneck=serializer.validated_data.get("simulate_bottleneck", False),
            bottleneck_seconds=serializer.validated_data.get("bottleneck_seconds", 0.0),
        )
        return Response(
            {
                "success": True,
                "processing_options": controller.get_processing_options(),
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
def partb_upload_source(request):
    image_file = request.FILES.get("image")
    if image_file is None:
        return Response(
            {"success": False, "error": "image is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        image_data = image_to_numpy(image_file)
        transform_controller.load_source(image_data)
        return Response(
            {
                "success": True,
                "viewports": transform_controller.get_viewports(),
                "meta": transform_controller.get_meta(),
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def partb_list_operations(request):
    return Response(
        {
            "success": True,
            "operations": transform_controller.list_operations(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def partb_apply_operation(request):
    payload = {
        "operation_id": request.data.get("operation_id"),
        "domain": request.data.get("domain", "spatial"),
        "params": request.data.get("params", {}),
    }

    try:
        task_id = transform_controller.start_apply_async(payload)
        return Response(
            {
                "success": True,
                "status": "started",
                "task_id": task_id,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
def partb_status(request):
    return Response(
        {
            "success": True,
            **transform_controller.get_status(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def partb_get_viewports(request):
    return Response(
        {
            "success": True,
            "viewports": transform_controller.get_viewports(),
            "meta": transform_controller.get_meta(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def partb_cancel(request):
    transform_controller.cancel()
    return Response(
        {
            "success": True,
            "message": "Part B cancellation requested",
        },
        status=status.HTTP_200_OK,
    )
