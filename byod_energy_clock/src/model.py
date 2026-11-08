"""Honest participant-held-out prediction and association models."""
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.linear_model import Ridge
from .ingest import CHOICES

NUMERIC = ["hours_since_start", "sin_hour", "cos_hour", "slept_h", "caffeine_today"]
CATEGORICAL = ["last_ate", "break_last_hour"]
FORMULA = "energy ~ hours_since_start + sin_hour + cos_hour + slept_h + caffeine_today + C(last_ate) + C(break_last_hour)"


def design(frame: pd.DataFrame) -> pd.DataFrame:
    """Fixed category vocabulary makes held-out categories safe without leakage."""
    parts = [frame[NUMERIC].astype(float)]
    for col in CATEGORICAL:
        for value in CHOICES[col][1:]:
            parts.append(pd.DataFrame({f"{col}={value}": frame[col].eq(value).astype(float)}, index=frame.index))
    return pd.concat(parts, axis=1)


def fit_models(checks: pd.DataFrame) -> dict:
    """Complete-case modeling; baseline mean is fit separately inside each fold."""
    data = checks.dropna(subset=NUMERIC + CATEGORICAL + ["energy"]).copy()
    n = data.participant_id.nunique()
    result = {"n": int(n) if n >= 3 else "n < 3", "rows": len(data) if n >= 3 else None, "status": "Insufficient complete data for participant-held-out evaluation.", "mae": None, "baseline_mae": None, "beats_baseline": False, "coefficients": [], "association_status": "Insufficient complete data.", "predictor": None}
    if n < 3 or len(data) < 6:
        return result
    x = design(data)
    predictions, truths, baselines, heldout_ids = [], [], [], []
    for person in data.participant_id.unique():
        test = data.participant_id.eq(person)
        model = Ridge(alpha=1).fit(x[~test], data.loc[~test, "energy"])
        predictions.extend(np.clip(model.predict(x[test]), 1, 5))
        truths.extend(data.loc[test, "energy"])
        baselines.extend([data.loc[~test, "energy"].mean()] * int(test.sum()))
        heldout_ids.extend([person] * int(test.sum()))
    errors = np.abs(np.array(predictions) - truths)
    baseline_errors = np.abs(np.array(baselines) - truths)
    # Weight each participant equally in evaluation, regardless of check-in count.
    scored = pd.DataFrame({"id": heldout_ids, "error": errors, "baseline": baseline_errors})
    mae = float(scored.groupby("id").error.mean().mean())
    baseline = float(scored.groupby("id").baseline.mean().mean())
    fitted = Ridge(alpha=1).fit(x, data.energy)
    result.update(mae=mae, baseline_mae=baseline, beats_baseline=mae < baseline, status="Model beats the baseline." if mae < baseline else "Model does not beat the baseline. Use observed hourly means.", predictor={"columns": list(x.columns), "coef": fitted.coef_.tolist(), "intercept": float(fitted.intercept_), "error95": float(np.quantile(errors, .95)), "elapsed_range": [float(data.hours_since_start.min()), float(data.hours_since_start.max())]})
    # Only publish inferential estimates with sufficient rank and residual degrees of freedom.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            base = smf.ols(FORMULA, data=data)
            if np.linalg.matrix_rank(base.exog) < base.exog.shape[1] or len(data) <= base.exog.shape[1] + 2:
                result["association_status"] = "Coefficients unavailable: insufficient independent variation or residual degrees of freedom."
                return result
            repeat_count = int((data.groupby("participant_id").size() >= 2).sum())
            if repeat_count >= 8:
                try:
                    fit = smf.mixedlm(FORMULA, data=data, groups=data.participant_id).fit(reml=False, method="lbfgs", disp=False)
                    if not fit.converged or not np.isfinite(fit.bse).all():
                        raise ValueError("Unstable fit")
                    label = "MixedLM with participant random intercept"
                except (ValueError, np.linalg.LinAlgError):
                    fit = base.fit(cov_type="cluster", cov_kwds={"groups": data.participant_id})
                    label = "Clustered OLS fallback: mixed model did not converge reliably"
            else:
                fit = base.fit(cov_type="cluster", cov_kwds={"groups": data.participant_id})
                label = "OLS with participant-clustered standard errors"
            ci = fit.conf_int()
            result["coefficients"] = [{"term": term, "estimate": float(value), "low": float(ci.loc[term, 0]), "high": float(ci.loc[term, 1])} for term, value in fit.params.items() if term != "Group Var" and np.isfinite([value, *ci.loc[term]]).all()]
            result["association_status"] = label + ". Associations, not causes; small-cluster uncertainty may be optimistic."
    except (ValueError, np.linalg.LinAlgError) as exc:
        result["association_status"] = "Association model unavailable: " + type(exc).__name__
    return result


def predict(model: dict, row: pd.DataFrame) -> tuple[float, float, float] | None:
    """Evaluate saved ridge coefficients with an empirical held-out error band."""
    saved = model.get("predictor")
    if not saved or not model["beats_baseline"]:
        return None
    point = float(np.clip(design(row)[saved["columns"]].to_numpy()[0] @ np.array(saved["coef"]) + saved["intercept"], 1, 5))
    return point, max(1., point - saved["error95"]), min(5., point + saved["error95"])
