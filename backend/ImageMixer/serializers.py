import base64
import cv2
import numpy as np
from rest_framework import serializers


class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    image_index = serializers.IntegerField(min_value=0, max_value=3)


class MixRequestSerializer(serializers.Serializer):
    weights = serializers.ListField(
        child=serializers.FloatField(min_value=0, max_value=100),
        min_length=4,
        max_length=4,
    )
    boundaries = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=4,
        max_length=4,
    )
    region_mode = serializers.CharField(default="FULL")
    image_region_modes = serializers.ListField(
        child=serializers.CharField(),
        min_length=4,
        max_length=4,
        required=False,
        default=["INNER", "INNER", "INNER", "INNER"],
    )
    output_viewer = serializers.IntegerField(min_value=0, max_value=1, default=0)
    current_mode = serializers.CharField(default="MAGNITUDE_PHASE")


class BrightnessContrastSerializer(serializers.Serializer):
    image_index = serializers.IntegerField(min_value=0, max_value=3)
    brightness = serializers.FloatField(min_value=-255, max_value=255)
    contrast = serializers.FloatField(min_value=-0.9, max_value=3.0)
    include_image = serializers.BooleanField(required=False, default=True)


class ImageIndexSerializer(serializers.Serializer):
    image_index = serializers.IntegerField(min_value=0, max_value=3)


class SetImageModeSerializer(serializers.Serializer):
    image_index = serializers.IntegerField(min_value=0, max_value=3)
    mode = serializers.CharField()


class SetMixingModeSerializer(serializers.Serializer):
    mode = serializers.CharField()


def numpy_to_base64(image: np.ndarray) -> str:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Failed to encode image")
    return base64.b64encode(encoded.tobytes()).decode("utf-8")
