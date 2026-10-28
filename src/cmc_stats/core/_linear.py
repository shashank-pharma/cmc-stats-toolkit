"""Shared least-squares helper for the core modules (private; pure numpy/scipy)."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import linalg


@dataclass(frozen=True)
class OlsFit:
    """Coefficients, unscaled covariance (X'X)^-1, residual sum of squares and residual df."""

    coef: NDArray[np.float64]
    xtx_inv: NDArray[np.float64]
    rss: float
    df: int

    @property
    def mse(self) -> float:
        return self.rss / self.df


def ols(x: NDArray[np.float64], y: NDArray[np.float64]) -> OlsFit:
    """Least squares via QR, so (X'X)^-1 is formed without squaring the condition number.

    Raises:
        ValueError: the design matrix is rank deficient.
    """
    n, p = x.shape
    q, r = np.linalg.qr(x)
    if np.min(np.abs(np.diag(r))) <= 1e-12 * np.max(np.abs(np.diag(r))):
        raise ValueError("design matrix is rank deficient: a coefficient cannot be estimated")
    coef = np.asarray(linalg.solve_triangular(r, q.T @ y), dtype=np.float64)
    r_inv = np.asarray(linalg.solve_triangular(r, np.eye(p)), dtype=np.float64)
    resid = y - x @ coef
    return OlsFit(coef=coef, xtx_inv=r_inv @ r_inv.T, rss=float(resid @ resid), df=n - p)
