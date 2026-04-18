from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger
from .image_utils import (
    crop_image,
    decode_frame_image,
    file_sha256,
    parse_silent_face_model_name,
    softmax,
)
from .types import FaceDetectionResult

from .types import AntiSpoofEvaluation, FrameInput


class AntiSpoofEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        frames: list[FrameInput],
        face_detections: list[FaceDetectionResult] | None = None,
    ) -> AntiSpoofEvaluation:
        """Score the input stream for presentation attacks."""

    @property
    def models_ready(self) -> bool:
        return False

    @property
    def runtime_label(self) -> str:
        return "mock"


class MockAntiSpoofEvaluator(AntiSpoofEvaluator):
    def __init__(
        self,
        threshold: float = 0.35,
        hard_fail_threshold: float = 0.75,
        model_hash: str = "sha256:mock-antispoof-v1",
    ) -> None:
        self.threshold = threshold
        self.hard_fail_threshold = hard_fail_threshold
        self.model_hash = model_hash

    @property
    def models_ready(self) -> bool:
        return True

    def evaluate(
        self,
        frames: list[FrameInput],
        face_detections: list[FaceDetectionResult] | None = None,
    ) -> AntiSpoofEvaluation:
        if not frames:
            return AntiSpoofEvaluation(
                passed=False,
                spoof_score=1.0,
                max_spoof_score=1.0,
                frames_processed=0,
                flagged_frames=[],
                model_hash=self.model_hash,
                message="No frames available for anti-spoof evaluation",
            )

        scores: list[tuple[int, float]] = []
        for frame in frames:
            score = self._frame_score(frame)
            scores.append((frame.frame_index, score))

        final_score = round(sum(score for _, score in scores) / len(scores), 4)
        max_score = round(max(score for _, score in scores), 4)
        flagged_frames = [
            frame_index for frame_index, score in scores if score >= self.threshold
        ]
        passed = final_score < self.threshold and max_score < self.hard_fail_threshold
        message = (
            "Anti-spoof checks passed"
            if passed
            else f"Potential spoof indicators found in {len(flagged_frames)} frame(s)"
        )
        return AntiSpoofEvaluation(
            passed=passed,
            spoof_score=final_score,
            max_spoof_score=max_score,
            frames_processed=len(frames),
            flagged_frames=flagged_frames,
            model_hash=self.model_hash,
            message=message,
        )

    def _frame_score(self, frame: FrameInput) -> float:
        if "force_spoof_score" in frame.metadata:
            return round(float(frame.metadata["force_spoof_score"]), 4)
        if frame.metadata.get("presentation_attack") is True:
            return 0.99
        return frame.pseudo_score("antispoof", 0.02, 0.24)


@dataclass(slots=True)
class SilentFaceModelSpec:
    path: str
    input_height: int
    input_width: int
    model_type: str
    scale: float | None
    model_hash: str
    session: object


class SilentFaceOnnxEvaluator(AntiSpoofEvaluator):
    def __init__(
        self,
        *,
        model_dir: str,
        threshold: float = 0.35,
        hard_fail_threshold: float = 0.75,
    ) -> None:
        import onnxruntime as ort

        self.model_dir = Path(model_dir).expanduser().resolve()
        self.threshold = threshold
        self.hard_fail_threshold = hard_fail_threshold
        self.sessions: list[SilentFaceModelSpec] = []
        self.model_hash = "sha256:silent-face-ensemble"

        model_paths = (
            [self.model_dir]
            if self.model_dir.is_file()
            else sorted(self.model_dir.glob("*.onnx"))
        )
        if not model_paths:
            raise FileNotFoundError(f"No ONNX anti-spoof models found in {self.model_dir}")

        for model_path in model_paths:
            h_input, w_input, model_type, scale = parse_silent_face_model_name(model_path.name)
            session = ort.InferenceSession(
                str(model_path),
                providers=["CPUExecutionProvider"],
            )
            self.sessions.append(
                SilentFaceModelSpec(
                    path=str(model_path),
                    input_height=h_input,
                    input_width=w_input,
                    model_type=model_type,
                    scale=scale,
                    model_hash=file_sha256(model_path),
                    session=session,
                )
            )

        self.model_hash = "|".join(spec.model_hash for spec in self.sessions)

    @property
    def models_ready(self) -> bool:
        return True

    @property
    def runtime_label(self) -> str:
        return "silent-face-onnx"

    def evaluate(
        self,
        frames: list[FrameInput],
        face_detections: list[FaceDetectionResult] | None = None,
    ) -> AntiSpoofEvaluation:
        if not frames:
            return AntiSpoofEvaluation(
                passed=False,
                spoof_score=1.0,
                max_spoof_score=1.0,
                frames_processed=0,
                flagged_frames=[],
                model_hash=self.model_hash,
                message="No frames available for anti-spoof evaluation",
            )

        detections_by_index = {
            detection.frame_index: detection
            for detection in (face_detections or [])
        }
        scores: list[tuple[int, float]] = []

        for frame in frames:
            if "force_spoof_score" in frame.metadata:
                score = round(float(frame.metadata["force_spoof_score"]), 4)
            elif frame.metadata.get("presentation_attack") is True:
                score = 0.99
            else:
                score = self._frame_score(frame, detections_by_index.get(frame.frame_index))
            scores.append((frame.frame_index, score))

        final_score = round(sum(score for _, score in scores) / len(scores), 4)
        max_score = round(max(score for _, score in scores), 4)
        flagged_frames = [
            frame_index for frame_index, score in scores if score >= self.threshold
        ]
        passed = final_score < self.threshold and max_score < self.hard_fail_threshold
        message = (
            "Anti-spoof checks passed"
            if passed
            else f"Potential spoof indicators found in {len(flagged_frames)} frame(s)"
        )
        return AntiSpoofEvaluation(
            passed=passed,
            spoof_score=final_score,
            max_spoof_score=max_score,
            frames_processed=len(frames),
            flagged_frames=flagged_frames,
            model_hash=self.model_hash,
            message=message,
        )

    def _frame_score(
        self,
        frame: FrameInput,
        detection: FaceDetectionResult | None,
    ) -> float:
        image = decode_frame_image(frame)
        if image is None or detection is None or not detection.detected or detection.bounding_box is None:
            return 1.0

        probabilities = []
        for spec in self.sessions:
            crop = crop_image(
                image,
                detection.bounding_box,
                scale=spec.scale,
                out_w=spec.input_width,
                out_h=spec.input_height,
                crop=spec.scale is not None,
            )
            # Match the upstream Silent-Face preprocessing exactly:
            # their ToTensor path converts HWC -> CHW float without scaling to 0..1.
            model_input = crop.astype("float32")
            model_input = model_input.transpose(2, 0, 1)[None, ...]

            input_name = spec.session.get_inputs()[0].name
            outputs = spec.session.run(None, {input_name: model_input})
            logits = outputs[0]
            if logits.ndim == 4:
                logits = logits.reshape(logits.shape[0], -1)
            probs = softmax(logits.astype("float32"))[0]
            probabilities.append(probs)

        mean_probs = sum(probabilities) / len(probabilities)
        real_probability = float(mean_probs[1]) if len(mean_probs) > 1 else float(mean_probs[0])
        return round(max(0.0, min(1.0, 1.0 - real_probability)), 4)


def build_antispoof_evaluator(
    *,
    mode: str,
    model_dir: str | None,
    threshold: float,
    hard_fail_threshold: float,
) -> AntiSpoofEvaluator:
    logger = get_logger(__name__)
    selected_mode = mode.lower()

    if selected_mode == "mock":
        logger.info("Using mock anti-spoof evaluator")
        return MockAntiSpoofEvaluator(
            threshold=threshold,
            hard_fail_threshold=hard_fail_threshold,
        )

    if not model_dir:
        logger.warning("No Silent-Face model directory configured; falling back to mock evaluator")
        return MockAntiSpoofEvaluator(
            threshold=threshold,
            hard_fail_threshold=hard_fail_threshold,
        )

    try:
        evaluator = SilentFaceOnnxEvaluator(
            model_dir=model_dir,
            threshold=threshold,
            hard_fail_threshold=hard_fail_threshold,
        )
        logger.info("Loaded Silent-Face ONNX evaluator from %s", model_dir)
        return evaluator
    except Exception as exc:
        logger.warning("Could not load Silent-Face ONNX evaluator from %s: %s", model_dir, exc)
        return MockAntiSpoofEvaluator(
            threshold=threshold,
            hard_fail_threshold=hard_fail_threshold,
        )
