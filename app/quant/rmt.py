from __future__ import annotations

import numpy as np


def compute_returns(prices):
    """Compute simple period-over-period returns from price observations.

    Prices are expected as rows of observations and columns of assets. Invalid
    return observations, including NaNs and zero previous prices, are returned
    as NaN so downstream estimators can ignore them pairwise.
    """

    price_array, was_1d = _as_time_series(prices)
    if price_array.shape[0] < 2:
        empty = np.empty((0, price_array.shape[1]), dtype=float)
        return empty[:, 0] if was_1d else empty

    previous = price_array[:-1]
    current = price_array[1:]
    valid = np.isfinite(previous) & np.isfinite(current) & (previous != 0)
    returns = np.full_like(current, np.nan, dtype=float)
    np.divide(current - previous, previous, out=returns, where=valid)

    return returns[:, 0] if was_1d else returns


def sample_covariance(returns):
    """Compute a pairwise sample covariance matrix while ignoring NaNs."""

    return_array = _as_return_matrix(returns)
    n_assets = return_array.shape[1]
    covariance = np.zeros((n_assets, n_assets), dtype=float)

    for i in range(n_assets):
        for j in range(i, n_assets):
            mask = np.isfinite(return_array[:, i]) & np.isfinite(return_array[:, j])
            if int(mask.sum()) < 2:
                value = 0.0
            else:
                left = return_array[mask, i]
                right = return_array[mask, j]
                centered_left = left - left.mean()
                centered_right = right - right.mean()
                value = float(centered_left @ centered_right / (len(left) - 1))

            if i == j:
                value = max(value, 0.0)
            covariance[i, j] = value
            covariance[j, i] = value

    return covariance


def sample_correlation(returns):
    """Compute a sample correlation matrix while ignoring NaNs."""

    covariance = sample_covariance(returns)
    return _correlation_from_covariance(covariance)


def marchenko_pastur_bounds(n_assets, n_observations, variance=1.0):
    """Return Marchenko-Pastur lower and upper eigenvalue bounds.

    Uses the aspect ratio N / T, where N is the number of assets and T is the
    number of observations. When observations are fewer than assets, the sample
    matrix is rank deficient, so the lower bound is reported as zero.
    """

    n_assets = int(n_assets)
    n_observations = int(n_observations)
    variance = float(variance)

    if n_assets <= 0:
        raise ValueError("n_assets must be positive.")
    if n_observations <= 0:
        raise ValueError("n_observations must be positive.")
    if not np.isfinite(variance) or variance < 0:
        raise ValueError("variance must be a finite non-negative value.")

    aspect_ratio = n_assets / n_observations
    spread = np.sqrt(aspect_ratio)
    lower = variance * (1.0 - spread) ** 2
    upper = variance * (1.0 + spread) ** 2

    if n_observations <= n_assets:
        lower = 0.0

    return float(lower), float(upper)


def clean_correlation_rmt(corr, n_observations):
    """Denoise a correlation matrix by averaging eigenvalues inside MP noise."""

    correlation = _sanitize_correlation(corr)
    n_assets = correlation.shape[0]

    if n_assets <= 1:
        return correlation

    n_observations = int(n_observations)
    if n_observations < 2:
        return _normalize_correlation(_project_psd(correlation))

    _, lambda_plus = marchenko_pastur_bounds(n_assets, n_observations)
    eigenvalues, eigenvectors = np.linalg.eigh(correlation)
    eigenvalues = np.clip(eigenvalues, 0.0, None)

    noise_mask = eigenvalues <= lambda_plus
    cleaned_eigenvalues = eigenvalues.copy()
    if np.any(noise_mask):
        cleaned_eigenvalues[noise_mask] = float(eigenvalues[noise_mask].mean())

    cleaned = (eigenvectors * cleaned_eigenvalues) @ eigenvectors.T
    return _normalize_correlation(_project_psd(cleaned))


def covariance_from_clean_correlation(clean_corr, volatilities):
    """Convert a cleaned correlation matrix and asset volatilities to covariance."""

    correlation = _sanitize_correlation(clean_corr)
    vol_array = np.asarray(volatilities, dtype=float)
    if vol_array.ndim != 1:
        raise ValueError("volatilities must be a one-dimensional array.")
    if len(vol_array) != correlation.shape[0]:
        raise ValueError("volatilities length must match the correlation matrix size.")

    vol_array = np.nan_to_num(vol_array, nan=0.0, posinf=0.0, neginf=0.0)
    vol_array = np.clip(vol_array, 0.0, None)
    covariance = correlation * np.outer(vol_array, vol_array)
    covariance = (covariance + covariance.T) / 2.0
    np.fill_diagonal(covariance, vol_array**2)
    return covariance


def _as_time_series(values):
    array = np.asarray(values, dtype=float)
    was_1d = array.ndim == 1
    if array.ndim == 0:
        array = array.reshape(1, 1)
    elif array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("values must be one- or two-dimensional.")

    return array, was_1d


def _as_return_matrix(values):
    array, _ = _as_time_series(values)
    return array


def _sanitize_correlation(corr):
    matrix = np.asarray(corr, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("correlation matrix must be square.")

    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    matrix = (matrix + matrix.T) / 2.0
    matrix = np.clip(matrix, -1.0, 1.0)
    np.fill_diagonal(matrix, 1.0)
    return matrix


def _correlation_from_covariance(covariance):
    volatilities = np.sqrt(np.clip(np.diag(covariance), 0.0, None))
    denominator = np.outer(volatilities, volatilities)

    correlation = np.zeros_like(covariance, dtype=float)
    np.divide(covariance, denominator, out=correlation, where=denominator > 0)
    correlation = np.nan_to_num(correlation, nan=0.0, posinf=0.0, neginf=0.0)
    correlation = (correlation + correlation.T) / 2.0
    correlation = np.clip(correlation, -1.0, 1.0)
    np.fill_diagonal(correlation, 1.0)
    return correlation


def _project_psd(matrix):
    eigenvalues, eigenvectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    return (eigenvectors * eigenvalues) @ eigenvectors.T


def _normalize_correlation(matrix):
    normalized = _correlation_from_covariance(matrix)
    return _sanitize_correlation(normalized)
