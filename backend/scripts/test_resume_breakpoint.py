"""Integration test for example/level breakpoint resume logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.repositories.generation_repository import GenerationRepository
from app.repositories.learning_session_repository import LearningSessionRepository
from app.models.entities import KnowledgePoint, LearningExample, LearningLevel


def run():
    db: Session = SessionLocal()
    sid = None
    try:
        session_repo = LearningSessionRepository(db)
        gen_repo = GenerationRepository(db)

        session = session_repo.create(
            tech_name="__test_resume__",
            user_level="beginner",
            learning_goal="test resume logic",
        )
        sid = session.id

        kp1 = KnowledgePoint(
            session_id=sid, tech_name="__test_resume__",
            title="Point 1", goal="goal1", category="must_learn",
            difficulty="easy", reason="reason1", sort_order=1,
        )
        kp2 = KnowledgePoint(
            session_id=sid, tech_name="__test_resume__",
            title="Point 2", goal="goal2", category="must_learn",
            difficulty="easy", reason="reason2", sort_order=2,
        )
        db.add_all([kp1, kp2])
        db.commit()
        db.refresh(kp1)
        db.refresh(kp2)

        # Test 1: point1 has example, point2 does not
        ex1 = LearningExample(
            session_id=sid, knowledge_point_id=kp1.id,
            official_example="existing", beginner_example="existing",
            baseline_example="existing", target_example="existing",
        )
        db.add(ex1)
        db.commit()

        kp1_ex = gen_repo.list_examples_by_knowledge_point(kp1.id)
        kp2_ex = gen_repo.list_examples_by_knowledge_point(kp2.id)
        assert len(kp1_ex) == 1, f"kp1 should have 1 example, got {len(kp1_ex)}"
        assert len(kp2_ex) == 0, f"kp2 should have 0 examples, got {len(kp2_ex)}"
        print("  PASS: Test 1 - per-point example check (kp1 has, kp2 missing)")

        # Test 2: kp1 has observe, missing hands_on/summary
        lv1 = LearningLevel(
            session_id=sid, knowledge_point_id=kp1.id,
            level_type="observe", title="Observe",
            task="task", hint="hint", sort_order=1,
        )
        db.add(lv1)
        db.commit()

        kp1_levels = gen_repo.list_levels_by_knowledge_point(kp1.id)
        kp1_types = {lv.level_type for lv in kp1_levels}
        assert "observe" in kp1_types, "kp1 should have observe"
        assert "hands_on" not in kp1_types, "kp1 missing hands_on should be detected"
        assert "summary" not in kp1_types, "kp1 missing summary should be detected"

        kp2_levels = gen_repo.list_levels_by_knowledge_point(kp2.id)
        assert len(kp2_levels) == 0, "kp2 should have 0 levels"
        print("  PASS: Test 2 - per-type level check (kp1 has observe, missing 2 types)")

        # Test 3: all exist -> should detect completeness
        lv2 = LearningLevel(
            session_id=sid, knowledge_point_id=kp1.id,
            level_type="hands_on", title="HandsOn",
            task="task", hint="hint", sort_order=2,
        )
        lv3 = LearningLevel(
            session_id=sid, knowledge_point_id=kp1.id,
            level_type="summary", title="Summary",
            task="task", hint="hint", sort_order=3,
        )
        db.add_all([lv2, lv3])
        db.commit()

        kp1_levels2 = gen_repo.list_levels_by_knowledge_point(kp1.id)
        kp1_types2 = {lv.level_type for lv in kp1_levels2}
        assert kp1_types2 == {"observe", "hands_on", "summary"}, f"kp1 should have all 3 types, got {kp1_types2}"
        print("  PASS: Test 3 - complete levels detected (no regeneration needed)")

        print("\n  Result: 3/3 passed")
    finally:
        if sid is not None:
            db.execute(text("DELETE FROM learning_examples WHERE session_id = :sid"), {"sid": sid})
            db.execute(text("DELETE FROM learning_levels WHERE session_id = :sid"), {"sid": sid})
            db.execute(text("DELETE FROM knowledge_points WHERE session_id = :sid"), {"sid": sid})
            db.execute(text("DELETE FROM learning_sessions WHERE id = :sid"), {"sid": sid})
            db.commit()
        db.close()


if __name__ == "__main__":
    run()
