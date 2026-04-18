from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.core.logging import get_logger

from .image_utils import crop_image, decode_frame_image
from .types import FaceDetectionResult, FrameInput, HumanFaceEvaluation

_HUMAN_FACE_LABEL = "a real human face"
_CANDIDATE_LABELS = [
    _HUMAN_FACE_LABEL,
    "an animal face",
    "a cartoon face",
    "a doll or mannequin face",
    "a costume or printed mask face",
]


class HumanFaceEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        frame: FrameInput,
        face_detection: FaceDetectionResult | None,
    ) -> HumanFaceEvaluation:
        """Estimate whether the detected face crop belongs to a real human face."""

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
    def enforced(self) -> bool:
        return False

    @property
    def model_hash(self) -> str | None:
        return None


class DisabledHumanFaceEvaluator(HumanFaceEvaluator):
    def evaluate(
        self,
        frame: FrameInput,
        face_detection: FaceDetectionResult | None,
    ) -> HumanFaceEvaluation:
        return HumanFaceEvaluation(
            enabled=False,
            enforced=False,
            passed=True,
            human_face_score=None,
            top_label=None,
            frames_processed=0,
            model_hash=None,
            message="Human-face scoring disabled",
        )


class MockHumanFaceEvaluator(HumanFaceEvaluator):
    def __init__(
        self,
        *,
        threshold: float = 0.55,
        enforce_decision: bool = False,
        model_hash: str = "hf:mock-human-face-v1",
    ) -> None:
        self.threshold = threshold
        self._enforced = enforce_decision
        self._model_hash = model_hash

    @property
    def models_ready(self) -> bool:
        return True

    @property
    def runtime_label(self) -> str:
        return "mock"

    @property
    def enabled(self) -> bool:
        return True

    @property
    def enforced(self) -> bool:
        return self._enforced

    @property
    def model_hash(self) -> str | None:
        return self._model_hash

    def evaluate(
        self,
        frame: FrameInput,
        face_detection: FaceDetectionResult | None,
    ) -> HumanFaceEvaluation:
        if not face_detection or not face_detection.detected:
            return HumanFaceEvaluation(
                enabled=True,
                enforced=self._enforced,
                passed=False,
                human_face_score=None,
                top_label=None,
                frames_processed=0,
                model_hash=self._model_hash,
                message="No detected face available for human-face scoring",
            )

        if "force_human_face_score" in frame.metadata:
            score = round(float(frame.metadata["force_human_face_score"]), 4)
        elif frame.metadata.get("force_human_face_passed") is not None:
            score = 0.9 if bool(frame.metadata["force_human_face_passed"]) else 0.1
        elif frame.metadata.get("synthetic_attack") is True:
            score = 0.08
        else:
            score = frame.pseudo_score("human-face", 0.72, 0.94)

        top_label = str(frame.metadata.get("force_human_face_label", _HUMAN_FACE_LABEL))
        passed = score >= self.threshold
        if not passed and top_label == _HUMAN_FACE_LABEL:
            top_label = "a non-human or ambiguous face-like subject"

        return HumanFaceEvaluation(
            enabled=True,
            enforced=self._enforced,
            passed=passed,
            human_face_score=score,
            top_label=top_label,
            frames_processed=1,
            model_hash=self._model_hash,
            message=_human_face_message(passed, score, top_label),
        )


@dataclass(slots=True)
class ZeroShotClipSpec:
    model_id: str
    threshold: float
    enforced: bool
    processor: object
    model: object
    device: str
    model_hash: str


class ZeroShotClipHumanFaceEvaluator(HumanFaceEvaluator):
    def __init__(
        self,
        *,
        model_id: str,
        threshold: float = 0.55,
        enforce_decision: bool = False,
    ) -> None:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        processor = CLIPProcessor.from_pretrained(model_id)
        model = CLIPModel.from_pretrained(model_id)
        model.eval()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        commit_hash = getattr(model.config, "_commit_hash", None)
        model_hash = f"hf:{model_id}@{commit_hash or 'local'}"

        self.spec = ZeroShotClipSpec(
            model_id=model_id,
            threshold=threshold,
            enforced=enforce_decision,
            processor=processor,
            model=model,
            device=device,
            model_hash=model_hash,
        )

    @property
    def models_ready(self) -> bool:
        return True

    @property
    def runtime_label(self) -> str:
        return f"transformers-clip:{self.spec.model_id}"

    @property
    def enabled(self) -> bool:
        return True

    @property
    def enforced(self) -> bool:
        return self.spec.enforced

    @property
    def model_hash(self) -> str | None:
        return self.spec.model_hash

    def evaluate(
        self,
        frame: FrameInput,
        face_detection: FaceDetectionResult | None,
    ) -> HumanFaceEvaluation:
        if not face_detection or not face_detection.detected or face_detection.bounding_box is None:
            return HumanFaceEvaluation(
                enabled=True,
                enforced=self.spec.enforced,
                passed=False,
                human_face_score=None,
                top_label=None,
                frames_processed=0,
                model_hash=self.spec.model_hash,
                message="No detected face available for human-face scoring",
            )

        image = decode_frame_image(frame)
        if image is None:
            return HumanFaceEvaluation(
                enabled=True,
                enforced=self.spec.enforced,
                passed=False,
                human_face_score=None,
                top_label=None,
                frames_processed=0,
                model_hash=self.spec.model_hash,
                message="No decodable frame image available for human-face scoring",
            )

        crop = crop_image(
            image,
            face_detection.bounding_box,
            scale=1.25,
            out_w=224,
            out_h=224,
        )
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        import torch
        from PIL import Image

        pil_image = Image.fromarray(crop_rgb)
        inputs = self.spec.processor(
            text=_CANDIDATE_LABELS,
            images=pil_image,
            return_tensors="pt",
            padding=True,
        )
        with torch.no_grad():
            prepared = {key: value.to(self.spec.device) for key, value in inputs.items()}
            outputs = self.spec.model(**prepared)
            probabilities = outputs.logits_per_image.softmax(dim=1)[0].detach().cpu().numpy()

        human_score = float(probabilities[0])
        top_index = int(np.argmax(probabilities))
        top_label = _CANDIDATE_LABELS[top_index]
        passed = human_score >= self.spec.threshold

        return HumanFaceEvaluation(
            enabled=True,
            enforced=self.spec.enforced,
            passed=passed,
            human_face_score=round(human_score, 4),
            top_label=top_label,
            frames_processed=1,
            model_hash=self.spec.model_hash,
            message=_human_face_message(passed, human_score, top_label),
        )


def build_human_face_evaluator(
    *,
    mode: str,
    enabled: bool,
    model_id: str | None,
    threshold: float,
    enforce_decision: bool,
) -> HumanFaceEvaluator:
    logger = get_logger(__name__)
    if not enabled:
        logger.info("Human-face evaluator disabled")
        return DisabledHumanFaceEvaluator()

    selected_mode = mode.lower()
    if selected_mode == "disabled":
        logger.info("Human-face evaluator disabled by mode")
        return DisabledHumanFaceEvaluator()

    if selected_mode == "mock":
        logger.info("Using mock human-face evaluator")
        return MockHumanFaceEvaluator(
            threshold=threshold,
            enforce_decision=enforce_decision,
        )

    if not model_id:
        logger.warning("No human-face model id configured; human-face scoring disabled")
        return DisabledHumanFaceEvaluator()

    try:
        evaluator = ZeroShotClipHumanFaceEvaluator(
            model_id=model_id,
            threshold=threshold,
            enforce_decision=enforce_decision,
        )
        logger.info("Loaded human-face CLIP evaluator from %s", model_id)
        return evaluator
    except Exception as exc:
        logger.warning("Could not load human-face evaluator from %s: %s", model_id, exc)
        if selected_mode == "auto":
            return DisabledHumanFaceEvaluator()
        return MockHumanFaceEvaluator(
            threshold=threshold,
            enforce_decision=enforce_decision,
        )


def _human_face_message(passed: bool, score: float | None, top_label: str | None) -> str:
    if score is None:
        return "Human-face score unavailable"
    if passed:
        return f"Human-face model passed ({score:.2f}, top label: {top_label or 'unknown'})"
    return f"Human-face model flagged a non-human or ambiguous face ({score:.2f}, top label: {top_label or 'unknown'})"
