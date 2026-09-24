import argparse
import json
from datetime import date
from pathlib import Path

from tramflow_ml import __version__
from tramflow_ml.evaluation import evaluate, load_cases
from tramflow_ml.synthetic import SyntheticConfig, generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(prog="tramflow-ml")
    subparsers = parser.add_subparsers(dest="command")
    evaluate_parser = subparsers.add_parser("evaluate", help="run the golden forecast suite")
    evaluate_parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("ml/evals/golden_cases.json"),
    )
    evaluate_parser.add_argument("--output", type=Path)
    synthetic_parser = subparsers.add_parser(
        "generate-synthetic", help="generate versioned synthetic validation/telemetry fixtures"
    )
    synthetic_parser.add_argument("--output", type=Path, required=True)
    synthetic_parser.add_argument("--mode", choices=("tiny", "million"), default="tiny")
    synthetic_parser.add_argument("--events", type=int)
    synthetic_parser.add_argument("--seed", type=int, default=42)
    synthetic_parser.add_argument("--start-date", type=date.fromisoformat, default=date(2024, 1, 1))
    synthetic_parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 1, 1))
    synthetic_parser.add_argument("--duplicate-every", type=int, default=17)
    synthetic_parser.add_argument("--late-every", type=int, default=11)
    synthetic_parser.add_argument("--telemetry-every", type=int, default=5)
    synthetic_parser.add_argument("--gap-every-days", type=int, default=13)
    args = parser.parse_args()

    if args.command == "generate-synthetic":
        try:
            config = SyntheticConfig(
                start=args.start_date,
                end=args.end_date,
                events=args.events
                if args.events is not None
                else (1_000_000 if args.mode == "million" else 64),
                seed=args.seed,
                duplicate_every=args.duplicate_every,
                late_every=args.late_every,
                telemetry_every=args.telemetry_every,
                gap_every_days=args.gap_every_days,
            )
            result = generate_dataset(config, args.output)
        except (ValueError, OSError) as error:
            parser.error(str(error))
        print(
            json.dumps(
                {
                    "dataset_id": result["manifest"]["dataset_id"],
                    "source_hash": result["manifest"]["source_hash"],
                    "counts": result["generation"]["counts"],
                },
                sort_keys=True,
            )
        )
        return

    if args.command != "evaluate":
        print(f"TramFlow ML {__version__}: workspace is ready")
        return

    summary = evaluate(load_cases(args.dataset))
    serialized = summary.model_dump_json(indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    if not summary.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
