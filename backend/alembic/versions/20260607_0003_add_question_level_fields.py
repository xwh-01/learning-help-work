"""add question oriented level fields

Revision ID: 20260607_0003
Revises: 20260607_0002
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "20260607_0003"
down_revision = "20260607_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_levels", sa.Column("scenario", sa.Text(), nullable=True))
    op.add_column("learning_levels", sa.Column("question", sa.Text(), nullable=True))
    op.add_column("learning_levels", sa.Column("answer_requirements", mysql.JSON(), nullable=True))
    op.add_column("learning_levels", sa.Column("rubric", mysql.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("learning_levels", "rubric")
    op.drop_column("learning_levels", "answer_requirements")
    op.drop_column("learning_levels", "question")
    op.drop_column("learning_levels", "scenario")
