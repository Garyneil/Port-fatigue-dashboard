# SADT Fp1/Fp2 fatigue tendency model v1

This directory contains the numeric inference export of the existing project model (`model.npz`), its training summary and its public raw EEG replay verification record. No participant raw recordings are included.

The runtime requires only NumPy and SciPy, without scikit-learn, joblib or the original training directory. The packaged model is byte-identical to the existing numeric export in `results/fatigue_classifier_v1/model.npz` of the local SADT project. Live preprocessing and thresholds are preserved.

`inference_verification.json` documents earlier public EEG replay verification, not current headset acceptance. The model output is an uncalibrated classifier score; hardware and field validity remain under evaluation.
