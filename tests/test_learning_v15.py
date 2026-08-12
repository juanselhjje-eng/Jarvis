from pathlib import Path
from memory.learning import LearningEngine


def main():
    db = Path(__file__).with_name("_v15_learning_test.db")
    if db.exists():
        db.unlink()
    engine = LearningEngine(db)
    engine.record_failure("abre unity", "open_application", "No encontré Unity")
    engine.record_recovery(
        "abre unity",
        "open_application",
        "No encontré Unity",
        "open_workspace",
        "Workspace abierto",
    )
    stats = engine.stats()
    assert stats["errors"] == 1
    assert stats["successes"] == 1
    assert stats["nodes"] >= 3
    context = engine.context("abre unity")
    assert "RECUPERACIÓN" in context
    db.unlink()
    print("V15 LEARNING TEST: OK")


if __name__ == "__main__":
    main()
