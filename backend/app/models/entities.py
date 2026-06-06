from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import BigIntPrimaryKeyMixin, TimestampMixin


TABLE_ARGS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


class User(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        TABLE_ARGS,
    )

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")


class LearningSession(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        Index("ix_learning_sessions_user_id", "user_id"),
        Index("ix_learning_sessions_tech_name", "tech_name"),
        Index("ix_learning_sessions_status", "status"),
        Index("ix_learning_sessions_current_knowledge_point_id", "current_knowledge_point_id"),
        Index("ix_learning_sessions_current_level_id", "current_level_id"),
        TABLE_ARGS,
    )

    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tech_name: Mapped[str] = mapped_column(String(255), nullable=False)
    learning_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    current_knowledge_point_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_level_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class OfficialMaterial(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "official_materials"
    __table_args__ = (
        Index("ix_official_materials_session_id", "session_id"),
        Index("ix_official_materials_tech_name", "tech_name"),
        TABLE_ARGS,
    )

    session_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    tech_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    official_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunks_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    raw_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class TechRelation(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tech_relations"
    __table_args__ = (
        UniqueConstraint("tech_name", name="uq_tech_relations_tech_name"),
        Index("ix_tech_relations_tech_name", "tech_name"),
        TABLE_ARGS,
    )

    tech_name: Mapped[str] = mapped_column(String(255), nullable=False)
    baseline: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    similar: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    skip_now: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ComparisonResult(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "comparison_results"
    __table_args__ = (
        Index("ix_comparison_results_session_id", "session_id"),
        Index("ix_comparison_results_tech_name", "tech_name"),
        TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    tech_name: Mapped[str] = mapped_column(String(255), nullable=False)
    selected_for_comparison: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    baseline_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    comparison_task: Mapped[str | None] = mapped_column(Text, nullable=True)
    comparison_table: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    when_to_use: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    when_not_to_use: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class KnowledgePoint(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_points"
    __table_args__ = (
        Index("ix_knowledge_points_session_id", "session_id"),
        Index("ix_knowledge_points_tech_name", "tech_name"),
        Index("ix_knowledge_points_category", "category"),
        TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    tech_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    depends_on: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")


class LearningExample(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_examples"
    __table_args__ = (
        Index("ix_learning_examples_session_id", "session_id"),
        Index("ix_learning_examples_knowledge_point_id", "knowledge_point_id"),
        TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_point_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
    )
    official_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    beginner_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    baseline_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    observe_questions: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class LearningLevel(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_levels"
    __table_args__ = (
        Index("ix_learning_levels_session_id", "session_id"),
        Index("ix_learning_levels_knowledge_point_id", "knowledge_point_id"),
        Index("ix_learning_levels_type", "level_type"),
        TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_point_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    task: Mapped[str | None] = mapped_column(Text, nullable=True)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_criteria: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    common_mistakes: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")


class UserAnswer(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_answers"
    __table_args__ = (
        Index("ix_user_answers_session_id", "session_id"),
        Index("ix_user_answers_knowledge_point_id", "knowledge_point_id"),
        Index("ix_user_answers_level_id", "level_id"),
        TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_point_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_points.id", ondelete="SET NULL"),
        nullable=True,
    )
    level_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    answer_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text", server_default="text")
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeedbackResult(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feedback_results"
    __table_args__ = (
        Index("ix_feedback_results_session_id", "session_id"),
        Index("ix_feedback_results_answer_id", "answer_id"),
        Index("ix_feedback_results_level_id", "level_id"),
        TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user_answers.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("learning_levels.id", ondelete="SET NULL"),
        nullable=True,
    )
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    correct_points: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    missing_points: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_review_points: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class PracticeTask(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "practice_tasks"
    __table_args__ = (
        Index("ix_practice_tasks_session_id", "session_id"),
        TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    background: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_points: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    task_requirements: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    comparison_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_criteria: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    review_questions: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class LearningCard(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_cards"
    __table_args__ = (
        Index("ix_learning_cards_session_id", "session_id"),
        Index("ix_learning_cards_tech_name", "tech_name"),
        TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    tech_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pain_point: Mapped[str | None] = mapped_column(Text, nullable=True)
    baseline_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_advantage: Mapped[str | None] = mapped_column(Text, nullable=True)
    when_to_use: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    when_not_to_use: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    minimal_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    my_understanding: Mapped[str | None] = mapped_column(Text, nullable=True)
    weak_points: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    card_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class AsyncTask(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "async_tasks"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_async_tasks_task_id"),
        Index("ix_async_tasks_task_id", "task_id"),
        Index("ix_async_tasks_session_id", "session_id"),
        Index("ix_async_tasks_task_type", "task_type"),
        Index("ix_async_tasks_status", "status"),
        TABLE_ARGS,
    )

    task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    progress: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    result_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
