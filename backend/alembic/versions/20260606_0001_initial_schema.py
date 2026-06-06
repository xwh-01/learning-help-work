"""initial schema

Revision ID: 20260606_0001
Revises:
Create Date: 2026-06-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260606_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def id_column() -> sa.Column:
    return sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False)


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


TABLE_OPTIONS = {
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_unicode_ci",
}


def upgrade() -> None:
    op.create_table(
        "users",
        id_column(),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "learning_sessions",
        id_column(),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("tech_name", sa.String(length=255), nullable=False),
        sa.Column("learning_goal", sa.Text(), nullable=True),
        sa.Column("user_level", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("current_knowledge_point_id", sa.BigInteger(), nullable=True),
        sa.Column("current_level_id", sa.BigInteger(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_learning_sessions_user_id", "learning_sessions", ["user_id"])
    op.create_index("ix_learning_sessions_tech_name", "learning_sessions", ["tech_name"])
    op.create_index("ix_learning_sessions_status", "learning_sessions", ["status"])
    op.create_index(
        "ix_learning_sessions_current_knowledge_point_id",
        "learning_sessions",
        ["current_knowledge_point_id"],
    )
    op.create_index("ix_learning_sessions_current_level_id", "learning_sessions", ["current_level_id"])

    op.create_table(
        "official_materials",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("tech_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("official_summary", sa.Text(), nullable=True),
        sa.Column("official_example", sa.Text(), nullable=True),
        sa.Column("chunks_json", mysql.JSON(), nullable=True),
        sa.Column("raw_json", mysql.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_official_materials_session_id", "official_materials", ["session_id"])
    op.create_index("ix_official_materials_tech_name", "official_materials", ["tech_name"])

    op.create_table(
        "tech_relations",
        id_column(),
        sa.Column("tech_name", sa.String(length=255), nullable=False),
        sa.Column("baseline", mysql.JSON(), nullable=True),
        sa.Column("similar", mysql.JSON(), nullable=True),
        sa.Column("skip_now", mysql.JSON(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tech_name", name="uq_tech_relations_tech_name"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_tech_relations_tech_name", "tech_relations", ["tech_name"])

    op.create_table(
        "comparison_results",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("tech_name", sa.String(length=255), nullable=False),
        sa.Column("selected_for_comparison", mysql.JSON(), nullable=True),
        sa.Column("baseline_solution", sa.Text(), nullable=True),
        sa.Column("comparison_task", sa.Text(), nullable=True),
        sa.Column("comparison_table", mysql.JSON(), nullable=True),
        sa.Column("when_to_use", mysql.JSON(), nullable=True),
        sa.Column("when_not_to_use", mysql.JSON(), nullable=True),
        sa.Column("result_json", mysql.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_comparison_results_session_id", "comparison_results", ["session_id"])
    op.create_index("ix_comparison_results_tech_name", "comparison_results", ["tech_name"])

    op.create_table(
        "knowledge_points",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("tech_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("depends_on", mysql.JSON(), nullable=True),
        sa.Column("difficulty", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_knowledge_points_session_id", "knowledge_points", ["session_id"])
    op.create_index("ix_knowledge_points_tech_name", "knowledge_points", ["tech_name"])
    op.create_index("ix_knowledge_points_category", "knowledge_points", ["category"])

    op.create_table(
        "learning_examples",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("knowledge_point_id", sa.BigInteger(), nullable=False),
        sa.Column("official_example", sa.Text(), nullable=True),
        sa.Column("beginner_example", sa.Text(), nullable=True),
        sa.Column("baseline_example", sa.Text(), nullable=True),
        sa.Column("target_example", sa.Text(), nullable=True),
        sa.Column("observe_questions", mysql.JSON(), nullable=True),
        sa.Column("result_json", mysql.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["knowledge_point_id"], ["knowledge_points.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_learning_examples_session_id", "learning_examples", ["session_id"])
    op.create_index("ix_learning_examples_knowledge_point_id", "learning_examples", ["knowledge_point_id"])

    op.create_table(
        "learning_levels",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("knowledge_point_id", sa.BigInteger(), nullable=False),
        sa.Column("level_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("task", sa.Text(), nullable=True),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria", mysql.JSON(), nullable=True),
        sa.Column("common_mistakes", mysql.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["knowledge_point_id"], ["knowledge_points.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_learning_levels_session_id", "learning_levels", ["session_id"])
    op.create_index("ix_learning_levels_knowledge_point_id", "learning_levels", ["knowledge_point_id"])
    op.create_index("ix_learning_levels_type", "learning_levels", ["level_type"])

    op.create_table(
        "user_answers",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("knowledge_point_id", sa.BigInteger(), nullable=True),
        sa.Column("level_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("answer_type", sa.String(length=32), server_default="text", nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_json", mysql.JSON(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["knowledge_point_id"], ["knowledge_points.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["level_id"], ["learning_levels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_user_answers_session_id", "user_answers", ["session_id"])
    op.create_index("ix_user_answers_knowledge_point_id", "user_answers", ["knowledge_point_id"])
    op.create_index("ix_user_answers_level_id", "user_answers", ["level_id"])

    op.create_table(
        "feedback_results",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("answer_id", sa.BigInteger(), nullable=False),
        sa.Column("level_id", sa.BigInteger(), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("correct_points", mysql.JSON(), nullable=True),
        sa.Column("missing_points", mysql.JSON(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("suggested_review_points", mysql.JSON(), nullable=True),
        sa.Column("result_json", mysql.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["answer_id"], ["user_answers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["level_id"], ["learning_levels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_feedback_results_session_id", "feedback_results", ["session_id"])
    op.create_index("ix_feedback_results_answer_id", "feedback_results", ["answer_id"])
    op.create_index("ix_feedback_results_level_id", "feedback_results", ["level_id"])

    op.create_table(
        "practice_tasks",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("background", sa.Text(), nullable=True),
        sa.Column("required_points", mysql.JSON(), nullable=True),
        sa.Column("task_requirements", mysql.JSON(), nullable=True),
        sa.Column("comparison_requirement", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria", mysql.JSON(), nullable=True),
        sa.Column("review_questions", mysql.JSON(), nullable=True),
        sa.Column("result_json", mysql.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_practice_tasks_session_id", "practice_tasks", ["session_id"])

    op.create_table(
        "learning_cards",
        id_column(),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("tech_name", sa.String(length=255), nullable=False),
        sa.Column("pain_point", sa.Text(), nullable=True),
        sa.Column("baseline_solution", sa.Text(), nullable=True),
        sa.Column("target_advantage", sa.Text(), nullable=True),
        sa.Column("when_to_use", mysql.JSON(), nullable=True),
        sa.Column("when_not_to_use", mysql.JSON(), nullable=True),
        sa.Column("minimal_example", sa.Text(), nullable=True),
        sa.Column("my_understanding", sa.Text(), nullable=True),
        sa.Column("weak_points", mysql.JSON(), nullable=True),
        sa.Column("card_markdown", sa.Text(), nullable=True),
        sa.Column("result_json", mysql.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_learning_cards_session_id", "learning_cards", ["session_id"])
    op.create_index("ix_learning_cards_tech_name", "learning_cards", ["tech_name"])

    op.create_table(
        "async_tasks",
        id_column(),
        sa.Column("task_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("result_json", mysql.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", name="uq_async_tasks_task_id"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_async_tasks_task_id", "async_tasks", ["task_id"])
    op.create_index("ix_async_tasks_session_id", "async_tasks", ["session_id"])
    op.create_index("ix_async_tasks_task_type", "async_tasks", ["task_type"])
    op.create_index("ix_async_tasks_status", "async_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_async_tasks_status", table_name="async_tasks")
    op.drop_index("ix_async_tasks_task_type", table_name="async_tasks")
    op.drop_index("ix_async_tasks_session_id", table_name="async_tasks")
    op.drop_index("ix_async_tasks_task_id", table_name="async_tasks")
    op.drop_table("async_tasks")

    op.drop_index("ix_learning_cards_tech_name", table_name="learning_cards")
    op.drop_index("ix_learning_cards_session_id", table_name="learning_cards")
    op.drop_table("learning_cards")

    op.drop_index("ix_practice_tasks_session_id", table_name="practice_tasks")
    op.drop_table("practice_tasks")

    op.drop_index("ix_feedback_results_level_id", table_name="feedback_results")
    op.drop_index("ix_feedback_results_answer_id", table_name="feedback_results")
    op.drop_index("ix_feedback_results_session_id", table_name="feedback_results")
    op.drop_table("feedback_results")

    op.drop_index("ix_user_answers_level_id", table_name="user_answers")
    op.drop_index("ix_user_answers_knowledge_point_id", table_name="user_answers")
    op.drop_index("ix_user_answers_session_id", table_name="user_answers")
    op.drop_table("user_answers")

    op.drop_index("ix_learning_levels_type", table_name="learning_levels")
    op.drop_index("ix_learning_levels_knowledge_point_id", table_name="learning_levels")
    op.drop_index("ix_learning_levels_session_id", table_name="learning_levels")
    op.drop_table("learning_levels")

    op.drop_index("ix_learning_examples_knowledge_point_id", table_name="learning_examples")
    op.drop_index("ix_learning_examples_session_id", table_name="learning_examples")
    op.drop_table("learning_examples")

    op.drop_index("ix_knowledge_points_category", table_name="knowledge_points")
    op.drop_index("ix_knowledge_points_tech_name", table_name="knowledge_points")
    op.drop_index("ix_knowledge_points_session_id", table_name="knowledge_points")
    op.drop_table("knowledge_points")

    op.drop_index("ix_comparison_results_tech_name", table_name="comparison_results")
    op.drop_index("ix_comparison_results_session_id", table_name="comparison_results")
    op.drop_table("comparison_results")

    op.drop_index("ix_tech_relations_tech_name", table_name="tech_relations")
    op.drop_table("tech_relations")

    op.drop_index("ix_official_materials_tech_name", table_name="official_materials")
    op.drop_index("ix_official_materials_session_id", table_name="official_materials")
    op.drop_table("official_materials")

    op.drop_index("ix_learning_sessions_current_level_id", table_name="learning_sessions")
    op.drop_index("ix_learning_sessions_current_knowledge_point_id", table_name="learning_sessions")
    op.drop_index("ix_learning_sessions_status", table_name="learning_sessions")
    op.drop_index("ix_learning_sessions_tech_name", table_name="learning_sessions")
    op.drop_index("ix_learning_sessions_user_id", table_name="learning_sessions")
    op.drop_table("learning_sessions")

    op.drop_table("users")
