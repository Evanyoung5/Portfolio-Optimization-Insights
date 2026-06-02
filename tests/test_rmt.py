import numpy as np
import pytest

from app.quant.rmt import (
    clean_correlation_rmt,
    compute_returns,
    covariance_from_clean_correlation,
    marchenko_pastur_bounds,
    sample_correlation,
    sample_covariance,
)


def test_compute_returns_handles_nans_and_zero_prices():
    prices = np.array(
        [
            [100.0, 50.0],
            [110.0, np.nan],
            [121.0, 55.0],
            [0.0, 60.0],
            [10.0, 66.0],
        ]
    )

    returns = compute_returns(prices)

    assert returns.shape == (4, 2)
    assert returns[0, 0] == pytest.approx(0.10)
    assert np.isnan(returns[0, 1])
    assert returns[2, 0] == pytest.approx(-1.0)
    assert np.isnan(returns[3, 0])
    assert not np.isinf(returns).any()


def test_compute_returns_supports_one_dimensional_prices():
    returns = compute_returns(np.array([100.0, 105.0, 110.25]))

    assert returns.shape == (2,)
    assert returns.tolist() == pytest.approx([0.05, 0.05])


def test_sample_covariance_uses_pairwise_finite_observations():
    returns = np.array(
        [
            [0.01, 0.02],
            [np.nan, 0.01],
            [0.03, np.nan],
        ]
    )

    covariance = sample_covariance(returns)

    assert covariance.shape == (2, 2)
    assert np.isfinite(covariance).all()
    assert covariance[0, 0] == pytest.approx(0.0002)
    assert covariance[1, 1] == pytest.approx(0.00005)
    assert covariance[0, 1] == 0


def test_sample_covariance_returns_zeros_for_too_few_observations():
    covariance = sample_covariance(np.array([[0.01, 0.02, 0.03]]))

    assert covariance.shape == (3, 3)
    assert np.array_equal(covariance, np.zeros((3, 3)))


def test_sample_correlation_is_finite_symmetric_and_unit_diagonal():
    returns = np.array(
        [
            [0.01, 0.03],
            [0.02, 0.02],
            [0.03, 0.01],
        ]
    )

    correlation = sample_correlation(returns)

    assert correlation.shape == (2, 2)
    assert np.isfinite(correlation).all()
    assert np.allclose(correlation, correlation.T)
    assert np.allclose(np.diag(correlation), 1.0)
    assert correlation[0, 1] == pytest.approx(-1.0)


def test_marchenko_pastur_bounds_for_well_sampled_matrix():
    lower, upper = marchenko_pastur_bounds(10, 100)

    expected_lower = (1 - np.sqrt(0.1)) ** 2
    expected_upper = (1 + np.sqrt(0.1)) ** 2
    assert lower == pytest.approx(expected_lower)
    assert upper == pytest.approx(expected_upper)


def test_marchenko_pastur_bounds_handles_rank_deficient_sample():
    lower, upper = marchenko_pastur_bounds(5, 2)

    assert lower == 0
    assert np.isfinite(upper)
    assert upper > 1


def test_clean_correlation_rmt_returns_valid_clean_matrix_with_nans():
    corr = np.array(
        [
            [1.0, 0.95, np.nan],
            [0.90, 1.0, 0.20],
            [np.nan, 0.20, 1.0],
        ]
    )

    cleaned = clean_correlation_rmt(corr, n_observations=20)

    assert cleaned.shape == (3, 3)
    assert np.isfinite(cleaned).all()
    assert np.allclose(cleaned, cleaned.T)
    assert np.allclose(np.diag(cleaned), 1.0)
    assert np.linalg.eigvalsh(cleaned).min() >= -1e-8
    assert np.max(np.abs(cleaned)) <= 1.0


def test_clean_correlation_rmt_handles_tiny_observation_count():
    corr = np.array([[1.0, 0.4], [0.4, 1.0]])

    cleaned = clean_correlation_rmt(corr, n_observations=1)

    assert cleaned.shape == (2, 2)
    assert np.isfinite(cleaned).all()
    assert np.allclose(np.diag(cleaned), 1.0)


def test_covariance_from_clean_correlation_handles_nan_volatilities():
    corr = np.array([[1.0, 0.5], [0.5, 1.0]])
    volatilities = np.array([0.2, np.nan])

    covariance = covariance_from_clean_correlation(corr, volatilities)

    assert covariance.shape == (2, 2)
    assert np.array_equal(covariance[1], np.zeros(2))
    assert covariance[0, 0] == pytest.approx(0.04)


def test_covariance_from_clean_correlation_rejects_size_mismatch():
    with pytest.raises(ValueError, match="volatilities length"):
        covariance_from_clean_correlation(np.eye(3), np.array([0.1, 0.2]))
