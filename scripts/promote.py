"""scripts/promote.py — promote MLflow Registry aliases with an audit log.

YOUR TASK (see tasks/task2.md): implement the four subcommand functions.
The argparse scaffolding below is wired so each cmd_* receives an `args`
namespace already parsed. See `_build_parser` for what's on `args` per
subcommand, and tasks/task2.md "Behavioral specs" for what each function
must do.

Versions are identified by their `config_id` tag (e.g., "v6"), NOT by
MLflow's integer version numbers. Resolution must be unique — if the
config_id matches zero or multiple registered versions, the CLI errors
out and forces the operator to disambiguate via the MLflow UI.

Successful `set` and `rollback` operations append a JSON event to
LOG_FILE (promotion-log.jsonl at repo root). `rollback` consults the
log to find the previous alias target.

Subcommands:
  set <alias> <config_id>   move alias, append `set` event to the log
  show <alias>              print current target + tags + key metrics
  list                      print all aliases on the registered model
  rollback <alias>          move alias back per the audit log, append
                            `rollback` event
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mlflow.tracking import MlflowClient
from src.config import get_settings
from mlflow.exceptions import RestException

import json
from datetime import datetime, timezone

REGISTERED_MODEL_NAME = "travel-assistant"
LOG_FILE = Path(__file__).resolve().parent.parent / "promotion-log.jsonl"

# Instantiate the client once at the top of the file so that i don't have to do it everytime
client = MlflowClient(tracking_uri=get_settings().mlflow_tracking_uri)


def cmd_set(args: argparse.Namespace) -> None:
    """args.alias: str, args.config_id: str. See tasks/task2.md → cmd_set."""
    # search for the version by config_id tag
    filter_string = f"name = '{REGISTERED_MODEL_NAME}' AND tags.config_id = '{args.config_id}'"
    versions = client.search_model_versions(filter_string)
    if len(versions) == 0:
        print(f"error: no version found with config_id={args.config_id}", file=sys.stderr)
        sys.exit(1)
    elif len(versions) > 1:
        chosen = max(versions, key=lambda v: int(v.version))
        all_versions = sorted(int(v.version) for v in versions)
        print(
            f"warning: multiple versions match config_id={args.config_id} "
            f"(MLflow versions {all_versions}); using latest ({chosen.version})"
        )
    else:
        chosen = versions[0]

    # capture the current alias state before moving it
    try:
        current = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, args.alias)
        current_config_id = current.tags["config_id"]
    except RestException:
        current_config_id = ""

    # move the alias
    client.set_registered_model_alias(REGISTERED_MODEL_NAME, args.alias, chosen.version)

    # write the audit log line
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "alias": args.alias,
        "from": current_config_id,
        "to": args.config_id,
        "op": "set",
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

    # print one summary line
    display_from = current_config_id if current_config_id else "(unset)"
    print(f"{args.alias}: {display_from} → {args.config_id}")


def cmd_show(args: argparse.Namespace) -> None:
    """args.alias: str. See tasks/task2.md → cmd_show."""
    try:
        mv = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, args.alias)
        run = client.get_run(mv.run_id)
        print(f"{REGISTERED_MODEL_NAME} @ {args.alias}")
        print(f"  model_version: {mv.version}")
        print(f"  config_id: {mv.tags['config_id']}")
        print(f"  model: {mv.tags['model']}")
        print(f"  accuracy_overall: {run.data.metrics['accuracy_overall']:.2f}")
        print(f"  verdict_rate_leaked: {run.data.metrics['verdict_rate_leaked']:.2f}")
        print(f"  total_cost_usd: ${run.data.metrics['total_cost_usd']:.2f}")
    except RestException:
        print(f"{args.alias} is not set", file=sys.stderr)
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """No args. See tasks/task2.md → cmd_list."""
    model = client.get_registered_model(REGISTERED_MODEL_NAME)
    if not model.aliases:
        print("no aliases set")
        return

    for alias in model.aliases:
        mv = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, alias)
        print(f"{alias} -> {mv.tags['config_id']}")


def cmd_rollback(args: argparse.Namespace) -> None:
    """args.alias: str. See tasks/task2.md → cmd_rollback."""

    # Pre-check: alias must be set
    try:
        current = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, args.alias)
        current_config_id = current.tags["config_id"]
    except RestException:
        print("nothing to roll back", file=sys.stderr)
        sys.exit(1)

    # Read the log (empty if missing)
    if not LOG_FILE.exists():
        lines = []
    else:
        lines = LOG_FILE.read_text().splitlines()

    # Walk backward, find the most recent matching entry
    most_recent = None
    for line in reversed(lines):
        event = json.loads(line)
        if event["alias"] == args.alias:
            most_recent = event
            break

    # Four-case rule
    if most_recent is None:
        # case 1: no promotion history
        print(f"no promotion history for {args.alias}", file=sys.stderr)
        sys.exit(1)
    elif most_recent["op"] == "rollback":
        # case 2: already rolled back
        print(
            f"{args.alias} was just rolled back; no further history to walk back to",
            file=sys.stderr,
        )
        sys.exit(1)
    elif most_recent["from"] == "":
        # case 3: first promotion ever
        print(
            f"{args.alias} has no previous target (first promotion ever)",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        # case 4: normal rollback
        target_config_id = most_recent["from"]

        # find the target version in MLflow (with multiplicity handling)
        filter_string = (
            f"name = '{REGISTERED_MODEL_NAME}' AND tags.config_id = '{target_config_id}'"
        )
        versions = client.search_model_versions(filter_string)
        if len(versions) == 0:
            print(
                f"error: no version found with config_id={target_config_id}",
                file=sys.stderr,
            )
            sys.exit(1)
        elif len(versions) > 1:
            chosen = max(versions, key=lambda v: int(v.version))
            all_versions = sorted(int(v.version) for v in versions)
            print(
                f"warning: multiple versions match config_id={target_config_id} "
                f"(MLflow versions {all_versions}); using latest ({chosen.version})"
            )
        else:
            chosen = versions[0]

        # move the alias to the rollback target
        client.set_registered_model_alias(REGISTERED_MODEL_NAME, args.alias, chosen.version)

        # write the rollback event to the audit log
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "alias": args.alias,
            "from": current_config_id,
            "to": target_config_id,
            "op": "rollback",
        }
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")

        # print summary
        print(f"{args.alias}: {current_config_id} → {target_config_id} (rolled back)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--name",
        default=REGISTERED_MODEL_NAME,
        help=f"Registered model name (default: {REGISTERED_MODEL_NAME})",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser(
        "set", help="Move an alias to a version (by config_id), append a set event"
    )
    p_set.add_argument("alias", help="Alias to assign (e.g., 'production')")
    p_set.add_argument(
        "config_id",
        help="Config identifier (e.g., 'v6') — resolved via the config_id tag on registered versions",
    )
    p_set.set_defaults(func=cmd_set)

    p_show = sub.add_parser("show", help="Show which version an alias points at")
    p_show.add_argument("alias")
    p_show.set_defaults(func=cmd_show)

    p_list = sub.add_parser("list", help="List all aliases on the registered model")
    p_list.set_defaults(func=cmd_list)

    p_rollback = sub.add_parser(
        "rollback",
        help="Move an alias back to its previous target per the audit log",
    )
    p_rollback.add_argument("alias")
    p_rollback.set_defaults(func=cmd_rollback)

    return parser


def main() -> None:
    args = _build_parser().parse_args()
    try:
        args.func(args)
    except NotImplementedError as exc:
        print(f"NOT IMPLEMENTED: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
