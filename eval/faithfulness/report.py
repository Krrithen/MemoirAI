"""Rescore saved runs with check.py and write docs/results/faithfulness.md (no model calls).

Usage, from the repo root:
    python3 eval/faithfulness/report.py baseline light-edit-t0
"""

import json
import statistics
import sys
from pathlib import Path

from check import score

HERE = Path(__file__).parent
ROOT = HERE.parent.parent


def summarize(label: str) -> dict:
    data = json.loads((HERE / "results" / f"{label}.json").read_text())
    transcripts = {t["id"]: t["transcript"] for t in json.loads((HERE / "transcripts.json").read_text())}
    rows = [r | score(transcripts[r["id"]], r["story"]) for r in data["rows"]]
    s = data["summary"]
    return {
        "label": label,
        "model": s["model"],
        "temperature": s["temperature"],
        "stories": len(rows),
        "mean_novel_rate": statistics.mean(r["novel_rate"] for r in rows),
        "clean": sum(1 for r in rows if not r["novel_words"]),
        "dropping": sum(1 for r in rows if r["dropped_words"]),
        "length_ratio": statistics.mean(r["length_ratio"] for r in rows),
        "seconds": statistics.mean(r["seconds"] for r in rows),
        "examples": sorted({w for r in rows for w in r["novel_words"]})[:25],
    }


def main(labels: list[str]) -> None:
    results = [summarize(label) for label in labels]
    lines = [
        "# Story faithfulness",
        "",
        "How much the enrichment step adds to what the speaker said. Produced by",
        "`eval/faithfulness/run.py` and `report.py` over the 10 synthetic transcripts in",
        "`eval/faithfulness/transcripts.json`, 3 samples each. The check is lexical (see `check.py`):",
        "good for comparing prompts on the same inputs, not an absolute truth score.",
        "",
        "| Config | Model | Temp | Novel-word rate (mean) | Stories adding nothing | Stories dropping a word"
        " | Length vs transcript | Mean s/story |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['label']} | {r['model']} | {r['temperature']} | {r['mean_novel_rate']:.0%} "
            f"| {r['clean']}/{r['stories']} | {r['dropping']}/{r['stories']} | {r['length_ratio']:.2f}x "
            f"| {r['seconds']:.1f} |"
        )
    lines += ["", "Words added but never said, by config:", ""]
    for r in results:
        lines.append(f"- **{r['label']}**: {', '.join(r['examples']) or 'none'}")
    out = ROOT / "docs" / "results" / "faithfulness.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main(sys.argv[1:])
