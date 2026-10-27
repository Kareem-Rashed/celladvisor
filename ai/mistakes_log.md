# AI mistakes log (overview, Appendix B)

| ID | Log entry | What was wrong | How you caught it | Would a weaker check have missed it? |
|---|---|---|---|---|
| M001 | L004 | The first version put the code in src/celladvisor/ (from AGENTS.md) and expected a parser returning (name, area, pins, truth_table), but the repo keeps modules directly in src/ and hdlib.py does not read cell area | Running the tests in the pulled repo: the imports failed | Yes: the code passed its own unit tests with hand-typed cells, so only running it against the real repo showed it |
