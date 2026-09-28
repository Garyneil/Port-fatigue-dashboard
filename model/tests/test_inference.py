from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


MODEL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODEL_DIR))

from infer import FatigueModel  # noqa: E402


class FatigueModelTest(unittest.TestCase):
    def test_exported_model_returns_finite_probabilities(self) -> None:
        rng = np.random.default_rng(42)
        baseline = rng.normal(size=(12, 17, 384))
        target = rng.normal(size=(4, 17, 384))
        model = FatigueModel(MODEL_DIR / "artifacts" / "seed_vig_ra_tangent_lr_v1.npz")
        result = model.predict(baseline, target)

        probability = np.asarray(result["fatigue_probability"])
        self.assertEqual(probability.shape, (4,))
        self.assertTrue(np.isfinite(probability).all())
        self.assertTrue(((probability >= 0.0) & (probability <= 1.0)).all())
        self.assertEqual(len(result["predicted_label"]), 4)

    def test_rejects_incompatible_channel_layout(self) -> None:
        model = FatigueModel(MODEL_DIR / "artifacts" / "seed_vig_ra_tangent_lr_v1.npz")
        with self.assertRaises(ValueError):
            model.predict(np.zeros((10, 8, 384)), np.zeros((2, 8, 384)))


if __name__ == "__main__":
    unittest.main()
