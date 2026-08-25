import argparse
import asyncio
import getpass

from sqlalchemy import text

from ev_twin_api.core.config import Settings
from ev_twin_api.core.database import Database
from ev_twin_api.core.security import PasswordHasher
from ev_twin_api.schemas.auth import AppRole


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Factory Twin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--role", required=True, choices=[role.value for role in AppRole])
    return parser.parse_args()


async def create_user(email: str, display_name: str, role: AppRole, password: str) -> None:
    settings = Settings()
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL is required")
    database = Database(
        settings.database_url.get_secret_value(), ssl_mode=settings.database_ssl_mode
    )
    password_hash = await PasswordHasher().hash(password)
    try:
        async with database.session() as session, session.begin():
            result = await session.execute(
                text(
                    """
                    insert into public.app_users (email, password_hash)
                    values (:email, :password_hash)
                    returning id
                    """
                ),
                {"email": email.strip().lower(), "password_hash": password_hash},
            )
            user_id = result.scalar_one()
            await session.execute(
                text(
                    """
                    insert into public.profiles (id, display_name, role)
                    values (:id, :display_name, cast(:role as public.app_role))
                    """
                ),
                {"id": user_id, "display_name": display_name.strip(), "role": role.value},
            )
    finally:
        await database.dispose()


def main() -> None:
    args = parse_args()
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("passwords do not match")
    if len(password) < 12:
        raise SystemExit("password must contain at least 12 characters")
    asyncio.run(create_user(args.email, args.display_name, AppRole(args.role), password))
    print(f"created {args.role} user {args.email.strip().lower()}")


if __name__ == "__main__":
    main()
