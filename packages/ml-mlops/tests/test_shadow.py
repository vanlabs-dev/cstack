from typing import Any

import numpy as np
import pandas as pd
from cstack_ml_mlops import shadow_score, should_promote


class _FixedPredictor:
    """Returns a fixed -1/1 prediction array."""

    def __init__(self, predictions: list[int]) -> None:
        self._predictions = np.array(predictions)

    def predict(self, df: pd.DataFrame) -> Any:
        return self._predictions[: len(df)]


def _make_df(n: int) -> pd.DataFrame:
    return pd.DataFrame({"feat_a": np.arange(n, dtype=float), "feat_b": np.arange(n, dtype=float)})


def test_shadow_score_perfect_agreement() -> None:
    n = 200
    pred = [1] * 198 + [-1] * 2
    champion = _FixedPredictor(pred)
    challenger = _FixedPredictor(pred)
    cmp = shadow_score(champion, challenger, _make_df(n))
    assert cmp.agreement_pct == 1.0
    assert cmp.alert_volume_delta_pct == 0.0
    assert cmp.disagreement_examples == []


def test_shadow_score_alert_volume_delta() -> None:
    n = 200
    champion = _FixedPredictor([1] * 198 + [-1] * 2)
    challenger = _FixedPredictor([1] * 196 + [-1] * 4)
    cmp = shadow_score(champion, challenger, _make_df(n))
    assert cmp.champion_anomalies == 2
    assert cmp.challenger_anomalies == 4
    assert cmp.alert_volume_delta_pct == 100.0


def test_should_promote_blocks_when_alert_delta_too_high() -> None:
    champion = _FixedPredictor([1] * 200)
    challenger = _FixedPredictor([1] * 150 + [-1] * 50)
    cmp = shadow_score(champion, challenger, _make_df(200))
    promote, reason = should_promote(cmp, max_alert_delta_pct=20.0)
    assert promote is False
    assert "alert volume delta" in reason


def test_should_promote_passes_when_volumes_close() -> None:
    pred_c = [1] * 195 + [-1] * 5
    pred_x = [1] * 194 + [-1] * 6
    champion = _FixedPredictor(pred_c)
    challenger = _FixedPredictor(pred_x)
    cmp = shadow_score(champion, challenger, _make_df(200))
    promote, _reason = should_promote(cmp, max_alert_delta_pct=25.0)
    assert promote is True


def test_should_promote_blocks_when_too_few_rows() -> None:
    champion = _FixedPredictor([1] * 50)
    challenger = _FixedPredictor([1] * 50)
    cmp = shadow_score(champion, challenger, _make_df(50))
    promote, reason = should_promote(cmp)
    assert promote is False
    assert "too few" in reason
