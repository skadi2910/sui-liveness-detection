from __future__ import annotations

from app.pipeline.deepfake import DisabledDeepfakeEvaluator, MockDeepfakeEvaluator
from app.pipeline.types import FaceBoundingBox, FaceDetectionResult, FrameInput


def test_disabled_deepfake_evaluator_returns_non_enforced_result() -> None:
    evaluator = DisabledDeepfakeEvaluator()

    result = evaluator.evaluate([])

    assert result.enabled is False
    assert result.enforced is False
    assert result.passed is True
    assert result.deepfake_score is None
    assert result.max_deepfake_score is None


def test_mock_deepfake_evaluator_uses_forced_score_and_threshold() -> None:
    evaluator = MockDeepfakeEvaluator(threshold=0.65, enforce_decision=True)
    frame = FrameInput(
        frame_index=3,
        metadata={"force_deepfake_score": 0.83},
    )
    detection = FaceDetectionResult(
        detected=True,
        confidence=0.9,
        frame_index=3,
        bounding_box=FaceBoundingBox(x=10, y=10, width=120, height=120),
    )

    result = evaluator.evaluate([frame], [detection], max_samples=1)

    assert result.enabled is True
    assert result.enforced is True
    assert result.passed is False
    assert result.deepfake_score == 0.83
    assert result.max_deepfake_score == 0.83
    assert result.flagged_frames == [3]
