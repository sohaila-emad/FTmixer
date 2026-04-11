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


class ImageSizingSerializer(serializers.Serializer):
    policy = serializers.ChoiceField(choices=["smallest", "largest", "fixed"], default="smallest")
    keep_aspect_ratio = serializers.BooleanField(required=False, default=False)
    fixed_width = serializers.IntegerField(required=False, min_value=1)
    fixed_height = serializers.IntegerField(required=False, min_value=1)
    apply_now = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        policy = attrs.get("policy", "smallest")
        if policy == "fixed":
            if attrs.get("fixed_width") is None or attrs.get("fixed_height") is None:
                raise serializers.ValidationError("fixed_width and fixed_height are required for fixed policy")
        return attrs


class ProcessingOptionsSerializer(serializers.Serializer):
    simulate_bottleneck = serializers.BooleanField(required=False, default=False)
    bottleneck_seconds = serializers.FloatField(required=False, default=0.0, min_value=0.0, max_value=10.0)


def numpy_to_base64(image: np.ndarray) -> str:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Failed to encode image")
    return base64.b64encode(encoded.tobytes()).decode("utf-8")
