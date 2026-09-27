"""Run the configured LLM over the fixed transcripts and score how much each story adds.

Usage, from the repo root (Ollama must be running):
    uv run --project backend python eval/faithfulness/run.py --label baseline --samples 3

Writes eval/faithfulness/results/<label>.json and prints a summary.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "backend"))
sys.path.insert(0, str(HERE))

from check import score  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.providers import get_llm  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--samples", type=int, default=3, help="runs per transcript (outputs vary at temperature > 0)")
    args = parser.parse_args()

    settings = get_settings()
    llm = get_llm()
    transcripts = json.loads((HERE / "transcripts.json").read_text())

    rows = []
    for item in transcripts:
        for sample in range(args.samples):
            start = time.perf_counter()
            enrichment = llm.enrich(item["transcript"])
            elapsed = time.perf_counter() - start
            rows.append(
                {
                    "id": item["id"],
                    "sample": sample,
                    "seconds": round(elapsed, 2),
                    "title": enrichment.title,
                    "story": enrichment.story,
                    "emotions": enrichment.emotions,
                    **score(item["transcript"], enrichment.story),
                }
            )
            print(f"{item['id']:<18} #{sample} novel={rows[-1]['novel_rate']:.0%} {rows[-1]['novel_words'][:8]}")

    rates = [r["novel_rate"] for r in rows]
    summary = {
        "label": args.label,
        "model": settings.ollama_model if settings.llm == "ollama" else settings.gemini_model,
        "story_style": settings.story_style,
        "temperature": llm.temperature,
        "samples_per_transcript": args.samples,
        "stories": len(rows),
        "mean_novel_rate": round(statistics.mean(rates), 3),
        "median_novel_rate": round(statistics.median(rates), 3),
        "stories_with_0_novel_words": sum(1 for r in rows if not r["novel_words"]),
        "mean_length_ratio": round(statistics.mean(r["length_ratio"] for r in rows), 2),
        "mean_seconds": round(statistics.mean(r["seconds"] for r in rows), 2),
    }
    out = HERE / "results" / f"{args.label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
