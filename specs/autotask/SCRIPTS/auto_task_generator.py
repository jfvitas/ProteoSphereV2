import os, json, subprocess, time, re
from pathlib import Path

CODEX_CMD = os.environ.get("CODEX_CMD", "codex")
TASK_REPLENISH_THRESHOLD = int(os.environ.get("TASK_REPLENISH_THRESHOLD", "12"))
TASK_BATCH_GENERATION_SIZE = int(os.environ.get("TASK_BATCH_GENERATION_SIZE", "25"))
QUEUE_PATH = Path("tasks/task_queue.json")
OUT_DIR = Path("artifacts/planner")
OUT_DIR.mkdir(parents=True, exist_ok=True)
PLANNER_PROMPT_PATH = Path("PROMPTS/AUTO_TASK_PLANNER_PROMPT.md")

def load_queue():
    if QUEUE_PATH.exists():
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    return []

def save_queue(queue):
    QUEUE_PATH.write_text(json.dumps(queue, indent=2), encoding="utf-8")

def queue_needs_replenish(queue):
    pending = sum(1 for t in queue if t.get("status") == "pending")
    return pending < TASK_REPLENISH_THRESHOLD

def existing_ids(queue):
    return {t["id"] for t in queue}

def build_context(queue):
    pending = [t for t in queue if t.get("status") == "pending"]
    blocked = [t for t in queue if t.get("status") == "blocked"]
    failed = [t for t in queue if t.get("status") == "failed"]
    done = [t for t in queue if t.get("status") == "done"]
    return json.dumps({
        "counts": {"pending": len(pending), "blocked": len(blocked), "failed": len(failed), "done": len(done)},
        "sample_pending": pending[:10],
        "sample_blocked": blocked[:10],
        "sample_failed": failed[:10],
    }, indent=2)

def call_codex_for_tasks(context_json):
    planner_prompt = PLANNER_PROMPT_PATH.read_text(encoding="utf-8")
    prompt = f"""{planner_prompt}

Generate {TASK_BATCH_GENERATION_SIZE} new tasks as a JSON array.
Each task object must contain:
- id
- title
- type
- phase
- files
- dependencies
- status
- success_criteria
- priority

Current context:
{context_json}

Output ONLY valid JSON.
"""
    out_file = OUT_DIR / f"planner_batch_{int(time.time())}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        subprocess.run([CODEX_CMD, prompt], stdout=f, stderr=subprocess.STDOUT)
    return out_file

def extract_json_array(text):
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return text
    m = re.search(r"(\[.*\])", text, flags=re.DOTALL)
    if m:
        return m.group(1)
    raise ValueError("No JSON array found")

def main():
    queue = load_queue()
    if not queue_needs_replenish(queue):
        print("Queue healthy; no replenishment needed.")
        return
    raw = call_codex_for_tasks(build_context(queue)).read_text(encoding="utf-8")
    arr = json.loads(extract_json_array(raw))
    ids = existing_ids(queue)
    added = 0
    for task in arr:
        if task["id"] in ids:
            continue
        task.setdefault("status", "pending")
        queue.append(task)
        ids.add(task["id"])
        added += 1
    save_queue(queue)
    print(f"Added {added} new tasks.")

if __name__ == "__main__":
    main()
