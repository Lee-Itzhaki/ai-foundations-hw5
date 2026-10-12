"""CLI: analyze tickets with the agent team (no payments are executed).

    PORTKEY_API_KEY=... .venv/bin/python -m backend 101 102 103
"""

import argparse
import asyncio

from .orchestrator import run_tickets


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team.")
    parser.add_argument("tickets", nargs="*", type=int, help="ticket ids (default: all open)")
    args = parser.parse_args()
    outcome = asyncio.run(run_tickets(args.tickets or None))
    if outcome.report:
        print(outcome.report.model_dump_json(indent=2))
        print("Pending actions for human approval:", outcome.action_ids)
    else:
        print("Run failed:", outcome.error)


if __name__ == "__main__":
    main()
