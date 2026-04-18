from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .image_utils import decode_frame_image, file_sha256
from app.core.logging import get_logger

from .types import FaceBoundingBox, FaceDetectionResult, FrameInput


class FaceDetector(ABC):
    @abstractmethod
    def detect(self, frame: FrameInput) -> FaceDetectionResult:
        """Return a deterministic face detection result for the frame."""

    @property
    def models_ready(self) -> bool:
        return False

    @property
    def runtime_label(self) -> str:
        return "mock"


class MockFaceDetector(FaceDetector):
    def __init__(
        self,
        detection_threshold: float = 0.35,
        model_hash: str = "sha256:mock-face-detector-v1",
    ) -> None:
        self.detection_threshold = detection_threshold
        self.model_hash = model_hash

    @property
    def models_ready(self) -> bool:
        return True

    def detect(self, frame: FrameInput) -> FaceDetectionResult:
        forced = frame.metadata.get("force_face_detected")
        image = decode_frame_image(frame)
        if forced is None:
            has_input = bool(frame.image_base64 or frame.landmarks)
            detected = has_input
        else:
            detected = bool(forced)

        confidence = round(
            0.99
            if detected and forced is True
            else 0.05
            if forced is False
            else frame.pseudo_score("face-confidence", 0.45 if detected else 0.01, 0.99 if detected else 0.35),
            4,
        )

        box_override = frame.metadata.get("face_bbox")
        if detected and isinstance(box_override, dict):
            bounding_box = FaceBoundingBox(
                x=float(box_override.get("x", 0.2)),
                y=float(box_override.get("y", 0.18)),
                width=float(box_override.get("width", 0.52)),
                height=float(box_override.get("height", 0.62)),
            )
        elif detected:
            image_width = float(image.shape[1]) if image is not None else 640.0
            image_height = float(image.shape[0]) if image is not None else 480.0
            offset = frame.pseudo_score("face-box", -0.04, 0.04)
            bounding_box = FaceBoundingBox(
                x=round((0.24 + offset) * image_width, 2),
                y=round((0.18 - offset) * image_height, 2),
                width=round(0.5 * image_width, 2),
                height=round(0.62 * image_height, 2),
            )
        else:
            bounding_box = None

        landmarks_source = "mediapipe" if frame.landmarks else "mock"
        face_hash = f"sha256:{frame.fingerprint('face-crop')}" if detected else None
        message = "Face detected and centered" if detected else "No face detected in frame"
        return FaceDetectionResult(
            detected=detected,
            confidence=confidence,
            frame_index=frame.frame_index,
            bounding_box=bounding_box,
            landmarks_source=landmarks_source,
            face_hash=face_hash,
            message=message,
        )


class YOLOv8FaceDetector(FaceDetector):
    def __init__(
        self,
        model_path: str,
        *,
        confidence_threshold: float = 0.35,
        image_size: int = 640,
    ) -> None:
        from ultralytics import YOLO

        self.model_path = str(Path(model_path).expanduser().resolve())
        self.model = YOLO(self.model_path, task="detect")
        self.confidence_threshold = confidence_threshold
        self.image_size = image_size
        self.model_hash = file_sha256(self.model_path)

    @property
    def models_ready(self) -> bool:
        return True

    @property
    def runtime_label(self) -> str:
        return "yolov8"

    def detect(self, frame: FrameInput) -> FaceDetectionResult:
        forced = frame.metadata.get("force_face_detected")
        if forced is not None and not bool(forced):
            return FaceDetectionResult(
                detected=False,
                confidence=0.05,
                frame_index=frame.frame_index,
                message="No face detected in frame",
            )

        image = decode_frame_image(frame)
        if image is None:
            return FaceDetectionResult(
                detected=False,
                confidence=0.0,
                frame_index=frame.frame_index,
                message="Frame could not be decoded",
            )

        results = self.model.predict(
            source=image,
            conf=self.confidence_threshold,
            imgsz=self.image_size,
            device="cpu",
            verbose=False,
        )
        if not results:
            return FaceDetectionResult(
                detected=False,
                confidence=0.0,
                frame_index=frame.frame_index,
                message="No face detected in frame",
            )

        boxes = results[0].boxes
        if boxes is None or boxes.xyxy is None or len(boxes.xyxy) == 0:
            return FaceDetectionResult(
                detected=False,
                confidence=0.0,
                frame_index=frame.frame_index,
                message="No face detected in frame",
            )

        confs = boxes.conf.tolist()
        best_index = max(range(len(confs)), key=confs.__getitem__)
        x1, y1, x2, y2 = boxes.xyxy[best_index].tolist()
        confidence = round(float(confs[best_index]), 4)
        face_hash = f"sha256:{frame.fingerprint('face-crop')}"
        return FaceDetectionResult(
            detected=True,
            confidence=confidence,
            frame_index=frame.frame_index,
            bounding_box=FaceBoundingBox(
                x=float(x1),
                y=float(y1),
                width=max(1.0, float(x2 - x1)),
                height=max(1.0, float(y2 - y1)),
            ),
            landmarks_source="yolov8",
            face_hash=face_hash,
            message="Face detected and centered",
        )


def build_face_detector(
    *,
    mode: str,
    model_path: str | None,
    confidence_threshold: float,
    image_size: int,
) -> FaceDetector:
    logger = get_logger(__name__)
    selected_mode = mode.lower()

    if selected_mode == "mock":
        logger.info("Using mock face detector")
        return MockFaceDetector(detection_threshold=confidence_threshold)

    if not model_path:
        logger.warning("No YOLO face model path configured; falling back to mock detector")
        return MockFaceDetector(detection_threshold=confidence_threshold)

    try:
        detector = YOLOv8FaceDetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            image_size=image_size,
        )
        logger.info("Loaded YOLOv8 face detector from %s", model_path)
        return detector
    except Exception as exc:
        logger.warning("Could not load YOLOv8 face detector from %s: %s", model_path, exc)
        return MockFaceDetector(detection_threshold=confidence_threshold)
