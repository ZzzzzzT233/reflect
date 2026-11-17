# Weekly review evaluation — backend: openai (gpt-4o-mini)

| journal | entries | stats found | review evidence | found real pattern | false claims | invented | bad dates | ungrounded | cite P / R | causal words | hints w/o evidence | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| clear_pattern_s1 | 21 | sleep_mood | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | 0 | 1 | ✅ |
| clear_pattern_s2 | 21 | sleep_mood | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | 0 | 2 | ✅ |
| clear_pattern_s3 | 21 | sleep_mood | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | 1 | 0 | ✅ |
| missing_days_s1 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 1 | 1 | ✅ |
| missing_days_s2 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 2 | 1 | ✅ |
| missing_days_s3 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 0 | ✅ |
| no_pattern_s1 | 21 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 3 | ✅ |
| no_pattern_s2 | 21 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 1 | ✅ |
| no_pattern_s3 | 21 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | 0 | 2 | ✅ |

*causal words* = phrases like “because of”, “boosts”, “led to” in any review; *hints w/o evidence* = “affected”, “linked”, “tended to”… in a review that said evidence is not enough. Both are reported, not part of pass/fail.

## Pass rate by kind

| kind | passed |
|---|---|
| clear_pattern | 3 / 3 |
| missing_days | 3 / 3 |
| no_pattern | 3 / 3 |

## What each review said (final week)

- **clear_pattern_s1** — This week, you had a neutral average mood of 0, with three low mood days. You also experienced late nights on three occasions, which may have affected your sleep quality, averaging 6.8 hours per night.
- **clear_pattern_s2** — This week had an average mood of +0.57, indicating a generally good week, although there were two low mood days. You successfully logged your bedtime every day, which is great for tracking your sleep patterns.
- **clear_pattern_s3** — This week had a neutral average mood of 0, with two low-mood days on the 19th and 20th. You experienced late nights on those days, which aligns with a pattern where low mood days tend to follow late nights, particularly when you had less than 6 hours of sleep. Overall, there isn't enough evidence yet to draw strong conclusions, but it's clear that sleep patterns are something to keep an eye on.
- **missing_days_s1** — This week, you had a low average mood of -1, with one day of particularly low mood on November 16th. You managed to get an average of 6.8 hours of sleep, but there were only two entries this week, which isn't enough to identify any patterns.
- **missing_days_s2** — This week had a neutral average mood of +0.33, with one low mood day on November 20th. You had a late night on that same day, which may have contributed to your lower mood and shorter sleep of just 4 hours. Overall, there isn't enough evidence yet for a pattern due to missing days and insufficient entries.
- **missing_days_s3** — This week, you had an average mood of +0.33, which is neutral overall. You recorded three entries, but unfortunately, there isn't enough evidence yet to identify any patterns, as you need more entries and days covered. Keep journaling to capture more details and entries in the coming weeks.
- **no_pattern_s1** — This week, you had an average mood score of 0.71, indicating a generally good week overall. You experienced low moods on two days, specifically on November 17 and 19, and had a couple of late nights that may have affected your sleep. However, your mood improved significantly on several days, particularly on November 18, 20, and 22, which were marked by positive emotions like joy and gratitude.
- **no_pattern_s2** — This week, you had an average mood score of +1, indicating a good week overall. You engaged in various activities, including classes and family calls, while managing to get an average of 7.1 hours of sleep. However, there isn't enough evidence yet for a pattern, as there are too few entries to establish any clear relationships.
- **no_pattern_s3** — This week, you had an average mood score of 0.14, indicating a neutral week overall. You experienced one low mood day on November 17th, and had a mix of activities including exercise, studying, and social time. However, there isn't enough evidence yet to identify any clear patterns in your mood or activities, as the data is still developing.

## Extraction accuracy on these journals

| journal | mood ±1 | sleep ±0.5h | bedtime | activities F1 |
|---|---|---|---|---|
| clear_pattern_s1 | 1.0 | 1.0 | 1.0 | 0.87 |
| clear_pattern_s2 | 1.0 | 1.0 | 1.0 | 0.85 |
| clear_pattern_s3 | 1.0 | 1.0 | 1.0 | 0.92 |
| missing_days_s1 | 1.0 | 1.0 | 1.0 | 0.89 |
| missing_days_s2 | 1.0 | 1.0 | 1.0 | 0.91 |
| missing_days_s3 | 1.0 | 1.0 | 1.0 | 0.91 |
| no_pattern_s1 | 1.0 | 1.0 | 1.0 | 0.86 |
| no_pattern_s2 | 1.0 | 1.0 | 1.0 | 0.86 |
| no_pattern_s3 | 1.0 | 1.0 | 1.0 | 0.92 |

LLM calls: 189 · tokens: 149539