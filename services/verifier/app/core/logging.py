from __future__ import annotations

from collections.abc import Mapping
import json
import logging
from logging.config import dictConfig
import re
from typing import Any

_KEY_VALUE_CONTEXT_ATTR = "_key_value_context"
_SAFE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._:/@+-]+$")


class CompactKeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        context = getattr(record, _KEY_VALUE_CONTEXT_ATTR, None)
        if not isinstance(context, Mapping) or not context:
            return message
        return f"{message} {_format_key_values(context)}"


class StructuredLogger(logging.LoggerAdapter[logging.Logger]):
    def bind(self, **context: Any) -> StructuredLogger:
        merged_context = dict(self.extra)
        merged_context.update(context)
        return type(self)(self.logger, merged_context)

    def kv(self, level: int, msg: str, /, *args: Any, **context: Any) -> None:
        self.log(level, msg, *args, extra={_KEY_VALUE_CONTEXT_ATTR: context})

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        context = dict(self.extra)

        call_context = kwargs.pop("context", None)
        if isinstance(call_context, Mapping):
            context.update(call_context)

        kv_context = kwargs.pop("kv", None)
        if isinstance(kv_context, Mapping):
            context.update(kv_context)

        passthrough_extra = dict(kwargs.get("extra") or {})
        explicit_context = passthrough_extra.pop(_KEY_VALUE_CONTEXT_ATTR, None)
        if isinstance(explicit_context, Mapping):
            context.update(explicit_context)
        context.update(passthrough_extra)

        if context:
            kwargs["extra"] = {
                **passthrough_extra,
                _KEY_VALUE_CONTEXT_ATTR: context,
            }
        elif passthrough_extra:
            kwargs["extra"] = passthrough_extra

        return msg, kwargs


def configure_logging(level: str = "INFO") -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": f"{__name__}.CompactKeyValueFormatter",
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": level.upper(),
            },
        }
    )


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(logging.getLogger(name), {})


def _format_key_values(context: Mapping[str, Any]) -> str:
    parts = [f"{key}={_format_value(value)}" for key, value in sorted(context.items())]
    return " ".join(parts)


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str) and _SAFE_TOKEN_PATTERN.fullmatch(value):
        return value
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), default=str)
