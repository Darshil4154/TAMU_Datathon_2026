# Collection instruments

The source specification gives field codes and allowed values, but does not supply the full question titles or exact consent text. They cannot be reproduced verbatim yet. The project owner will add the existing `index.html`; this project does not replace it. The owner confirmed that survey consent covers both instruments.

## Check-in export contract

The form is titled `Datathon Energy Clock - 30-second check-in`. Participants are invited to check in about once an hour. Export Timestamp plus these bracket-coded fields:

| Code | Values |
| --- | --- |
| consent | I agree |
| anon_code | First name, optionally a letter; private linking field |
| energy | 1-5: Running on empty to Fully charged |
| focus | 1-5: Can't focus to Locked in |
| slept_h | 0-14 |
| caffeine_today | 0-15 |
| last_ate | Within 1 hour / 1-3 hours ago / 3-6 hours ago / 6+ hours ago |
| break_last_hour | Yes / No |
| progress | Stuck / Making progress / Almost done |
| would_help | Food, Coffee or tea, Water, A short break, A quiet space, Mentor help, Sleep, Nothing |

## Fatigue Lab export contract

The existing game measures reaction time and a ten-second estimate during an approximately 45-second task. Its form exports Timestamp plus bracket-coded `session_id`, `anon_code`, `energy`, `reaction_avg_ms`, `reaction_best_ms`, `reaction_slowest_ms`, `false_starts`, `time_estimate_s`, `time_error_s`, `device`, and `client_time`. Backups use plain field-code headers and may omit Timestamp. An optional consent field is honored when present.

Consent coverage is confirmed, but the agreement phrase `I agree` is not a substitute for documenting the exact participant-facing consent statement. Add the verbatim form titles/questions and consent wording from the actual instruments before submission.
