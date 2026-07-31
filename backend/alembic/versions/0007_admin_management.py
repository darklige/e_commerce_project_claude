"""phase 6: admin account management

Revision ID: 0007_admin_management
Revises: 0006_phase7_perf_indexes
Create Date: 2026-07-31

Adds the platform-admin account-management pieces:

* Two new ``admin_role`` values — ``CUSTOMER_SERVICE_LEAD`` and
  ``CUSTOMER_SERVICE_AGENT`` (Postgres native enum gets ``ALTER TYPE``
  ``ADD VALUE``; on SQLite the column is a CHECK-backed VARCHAR so the
  model enum alone suffices).
* ``admin_users.password_changed_at`` — when the password hash was last
  set/rotated, so the console can prompt an initial-password change.
* ``ix_aftersales_status_arbitrator`` — covers the CS-agent data scope
  (``status = 'admin_arbitrating'`` + ``arbitrator_admin_id IS NULL`` /
  ``= mine``) and the unclaimed-pool count in the admin stats.

Notes:

* Postgres does not support ``ALTER TYPE ... DROP VALUE``, so enum
  values are additive and are *not* removed on downgrade.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_admin_management"
down_revision: str | None = "0006_phase7_perf_indexes"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

_NEW_ADMIN_ROLES = ("CUSTOMER_SERVICE_LEAD", "CUSTOMER_SERVICE_AGENT")


def _add_admin_role_values() -> None:
    """Add new admin_role enum labels on Postgres (guarded by existence)."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for value in _NEW_ADMIN_ROLES:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'admin_role' AND e.enumlabel = :v"
            ),
            {"v": value},
        ).first()
        if exists is None:
            bind.execute(sa.text(f"ALTER TYPE admin_role ADD VALUE '{value}'"))


def upgrade() -> None:
    _add_admin_role_values()

    op.add_column(
        "admin_users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_aftersales_status_arbitrator",
        "aftersales",
        ["status", "arbitrator_admin_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_aftersales_status_arbitrator",
        table_name="aftersales",
        if_exists=True,
    )
    op.drop_column("admin_users", "password_changed_at")
    # admin_role enum values are intentionally NOT removed on downgrade
    # (Postgres does not support ALTER TYPE ... DROP VALUE).
