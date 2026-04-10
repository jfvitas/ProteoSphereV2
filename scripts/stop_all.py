from __future__ import annotations

from pathlib import Path


def main() -> None:
    Path("artifacts/status").mkdir(parents=True, exist_ok=True)
    Path("artifacts/status/STOP").write_text("stop\n", encoding="utf-8")
    print("Stop signal written.")


if __name__ == "__main__":
    main()
