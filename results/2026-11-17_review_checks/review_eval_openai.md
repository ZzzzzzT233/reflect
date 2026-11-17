# Weekly review evaluation — backend: openai (gpt-4o-mini)

| journal | entries | stats found | review evidence | found real pattern | false claims | invented | bad dates | ungrounded | cite P / R | causal words | hints w/o evidence | 1st-draft problems | rewrites | sentences removed | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| clear_pattern_s1 | 21 | sleep_mood | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | 0 | 0 | 1 | 1 | 0 | ✅ |
| clear_pattern_s2 | 21 | sleep_mood | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | 0 | 0 | 0 | 0 | 0 | ✅ |
| clear_pattern_s3 | 21 | sleep_mood | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | 0 | 0 | 1 | 1 | 0 | ✅ |
| missing_days_s1 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 0 | 1 | 1 | 0 | ✅ |
| missing_days_s2 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 0 | 2 | 2 | 0 | ✅ |
| missing_days_s3 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 0 | 0 | 0 | 0 | ✅ |
| no_pattern_s1 | 21 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 0 | 2 | 2 | 0 | ✅ |
| no_pattern_s2 | 21 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 0 | 2 | 1 | 0 | ✅ |
| no_pattern_s3 | 21 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 0 | 4 | 3 | 0 | ✅ |

*causal words* = phrases like “because of”, “boosts”, “led to” in any review; *hints w/o evidence* = “affected”, “linked”, “tended to”… in a review that said evidence is not enough. Both are reported, not part of pass/fail. *1st-draft problems* = rule breaks the checker found in the model's first draft (all weeks); *rewrites* = times the review was sent back; *sentences removed* = deleted by the last-resort scrub.

## Pass rate by kind

| kind | passed |
|---|---|
| clear_pattern | 3 / 3 |
| missing_days | 3 / 3 |
| no_pattern | 3 / 3 |

## What each review said (final week)

- **clear_pattern_s1** — This week, your average mood was neutral, with three low-mood days. You had some late nights, which may have affected your mood, as seen in the pattern where low-mood days followed late nights. It's important to keep tracking your sleep and mood to see how they relate over time.
- **clear_pattern_s2** — This week had an average mood score of 0.57, indicating a generally good week overall, though there were two days of low mood. You experienced late nights on two occasions, which may have contributed to those low mood days.
- **clear_pattern_s3** — This week had a slightly positive average mood of +0.14, indicating a generally neutral experience overall. You had two low mood days, particularly on the 19th and 20th, which coincided with late nights and less sleep. It's great to see you consistently logged your bedtime every day, which is a positive step towards maintaining a routine.
- **missing_days_s1** — This week had a low average mood of -1, indicating a challenging time, especially on November 16th when you reported feeling very low. You managed to journal on two days, but there were several missed entries, which means there isn't enough evidence yet to identify any clear patterns in your mood and activities.
- **missing_days_s2** — This week, you had an average mood of +0.33, which is neutral, and you recorded three entries. You experienced one low mood day on November 20, and had a late night on that same day. More entries are needed to identify any patterns or relationships.
- **missing_days_s3** — This week had an average mood of +0.33, indicating a generally neutral experience, with one low mood day on November 20th. You recorded a late night once and managed to get an average of 6.8 hours of sleep, which is slightly below the recommended amount. Overall, there isn't enough evidence yet to identify any patterns, as there are too few entries and missing days.
- **no_pattern_s1** — This week had an average mood score of 0.86, indicating a generally good week, though there were two low mood days on November 17 and 19. You experienced late nights on two occasions, and more entries are needed to explore any potential relationships with your mood and sleep quality.
- **no_pattern_s2** — This week was generally positive with an average mood score of +1.29, indicating a good week overall. You maintained a consistent journaling habit, noting your bedtime every day, which is great for tracking your sleep patterns. However, there isn't enough evidence yet for any specific patterns, as we need more entries to draw clearer insights.
- **no_pattern_s3** — This week, you had an average mood score of +0.29, indicating a generally neutral week with some positive moments. You experienced one low mood day on November 17th and had a couple of late nights. However, there isn't enough evidence yet to identify any clear patterns in your mood or activities, as more entries are needed.

## Extraction accuracy on these journals

| journal | mood ±1 | sleep ±0.5h | bedtime | activities F1 |
|---|---|---|---|---|
| clear_pattern_s1 | 1.0 | 1.0 | 1.0 | 0.89 |
| clear_pattern_s2 | 1.0 | 1.0 | 1.0 | 0.85 |
| clear_pattern_s3 | 1.0 | 1.0 | 1.0 | 0.93 |
| missing_days_s1 | 1.0 | 1.0 | 1.0 | 0.82 |
| missing_days_s2 | 1.0 | 1.0 | 1.0 | 0.91 |
| missing_days_s3 | 1.0 | 1.0 | 1.0 | 0.92 |
| no_pattern_s1 | 1.0 | 1.0 | 1.0 | 0.88 |
| no_pattern_s2 | 1.0 | 1.0 | 1.0 | 0.85 |
| no_pattern_s3 | 1.0 | 1.0 | 1.0 | 0.92 |

LLM calls: 195 · tokens: 170780