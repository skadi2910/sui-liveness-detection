#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

import onnx
import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export official Silent-Face .pth weights to ONNX files.",
    )
    parser.add_argument(
        "--upstream-repo",
        type=Path,
        default=Path("/tmp/Silent-Face-Anti-Spoofing"),
        help="Path to a local checkout of the official Silent-Face repo.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("services/verifier/models/anti_spoof"),
        help="Directory containing the official .pth weights.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("services/verifier/models/anti_spoof"),
        help="Directory where the exported .onnx files should be written.",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=18,
        help="ONNX opset version to export with.",
    )
    return parser.parse_args()


def load_upstream_modules(upstream_repo: Path):
    sys.path.insert(0, str(upstream_repo))
    from src.model_lib.MiniFASNet import (  # type: ignore
        MiniFASNetV1,
        MiniFASNetV1SE,
        MiniFASNetV2,
        MiniFASNetV2SE,
    )
    from src.utility import get_kernel, parse_model_name  # type: ignore

    model_mapping = {
        "MiniFASNetV1": MiniFASNetV1,
        "MiniFASNetV2": MiniFASNetV2,
        "MiniFASNetV1SE": MiniFASNetV1SE,
        "MiniFASNetV2SE": MiniFASNetV2SE,
    }
    return model_mapping, get_kernel, parse_model_name


def normalize_state_dict(state_dict: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    first_key = next(iter(state_dict))
    if not first_key.startswith("module."):
        return state_dict

    normalized: OrderedDict[str, torch.Tensor] = OrderedDict()
    for key, value in state_dict.items():
        normalized[key[7:]] = value
    return normalized


def export_one_model(
    weight_path: Path,
    output_dir: Path,
    model_mapping,
    get_kernel,
    parse_model_name,
    opset: int,
) -> dict[str, object]:
    height, width, model_type, _ = parse_model_name(weight_path.name)
    kernel = get_kernel(height, width)
    model = model_mapping[model_type](conv6_kernel=kernel)

    state_dict = torch.load(weight_path, map_location="cpu")
    model.load_state_dict(normalize_state_dict(state_dict))
    model.eval()

    output_path = output_dir / f"{weight_path.stem}.onnx"
    dummy_input = torch.randn(1, 3, height, width, dtype=torch.float32)

    with torch.no_grad():
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=opset,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["logits"],
        )

    exported_model = onnx.load(str(output_path))
    onnx.checker.check_model(exported_model)

    return {
        "source_weight": str(weight_path.resolve()),
        "onnx_path": str(output_path.resolve()),
        "input_shape": [1, 3, height, width],
        "model_type": model_type,
        "opset": opset,
    }


def main() -> int:
    args = parse_args()
    upstream_repo = args.upstream_repo.expanduser().resolve()
    input_dir = args.input_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not upstream_repo.exists():
        raise FileNotFoundError(f"Upstream Silent-Face repo not found: {upstream_repo}")
    if not input_dir.exists():
        raise FileNotFoundError(f"Input weight directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    model_mapping, get_kernel, parse_model_name = load_upstream_modules(upstream_repo)

    exports: list[dict[str, object]] = []
    for weight_path in sorted(input_dir.glob("*.pth")):
        exports.append(
            export_one_model(
                weight_path=weight_path,
                output_dir=output_dir,
                model_mapping=model_mapping,
                get_kernel=get_kernel,
                parse_model_name=parse_model_name,
                opset=args.opset,
            )
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"exports": exports}, indent=2), encoding="utf-8")
    print(json.dumps({"exports": exports, "manifest": str(manifest_path.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
