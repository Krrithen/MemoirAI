# Story faithfulness

The app defaults to `STORY_STYLE=creative` (creative-v2-t0.7), which adds atmosphere on purpose;
`STORY_STYLE=faithful` (light-edit-t0) adds nothing. baseline is the original prompt.

How much the enrichment step adds to what the speaker said. Produced by
`eval/faithfulness/run.py` and `report.py` over the 10 synthetic transcripts in
`eval/faithfulness/transcripts.json`, 3 samples each. The check is lexical (see `check.py`):
good for comparing prompts on the same inputs, not an absolute truth score.

| Config | Model | Temp | Novel-word rate (mean) | Stories adding nothing | Stories dropping a word | Length vs transcript | Mean s/story |
|---|---|---|---|---|---|---|---|
| baseline | qwen3:8b | 0.3 | 32% | 7/30 | 6/30 | 1.65x | 4.9 |
| light-edit-t0 | qwen3:8b | 0.0 | 0% | 30/30 | 6/30 | 0.97x | 3.4 |
| creative-v2-t0.7 | qwen3:8b | 0.7 | 74% | 0/30 | 30/30 | 3.41x | 8.4 |

Words added but never said, by config:

- **baseline**: accidentally, accomplishment, across, almost, amount, away, back, became, bed, behind, best, better, bigger, book, bought, broken, brought, carried, cheering, cherished, cinnamon, community, connection, contentment, contribution
- **light-edit-t0**: none
- **creative-v2-t0.7**: accomplishment, ache, aching, across, adored, afraid, afternoon, aged, air, aisles, alive, almost, already, altogether, always, amount, anticipation, antiseptic, apartment, appeared, arms, aroma, around, arrived, asphalt
