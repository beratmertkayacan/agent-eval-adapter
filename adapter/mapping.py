from typing import Any

MISSING = object()


def get_path(data: Any, path: str) -> Any:
    current = data
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
            current = current[int(key)]
        else:
            return MISSING
    return current


def map_response(raw: Any, mapping: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    values: dict[str, Any] = {}
    missing: list[str] = []
    for field, path in mapping.items():
        value = get_path(raw, path)
        if value is MISSING:
            missing.append(field)
            value = None
        values[field] = value
    return values, missing
