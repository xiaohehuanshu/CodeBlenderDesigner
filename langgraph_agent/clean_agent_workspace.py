from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parent

# Quick settings:
# Change these True/False values if you want to change the default cleanup behavior.
# You can still override them from the command line with --only / --skip / --include-inputs / --full-reset.
USER_DEFAULTS: dict[str, bool | int] = {
    "clean_generated_scripts": True,
    "clean_internet_research": True,
    "clean_memory": True,
    "clean_traces": True,
    "clean_input_images": False,
    "clean_input_rules": False,
    "clean_cache_dirs": True,
    "clean_compiled_python": True,
    "preview_limit": 20,
}

OUTPUT_TARGETS = {
    "clean_generated_scripts": PROJECT_ROOT / "outputs" / "generated_scripts",
    "clean_internet_research": PROJECT_ROOT / "outputs" / "internet_research",
    "clean_memory": PROJECT_ROOT / "outputs" / "memory",
    "clean_traces": PROJECT_ROOT / "outputs" / "traces",
}

INPUT_TARGETS = {
    "clean_input_images": PROJECT_ROOT / "inputs" / "images",
    "clean_input_rules": PROJECT_ROOT / "inputs" / "rules",
}

LABELS = {
    "clean_generated_scripts": "outputs/generated_scripts",
    "clean_internet_research": "outputs/internet_research",
    "clean_memory": "outputs/memory",
    "clean_traces": "outputs/traces",
    "clean_input_images": "inputs/images",
    "clean_input_rules": "inputs/rules",
    "clean_cache_dirs": "__pycache__ / cache directories",
    "clean_compiled_python": ".pyc / .pyo compiled files",
}

CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
CACHE_FILE_SUFFIXES = {".pyc", ".pyo"}
BOOLEAN_KEYS = tuple(key for key, value in USER_DEFAULTS.items() if isinstance(value, bool))
VALID_ONLY_SKIP_NAMES = tuple(key.removeprefix("clean_") for key in BOOLEAN_KEYS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean generated files and caches for langgraph_agent."
    )
    parser.add_argument(
        "--include-inputs",
        action="store_true",
        help="Enable cleanup for both inputs/images and inputs/rules.",
    )
    parser.add_argument(
        "--full-reset",
        action="store_true",
        help="Enable every cleanup target, including inputs.",
    )
    parser.add_argument(
        "--only",
        help=(
            "Comma-separated cleanup targets to keep enabled. "
            f"Choices: {', '.join(VALID_ONLY_SKIP_NAMES)}"
        ),
    )
    parser.add_argument(
        "--skip",
        help=(
            "Comma-separated cleanup targets to disable. "
            f"Choices: {', '.join(VALID_ONLY_SKIP_NAMES)}"
        ),
    )
    parser.add_argument(
        "--preview-limit",
        type=int,
        default=None,
        help="How many cache paths to print in the plan. Defaults to USER_DEFAULTS['preview_limit'].",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print the effective cleanup config before the plan.",
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="Print all supported target names and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the cleanup plan without deleting anything.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    return parser


def parse_target_list(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    return {
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    }


def validate_target_names(target_names: set[str]) -> None:
    invalid = sorted(name for name in target_names if name not in VALID_ONLY_SKIP_NAMES)
    if invalid:
        raise ValueError(
            "Unknown cleanup targets: "
            + ", ".join(invalid)
            + ". Valid targets: "
            + ", ".join(VALID_ONLY_SKIP_NAMES)
        )


def build_effective_config(args: argparse.Namespace) -> dict[str, bool | int]:
    config = dict(USER_DEFAULTS)

    if args.preview_limit is not None:
        config["preview_limit"] = max(1, int(args.preview_limit))

    if args.include_inputs:
        config["clean_input_images"] = True
        config["clean_input_rules"] = True

    if args.full_reset:
        for key in BOOLEAN_KEYS:
            config[key] = True

    only_targets = parse_target_list(args.only)
    skip_targets = parse_target_list(args.skip)
    validate_target_names(only_targets | skip_targets)

    if only_targets:
        for key in BOOLEAN_KEYS:
            config[key] = False
        for name in only_targets:
            config[f"clean_{name}"] = True

    for name in skip_targets:
        config[f"clean_{name}"] = False

    return config


def reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def clear_directory_contents(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return

    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    path.mkdir(parents=True, exist_ok=True)


def remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def find_cache_paths(
    root: Path,
    *,
    include_cache_dirs: bool,
    include_compiled_python: bool,
) -> list[Path]:
    matches: set[Path] = set()
    for path in root.rglob("*"):
        if include_cache_dirs and path.name in CACHE_DIR_NAMES:
            matches.add(path)
        elif include_compiled_python and path.is_file() and path.suffix in CACHE_FILE_SUFFIXES:
            matches.add(path)
    return sorted(matches)


def count_children(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.iterdir())


def active_cleanup_labels(config: dict[str, bool | int]) -> list[str]:
    labels: list[str] = []
    for key in BOOLEAN_KEYS:
        if bool(config[key]):
            labels.append(LABELS[key])
    return labels


def print_effective_config(config: dict[str, bool | int]) -> None:
    print("Effective cleanup config:")
    print()
    for key in BOOLEAN_KEYS:
        print(f"- {key}: {config[key]}")
    print(f"- preview_limit: {config['preview_limit']}")


def print_plan(config: dict[str, bool | int], cache_paths: list[Path]) -> None:
    preview_limit = int(config["preview_limit"])
    print("Cleanup plan:")
    print()

    for key, path in OUTPUT_TARGETS.items():
        if bool(config[key]):
            print(f"- reset output directory: {path} (items={count_children(path)})")

    for key, path in INPUT_TARGETS.items():
        if bool(config[key]):
            print(f"- clear input directory contents: {path} (items={count_children(path)})")

    if bool(config["clean_cache_dirs"]) or bool(config["clean_compiled_python"]):
        if cache_paths:
            print(f"- remove cache paths: {len(cache_paths)} item(s)")
            for path in cache_paths[:preview_limit]:
                print(f"  {path}")
            if len(cache_paths) > preview_limit:
                print(f"  ... and {len(cache_paths) - preview_limit} more")
        else:
            print("- remove cache paths: none found")


def confirm(config: dict[str, bool | int]) -> bool:
    labels = active_cleanup_labels(config)
    scope = ", ".join(labels) if labels else "nothing"
    response = input(f"Delete {scope}? Type 'y' to continue: ").strip().lower()
    return response == "y"


def run_actions(
    config: dict[str, bool | int],
    cache_paths: list[Path],
    *,
    dry_run: bool,
) -> None:
    dir_action: Callable[[Path], None]

    for key, path in OUTPUT_TARGETS.items():
        if not bool(config[key]):
            continue
        if not dry_run:
            reset_directory(path)

    for key, path in INPUT_TARGETS.items():
        if not bool(config[key]):
            continue
        if not dry_run:
            clear_directory_contents(path)

    if not dry_run:
        for path in cache_paths:
            remove_path(path)


def print_target_list() -> None:
    print("Supported cleanup targets:")
    print()
    for name in VALID_ONLY_SKIP_NAMES:
        print(f"- {name}")


def main() -> int:
    args = build_parser().parse_args()

    if args.list_targets:
        print_target_list()
        return 0

    config = build_effective_config(args)
    cache_paths = find_cache_paths(
        PROJECT_ROOT,
        include_cache_dirs=bool(config["clean_cache_dirs"]),
        include_compiled_python=bool(config["clean_compiled_python"]),
    )

    if args.show_config:
        print_effective_config(config)
        print()

    print_plan(config, cache_paths)
    print()

    if args.dry_run:
        print("Dry run only. No files were deleted.")
        return 0

    if not active_cleanup_labels(config):
        print("No cleanup target is enabled. Nothing to do.")
        return 0

    if not args.yes and not confirm(config):
        print("Cleanup canceled.")
        return 0

    run_actions(config, cache_paths, dry_run=False)
    print("Cleanup completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
