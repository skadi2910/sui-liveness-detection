# Deepfake Detector Research Memo

**Date:** April 18, 2026
**Scope:** practical deepfake / video-synthesis detection options for the current verifier stack

## Repo Context

Current verifier stack:

- YOLOv8 face detection (server)
- Silent-Face anti-spoof (server, ONNX)
- TensorFlow.js face landmarks (browser)
- FastAPI verifier with per-frame quality / liveness gates and finalize-time verdict logic

What we need from a deepfake detector:

- CPU-friendly inference
- easy server-side integration with the existing face-crop pipeline
- ideally ONNX-ready
- compatible with our current "second decision head" approach rather than replacing Silent-Face

---

## Recommendation

### 1. Best MVP path: ONNX image-level detector on accepted face crops

**Candidate:** `onnx-community/Deep-Fake-Detector-v2-Model-ONNX`

Links:

- [ONNX model card](https://huggingface.co/onnx-community/Deep-Fake-Detector-v2-Model-ONNX)
- [Original model card](https://huggingface.co/prithivMLmods/Deep-Fake-Detector-v2-Model)
- [Optimum ONNX Runtime overview](https://huggingface.co/docs/optimum/main/en/onnxruntime/overview)

Why it fits:

- already ONNX packaged
- binary image-classification head, which maps well to our existing accepted face-crop flow
- CPU inference is realistic with ONNX Runtime
- easiest path to add without retraining a custom detector first

Why it does not fully fit:

- the model card explicitly describes it as an **image** detector, not a video detector
- it may miss attacks that look frame-realistic but fail only in temporal consistency
- the published metrics are model-card metrics, not a repo-specific benchmark against our webcam / replay conditions

Expected input / output:

- input: RGB face crop resized to `224 x 224`
- output: binary class logits / probabilities for `Realism` vs `Deepfake`

Recommended integration point:

- run **after** face detection, quality gate, and spot-check filtering
- sample a small number of accepted face crops per session, not every frame
- aggregate with `max` plus `mean` across sampled frames
- fuse with Silent-Face at finalize time:
  - reject if Silent-Face trips
  - reject if deepfake score trips

Expected latency / cost tradeoff:

- likely the cheapest practical option for this repo
- expected CPU latency is moderate rather than tiny; use frame sampling to stay inside MVP latency
- quantized ONNX variants on the model card make this more realistic than a raw PyTorch-only model

Verdict:

- **best first experiment for this repo**

---

### 2. Best custom path if the off-the-shelf ONNX model underperforms: DeepfakeBench image detector exported to ONNX

**Candidate approach:** use DeepfakeBench as the training / evaluation source of truth, then export one of the simpler image detectors such as EfficientNet-B4 or Xception to ONNX for our runtime

Links:

- [DeepfakeBench repository](https://github.com/SCLBD/DeepfakeBench)
- [DeepfakeBench EfficientNet-B4 detector](https://github.com/SCLBD/DeepfakeBench/blob/main/training/detectors/efficientnetb4_detector.py)
- [DeepfakeBench benchmark paper](https://proceedings.neurips.cc/paper_files/paper/2023/file/0e735e4b4f07de483cbe250130992726-Paper-Datasets_and_Benchmarks.pdf)

Why it fits:

- DeepfakeBench is the strongest primary-source benchmark among the options we checked
- it already standardizes datasets and cross-dataset evaluation for deepfake detectors
- it gives us a clean path to train or benchmark a detector on the exact attack classes we care about
- an image-level detector still fits our existing face-crop server pipeline

Why it does not fully fit:

- not drop-in for our repo today
- engineering cost is higher: train or validate weights, export to ONNX, build preprocessing parity, then calibrate thresholds
- most DeepfakeBench detectors are research-oriented PyTorch implementations first, deployment artifacts second

Expected input / output:

- image-level face crops
- output: binary fake / real score per crop
- typical input size will depend on chosen backbone:
  - Xception-style path: commonly `299 x 299`
  - EfficientNet-B4 path: commonly around `380 x 380`

Recommended integration point:

- same placement as candidate 1: accepted face crops after quality / spot-check
- use only in `full` and `antispoof_only` finalize paths
- add preview support only if CPU cost stays acceptable

Expected latency / cost tradeoff:

- inference could still be acceptable on CPU after ONNX export, but integration cost is materially higher
- this is the better long-term path if we discover that the off-the-shelf ViT model does not generalize to our capture conditions

Verdict:

- **best fallback / custom path**

---

### 3. Best higher-accuracy later-stage path: temporal video detector such as TALL

**Candidate approach:** TALL / TALL++ style temporal detector run on a short clip of accepted session frames

Links:

- [Official TALL repository](https://github.com/rainy-xu/TALL4Deepfake)
- [ICCV 2023 TALL paper](https://openaccess.thecvf.com/content/ICCV2023/html/Xu_TALL_Thumbnail_Layout_for_Deepfake_Video_Detection_ICCV_2023_paper.html)
- [DeepfakeBench repository listing TALL among supported video detectors](https://github.com/SCLBD/DeepfakeBench)

Why it fits:

- this is the right class of model for talking-head and face-swap **video** attacks
- the paper specifically targets deepfake video detection rather than single-image classification
- a temporal model is more likely to catch synthesis artifacts that survive per-frame inspection

Why it does not fit the current MVP well:

- heavier engineering and compute footprint
- clip assembly, temporal preprocessing, and batching logic would complicate the current finalize path
- this is not a good candidate for per-frame live preview on CPU

Expected input / output:

- short clip of multiple accepted frames
- TALL README examples use:
  - `input_size 112`
  - `duration 4`
  - `num_clips 8`
- output: clip- or video-level fake / real score

Recommended integration point:

- finalize only
- run on a small clip built from already accepted session frames
- do not insert it into the real-time per-frame loop for the MVP

Expected latency / cost tradeoff:

- highest latency and engineering cost of the shortlist
- likely acceptable only as a finalize-time step, not as a per-frame gate

Verdict:

- **best later-stage path if image-level detectors are not enough**

---

## Top 3 Summary

1. `onnx-community/Deep-Fake-Detector-v2-Model-ONNX`
   - best immediate MVP experiment
   - easiest integration
   - image-only limitation

2. DeepfakeBench image detector exported to ONNX
   - best custom training / benchmarking path
   - stronger control over data and evaluation
   - more engineering work

3. TALL / TALL++
   - best temporal-video path
   - most likely to catch replayed talking-head artifacts
   - too heavy for the current MVP live loop

---

## Recommended Next Step For This MVP

Implementation status as of April 18, 2026:

1. The verifier now has a finalize-time deepfake scoring slot and result/health telemetry.
2. The first operational target remains candidate 1:
   - sample `4` to `8` accepted face crops per session
   - run the ONNX detector at finalize time only
   - record `deepfake_score` and `max_deepfake_score`
   - keep the head as a fused verdict alongside Silent-Face, not as a replacement
3. Keep enforcement disabled by default until the local attack matrix shows the head improves talking-head / face-swap coverage without hurting live-user pass rate.
4. If candidate 1 is noisy or fails to generalize, move to candidate 2 using DeepfakeBench as the training and evaluation path.
5. Only move to candidate 3 if image-level detection is not enough and the attack matrix proves temporal synthesis remains a real gap.

## Practical Integration Sketch

Suggested server-side flow:

```text
accepted session frames
  -> face crop sampler (4-8 crops)
  -> deepfake detector
  -> aggregate max / mean score
  -> finalize verdict fusion
```

Suggested result fields:

- `deepfake_score`
- `max_deepfake_score`
- `deepfake_frames_processed`
- `deepfake_model_hash`
- `deepfake_message`

This keeps the change aligned with how `Silent-Face` is already represented in the verifier.
