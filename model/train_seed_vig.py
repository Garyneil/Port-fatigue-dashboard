"""Train and export the SEED-VIG RA + tangent-space logistic model.

The exported NPZ contains numeric parameters only. It does not require pickle and
can be loaded safely by the accompanying inference script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from riemann_core import align_by_subject, epochs_to_covariances, tangent_features_at_identity


MODEL_VERSION = "seed-vig-ra-tangent-lr-v1.0.0"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metrics(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    prediction = (probability >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, prediction)),
        "f1": float(f1_score(y_true, prediction)),
        "roc_auc": float(roc_auc_score(y_true, probability)),
    }


def train_classifier(features: np.ndarray, labels: np.ndarray) -> tuple[StandardScaler, LogisticRegression]:
    scaler = StandardScaler().fit(features)
    classifier = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        random_state=42,
    ).fit(scaler.transform(features), labels)
    return scaler, classifier


def run(data_path: Path, artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    raw = loadmat(data_path, variable_names=["EEGsample", "substate", "subindex"])
    epochs = np.asarray(raw["EEGsample"], dtype=np.float64)
    labels = raw["substate"].ravel().astype(np.int64)
    subjects = raw["subindex"].ravel().astype(np.int64)

    if epochs.ndim != 3 or epochs.shape[1] != 17:
        raise ValueError(f"Expected epochs shaped (n, 17, time), received {epochs.shape}")
    if set(np.unique(labels)) != {0, 1}:
        raise ValueError("Expected binary labels 0=alert and 1=drowsy")

    covariances = epochs_to_covariances(epochs, shrinkage=0.10)
    aligned_covariances = align_by_subject(covariances, subjects)
    features = tangent_features_at_identity(aligned_covariances)

    rows = []
    for held_out in np.unique(subjects):
        train_mask = subjects != held_out
        test_mask = subjects == held_out
        scaler, classifier = train_classifier(features[train_mask], labels[train_mask])
        probability = classifier.predict_proba(scaler.transform(features[test_mask]))[:, 1]
        rows.append({"subject": int(held_out), "n_test": int(test_mask.sum()), **metrics(labels[test_mask], probability)})

    with (artifact_dir / "loso_metrics.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    scaler, classifier = train_classifier(features, labels)
    np.savez_compressed(
        artifact_dir / "seed_vig_ra_tangent_lr_v1.npz",
        scaler_mean=scaler.mean_,
        scaler_scale=scaler.scale_,
        classifier_coef=classifier.coef_[0],
        classifier_intercept=classifier.intercept_,
        classes=classifier.classes_,
        n_channels=np.asarray([epochs.shape[1]], dtype=np.int64),
        sample_rate_hz=np.asarray([128], dtype=np.int64),
        window_samples=np.asarray([epochs.shape[2]], dtype=np.int64),
        shrinkage=np.asarray([0.10], dtype=np.float64),
        decision_threshold=np.asarray([0.50], dtype=np.float64),
    )

    summary = {
        "model_version": MODEL_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "subject-wise Riemannian alignment + identity tangent space + standardized logistic regression",
        "dataset": "Extracted SEED-VIG, Figshare 26104987 v1",
        "dataset_sha256": file_sha256(data_path),
        "n_subjects": int(len(np.unique(subjects))),
        "subject_ids": [int(item) for item in np.unique(subjects)],
        "n_epochs": int(len(labels)),
        "class_counts": {"alert_0": int((labels == 0).sum()), "drowsy_1": int((labels == 1).sum())},
        "input": {
            "channels": int(epochs.shape[1]),
            "samples_per_epoch": int(epochs.shape[2]),
            "sample_rate_hz": 128,
            "window_seconds": float(epochs.shape[2] / 128),
        },
        "validation": {
            "protocol": "leave-one-subject-out",
            "alignment": "unlabeled full held-out-subject center (transductive offline estimate)",
            "mean": {key: float(np.mean([row[key] for row in rows])) for key in ("accuracy", "balanced_accuracy", "f1", "roc_auc")},
            "std_sample": {key: float(np.std([row[key] for row in rows], ddof=1)) for key in ("accuracy", "balanced_accuracy", "f1", "roc_auc")},
        },
        "deployment_contract": {
            "personal_calibration": "Required: estimate an unlabeled Riemannian center from recent baseline epochs.",
            "output": "Per-window drowsiness probability; temporal smoothing and alarm hysteresis are external decision-layer responsibilities.",
            "warning": "Research prototype only. Not validated for port safety decisions.",
        },
    }
    (artifact_dir / "metadata.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True, help="Path to extracted SEED_VIG.mat")
    parser.add_argument("--artifacts", type=Path, default=Path(__file__).parent / "artifacts")
    arguments = parser.parse_args()
    run(arguments.data, arguments.artifacts)
