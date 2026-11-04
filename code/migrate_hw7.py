from __future__ import annotations

from code.database import engine
from typing import Any

from pwdlib import PasswordHash
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

PASSWORD_HASH = PasswordHash.recommended()

VALID_ROLES = {
    "reader",
    "writer",
    "moderator",
}


DEMO_USERS: tuple[
    dict[str, Any],
    ...,
] = (
    {
        "username": "reader7801",
        "display_name": ("Homework 7 Reader"),
        "email": ("reader7801@example.edu"),
        "password": ("Data260Reader!7801"),
        "role": "reader",
    },
    {
        "username": "writer7801",
        "display_name": ("Homework 7 Writer"),
        "email": ("writer7801@example.edu"),
        "password": ("Data260Writer!7801"),
        "role": "writer",
    },
    {
        "username": "moderator7801",
        "display_name": ("Homework 7 Moderator"),
        "email": ("moderator7801@example.edu"),
        "password": ("Data260Moderator!7801"),
        "role": "moderator",
    },
)


def column_names() -> set[str]:
    """Return existing columns in the users table."""

    inspector = inspect(engine)

    return {str(column["name"]) for column in inspector.get_columns("users")}


def index_exists(
    connection: Connection,
    index_name: str,
) -> bool:
    """Return whether a users-table index exists."""

    count = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 'users'
              AND index_name = :index_name
            """
        ),
        {
            "index_name": index_name,
        },
    ).scalar_one()

    return bool(count)


def add_username_column(
    connection: Connection,
) -> None:
    """Add and populate users.username."""

    columns = column_names()

    if "username" not in columns:
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN username VARCHAR(80)
                NULL AFTER id
                """
            )
        )

        print("Added users.username.")
    else:
        print("users.username already exists.")

    connection.execute(
        text(
            """
            UPDATE users
            SET username = CONCAT(
                'legacy_user_',
                id
            )
            WHERE username IS NULL
               OR TRIM(username) = ''
            """
        )
    )

    connection.execute(
        text(
            """
            ALTER TABLE users
            MODIFY COLUMN username
            VARCHAR(80) NOT NULL
            """
        )
    )

    if not index_exists(
        connection,
        "uq_users_username",
    ):
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX
                uq_users_username
                ON users (username)
                """
            )
        )

        print("Created unique username index.")
    else:
        print("Unique username index already exists.")


def add_role_column(
    connection: Connection,
) -> None:
    """Add and normalize users.role."""

    columns = column_names()

    if "role" not in columns:
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN role VARCHAR(20)
                NOT NULL DEFAULT 'reader'
                AFTER password_hash
                """
            )
        )

        print("Added users.role.")
    else:
        print("users.role already exists.")

    connection.execute(
        text(
            """
            UPDATE users
            SET role = 'reader'
            WHERE role IS NULL
               OR role NOT IN (
                    'reader',
                    'writer',
                    'moderator'
               )
            """
        )
    )


def seed_demo_users(
    connection: Connection,
) -> None:
    """Insert or update the three RBAC users."""

    for user in DEMO_USERS:
        role = str(user["role"])

        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}")

        password_hash = PASSWORD_HASH.hash(str(user["password"]))

        connection.execute(
            text(
                """
                INSERT INTO users (
                    username,
                    display_name,
                    email,
                    password_hash,
                    role,
                    is_active,
                    created_at
                )
                VALUES (
                    :username,
                    :display_name,
                    :email,
                    :password_hash,
                    :role,
                    true,
                    UTC_TIMESTAMP()
                )
                ON DUPLICATE KEY UPDATE
                    display_name = VALUES(
                        display_name
                    ),
                    email = VALUES(email),
                    password_hash = VALUES(
                        password_hash
                    ),
                    role = VALUES(role),
                    is_active = true
                """
            ),
            {
                "username": (user["username"]),
                "display_name": (user["display_name"]),
                "email": user["email"],
                "password_hash": (password_hash),
                "role": role,
            },
        )

        print(
            "Seeded user:",
            user["username"],
            "| role:",
            role,
        )


def validate_migration(
    connection: Connection,
) -> None:
    """Validate the required users and roles."""

    rows = (
        connection.execute(
            text(
                """
            SELECT
                username,
                role,
                is_active
            FROM users
            WHERE username IN (
                'reader7801',
                'writer7801',
                'moderator7801'
            )
            ORDER BY username
            """
            )
        )
        .mappings()
        .all()
    )

    if len(rows) != 3:
        raise RuntimeError("Expected three Homework 7 users.")

    observed = {str(row["role"]) for row in rows}

    if observed != VALID_ROLES:
        raise RuntimeError("The required RBAC roles were not seeded correctly.")

    if not all(bool(row["is_active"]) for row in rows):
        raise RuntimeError("All Homework 7 users must be active.")

    print("Homework 7 user validation passed.")


def main() -> None:
    """Run the Homework 7 user migration."""

    print("Starting Homework 7 database migration.")

    with engine.begin() as connection:
        add_username_column(connection)

        add_role_column(connection)

        seed_demo_users(connection)

        validate_migration(connection)

    print("\nHomework 7 migration complete.")

    print("\nDemo credentials:")

    for user in DEMO_USERS:
        print(
            "-",
            user["username"],
            "|",
            user["password"],
            "|",
            user["role"],
        )


if __name__ == "__main__":
    main()
