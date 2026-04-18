# Verifier Model Assets

This folder documents the expected local model assets for the verifier.

Current local asset provenance and hashes are tracked in [SOURCES.md](/Users/skadi2910/projects/sui-liveness-detection/services/verifier/models/SOURCES.md).

## Face Detection

The current runtime supports a YOLOv8 face model through Ultralytics.

Configure:

- `VERIFIER_FACE_MODEL_MODE=auto`
- `VERIFIER_FACE_MODEL_PATH=/absolute/path/to/your/yolov8-face.onnx`

The current local verifier is already wired to:

- `/Users/skadi2910/projects/sui-liveness-detection/services/verifier/models/face/yolov8n-face-lindevs.onnx`

## Anti-Spoof

The current runtime supports Silent-Face style ONNX models through ONNX Runtime.

Configure:

- `VERIFIER_ANTISPOOF_MODEL_MODE=auto`
- `VERIFIER_ANTISPOOF_MODEL_DIR=/absolute/path/to/anti_spoof_models`

The evaluator accepts either:

- a single `.onnx` file
- a directory of `.onnx` files

The current local verifier is already wired to:

- `/Users/skadi2910/projects/sui-liveness-detection/services/verifier/models/anti_spoof`

The file naming convention should follow the Silent-Face patch naming pattern, for example:

- `1_80x80_MiniFASNetV2.onnx`
- `2.7_80x80_MiniFASNetV2.onnx`
- `4_80x80_MiniFASNetV1SE.onnx`

This allows the evaluator to infer input size and crop scale in the same spirit as the original Silent-Face project.

The exported Silent-Face files currently include adjacent `.onnx.data` sidecars produced by the ONNX exporter. Keep those files next to the `.onnx` files.
