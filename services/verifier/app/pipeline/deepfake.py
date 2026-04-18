from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from pathlib import Path

import cv2
import numpy as np

from app.core.logging import get_logger

from .image_utils import crop_image, decode_frame_image, file_sha256, softmax
from .types import DeepfakeEvaluation, FaceDetectionResult, FrameInput


class DeepfakeEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        frames: list[FrameInput],
        face_detections: list[FaceDetectionResult] | None = None,
        *,
        max_samples: int = 6,
    ) -> DeepfakeEvaluation:
        """Score accepted face crops for synthetic-generation indicators."""

    @property
    def models_ready(self) -> bool:
        return False

    @property
    def runtime_label(self) -> str:
        return "disabled"

    @property
    def enabled(self) -> bool:
        return False

    @property
    def model_hash(self) -> str | None:
        return None


class DisabledDeepfakeEvaluator(DeepfakeEvaluator):
    def evaluate(
        self,
        frames: list[FrameInput],
        face_detections: list[FaceDetectionResult] | None = None,
        *,
        max_samples: int = 6,
    ) -> DeepfakeEvaluation:
        return DeepfakeEvaluation(
            enabled=False,
            enforced=False,
            passed=True,
            deepfake_score=None,
            max_deepfake_score=None,
            frames_processed=0,
            flagged_frames=[],
            model_hash=None,
            message="Deepfake scoring disabled",
        )


class MockDeepfakeEvaluator(DeepfakeEvaluator):
    def __init__(
        self,
        *,
        threshold: float = 0.65,
        enforce_decision: bool = False,
        model_hash: str = "sha256:mock-deepfake-v1",
    ) -> None:
        self.threshold = threshold
        self.enforce_decision = enforce_decision
        self._model_hash = model_hash

    @property
    def enabled(self) -> bool:
        return True

    @property
    def models_ready(self) -> bool:
        return True

    @property
    def runtime_label(self) -> str:
        return "mock"

    @property
    def model_hash(self) -> str | None:
        return self._model_hash

    def evaluate(
        self,
        frames: list[FrameInput],
        face_detections: list[FaceDetectionResult] | None = None,
        *,
        max_samples: int = 6,
    ) -> DeepfakeEvaluation:
        sampled = _sample_frames(frames, max_samples=max_samples)
        if not sampled:
            return DeepfakeEvaluation(
                enabled=True,
                enforced=self.enforce_decision,
                passed=True,
                deepfake_score=None,
                max_deepfake_score=None,
                frames_processed=0,
                flagged_frames=[],
                model_hash=self._model_hash,
                message="No accepted frames available for deepfake scoring",
            )

        scores: list[tuple[int, float]] = []
        for frame in sampled:
            if "force_deepfake_score" in frame.metadata:
                score = round(float(frame.metadata["force_deepfake_score"]), 4)
            elif frame.metadata.get("synthetic_attack") is True:
                score = 0.99
            else:
                score = frame.pseudo_score("deepfake", 0.02, 0.42)
            scores.append((frame.frame_index, score))

        return _build_evaluation(
            scores=scores,
            threshold=self.threshold,
            enforce_decision=self.enforce_decision,
            model_hash=self._model_hash,
        )


@dataclass(slots=True)
class DeepfakeModelSpec:
    path: str
    input_height: int
    input_width: int
    input_name: str
    output_name: str
    model_hash: str
    session: object
    image_mean: tuple[float, float, float]
    image_std: tuple[float, float, float]
    deepfake_index: int


class OnnxDeepfakeEvaluator(DeepfakeEvaluator):
    def __init__(
        self,
        *,
        model_path: str,
        threshold: float = 0.65,
        enforce_decision: bool = False,
    ) -> None:
        import onnxruntime as ort

        resolved = Path(model_path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Deepfake model not found at {resolved}")

        session = ort.InferenceSession(str(resolved), providers=["CPUExecutionProvider"])
        input_meta = session.get_inputs()[0]
        output_meta = session.get_outputs()[0]
        input_shape = list(input_meta.shape)

        if len(input_shape) != 4:
            raise ValueError(f"Unexpected deepfake model input shape: {input_shape}")

        input_height = _shape_dim_to_int(input_shape[2], default=224)
        input_width = _shape_dim_to_int(input_shape[3], default=224)
        image_mean, image_std = _load_preprocessor_stats(resolved)
        deepfake_index = _load_deepfake_label_index(resolved)

        self.threshold = threshold
        self.enforce_decision = enforce_decision
        self.spec = DeepfakeModelSpec(
            path=str(resolved),
            input_height=input_height,
            input_width=input_width,
            input_name=input_meta.name,
            output_name=output_meta.name,
            model_hash=file_sha256(resolved),
            session=session,
            image_mean=image_mean,
            image_std=image_std,
            deepfake_index=deepfake_index,
        )

    @property
    def enabled(self) -> bool:
        return True

    @property
    def models_ready(self) -> bool:
        return True

    @property
    def runtime_label(self) -> str:
        return "onnx-image"

    @property
    def model_hash(self) -> str | None:
        return self.spec.model_hash

    def evaluate(
        self,
        frames: list[FrameInput],
        face_detections: list[FaceDetectionResult] | None = None,
        *,
        max_samples: int = 6,
    ) -> DeepfakeEvaluation:
        sampled = _sample_frames(frames, max_samples=max_samples)
        if not sampled:
            return DeepfakeEvaluation(
                enabled=True,
                enforced=self.enforce_decision,
                passed=True,
                deepfake_score=None,
                max_deepfake_score=None,
                frames_processed=0,
                flagged_frames=[],
                model_hash=self.spec.model_hash,
                message="No accepted frames available for deepfake scoring",
            )

        detections_by_index = {
            detection.frame_index: detection
            for detection in (face_detections or [])
        }

        scores: list[tuple[int, float]] = []
        for frame in sampled:
            if "force_deepfake_score" in frame.metadata:
                score = round(float(frame.metadata["force_deepfake_score"]), 4)
            elif frame.metadata.get("synthetic_attack") is True:
                score = 0.99
            else:
                score = self._frame_score(frame, detections_by_index.get(frame.frame_index))
            scores.append((frame.frame_index, score))

        return _build_evaluation(
            scores=scores,
            threshold=self.threshold,
            enforce_decision=self.enforce_decision,
            model_hash=self.spec.model_hash,
        )

    def _frame_score(
        self,
        frame: FrameInput,
        detection: FaceDetectionResult | None,
    ) -> float:
        image = decode_frame_image(frame)
        if image is None or detection is None or not detection.detected or detection.bounding_box is None:
            return 0.5

        crop = crop_image(
            image,
            detection.bounding_box,
            scale=1.4,
            out_w=self.spec.input_width,
            out_h=self.spec.input_height,
        )
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype("float32") / 255.0
        mean = np.asarray(self.spec.image_mean, dtype="float32").reshape(1, 1, 3)
        std = np.asarray(self.spec.image_std, dtype="float32").reshape(1, 1, 3)
        rgb = (rgb - mean) / np.clip(std, 1e-6, None)
        model_input = rgb.transpose(2, 0, 1)[None, ...]
        outputs = self.spec.session.run(
            [self.spec.output_name],
            {self.spec.input_name: model_input},
        )
        return round(
            _extract_fake_probability(
                np.asarray(outputs[0], dtype="float32"),
                deepfake_index=self.spec.deepfake_index,
            ),
            4,
        )


def _sample_frames(frames: list[FrameInput], *, max_samples: int) -> list[FrameInput]:
    if not frames:
        return []

    bounded = max(1, max_samples)
    if len(frames) <= bounded:
        return list(frames)

    sampled_indices = sorted(
        {
            min(len(frames) - 1, round(index * (len(frames) - 1) / (bounded - 1)))
            for index in range(bounded)
        }
    )
    return [frames[index] for index in sampled_indices]


def _build_evaluation(
    *,
    scores: list[tuple[int, float]],
    threshold: float,
    enforce_decision: bool,
    model_hash: str | None,
) -> DeepfakeEvaluation:
    if not scores:
        return DeepfakeEvaluation(
            enabled=True,
            enforced=enforce_decision,
            passed=True,
            deepfake_score=None,
            max_deepfake_score=None,
            frames_processed=0,
            flagged_frames=[],
            model_hash=model_hash,
            message="No deepfake scores available",
        )

    mean_score = round(sum(score for _, score in scores) / len(scores), 4)
    max_score = round(max(score for _, score in scores), 4)
    flagged_frames = [frame_index for frame_index, score in scores if score >= threshold]
    passed = mean_score < threshold and max_score < threshold
    message = (
        (
            "Deepfake checks passed across sampled frames"
            if passed and enforce_decision
            else "Deepfake telemetry collected"
        )
        if passed or not enforce_decision
        else f"Potential deepfake indicators found in {len(flagged_frames)} sampled frame(s)"
    )
    if not enforce_decision:
        message = f"{message}; not enforced in final decision"

    return DeepfakeEvaluation(
        enabled=True,
        enforced=enforce_decision,
        passed=passed,
        deepfake_score=mean_score,
        max_deepfake_score=max_score,
        frames_processed=len(scores),
        flagged_frames=flagged_frames,
        model_hash=model_hash,
        message=message,
    )


def _extract_fake_probability(logits: np.ndarray, *, deepfake_index: int = -1) -> float:
    squeezed = np.squeeze(logits)
    if squeezed.ndim == 0:
        scalar = float(squeezed)
        return max(0.0, min(1.0, scalar))

    flattened = squeezed.astype("float32").reshape(-1)
    if flattened.size == 1:
        scalar = float(flattened[0])
        if 0.0 <= scalar <= 1.0:
            return scalar
        sigmoid = 1.0 / (1.0 + float(np.exp(-scalar)))
        return max(0.0, min(1.0, sigmoid))

    probabilities = softmax(flattened[None, ...])[0]
    if probabilities.size >= 2:
        selected_index = deepfake_index if 0 <= deepfake_index < probabilities.size else probabilities.size - 1
        return max(0.0, min(1.0, float(probabilities[selected_index])))
    return max(0.0, min(1.0, float(probabilities[0])))


def _load_preprocessor_stats(model_path: Path) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    config_path = model_path.with_name("preprocessor_config.json")
    if not config_path.exists():
        return (0.5, 0.5, 0.5), (0.5, 0.5, 0.5)

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return (0.5, 0.5, 0.5), (0.5, 0.5, 0.5)

    image_mean = payload.get("image_mean") or [0.5, 0.5, 0.5]
    image_std = payload.get("image_std") or [0.5, 0.5, 0.5]
    if len(image_mean) != 3 or len(image_std) != 3:
        return (0.5, 0.5, 0.5), (0.5, 0.5, 0.5)

    return tuple(float(value) for value in image_mean), tuple(float(value) for value in image_std)


def _load_deepfake_label_index(model_path: Path) -> int:
    config_path = model_path.with_name("config.json")
    if not config_path.exists():
        return 1

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return 1

    id2label = payload.get("id2label")
    if not isinstance(id2label, dict):
        return 1

    for key, value in id2label.items():
        if isinstance(value, str) and value.strip().lower() == "deepfake":
            try:
                return int(key)
            except (TypeError, ValueError):
                return 1
    return 1


def _shape_dim_to_int(value: object, *, default: int) -> int:
    if isinstance(value, int):
        return value
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_deepfake_evaluator(
    *,
    mode: str,
    enabled: bool,
    model_path: str | None,
    threshold: float,
    enforce_decision: bool,
) -> DeepfakeEvaluator:
    logger = get_logger(__name__)
    if not enabled:
        logger.info("Deepfake evaluator disabled")
        return DisabledDeepfakeEvaluator()

    selected_mode = mode.lower()
    if selected_mode == "disabled":
        logger.info("Deepfake evaluator disabled by mode")
        return DisabledDeepfakeEvaluator()

    if selected_mode == "mock":
        logger.info("Using mock deepfake evaluator")
        return MockDeepfakeEvaluator(
            threshold=threshold,
            enforce_decision=enforce_decision,
        )

    if not model_path:
        logger.warning("No deepfake model path configured; deepfake scoring disabled")
        return DisabledDeepfakeEvaluator()

    try:
        evaluator = OnnxDeepfakeEvaluator(
            model_path=model_path,
            threshold=threshold,
            enforce_decision=enforce_decision,
        )
        logger.info("Loaded deepfake ONNX evaluator from %s", model_path)
        return evaluator
    except Exception as exc:
        logger.warning("Could not load deepfake ONNX evaluator from %s: %s", model_path, exc)
        if selected_mode == "auto":
            return DisabledDeepfakeEvaluator()
        return MockDeepfakeEvaluator(
            threshold=threshold,
            enforce_decision=enforce_decision,
        )
