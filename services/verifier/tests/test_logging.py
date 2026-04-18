from __future__ import annotations

from io import StringIO
import logging

from app.core.logging import CompactKeyValueFormatter, StructuredLogger, get_logger


def _build_logger(name: str) -> tuple[StructuredLogger, StringIO]:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(CompactKeyValueFormatter("%(levelname)s %(name)s %(message)s"))

    base_logger = logging.getLogger(name)
    base_logger.handlers = [handler]
    base_logger.propagate = False
    base_logger.setLevel(logging.INFO)

    return StructuredLogger(base_logger, {}), stream


def test_structured_logger_formats_bound_and_per_call_context() -> None:
    logger, stream = _build_logger("tests.logging.bound")

    logger.bind(session_id="sess_123", lane="verification").info(
        "step advanced",
        context={
            "challenge_sequence": ["blink_twice", "turn_right"],
            "current_challenge_index": 1,
        },
    )

    assert (
        stream.getvalue().strip()
        == "INFO tests.logging.bound step advanced challenge_sequence=[\"blink_twice\",\"turn_right\"] "
        "current_challenge_index=1 lane=verification session_id=sess_123"
    )


def test_structured_logger_merges_extra_fields_into_compact_output() -> None:
    logger, stream = _build_logger("tests.logging.extra")

    logger.info(
        "terminal result",
        extra={
            "session_id": "sess_final",
            "status": "failed",
            "human": False,
            "failure_reason": "spoof_detected",
        },
    )

    assert (
        stream.getvalue().strip()
        == "INFO tests.logging.extra terminal result failure_reason=spoof_detected human=false "
        "session_id=sess_final status=failed"
    )


def test_get_logger_returns_structured_logger_adapter() -> None:
    logger = get_logger("tests.logging.factory")

    assert isinstance(logger, StructuredLogger)
