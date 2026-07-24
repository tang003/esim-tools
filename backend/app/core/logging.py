import logging
from typing import Any


SENSITIVE_KEYS = {"cookie", "authorization", "accessToken", "lpaString", "code", "mfaSignature"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if key in SENSITIVE_KEYS else redact(nested)
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

