from ImageMixer.services.transform_explorer.actions import OperationSpec


def sanitize_apply_request(payload: dict, registry: dict[str, OperationSpec]) -> tuple[str, str, dict, int]:
    operation_id = str(payload.get("operation_id", "")).strip()
    if operation_id not in registry:
        raise ValueError("Invalid operation_id")

    domain = str(payload.get("domain", "spatial")).strip().lower()
    if domain not in ("spatial", "frequency"):
        raise ValueError("domain must be spatial or frequency")

    raw_params = payload.get("params", {})
    if raw_params is None:
        raw_params = {}
    if not isinstance(raw_params, dict):
        raise ValueError("params must be an object")

    spec = registry[operation_id]
    params = {}
    repeat_fourier_count = int(payload.get("repeat_fourier_count", 0))
    if repeat_fourier_count < 0:
        raise ValueError("repeat_fourier_count is below minimum")
    if repeat_fourier_count > 12:
        raise ValueError("repeat_fourier_count is above maximum")

    for field in spec.parameters:
        key = field["id"]
        field_type = field["type"]
        value = raw_params.get(key, field.get("default"))

        if field_type == "number":
            value = float(value)
            min_v = field.get("min")
            max_v = field.get("max")
            if min_v is not None and value < float(min_v):
                raise ValueError(f"{key} is below minimum")
            if max_v is not None and value > float(max_v):
                raise ValueError(f"{key} is above maximum")
        elif field_type == "int":
            value = int(value)
            min_v = field.get("min")
            max_v = field.get("max")
            if min_v is not None and value < int(min_v):
                raise ValueError(f"{key} is below minimum")
            if max_v is not None and value > int(max_v):
                raise ValueError(f"{key} is above maximum")
        elif field_type == "bool":
            if isinstance(value, bool):
                pass
            elif isinstance(value, str):
                lowered = value.lower().strip()
                if lowered in ("true", "1", "yes", "on"):
                    value = True
                elif lowered in ("false", "0", "no", "off"):
                    value = False
                else:
                    raise ValueError(f"{key} has invalid boolean value")
            else:
                value = bool(value)
        elif field_type == "select":
            value = str(value)
            options = field.get("options", [])
            if options and value not in options:
                raise ValueError(f"{key} has invalid option")
        else:
            raise ValueError(f"Unsupported field type: {field_type}")

        params[key] = value

    return operation_id, domain, params, repeat_fourier_count
