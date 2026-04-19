from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import get_settings

from .landmark_metrics import extract_landmark_metrics, inter_frame_landmark_displacement
from .types import ChallengeSignal, ChallengeType, FrameInput, LivenessEvaluation


class LivenessEvaluator(ABC):
    @abstractmethod
    def evaluate(self, challenge_type: ChallengeType, frames: list[FrameInput]) -> LivenessEvaluation:
        """Evaluate whether the requested liveness challenge completed."""


class MockLivenessEvaluator(LivenessEvaluator):
    REQUIRED_SIGNALS = {
        ChallengeType.BLINK_TWICE: 2,
        ChallengeType.TURN_LEFT: 1,
        ChallengeType.TURN_RIGHT: 1,
        ChallengeType.NOD_HEAD: 1,
        ChallengeType.SMILE: 1,
        ChallengeType.OPEN_MOUTH: 1,
    }

    @dataclass(slots=True)
    class FrameObservation:
        frame_index: int
        value: float
        detected: bool
        source: str
        closed: bool = False

    @dataclass(slots=True)
    class MotionContinuityObservation:
        enforced: bool
        passed: bool
        valid_transitions: int
        still_ratio: float
        mean_displacement: float
        message: str

    def __init__(
        self,
        *,
        blink_closed_threshold: float | None = None,
        blink_open_threshold: float | None = None,
        blink_min_closed_frames: int | None = None,
        turn_yaw_threshold_degrees: float | None = None,
        turn_offset_threshold: float | None = None,
        mouth_open_threshold: float | None = None,
        nod_pitch_threshold: float | None = None,
        nod_pitch_ratio_threshold: float | None = None,
        smile_ratio_threshold: float | None = None,
        motion_min_displacement: float | None = None,
        motion_max_still_ratio: float | None = None,
        motion_min_transitions: int | None = None,
    ) -> None:
        settings = get_settings()
        self.blink_closed_threshold = (
            blink_closed_threshold
            if blink_closed_threshold is not None
            else settings.verifier_liveness_blink_closed_threshold
        )
        self.blink_open_threshold = (
            blink_open_threshold
            if blink_open_threshold is not None
            else settings.verifier_liveness_blink_open_threshold
        )
        self.blink_min_closed_frames = (
            blink_min_closed_frames
            if blink_min_closed_frames is not None
            else settings.verifier_liveness_blink_min_closed_frames
        )
        self.turn_yaw_threshold_degrees = (
            turn_yaw_threshold_degrees
            if turn_yaw_threshold_degrees is not None
            else settings.verifier_liveness_turn_yaw_threshold_degrees
        )
        self.turn_offset_threshold = (
            turn_offset_threshold
            if turn_offset_threshold is not None
            else settings.verifier_liveness_turn_offset_threshold
        )
        self.mouth_open_threshold = (
            mouth_open_threshold
            if mouth_open_threshold is not None
            else settings.verifier_liveness_mouth_open_threshold
        )
        self.nod_pitch_threshold = (
            nod_pitch_threshold
            if nod_pitch_threshold is not None
            else settings.verifier_liveness_nod_pitch_threshold
        )
        self.nod_pitch_ratio_threshold = (
            nod_pitch_ratio_threshold
            if nod_pitch_ratio_threshold is not None
            else settings.verifier_liveness_nod_pitch_ratio_threshold
        )
        self.smile_ratio_threshold = (
            smile_ratio_threshold
            if smile_ratio_threshold is not None
            else settings.verifier_liveness_smile_ratio_threshold
        )
        self.motion_min_displacement = (
            motion_min_displacement
            if motion_min_displacement is not None
            else settings.verifier_liveness_motion_min_displacement
        )
        self.motion_max_still_ratio = (
            motion_max_still_ratio
            if motion_max_still_ratio is not None
            else settings.verifier_liveness_motion_max_still_ratio
        )
        self.motion_min_transitions = (
            motion_min_transitions
            if motion_min_transitions is not None
            else settings.verifier_liveness_motion_min_transitions
        )

    def evaluate(self, challenge_type: ChallengeType, frames: list[FrameInput]) -> LivenessEvaluation:
        required_signals = self.REQUIRED_SIGNALS[challenge_type]
        observations = [self._extract_signal(frame, challenge_type) for frame in frames]

        if challenge_type is ChallengeType.BLINK_TWICE:
            matched_signals, progress, passed, message, detected_signals = self._evaluate_blink(observations)
        elif challenge_type is ChallengeType.NOD_HEAD:
            matched_signals, progress, passed, message, detected_signals = self._evaluate_nod(observations)
        else:
            matched_signals, progress, passed, message, detected_signals = self._evaluate_single_signal(
                challenge_type,
                observations,
            )

        continuity = self._evaluate_motion_continuity(frames)
        if continuity.enforced and not continuity.passed:
            matched_signals = 0
            passed = False
            progress = round(min(progress, 0.85), 4)
            message = continuity.message
            detected_signals = []

        signal_values = [signal.value for signal in detected_signals]
        if signal_values:
            confidence = round(min(0.99, 0.55 + (sum(signal_values) / len(signal_values)) * 0.4), 4)
        else:
            confidence = round(min(progress * 0.7, 0.49), 4) if frames else 0.0

        return LivenessEvaluation(
            challenge_type=challenge_type,
            passed=passed,
            progress=progress,
            frames_processed=len(frames),
            matched_signals=matched_signals,
            required_signals=required_signals,
            confidence=confidence,
            message=message,
            detected_signals=detected_signals,
        )

    def _evaluate_motion_continuity(
        self,
        frames: list[FrameInput],
    ) -> MotionContinuityObservation:
        if len(frames) < 2:
            return self.MotionContinuityObservation(False, True, 0, 0.0, 0.0, "Waiting for natural movement")

        displacements: list[float] = []
        for previous_frame, current_frame in zip(frames, frames[1:]):
            displacement = inter_frame_landmark_displacement(previous_frame, current_frame)
            if displacement is None:
                continue
            displacements.append(displacement)

        valid_transitions = len(displacements)
        if valid_transitions < self.motion_min_transitions:
            return self.MotionContinuityObservation(
                False,
                True,
                valid_transitions,
                0.0,
                0.0,
                "Waiting for natural movement",
            )

        still_transitions = [
            displacement
            for displacement in displacements
            if displacement < self.motion_min_displacement
        ]
        still_ratio = len(still_transitions) / valid_transitions if valid_transitions else 0.0
        mean_displacement = sum(displacements) / valid_transitions if valid_transitions else 0.0
        passed = still_ratio <= self.motion_max_still_ratio
        message = (
            "Natural face movement confirmed"
            if passed
            else "Move naturally before and after the challenge"
        )
        return self.MotionContinuityObservation(
            True,
            passed,
            valid_transitions,
            round(still_ratio, 4),
            round(mean_displacement, 6),
            message,
        )

    def _extract_signal(self, frame: FrameInput, challenge_type: ChallengeType) -> FrameObservation:
        if challenge_type is ChallengeType.BLINK_TWICE:
            return self._extract_blink_signal(frame)
        if challenge_type is ChallengeType.TURN_LEFT:
            return self._extract_turn_signal(frame, direction="left")
        if challenge_type is ChallengeType.TURN_RIGHT:
            return self._extract_turn_signal(frame, direction="right")
        if challenge_type is ChallengeType.NOD_HEAD:
            return self._extract_nod_signal(frame)
        if challenge_type is ChallengeType.SMILE:
            return self._extract_smile_signal(frame)
        return self._extract_mouth_signal(frame)

    def _extract_blink_signal(self, frame: FrameInput) -> FrameObservation:
        metrics = extract_landmark_metrics(frame)
        if frame.landmarks:
            if isinstance(frame.landmarks.get("blink"), bool):
                value = 1.0 if frame.landmarks["blink"] else 0.0
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks", closed=bool(value))
            if isinstance(frame.landmarks.get("eyes_closed"), bool):
                value = 1.0 if frame.landmarks["eyes_closed"] else 0.0
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks", closed=bool(value))
            if metrics.ear is not None:
                value = self._inverse_threshold_score(
                    metrics.ear,
                    active_threshold=self.blink_closed_threshold,
                    inactive_threshold=self.blink_open_threshold,
                )
                return self.FrameObservation(
                    frame.frame_index,
                    value,
                    value >= 0.8,
                    "landmarks",
                    closed=metrics.ear <= self.blink_closed_threshold,
                )

        override = frame.metadata.get("blink")
        if override is not None:
            value = 1.0 if bool(override) else 0.0
            return self.FrameObservation(frame.frame_index, value, value >= 0.8, "metadata", closed=bool(value))

        eyes_closed = frame.get_flag("eyes_closed")
        if eyes_closed is not None:
            value = 1.0 if bool(eyes_closed) else 0.0
            return self.FrameObservation(frame.frame_index, value, value >= 0.8, "metadata", closed=bool(value))

        return self.FrameObservation(frame.frame_index, 0.0, False, "missing", closed=False)

    def _extract_turn_signal(self, frame: FrameInput, *, direction: str) -> FrameObservation:
        metrics = extract_landmark_metrics(frame)
        direction_multiplier = -1 if direction == "left" else 1

        if frame.landmarks:
            head_turn = frame.landmarks.get("head_turn")
            if head_turn in {"left", "right"}:
                value = 1.0 if head_turn == direction else 0.0
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks")
            if metrics.yaw_degrees is not None:
                directed_yaw = metrics.yaw_degrees * direction_multiplier
                value = self._threshold_score(directed_yaw, self.turn_yaw_threshold_degrees)
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks")
            if metrics.yaw_ratio is not None:
                directed_offset = metrics.yaw_ratio * direction_multiplier
                value = self._threshold_score(directed_offset, self.turn_offset_threshold)
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks")

        override = frame.metadata.get("head_turn")
        if override is not None:
            value = 1.0 if override == direction else 0.0
            return self.FrameObservation(frame.frame_index, value, value >= 0.8, "metadata")

        yaw = frame.get_flag("yaw")
        if yaw is not None:
            directed_yaw = float(yaw) * direction_multiplier
            value = self._threshold_score(directed_yaw, self.turn_yaw_threshold_degrees)
            return self.FrameObservation(frame.frame_index, value, value >= 0.8, "metadata")

        return self.FrameObservation(frame.frame_index, 0.0, False, "missing")

    def _extract_nod_signal(self, frame: FrameInput) -> FrameObservation:
        metrics = extract_landmark_metrics(frame)
        if frame.landmarks:
            pitch = frame.landmarks.get("pitch")
            if isinstance(pitch, (int, float)):
                value = float(pitch)
                return self.FrameObservation(frame.frame_index, value, abs(value) >= self.nod_pitch_threshold * 0.8, "landmarks")
            if metrics.pitch is not None:
                value = metrics.pitch
                return self.FrameObservation(frame.frame_index, value, abs(value) >= self.nod_pitch_threshold * 0.8, "landmarks")
            if metrics.pitch_ratio is not None:
                value = metrics.pitch_ratio
                return self.FrameObservation(
                    frame.frame_index,
                    value,
                    abs(value) >= self.nod_pitch_ratio_threshold * 0.8,
                    "landmarks",
                )

        pitch_override = frame.metadata.get("pitch")
        if isinstance(pitch_override, (int, float)):
            value = float(pitch_override)
            return self.FrameObservation(frame.frame_index, value, abs(value) >= self.nod_pitch_threshold * 0.8, "metadata")

        pitch_ratio_override = frame.metadata.get("pitch_ratio")
        if isinstance(pitch_ratio_override, (int, float)):
            value = float(pitch_ratio_override)
            return self.FrameObservation(
                frame.frame_index,
                value,
                abs(value) >= self.nod_pitch_ratio_threshold * 0.8,
                "metadata",
            )

        return self.FrameObservation(frame.frame_index, 0.0, False, "missing")

    def _extract_smile_signal(self, frame: FrameInput) -> FrameObservation:
        metrics = extract_landmark_metrics(frame)
        if frame.landmarks:
            smile = frame.landmarks.get("smile")
            if smile is not None:
                value = 1.0 if bool(smile) else 0.0
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks")
            if metrics.smile_ratio is not None:
                value = self._threshold_score(metrics.smile_ratio, self.smile_ratio_threshold)
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks")

        smile_override = frame.metadata.get("smile")
        if smile_override is not None:
            value = 1.0 if bool(smile_override) else 0.0
            return self.FrameObservation(frame.frame_index, value, value >= 0.8, "metadata")

        smile_ratio = frame.get_flag("smile_ratio")
        if smile_ratio is not None:
            value = self._threshold_score(float(smile_ratio), self.smile_ratio_threshold)
            return self.FrameObservation(frame.frame_index, value, value >= 0.8, "metadata")

        return self.FrameObservation(frame.frame_index, 0.0, False, "missing")

    def _extract_mouth_signal(self, frame: FrameInput) -> FrameObservation:
        metrics = extract_landmark_metrics(frame)
        if frame.landmarks:
            mouth_open = frame.landmarks.get("mouth_open")
            if mouth_open is not None:
                value = 1.0 if bool(mouth_open) else 0.0
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks")
            if metrics.mar is not None:
                value = self._threshold_score(metrics.mar, self.mouth_open_threshold)
                return self.FrameObservation(frame.frame_index, value, value >= 0.8, "landmarks")

        override = frame.metadata.get("mouth_open")
        if override is not None:
            value = 1.0 if bool(override) else 0.0
            return self.FrameObservation(frame.frame_index, value, value >= 0.8, "metadata")

        mouth_ratio = frame.get_flag("mouth_ratio")
        if mouth_ratio is not None:
            value = self._threshold_score(float(mouth_ratio), self.mouth_open_threshold)
            return self.FrameObservation(frame.frame_index, value, value >= 0.8, "metadata")

        return self.FrameObservation(frame.frame_index, 0.0, False, "missing")

    def _evaluate_blink(
        self,
        observations: list[FrameObservation],
    ) -> tuple[int, float, bool, str, list[ChallengeSignal]]:
        blink_count = 0
        closed_run = 0
        last_closed_observation: MockLivenessEvaluator.FrameObservation | None = None
        detected_signals: list[ChallengeSignal] = []

        for observation in observations:
            if observation.closed:
                closed_run += 1
                if last_closed_observation is None or observation.value >= last_closed_observation.value:
                    last_closed_observation = observation
                continue

            if closed_run >= self.blink_min_closed_frames and last_closed_observation is not None:
                blink_count += 1
                detected_signals.append(
                    ChallengeSignal(
                        name=ChallengeType.BLINK_TWICE.value,
                        value=round(last_closed_observation.value, 4),
                        detected=True,
                        frame_index=last_closed_observation.frame_index,
                        source=last_closed_observation.source,
                    )
                )
            closed_run = 0
            last_closed_observation = None

        partial_units = blink_count
        if closed_run >= self.blink_min_closed_frames:
            partial_units += 0.5
        required_signals = self.REQUIRED_SIGNALS[ChallengeType.BLINK_TWICE]
        progress = round(min(partial_units / required_signals, 1.0), 4)
        passed = blink_count >= required_signals

        if passed:
            message = self._success_message(ChallengeType.BLINK_TWICE, blink_count)
        elif not observations:
            message = "Waiting for frames"
        elif blink_count == 0 and closed_run >= self.blink_min_closed_frames:
            message = "Re-open your eyes to register the first blink"
        elif blink_count == 1 and closed_run >= self.blink_min_closed_frames:
            message = "Re-open your eyes to register the second blink"
        elif blink_count == 1:
            message = "Blink one more time"
        else:
            message = "Blink twice to continue"

        return min(blink_count, required_signals), progress, passed, message, detected_signals

    def _evaluate_nod(
        self,
        observations: list[FrameObservation],
    ) -> tuple[int, float, bool, str, list[ChallengeSignal]]:
        if not observations:
            return 0, 0.0, False, "Waiting for frames", []

        max_observation = max(observations, key=lambda item: item.value)
        min_observation = min(observations, key=lambda item: item.value)

        uses_ratio = max(abs(item.value) for item in observations) <= 1.0
        threshold = self.nod_pitch_ratio_threshold if uses_ratio else self.nod_pitch_threshold
        return_tolerance = threshold * 0.2
        has_up = max_observation.value >= threshold
        has_down = min_observation.value <= -threshold
        has_down_and_return = has_up and min_observation.value <= return_tolerance
        has_up_and_return = has_down and max_observation.value >= -return_tolerance
        range_progress = (max_observation.value - min_observation.value) / (threshold * 2) if threshold > 0 else 0.0
        peak_progress = max(abs(max_observation.value), abs(min_observation.value)) / threshold if threshold > 0 else 0.0
        progress = round(max(0.0, min(max(range_progress, peak_progress * 0.75), 1.0)), 4)
        passed = (
            (has_up and has_down) or has_down_and_return or has_up_and_return
        ) and min_observation.frame_index != max_observation.frame_index

        if passed:
            strongest = max(
                (max_observation, min_observation),
                key=lambda item: abs(item.value),
            )
            signal = ChallengeSignal(
                name=ChallengeType.NOD_HEAD.value,
                value=round(abs(strongest.value), 4),
                detected=True,
                frame_index=strongest.frame_index,
                source=strongest.source,
            )
            return 1, 1.0, True, self._success_message(ChallengeType.NOD_HEAD, 1), [signal]

        if has_down or has_up:
            message = "Bring your head back toward center to finish the nod"
        else:
            message = "Nod your head up and down"
        return 0, progress, False, message, []

    def _evaluate_single_signal(
        self,
        challenge_type: ChallengeType,
        observations: list[FrameObservation],
    ) -> tuple[int, float, bool, str, list[ChallengeSignal]]:
        required_signals = self.REQUIRED_SIGNALS[challenge_type]
        matches = [observation for observation in observations if observation.detected]
        if matches:
            best_match = max(matches, key=lambda observation: observation.value)
            signal = ChallengeSignal(
                name=challenge_type.value,
                value=round(best_match.value, 4),
                detected=True,
                frame_index=best_match.frame_index,
                source=best_match.source,
            )
            return 1, 1.0, True, self._success_message(challenge_type, 1), [signal]

        best_score = max((observation.value for observation in observations), default=0.0)
        if not observations:
            message = "Waiting for frames"
        elif challenge_type is ChallengeType.TURN_LEFT:
            message = "Turn your head left"
        elif challenge_type is ChallengeType.TURN_RIGHT:
            message = "Turn your head right"
        elif challenge_type is ChallengeType.SMILE:
            message = "Smile naturally"
        else:
            message = "Open your mouth"
        return 0, round(min(max(best_score, 0.0), 0.95), 4), False, message, []

    def _threshold_score(self, value: float, threshold: float) -> float:
        if value <= 0:
            return 0.0
        return round(min(value / threshold, 1.0), 4)

    def _inverse_threshold_score(
        self,
        value: float,
        *,
        active_threshold: float,
        inactive_threshold: float,
    ) -> float:
        if value <= active_threshold:
            return 1.0
        if value >= inactive_threshold:
            return 0.0
        span = inactive_threshold - active_threshold
        if span <= 0:
            return 0.0
        return round((inactive_threshold - value) / span, 4)

    def _success_message(self, challenge_type: ChallengeType, matched_signals: int) -> str:
        if challenge_type is ChallengeType.BLINK_TWICE:
            return f"Blink detected {matched_signals} times"
        if challenge_type is ChallengeType.TURN_LEFT:
            return "Head turn left confirmed"
        if challenge_type is ChallengeType.TURN_RIGHT:
            return "Head turn right confirmed"
        if challenge_type is ChallengeType.NOD_HEAD:
            return "Head nod confirmed"
        if challenge_type is ChallengeType.SMILE:
            return "Smile confirmed"
        return "Mouth opening confirmed"
