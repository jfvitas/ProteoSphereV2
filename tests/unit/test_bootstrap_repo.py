from pathlib import Path

from scripts.bootstrap_repo import main


def test_bootstrap_creates_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main()
    assert Path("tasks/task_queue.json").exists()
    assert Path("artifacts/status/orchestrator_state.json").exists()
