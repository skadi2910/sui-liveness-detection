from __future__ import annotations

from app.pipeline.liveness import MockLivenessEvaluator
from app.pipeline.types import ChallengeType, FrameInput


def _landmark_frame(
    frame_index: int,
    *,
    x_offset: float,
    y_offset: float = 0.0,
    head_turn: str = "left",
) -> FrameInput:
    return FrameInput(
        frame_index=frame_index,
        landmarks={
            "head_turn": head_turn,
            "nose_tip_x": 0.50 + x_offset,
            "nose_tip_y": 0.44 + y_offset,
            "left_eye_outer_x": 0.38 + x_offset,
            "left_eye_outer_y": 0.40 + y_offset,
            "right_eye_outer_x": 0.62 + x_offset,
            "right_eye_outer_y": 0.40 + y_offset,
            "mouth_left_x": 0.43 + x_offset,
            "mouth_left_y": 0.58 + y_offset,
            "mouth_right_x": 0.57 + x_offset,
            "mouth_right_y": 0.58 + y_offset,
        },
    )


def test_motion_continuity_allows_natural_turn_sequence() -> None:
    evaluator = MockLivenessEvaluator(
        motion_min_displacement=0.002,
        motion_max_still_ratio=0.8,
        motion_min_transitions=4,
    )
    frames = [
        _landmark_frame(0, x_offset=0.0000, y_offset=0.0000),
        _landmark_frame(1, x_offset=0.0035, y_offset=0.0010),
        _landmark_frame(2, x_offset=0.0010, y_offset=-0.0015),
        _landmark_frame(3, x_offset=0.0055, y_offset=0.0015),
        _landmark_frame(4, x_offset=0.0020, y_offset=-0.0020),
    ]

    result = evaluator.evaluate(ChallengeType.TURN_LEFT, frames)

    assert result.passed is True
    assert result.progress == 1.0
    assert result.message == "Head turn left confirmed"


def test_motion_continuity_blocks_replay_like_static_frames() -> None:
    evaluator = MockLivenessEvaluator(
        motion_min_displacement=0.002,
        motion_max_still_ratio=0.8,
        motion_min_transitions=4,
    )
    frames = [_landmark_frame(index, x_offset=0.0, y_offset=0.0) for index in range(5)]

    result = evaluator.evaluate(ChallengeType.TURN_LEFT, frames)

    assert result.passed is False
    assert result.progress == 0.85
    assert result.message == "Move naturally before and after the challenge"
    assert result.detected_signals == []


def test_motion_continuity_skips_enforcement_when_landmark_positions_are_missing() -> None:
    evaluator = MockLivenessEvaluator(
        motion_min_displacement=0.002,
        motion_max_still_ratio=0.8,
        motion_min_transitions=4,
    )
    frames = [
        FrameInput(frame_index=index, metadata={"head_turn": "left"})
        for index in range(5)
    ]

    result = evaluator.evaluate(ChallengeType.TURN_LEFT, frames)

    assert result.passed is True
    assert result.progress == 1.0
    assert result.message == "Head turn left confirmed"
