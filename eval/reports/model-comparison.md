# Model comparison

v2 with three model setups, both test sets, each question twice, graded. Cost per question is from the tokens used, at list prices.

Graded with an earlier version of the grader that only saw each question's own page, so scores are lower than in v1-vs-v2.md. Compare the rows with each other, not with the other report.

| Setup | Main set: graded pass | Main: passed both runs | Held-out: graded pass | Held-out: passed both runs | Median / 95th pct reply | Cost per question |
|---|---|---|---|---|---|---|
| haiku-4-5 | 83% | 66 of 86 | 66% | 12 of 19 | 4.1s / 5.8s | $0.0051 |
| haiku-5-5 | 91% | 75 of 86 | 82% | 14 of 19 | 3.9s / 6.8s | $0.0009 |
| sonnet-5-5 | 87% | 69 of 86 | 79% | 14 of 19 | 4.4s / 6.9s | $0.0163 |

haiku-4-5: 210 requests; tokens {"claude-haiku-4-5": {"input": 832476, "output": 49242, "thinking": 0}}; grader averages main {'correct': 1.81, 'complete': 1.88, 'actionable': 1.94, 'clear': 0.93}, held-out {'correct': 1.68, 'complete': 1.5, 'actionable': 1.84, 'clear': 0.87}
haiku-5-5: 210 requests; tokens {"claude-haiku-5-5": {"input": 1550283, "output": 82516, "thinking": 15736}}; grader averages main {'correct': 1.88, 'complete': 1.93, 'actionable': 1.98, 'clear': 0.96}, held-out {'correct': 1.79, 'complete': 1.66, 'actionable': 2, 'clear': 0.95}
sonnet-5-5: 210 requests; tokens {"claude-haiku-5-5": {"input": 197191, "output": 12507, "thinking": 534}, "claude-sonnet-5-5": {"input": 1346586, "output": 69746, "thinking": 1256}}; grader averages main {'correct': 1.86, 'complete': 1.95, 'actionable': 1.99, 'clear': 0.94}, held-out {'correct': 1.79, 'complete': 1.63, 'actionable': 1.97, 'clear': 0.95}
