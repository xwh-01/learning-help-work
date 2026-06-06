#!/usr/bin/env python
"""Repair stale async tasks stuck in 'running' state.

Usage:
    cd backend
    python scripts/repair_stale_tasks.py --dry-run
    python scripts/repair_stale_tasks.py --older-than-minutes 30
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.services.task_recovery_service import TaskRecoveryService


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair stale async tasks")
    parser.add_argument(
        "--older-than-minutes",
        type=int,
        default=30,
        help="Tasks with updated_at older than this many minutes are considered stale (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List stale tasks without making changes",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        service = TaskRecoveryService(db)
        results = service.recover_stale_tasks(
            older_than_minutes=args.older_than_minutes,
            dry_run=args.dry_run,
        )

        if not results:
            print("No stale tasks found.")
            return

        mode = "[DRY RUN] " if args.dry_run else ""
        print(f"{mode}Found {len(results)} stale task(s):")
        for result in results:
            print(f"  task_id={result['task_id']} session_id={result['session_id']} "
                  f"action={result['action']}")
            details = result.get("details")
            if details:
                print(f"    must_learn_count={details.get('must_learn_count', 'N/A')} "
                      f"missing_examples={details.get('missing_example_count', 'N/A')} "
                      f"missing_levels={details.get('missing_level_count', 'N/A')}")
            reason = result.get("reason")
            if reason:
                print(f"    reason={reason}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
