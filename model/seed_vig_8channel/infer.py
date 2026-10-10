"""Run calibrated fatigue inference from an exported numeric model artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from riemann_core import calibrated_tangent_features


class FatigueModel:
    def __init__(self, model_path: Path):
        saved = np.load(model_path)
        self.mean = saved["scaler_mean"]
        self.scale = saved["scaler_scale"]
        self.coef = saved["classifier_coef"]
        self.intercept = float(saved["classifier_intercept"][0])
        self.n_channels = int(saved["n_channels"][0])
        self.window_samples = int(saved["window_samples"][0])
        self.shrinkage = float(saved["shrinkage"][0])
        self.threshold = float(saved["decision_threshold"][0])

    def predict(self, baseline_epochs: np.ndarray, target_epochs: np.ndarray) -> dict:
        for name, epochs in (("baseline", baseline_epochs), ("target", target_epochs)):
            if epochs.ndim != 3 or epochs.shape[1:] != (self.n_channels, self.window_samples):
                raise ValueError(
                    f"{name} must have shape (n, {self.n_channels}, {self.window_samples}); got {epochs.shape}"
                )
        features, _ = calibrated_tangent_features(baseline_epochs, target_epochs, self.shrinkage)
        standardized = (features - self.mean) / self.scale
        logits = standardized @ self.coef + self.intercept
        probability = 1.0 / (1.0 + np.exp(-np.clip(logits, -40.0, 40.0)))
        return {
            "fatigue_probability": probability.tolist(),
            "predicted_label": (probability >= self.threshold).astype(int).tolist(),
            "threshold": self.threshold,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=Path(__file__).parent / "artifacts" / "seed_vig_ra_tangent_lr_v1.npz")
    parser.add_argument("--input", type=Path, required=True, help="NPZ containing baseline_epochs and target_epochs")
    args = parser.parse_args()
    payload = np.load(args.input)
    result = FatigueModel(args.model).predict(payload["baseline_epochs"], payload["target_epochs"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
