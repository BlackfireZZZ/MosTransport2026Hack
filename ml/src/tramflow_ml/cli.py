import argparse
from pathlib import Path

from tramflow_ml import __version__
from tramflow_ml.evaluation import evaluate, load_cases


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
    args = parser.parse_args()

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
