"""Writes data/demo_journal.json: a 3-week synthetic journal (fictional student)
with hand-written gold labels. Used for the demo and to score the extractor."""
import json
N = None
def g(mood, emo, sleep, bed, acts, people=(), stress=(), high=(), fu=(False, N, ""), risk=False):
    return {"mood_score": mood, "emotions": list(emo), "sleep_hours": sleep, "bedtime": bed,
            "activities": list(acts), "people": list(people), "stressors": list(stress),
            "highlights": list(high),
            "suggestion_followup": {"mentioned": fu[0], "followed": fu[1], "evidence": fu[2]},
            "risk_flag": risk}
E = [
("2026-10-05", "Slept about 7 hours, in bed at 23:45. Classes all morning, then started the 1.125 problem set in the afternoon. Grabbed dinner with Mia, which was nice. The PS is way bigger than I thought and it's due Tuesday morning, so I'm going to push through tonight.",
 g(0, ["nervousness"], 7, "23:45", ["class", "studying", "deadline_work", "social"], ["Mia"], ["problem set"], ["dinner with Mia"])),
("2026-10-06", "Went to bed at 2:30 after finishing the PS, maybe 5 hours of sleep. Dragged myself through class and couldn't focus at all. Snapped at my roommate over the dishes. Felt kind of useless all day.",
 g(-1, ["sadness", "annoyance"], 5, "02:30", ["class"], ["roommate"], ["tired", "couldn't focus"])),
("2026-10-07", "Slept 8 hours, in bed by 23:30. Went to the gym this morning for the first time in two weeks and felt so much better. Office hours were really useful. Another problem set due tomorrow morning though, so it'll be a long night.",
 g(1, ["joy", "relief"], 8, "23:30", ["exercise", "studying", "deadline_work"], ["TA"], ["problem set"], ["gym", "office hours"])),
("2026-10-08", "Bed at 3am, about 4.5 hours of sleep. Submitted the stats PS at 8:58. Skipped lunch, felt anxious and flat the whole day. Didn't really talk to anyone.",
 g(-1, ["nervousness", "sadness"], 4.5, "03:00", ["class", "studying"], [], ["stats problem set"])),
("2026-10-09", "Slept in, 9 hours (bed around 00:30). Called mom in the afternoon and we talked for an hour. Lazy evening watching shows.",
 g(1, ["joy", "caring"], 9, "00:30", ["family_call", "rest", "screen_time"], ["mom"], [], ["call with mom"])),
("2026-10-10", "7.5 hours, bed at 1:15. Long walk along the Charles with Mia and Jake, then we cooked dinner together. Best day this week.",
 g(2, ["joy", "gratitude"], 7.5, "01:15", ["outdoors", "social"], ["Mia", "Jake"], [], ["walk along the Charles", "cooking with friends"])),
("2026-10-11", "Bed at midnight, 8 hours. Spent most of the day reading for next week, a bit bored. Groceries and laundry.",
 g(0, ["neutral"], 8, "00:00", ["studying", "chores"])),
# week 2 -- after the first weekly review
("2026-10-12", "8 hours, bed 23:40. Started the new PS early this time. Did half of it tonight and stopped at 12:15 like I planned. Feels weird to stop but good.",
 g(1, ["optimism", "pride"], 8, "23:40", ["class", "studying"], [], [], ["started PS early"], (True, True, "stopped at 12:15 like I planned"))),
("2026-10-13", "7 hours, bed 00:50. Gym at 7am, then class. Lunch with Jake. Pretty solid day.",
 g(1, ["joy"], 7, "00:50", ["exercise", "class", "social"], ["Jake"], [], ["gym", "lunch with Jake"])),
("2026-10-14", "Bed 00:20, 7.5 hours. Finished the PS a day early and actually went to bed at a normal time. Group project meeting was frustrating, nobody had read the brief.",
 g(0, ["annoyance", "relief"], 7.5, "00:20", ["class", "studying"], ["project group"], ["group project"], ["finished PS early"], (True, True, "went to bed at a normal time"))),
("2026-10-15", "7 hours, bed 00:45. Quiet day, class and library. Talked to mom briefly. Then found out the group slides are due tomorrow at 9 and nobody has started. Ugh.",
 g(0, ["annoyance"], 7, "00:45", ["class", "studying", "family_call", "deadline_work"], ["mom", "project group"], ["group project"])),
("2026-10-16", "Bed at 2, maybe 5.5 hours. I broke the rule, the slides had to get done. Tired and irritated all day.",
 g(-1, ["annoyance", "disappointment"], 5.5, "02:00", ["class"], ["project group"], ["group project", "tired"], [], (True, False, "I broke the rule"))),
("2026-10-17", "Slept 9.5 hours, bed 23:30. Climbing gym with Mia in the afternoon. Feeling human again.",
 g(2, ["joy", "relief"], 9.5, "23:30", ["exercise", "social"], ["Mia"], [], ["climbing with Mia"])),
("2026-10-18", "8 hours, bed 00:10. Planned the week. Midterms on Tuesday and Wednesday, a bit nervous. Video call with my sister.",
 g(0, ["nervousness"], 8, "00:10", ["studying", "family_call"], ["sister"], ["midterms"], ["call with sister"])),
# week 3
("2026-10-19", "7.5 hours, bed 00:30. Studied all day for the econ midterm tomorrow. I'll try to stop by 12:30 but I don't feel ready.",
 g(0, ["nervousness"], 7.5, "00:30", ["studying"], [], ["midterm"], [], (True, None, "I'll try to stop by 12:30"))),
("2026-10-20", "Ended up cramming until 3, about 4 hours of sleep. The midterm went badly, I blanked on two questions. Cried a bit after.",
 g(-2, ["sadness", "disappointment"], 4, "03:00", ["class", "studying"], [], ["midterm"], [], (True, False, "cramming until 3"))),
("2026-10-21", "Crashed early, bed at 23:00, 8.5 hours. Second midterm went much better than yesterday's. Celebrated with Jake and Mia with pizza.",
 g(1, ["relief", "joy"], 8.5, "23:00", ["class", "social"], ["Jake", "Mia"], [], ["second midterm went well", "pizza with friends"])),
("2026-10-22", "8 hours, bed 00:15. Gym in the morning. Feeling lighter now that midterms are done. Started reading for the term project.",
 g(1, ["relief", "optimism"], 8, "00:15", ["exercise", "studying"], [], [], ["gym"])),
("2026-10-23", "Bed at 1:40, about 6 hours. Was on my phone scrolling until late, not even working. Groggy and a bit low.",
 g(-1, ["sadness"], 6, "01:40", ["class", "screen_time"], [], ["tired"])),
("2026-10-24", "9 hours, bed 00:30. Long walk and brunch with Mia. Called mom in the evening.",
 g(2, ["joy", "gratitude"], 9, "00:30", ["outdoors", "social", "family_call"], ["Mia", "mom"], [], ["brunch with Mia", "call with mom"])),
("2026-10-25", "7.5 hours, bed 00:45. Slow day. Laundry and some reading. A bit anxious about the term project proposal due Thursday.",
 g(0, ["nervousness"], 7.5, "00:45", ["chores", "studying"], [], ["term project proposal"])),
]
json.dump([{"date": d, "text": t, "gold": x} for d, t, x in E],
          open(__file__.replace("make_demo.py", "demo_journal.json"), "w"), indent=1, ensure_ascii=False)
print(len(E), "entries")
