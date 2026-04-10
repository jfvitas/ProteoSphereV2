import os, subprocess, time
from pathlib import Path

CODEX_CMD = os.environ.get("CODEX_CMD", "codex")
POLL_SECONDS = int(os.environ.get("REVIEW_POLL_SECONDS", "180"))
Path("artifacts/reviews").mkdir(parents=True, exist_ok=True)

PROMPT = """
You are the reviewer.
Inspect the repository state and write a concise review report under artifacts/reviews/.
Check:
- spec compliance
- tests
- shortcuts
- provenance/canonical correctness
- branch hygiene
Do not write production code.
"""

while True:
    out = Path("artifacts/reviews") / f"review_{int(time.time())}.md"
    with open(out, "w", encoding="utf-8") as f:
        subprocess.run([CODEX_CMD, PROMPT], stdout=f, stderr=subprocess.STDOUT)
    time.sleep(POLL_SECONDS)
