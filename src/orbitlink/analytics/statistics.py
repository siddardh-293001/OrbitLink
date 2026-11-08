"""Descriptive summaries and confidence intervals without hidden dependencies."""

from __future__ import annotations

import math
import statistics


_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
        15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
        27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def summarize(values: list[float]) -> dict[str, float | int | None]:
    """Summarize observations; 95% t interval is null for fewer than 2 runs."""
    if not values:
        return {"n": 0, "mean": None, "median": None, "p95": None,
                "sample_stddev": None, "ci95_low": None, "ci95_high": None}
    ordered = sorted(values)
    n = len(values)
    mean = statistics.fmean(values)
    p95 = ordered[max(0, math.ceil(0.95 * n) - 1)]
    if n < 2:
        return {"n": n, "mean": mean, "median": statistics.median(values), "p95": p95,
                "sample_stddev": None, "ci95_low": None, "ci95_high": None}
    std = statistics.stdev(values)
    if std == 0:
        return {"n": n, "mean": mean, "median": statistics.median(values), "p95": p95,
                "sample_stddev": 0.0, "ci95_low": None, "ci95_high": None}
    margin = _T95.get(n - 1, 1.96) * std / math.sqrt(n)
    return {"n": n, "mean": mean, "median": statistics.median(values), "p95": p95,
            "sample_stddev": std, "ci95_low": mean - margin, "ci95_high": mean + margin}
