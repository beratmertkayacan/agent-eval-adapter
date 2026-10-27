from typing import Any, Iterable

REDACTED = "[REDACTED]"
DEFAULT_SENSITIVE_FIELDS = ["apiKey", "authorization", "token", "password", "secret"]


def simplify(name: str) -> str:
    return name.lower().replace("_", "").replace("-", "")


def redact(data: Any, extra_fields: Iterable[str] = ()) -> Any:
    words = [simplify(name) for name in [*DEFAULT_SENSITIVE_FIELDS, *extra_fields]]
    return _redact(data, words)


def _redact(data: Any, words: list[str]) -> Any:
    if isinstance(data, dict):
        return {
            key: REDACTED if is_sensitive(key, words) else _redact(value, words)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [_redact(item, words) for item in data]
    return data


def is_sensitive(key: str, words: list[str]) -> bool:
    name = simplify(str(key))
    return any(word in name for word in words)
