"""Operational commands.

    python -m app.cli seed
    python -m app.cli create-superadmin --email you@example.com --name "Your Name"
    python -m app.cli apply-due          # run from cron/Celery beat every minute
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
    admin = commands.add_parser("create-superadmin")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "seed":
            seed(db)
            print("Seed complete.")
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


if __name__ == "__main__":
    main()
