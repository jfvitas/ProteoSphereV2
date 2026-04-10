from pathlib import Path

from scripts.stop_all import main


def test_stop_signal_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main()
    assert Path("artifacts/status/STOP").exists()
