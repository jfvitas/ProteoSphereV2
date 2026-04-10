import json
from pathlib import Path

seed_tasks = [
    {"id":"P1-T001","title":"Implement minimum RCSB connector for locked baseline","type":"coding","phase":1,"files":["connectors/rcsb/","tests/unit/connectors/test_rcsb.py"],"dependencies":[],"status":"pending","success_criteria":["baseline structure retrieval works","unit tests pass"],"priority":"high"},
    {"id":"P1-T002","title":"Implement minimum UniProt connector for locked baseline","type":"coding","phase":1,"files":["connectors/uniprot/","tests/unit/connectors/test_uniprot.py"],"dependencies":[],"status":"pending","success_criteria":["canonical sequence retrieval works","unit tests pass"],"priority":"high"},
    {"id":"P1-T003","title":"Implement minimum BindingDB connector for locked baseline","type":"coding","phase":1,"files":["connectors/bindingdb/","tests/unit/connectors/test_bindingdb.py"],"dependencies":[],"status":"pending","success_criteria":["baseline assay retrieval works","unit tests pass"],"priority":"high"},
    {"id":"P3-A001","title":"Analyze RCSB source content and compatibility","type":"data_analysis","phase":3,"files":["artifacts/reports/"],"dependencies":[],"status":"pending","success_criteria":["source report written"],"priority":"medium"}
]
Path("tasks/task_queue.json").write_text(json.dumps(seed_tasks, indent=2), encoding="utf-8")
print(f"Seeded {len(seed_tasks)} tasks.")
