# Energy Clock model card

Live collection data only.

Predicts self-reported energy, not health or ability. Complete-case ridge regression; no imputation. Features: elapsed hours, cyclic clock hour, sleep, caffeine, meal recency, break. Leave-one-participant-out CV, equal participant weighting; training-fold mean baseline.

Status: Model beats the baseline.

MAE: 1.0215962958907765; baseline MAE: 1.1131055363321798; participants: 17.

The displayed prediction band uses the 95th percentile of held-out absolute residuals. It is descriptive and has no guaranteed prospective coverage. Small convenience sample, selection bias, repeated participants, device confounding and temporal drift limit generalization. No causal or medical claims.
