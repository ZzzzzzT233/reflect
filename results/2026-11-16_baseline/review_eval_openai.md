# Weekly review evaluation — backend: openai (gpt-4o-mini)

| journal | entries | stats found | review evidence | found real pattern | false claims | invented | bad dates | ungrounded | cite P / R | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| clear_pattern_s1 | 21 | sleep_mood, stressor:problem set due tomorrow | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | ✅ |
| clear_pattern_s2 | 21 | sleep_mood, stressor:feeling drained, stressor:feeling low, stressor:problem set due tomorrow | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | ✅ |
| clear_pattern_s3 | 21 | sleep_mood, stressor:problem set due tomorrow | enough | ✓ | 0 | 0 | 0 | 0 | 1.0 / 1.0 | ✅ |
| missing_days_s1 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | ✅ |
| missing_days_s2 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | ✅ |
| missing_days_s3 | 8 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | ✅ |
| no_pattern_s1 | 21 | — | not_enough | ✓ | 0 | 0 | 0 | 0 | – | ✅ |
| no_pattern_s2 | 21 | stressor:everything felt heavy | enough | ✓ | 0 | 0 | 0 | 0 | – | ❌ |
| no_pattern_s3 | 21 | stressor:felt awful | enough | ✓ | 0 | 0 | 0 | 0 | – | ❌ |

## Pass rate by kind

| kind | passed |
|---|---|
| clear_pattern | 3 / 3 |
| missing_days | 3 / 3 |
| no_pattern | 1 / 3 |

## What each review said (final week)

- **clear_pattern_s1** — This week, you followed the suggestion to include your bedtime every day, which is great! However, you experienced low moods on several days, particularly after late nights. It's important to note that 6 of your 6 low-mood days followed a late night, indicating a strong link between your sleep patterns and mood.
- **clear_pattern_s2** — This week, you had a challenging time with your mood, especially on the 16th and 17th, where you reported feelings of sadness and disappointment. You aimed for earlier bedtimes, but it seems you followed through on only two days. It's great that you had some better days later in the week, especially on the 18th and 19th, where your mood improved significantly.
- **clear_pattern_s3** — This week, you continued to track your sleep and mood, which is great! However, your average mood was quite low at 0.14, with two low-mood days on the 19th and 20th. It's important to note that your mood tended to be lower after late nights, as seen in the pattern where all low-mood days followed nights with less sleep or late bedtimes.
- **missing_days_s1** — This week, you had two entries with an average mood of -1, indicating some challenges, especially on November 16th when you reported feeling sad and confused. You also had a late night on that day, which might have affected your mood and sleep. It seems like there isn't enough evidence yet to identify any clear patterns due to the limited number of entries and missing days.
- **missing_days_s2** — This week, you had a mix of moods and activities, with an average mood of 0.33 and some late nights. You followed the suggestion to continue journaling daily, but it seems you missed a few days, which might have limited your insights.
- **missing_days_s3** — This week, you had a mix of moods, with a low point on November 20th. You also had a late night on the 19th, which might have affected your mood and sleep. It's great that you were able to study and engage socially, but it seems like there isn't enough evidence yet to identify any clear patterns in your journaling.
- **no_pattern_s1** — This week, you continued journaling about your mood and sleep, which is great! However, there isn't enough evidence yet to identify any clear patterns in your entries, as there are currently no computed patterns. This could be due to the variability in your mood and sleep over the past weeks.
- **no_pattern_s2** — This week, you maintained a consistent journaling practice with entries every day. Your average mood was quite low at 1, but you did have some brighter moments, especially on the 18th and 20th. It seems like the feeling of 'everything felt heavy' is still relevant, as it appeared on a few days in previous weeks.
- **no_pattern_s3** — This week, you followed through on noting your bedtime every day, which is great! Your average mood improved compared to the previous weeks, but there was a low mood day on November 17th linked to feeling awful. It's encouraging to see some positive emotions later in the week, especially on November 19th and 20th.

## Extraction accuracy on these journals

| journal | mood ±1 | sleep ±0.5h | bedtime | activities F1 |
|---|---|---|---|---|
| clear_pattern_s1 | 1.0 | 1.0 | 1.0 | 0.88 |
| clear_pattern_s2 | 1.0 | 1.0 | 1.0 | 0.84 |
| clear_pattern_s3 | 1.0 | 1.0 | 1.0 | 0.9 |
| missing_days_s1 | 1.0 | 1.0 | 1.0 | 0.85 |
| missing_days_s2 | 1.0 | 1.0 | 1.0 | 0.91 |
| missing_days_s3 | 1.0 | 1.0 | 1.0 | 0.83 |
| no_pattern_s1 | 1.0 | 1.0 | 1.0 | 0.9 |
| no_pattern_s2 | 1.0 | 1.0 | 1.0 | 0.86 |
| no_pattern_s3 | 1.0 | 1.0 | 1.0 | 0.86 |

LLM calls: 195 · tokens: 132672