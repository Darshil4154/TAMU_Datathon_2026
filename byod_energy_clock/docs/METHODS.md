# Methods

Event start: 2026-11-07 at 11:00 America/Chicago. Offset timestamps take precedence for games. Naive form timestamps are Chicago local time; ambiguous or nonexistent DST times are rejected. Elapsed time uses absolute time. Morning includes hours 08-12; afternoon covers 13-17.

Survey consent must exactly match the trimmed value `I agree`. The project owner confirmed on 2026-11-08 that this consent covers both instruments. Games without a consent field must match a consented survey identity; explicit game refusals or blanks are excluded. Names are normalized, manual aliases applied, and stable pseudonyms privately assigned in random order. Names are not retained in processed outputs. Blank names are unlinked.

Only allowlisted headers are ingested. Forms use bracket codes, not question wording. Device backups use field codes. Sessions are deduplicated by UUID, preferring the form export and then the first backup. Invalid numeric values become missing; required energy or timestamp failures drop rows. Missing values are not zero and are not imputed. Free-text observations, areas and unknown columns do not enter processed data.

Game sessions pair to the same participant's nearest check-in within 45 minutes, inclusive, choosing the earlier check-in on a tie. Pairing is repeated within each filtered view. Repeated games may pair to one check-in; participant bootstrap handles dependence but cannot remove selection bias.

Centered energy subtracts each participant's mean within the selected view. Crash hour minimizes mean centered energy among hours with at least three contributors. Bootstrap resamples whole participants 2,000 times with seed 2026. Hour uncertainty is a percentile interval of circular offsets around the observed crash hour. It may wrap midnight; discrete multimodal estimates should be interpreted cautiously. The saved bootstrap hour shares preserve more detail than this interval alone.

Means and Spearman correlations use participant-cluster bootstrap CIs. Correlation bootstrap draws with no variation are discarded; if too many are unusable the CI is unavailable. Awareness gap uses game ratings, complete reaction/energy pairs, population standard deviations, and the formula z(energy) + z(reaction time). Paired survey correlations are reported separately.

Inference uses complete cases in `energy ~ hours_since_start + sin_hour + cos_hour + slept_h + caffeine_today + C(last_ate) + C(break_last_hour)`. Eight participants with at least two complete check-ins permit a random-intercept MixedLM. Otherwise, or on mixed-fit failure, OLS uses participant-clustered standard errors. Rank-deficient models are withheld. Association intervals are approximate, especially with few clusters.

Prediction uses ridge regression, alpha 1, with the same feature set and a fixed category vocabulary. Leave-one-participant-out evaluation trains every fold independently. The baseline is the training-fold energy mean. MAE weights each participant equally. Prediction bands use the empirical 95th percentile of held-out absolute residuals; they are not guaranteed prediction intervals. A model that does not beat baseline is replaced in the UI by eligible observed hourly means.

Request shares use answered check-ins as denominators. Cells need three contributing participants and three requesters. Food, coffee/tea, sleep and break request peaks yield a timing heuristic 30 minutes earlier. Recommendations are associations and preferences, not tested interventions.
