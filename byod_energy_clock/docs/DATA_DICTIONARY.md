# Data dictionary

| Field | Meaning and provenance |
| --- | --- |
| participant_id | Derived stable pseudonym; U-prefixed IDs are unlinked blank-name responses |
| time | Derived UTC timestamp from form or preferred game client time |
| energy, focus | Self-reported scales from 1 to 5 |
| slept_h | Self-reported sleep, 0-14 hours |
| caffeine_today | Self-reported caffeinated drinks, 0-15 |
| last_ate | Self-reported Within 1 hour / 1-3 hours ago / 3-6 hours ago / 6+ hours ago |
| break_last_hour | Self-reported Yes / No |
| progress | Self-reported Stuck / Making progress / Almost done |
| would_help | Allowlisted self-reported request selections |
| session_id | Game UUID, used for deduplication |
| reaction_avg_ms, reaction_best_ms, reaction_slowest_ms | Measured reaction milliseconds; accepted range 100-2000 |
| false_starts | Measured early attempts; missing is not zero |
| time_estimate_s | Measured seconds for intended ten-second interval; accepted range 1-60 |
| time_error_s | Derived estimate minus ten seconds |
| device | Collection mode: station / roving |
| hours_since_start | Derived elapsed hours from event start |
| clock_hour, night_phase, sin_hour, cos_hour | Derived Chicago clock features |
| checkin_energy, checkin_time, pair_minutes | Derived linkage to nearest consented same-person check-in within 45 minutes |
| is_fake | Present and true on synthetic fixture rows; never a production-data generator |

Missing CSV cells remain missing. Analysis JSON uses null for unavailable or suppressed estimates; `n < 3` is a suppression label, not a count. In chart hover, n is the number of distinct contributing participants. Rows count observations and can exceed n. Room observation exports include only validated timestamps and numeric measures, never notes or area text.
