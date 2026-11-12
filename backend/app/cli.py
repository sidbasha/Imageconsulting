"""Operational commands.

    python -m app.cli seed
    python -m app.cli create-superadmin --email you@example.com --name "Your Name"
    python -m app.cli apply-due          # run from cron/Celery beat every minute
    python -m app.cli fetch-models       # download and verify the photo-analysis models
    python -m app.cli renew-subscriptions  # run daily: expire or open renewal orders

Release control (what phases and features are live) is developer-only:
edit app/release_plan.py, then

    python -m app.cli release status
    python -m app.cli release check
    python -m app.cli release apply --note "Why" [--at 2027-01-15T06:00:00+04:00]
    python -m app.cli release history
    python -m app.cli release rollback <version> --note "Why"
    python -m app.cli release cancel <version>        # a scheduled release
"""

import argparse
import getpass

from app.database import models  # noqa: F401
from app.database.session import SessionLocal
from app.modules.auth import service as auth_service
from app.modules.phase_management import service as release_service
from app.modules.phase_management.seed import seed


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed")
    commands.add_parser("apply-due")
    commands.add_parser("fetch-models")
    commands.add_parser("renew-subscriptions")
    release = commands.add_parser("release", help="developer-only release control, see app/release_plan.py")
    release_commands = release.add_subparsers(dest="release_command", required=True)
    release_commands.add_parser("status")
    release_commands.add_parser("check")
    release_commands.add_parser("history")
    apply_cmd = release_commands.add_parser("apply")
    apply_cmd.add_argument("--note", required=True)
    apply_cmd.add_argument("--at", help="ISO time with offset to schedule instead of applying now")
    rollback_cmd = release_commands.add_parser("rollback")
    rollback_cmd.add_argument("version", type=int)
    rollback_cmd.add_argument("--note", required=True)
    cancel_cmd = release_commands.add_parser("cancel")
    cancel_cmd.add_argument("version", type=int)
    admin = commands.add_parser("create-superadmin")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    args = parser.parse_args()

    if args.command == "fetch-models":
        from app.modules.ai_analysis.engine import fetch_models

        for path in fetch_models():
            print(f"ok  {path}")
        return

    with SessionLocal() as db:
        if args.command == "seed":
            seed(db)
            print("Seed complete.")
        elif args.command == "renew-subscriptions":
            from app.integrations.payments import get_payments
            from app.modules.commerce.service import renew_due

            print(renew_due(db, get_payments()))
        elif args.command == "release":
            run_release(db, args)
        elif args.command == "apply-due":
            print(f"Activated {release_service.apply_due(db)} scheduled release(s).")
        elif args.command == "create-superadmin":
            password = getpass.getpass("Password (min 10 characters): ")
            if len(password) < 10:
                raise SystemExit("Password too short.")
            auth_service.create_user(
                db, email=args.email, password=password, full_name=args.name, role_key="super_admin"
            )
            print(f"Super Admin {args.email} created.")
        db.commit()


def run_release(db, args) -> None:
    from datetime import datetime

    from app.core.errors import AppError
    from app.modules.phase_management import plan

    try:
        if args.release_command == "status":
            state = plan.status(db)
            print(f"Live release v{state['version']}")
            for key, on in state["phases"].items():
                print(f"  {key}: {'ON' if on else 'off'}")
            print(f"  {len(state['live'])} features live, {len(state['hidden'])} hidden")
            for key in state["hidden"]:
                print(f"    hidden: {key}")
        elif args.release_command == "check":
            result = plan.check(db)
            if result["violations"]:
                print("Refused: these features need something the plan switches off:")
                for v in result["violations"]:
                    print(f"  {v['feature']} needs {v['requires']} ({v['reason']})")
                raise SystemExit(1)
            print("OK. Turns on:", ", ".join(result["would_enable"]) or "nothing")
            print("    Turns off:", ", ".join(result["would_disable"]) or "nothing")
        elif args.release_command == "apply":
            at = datetime.fromisoformat(args.at) if args.at else None
            done = plan.apply(db, args.note, at)
            print("Already live; nothing to do." if done is None else
                  f"Release v{done.version} {'scheduled for ' + at.isoformat() if at else 'is live'}.")
        elif args.release_command == "history":
            for r in plan.history(db):
                when = r["activated_at"] or r["activate_at"]
                print(f"  v{r['version']:<4} {r['status']:<11} {when.isoformat(timespec='minutes') if when else '':<25} {r['note']}")
        elif args.release_command == "rollback":
            target = plan.by_version(db, args.version)
            done = release_service.rollback(db, None, target.id, args.note)
            print(f"Release v{done.version} restores v{args.version}. Update app/release_plan.py to match, "
                  "or the next deploy will apply the file again.")
        elif args.release_command == "cancel":
            release_service.cancel(db, None, plan.by_version(db, args.version).id)
            print(f"Scheduled release v{args.version} cancelled.")
    except AppError as exc:
        detail = exc.detail.get("violations") if isinstance(exc.detail, dict) else None
        if detail:
            print("Refused: these features need something that would be off:")
            for v in detail:
                print(f"  {v['feature']} needs {v['requires']} ({v['reason']})")
        else:
            print(f"Refused: {exc.code}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
