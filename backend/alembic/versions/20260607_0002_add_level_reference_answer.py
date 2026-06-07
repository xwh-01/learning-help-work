"""add reference answer to learning levels

Revision ID: 20260607_0002
Revises: 20260606_0001
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260607_0002"
down_revision = "20260606_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_levels", sa.Column("reference_answer", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("learning_levels", "reference_answer")
