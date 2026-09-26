# Story faithfulness

How much the enrichment step adds to what the speaker said. Produced by
`eval/faithfulness/run.py` and `report.py` over the 10 synthetic transcripts in
`eval/faithfulness/transcripts.json`, 3 samples each. The check is lexical (see `check.py`):
good for comparing prompts on the same inputs, not an absolute truth score.

| Config | Model | Temp | Novel-word rate (mean) | Stories adding nothing | Stories dropping a word | Length vs transcript | Mean s/story |
|---|---|---|---|---|---|---|---|
| baseline | qwen3:8b | 0.3 | 32% | 7/30 | 6/30 | 1.65x | 4.9 |
| light-edit-t0 | qwen3:8b | 0.0 | 0% | 30/30 | 6/30 | 0.97x | 3.4 |

Words added but never said, by config:

- **baseline**: accidentally, accomplishment, across, almost, amount, away, back, became, bed, behind, best, better, bigger, book, bought, broken, brought, carried, cheering, cherished, cinnamon, community, connection, contentment, contribution
- **light-edit-t0**: none
