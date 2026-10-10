"""Small, dependency-light Riemannian EEG feature utilities."""

from __future__ import annotations

import numpy as np


EPS = 1e-8


def _spectral_function(matrix: np.ndarray, function) -> np.ndarray:
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    values = np.maximum(values, EPS)
    return (vectors * function(values)) @ vectors.T


def matrix_log(matrix: np.ndarray) -> np.ndarray:
    return _spectral_function(matrix, np.log)


def matrix_exp(matrix: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    return (vectors * np.exp(values)) @ vectors.T


def matrix_inv_sqrt(matrix: np.ndarray) -> np.ndarray:
    return _spectral_function(matrix, lambda value: value ** -0.5)


def log_euclidean_mean(covariances: np.ndarray) -> np.ndarray:
    return matrix_exp(np.mean([matrix_log(covariance) for covariance in covariances], axis=0))


def regularized_covariance(epoch: np.ndarray, shrinkage: float = 0.10) -> np.ndarray:
    """Return an SPD covariance matrix for one channels x samples EEG epoch."""
    centered = epoch - epoch.mean(axis=1, keepdims=True)
    covariance = centered @ centered.T / max(1, centered.shape[1] - 1)
    scale = np.trace(covariance) / covariance.shape[0]
    covariance = (1.0 - shrinkage) * covariance + shrinkage * scale * np.eye(covariance.shape[0])
    return (covariance + covariance.T) / 2.0


def epochs_to_covariances(epochs: np.ndarray, shrinkage: float = 0.10) -> np.ndarray:
    return np.asarray([regularized_covariance(epoch, shrinkage) for epoch in epochs])


def align_covariances(covariances: np.ndarray, center: np.ndarray) -> np.ndarray:
    transform = matrix_inv_sqrt(center)
    return np.asarray([transform @ covariance @ transform for covariance in covariances])


def align_by_subject(covariances: np.ndarray, subjects: np.ndarray) -> np.ndarray:
    """Unsupervised subject-wise recentering at the identity matrix."""
    aligned = np.empty_like(covariances)
    for subject in np.unique(subjects):
        mask = subjects == subject
        center = log_euclidean_mean(covariances[mask])
        aligned[mask] = align_covariances(covariances[mask], center)
    return aligned


def tangent_features_at_identity(covariances: np.ndarray) -> np.ndarray:
    """Vectorize log-mapped SPD matrices with the isometric sqrt(2) convention."""
    n_channels = covariances.shape[1]
    upper = np.triu_indices(n_channels)
    off_diagonal = upper[0] != upper[1]
    features = []
    for covariance in covariances:
        tangent = matrix_log(covariance)
        vector = tangent[upper].copy()
        vector[off_diagonal] *= np.sqrt(2.0)
        features.append(vector)
    return np.asarray(features)


def calibrated_tangent_features(
    baseline_epochs: np.ndarray,
    target_epochs: np.ndarray,
    shrinkage: float = 0.10,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit an unlabeled personal center, then transform target epochs."""
    baseline_covariances = epochs_to_covariances(baseline_epochs, shrinkage)
    center = log_euclidean_mean(baseline_covariances)
    target_covariances = epochs_to_covariances(target_epochs, shrinkage)
    aligned = align_covariances(target_covariances, center)
    return tangent_features_at_identity(aligned), center
